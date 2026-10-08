"""
Conversa com o FIWARE (Orion, STH-Comet e IoT Agent).

Por que o dashboard não chama o FIWARE direto? O FIWARE exige os headers fiware-service e
fiware-servicepath e não libera CORS para o navegador. O dashboard fala só com esta API,
e ela fala com o FIWARE.

Vinheria = fiware-service. Adega = fiware-servicepath.
"""

import asyncio
import weakref
from datetime import datetime

import httpx

from . import config, dominio
from .dominio import VARIAVEIS, para_iso


class FiwareIndisponivel(Exception):
    """Rede caiu, FIWARE fora do ar ou respondeu com erro inesperado."""


def cabecalhos(service=None, servicepath=None) -> dict:
    """Definem de qual vinheria (service) e adega (servicepath) vem o dado."""
    return {
        "fiware-service": service or config.FIWARE_SERVICE,
        "fiware-servicepath": servicepath or config.FIWARE_SERVICEPATH,
    }


async def _pedir(cliente, metodo, url, origem, service=None, servicepath=None, params=None, json=None):
    """Um pedido HTTP; falha de rede vira FiwareIndisponivel. Quem chama confere o status."""
    try:
        return await cliente.request(
            metodo, url, params=params, json=json, headers=cabecalhos(service, servicepath)
        )
    except httpx.HTTPError as exc:
        raise FiwareIndisponivel(f"{origem}: {exc}") from exc


def _erro(origem, r):
    return FiwareIndisponivel(f"{origem} respondeu {r.status_code}: {r.text[:200]}")


# ================================================================ leitura
async def obter_entidade(cliente, entidade: str, service=None, servicepath=None):
    """
    Última leitura do dispositivo no Orion. Devolve None se o Orion não conhece a entidade
    (o Node ainda nunca enviou dados).
    O TimeInstant (gravado pelo IoT Agent a cada mensagem) diz QUANDO a última leitura chegou, e é
    com ele que se sabe se o Node está online. O dateModified fica de reserva: o Orion só o muda
    quando o valor muda.
    """
    r = await _pedir(
        cliente, "GET", f"{config.ORION_URL}/v2/entities/{entidade}", "Orion", service, servicepath,
        params={
            "type": config.TIPO_ENTIDADE,
            "attrs": "temperature,humidity,luminosity,state,muted,rssi,firmware,TimeInstant",
            "metadata": "dateModified",
        },
    )
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise _erro("Orion", r)
    return r.json()


async def _historico_variavel(cliente, entidade, variavel, inicio: datetime, fim: datetime, agrupamento: str,
                              service=None, servicepath=None, metodo: str = "sum"):
    r = await _pedir(
        cliente, "GET",
        f"{config.STH_URL}/STH/v1/contextEntities/type/{config.TIPO_ENTIDADE}/id/{entidade}/attributes/{variavel}",
        "STH-Comet", service, servicepath,
        params={
            "aggrMethod": metodo,         # 'sum' (com 'samples' dá a média), 'min' ou 'max'
            "aggrPeriod": agrupamento,
            "dateFrom": para_iso(inicio),
            "dateTo": para_iso(fim),
        },
    )
    if r.status_code == 404:
        return {}  # nenhuma leitura guardada ainda
    if r.status_code != 200:
        raise _erro("STH-Comet", r)
    return r.json()


async def obter_historico(cliente, entidade: str, inicio: datetime, fim: datetime, agrupamento: str,
                          service=None, servicepath=None) -> dict:
    """As 3 variáveis de uma vez (busca em paralelo). Devolve {variavel: resposta_do_sth}."""
    respostas = await asyncio.gather(
        *[_historico_variavel(cliente, entidade, v, inicio, fim, agrupamento, service, servicepath)
          for v in VARIAVEIS]
    )
    return dict(zip(VARIAVEIS, respostas))


async def obter_extremos(cliente, entidade: str, inicio: datetime, fim: datetime, service=None, servicepath=None):
    """Mínimos e máximos da temperatura por hora, no período (para a estabilidade). Devolve (resp_min, resp_max)."""
    return tuple(await asyncio.gather(*[
        _historico_variavel(cliente, entidade, "temperature", inicio, fim, "hour", service, servicepath, metodo)
        for metodo in ("min", "max")
    ]))


async def enviar_comando(cliente, entidade: str, comando: str, valor: str, service=None, servicepath=None):
    """API -> Orion -> IoT Agent -> MQTT -> ESP32. O Node responde em cmdexe."""
    r = await _pedir(
        cliente, "PATCH", f"{config.ORION_URL}/v2/entities/{entidade}/attrs", "Orion", service, servicepath,
        params={"type": config.TIPO_ENTIDADE},
        json={comando: {"type": "command", "value": valor}},
    )
    if r.status_code not in (200, 204):
        raise _erro("Orion", r)


# ======================================================== onde mora o device
# device_id -> servicepath da adega. Só guarda o que foi descoberto (nunca o palpite padrão).
_cache_servicepath = {}


def lembrar_servicepath(service: str, device_id: str, servicepath: str):
    _cache_servicepath[(service, device_id)] = servicepath


def esquecer_servicepath(service: str, device_id: str):
    _cache_servicepath.pop((service, device_id), None)


ATRIBUTOS_LISTAGEM = ("nome,preset,adegaId,adegaNome,criadoEm,triggers,"
                      "temperature,humidity,luminosity,state,muted,rssi,firmware,TimeInstant")


async def listar_entidades(cliente, service: str, servicepath: str = "/#", entidade_id=None,
                           tipo=None, attrs=None):
    """
    Entidades da vinheria (por padrão as WineGuardNode). Com servicepath '/#' o Orion devolve as de
    TODAS as adegas.
    """
    params = {"type": tipo or config.TIPO_ENTIDADE, "limit": 1000, "attrs": attrs or ATRIBUTOS_LISTAGEM,
              "metadata": "dateModified"}
    if entidade_id:
        params["id"] = entidade_id
    r = await _pedir(cliente, "GET", f"{config.ORION_URL}/v2/entities", "Orion", service, servicepath,
                     params=params)
    if r.status_code != 200:
        raise _erro("Orion", r)
    return r.json()


async def resolver_servicepath(cliente, device_id: str, service=None) -> str:
    """
    Em qual adega (servicepath) está o dispositivo? Lê o atributo adegaId gravado no cadastro.
    Dispositivos antigos (wgn001, criado à mão) não têm: valem o servicepath padrão.
    """
    service = service or config.FIWARE_SERVICE
    guardado = _cache_servicepath.get((service, device_id))
    if guardado:
        return guardado
    achadas = await listar_entidades(cliente, service, "/#", dominio.entidade_do_dispositivo(device_id))
    if achadas:  # achou a entidade: sem adegaId (wgn001 antigo) ela está no servicepath padrão
        caminho = dominio.servicepath_do_dispositivo(achadas[0], service) or config.FIWARE_SERVICEPATH
        lembrar_servicepath(service, device_id, caminho)
        return caminho
    return config.FIWARE_SERVICEPATH  # ainda não existe: não guarda o palpite


# ============================================================== IoT Agent
async def garantir_grupo(cliente, service: str, servicepath: str, apikey: str):
    """Cria o grupo de dispositivos (apikey) da adega. Se já existe, tudo bem."""
    r = await _pedir(cliente, "POST", f"{config.IOTA_URL}/iot/services", "IoT Agent", service, servicepath,
                     json=dominio.corpo_grupo(apikey, config.CBROKER_INTERNO))
    if r.status_code not in (200, 201, 409):
        raise _erro("IoT Agent", r)


async def registrar_dispositivo(cliente, service: str, servicepath: str, device_id: str, apikey: str) -> bool:
    """Registra o device COM apikey. True se criou; False se o id já existia (409)."""
    r = await _pedir(cliente, "POST", f"{config.IOTA_URL}/iot/devices", "IoT Agent", service, servicepath,
                     json=dominio.corpo_dispositivo(device_id, apikey, dominio.entidade_do_dispositivo(device_id)))
    if r.status_code in (200, 201):
        return True
    if r.status_code == 409:
        return False
    raise _erro("IoT Agent", r)


async def apagar_dispositivo(cliente, service: str, servicepath: str, device_id: str) -> int:
    """
    Remove o device do IoT Agent (repetindo até dar 404: versões antigas deixam duplicatas) e as
    entidades dele no Orion. Devolve quantos registros do IoT Agent foram apagados.
    """
    apagados = 0
    for _ in range(10):
        r = await _pedir(cliente, "DELETE", f"{config.IOTA_URL}/iot/devices/{device_id}", "IoT Agent",
                         service, servicepath)
        if r.status_code == 404:
            break
        if r.status_code not in (200, 204):
            raise _erro("IoT Agent", r)
        apagados += 1
    for entidade in (dominio.entidade_do_dispositivo(device_id), f"{config.TIPO_ENTIDADE}:{device_id}"):
        r = await _pedir(cliente, "DELETE", f"{config.ORION_URL}/v2/entities/{entidade}", "Orion",
                         service, servicepath, params={"type": config.TIPO_ENTIDADE})
        if r.status_code not in (200, 204, 404):
            raise _erro("Orion", r)
    esquecer_servicepath(service, device_id)
    return apagados


# ================================================================== Orion
async def garantir_assinatura_sth(cliente, service: str, servicepath: str) -> str:
    """
    Garante a assinatura que alimenta o STH-Comet nesta adega (com TimeInstant na condição).
    Devolve 'criada', 'atualizada' ou 'ok'.
    """
    r = await _pedir(cliente, "GET", f"{config.ORION_URL}/v2/subscriptions", "Orion", service, servicepath,
                     params={"limit": 1000})
    if r.status_code != 200:
        raise _erro("Orion", r)
    existente = next(
        (s for s in r.json()
         if s.get("notification", {}).get("http", {}).get("url") == config.STH_NOTIFY_INTERNO), None)

    if existente is None:
        r = await _pedir(cliente, "POST", f"{config.ORION_URL}/v2/subscriptions", "Orion", service, servicepath,
                         json=dominio.corpo_assinatura(config.STH_NOTIFY_INTERNO))
        if r.status_code != 201:
            raise _erro("Orion", r)
        return "criada"
    if dominio.assinatura_precisa_atualizar(existente):
        nova = dominio.corpo_assinatura(config.STH_NOTIFY_INTERNO)
        r = await _pedir(cliente, "PATCH", f"{config.ORION_URL}/v2/subscriptions/{existente['id']}", "Orion",
                         service, servicepath, json={"subject": nova["subject"]})
        if r.status_code != 204:
            raise _erro("Orion", r)
        return "atualizada"
    return "ok"


async def gravar_metadados(cliente, service: str, servicepath: str, entidade: str, atributos: dict,
                           tipo=None, criar: bool = True):
    """
    Grava/atualiza atributos (nome, preset, triggers, adega...) na entidade. Se a entidade ainda não
    existe, cria (criar=True) ou não faz nada (criar=False).
    """
    tipo = tipo or config.TIPO_ENTIDADE
    r = await _pedir(cliente, "POST", f"{config.ORION_URL}/v2/entities/{entidade}/attrs", "Orion",
                     service, servicepath, params={"type": tipo}, json=atributos)
    if r.status_code == 404:
        if not criar:
            return
        await criar_entidade(cliente, service, servicepath, entidade, tipo, atributos)
        return
    if r.status_code not in (200, 204):
        raise _erro("Orion", r)


async def criar_entidade(cliente, service: str, servicepath: str, entidade: str, tipo: str, atributos: dict):
    r = await _pedir(cliente, "POST", f"{config.ORION_URL}/v2/entities", "Orion", service, servicepath,
                     json={"id": entidade, "type": tipo, **atributos})
    if r.status_code != 201:
        raise _erro("Orion", r)


async def apagar_atributo(cliente, service: str, servicepath: str, entidade: str, atributo: str, tipo=None):
    """Remove um atributo da entidade (se ele não existe, não faz nada)."""
    r = await _pedir(cliente, "DELETE", f"{config.ORION_URL}/v2/entities/{entidade}/attrs/{atributo}", "Orion",
                     service, servicepath, params={"type": tipo or config.TIPO_ENTIDADE})
    if r.status_code not in (200, 204, 404):
        raise _erro("Orion", r)


async def obter_atributos(cliente, entidade: str, atributos: str, service=None, servicepath=None, tipo=None):
    """Só os atributos pedidos (com dateModified). None se a entidade não existe."""
    r = await _pedir(cliente, "GET", f"{config.ORION_URL}/v2/entities/{entidade}", "Orion", service, servicepath,
                     params={"type": tipo or config.TIPO_ENTIDADE, "attrs": atributos, "metadata": "dateModified"})
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise _erro("Orion", r)
    return r.json()


# ----------------------------------------------------- contador de ids
_travas = weakref.WeakKeyDictionary()


def _trava() -> asyncio.Lock:
    """Uma trava por loop de eventos (a API roda em um processo só)."""
    return _travas.setdefault(asyncio.get_running_loop(), asyncio.Lock())


async def reservar_numero(cliente, minimo: int = 1, nome: str = "dispositivos") -> int:
    """
    Reserva o próximo número de dispositivo (wgn002 -> 2). O contador é global e só cresce, então
    um id apagado nunca é reaproveitado (o Node físico apagado não "ressuscita" em outro cadastro).
    'nome' escolhe o contador: 'dispositivos' (wgn###) ou 'alertas' (id dos alertas).
    O device_id precisa ser único no sistema todo: o MQTT identifica o Node só por apikey + device_id.
    """
    contador = f"urn:ngsi-ld:Contador:{nome}"
    async with _trava():
        r = await _pedir(cliente, "GET", f"{config.ORION_URL}/v2/entities/{contador}", "Orion",
                         config.ADMIN_SERVICE, "/", params={"type": "Contador", "attrs": "proximo"})
        if r.status_code == 200:
            numero = max(int(r.json()["proximo"]["value"]), minimo)
            gravado = await _pedir(cliente, "POST", f"{config.ORION_URL}/v2/entities/{contador}/attrs", "Orion",
                                   config.ADMIN_SERVICE, "/", params={"type": "Contador"},
                                   json={"proximo": {"type": "Integer", "value": numero + 1}})
            if gravado.status_code not in (200, 204):
                raise _erro("Orion", gravado)
        elif r.status_code == 404:
            numero = minimo
            gravado = await _pedir(cliente, "POST", f"{config.ORION_URL}/v2/entities", "Orion",
                                   config.ADMIN_SERVICE, "/",
                                   json={"id": contador, "type": "Contador",
                                         "proximo": {"type": "Integer", "value": numero + 1}})
            if gravado.status_code != 201:
                raise _erro("Orion", gravado)
        else:
            raise _erro("Orion", r)
        return numero
