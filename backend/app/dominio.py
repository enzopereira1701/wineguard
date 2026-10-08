"""
Regras do WineGuard que NÃO dependem de rede nem do FastAPI.

Ficam separadas das rotas para poderem ser testadas sozinhas (veja tests/).
Aqui: validar o id do dispositivo, montar a janela de tempo do histórico,
transformar a resposta do STH-Comet em pontos e montar a resposta "atual".
"""

import re
import unicodedata
from datetime import datetime, timedelta, timezone

VARIAVEIS = ("temperature", "humidity", "luminosity")

_ID_DISPOSITIVO = re.compile(r"^wgn\d{3,}$")

# periodo pedido pelo dashboard -> (tamanho da janela, agrupamento no STH-Comet)
# O STH-Comet agrupa por minuto ou hora; cada ponto é a média do grupo.
PERIODOS = {
    "1h": (timedelta(hours=1), "minute"),    # até 60 pontos
    "24h": (timedelta(hours=24), "hour"),    # até 24 pontos
    "7d": (timedelta(days=7), "hour"),       # até 168 pontos
}

_SEGUNDOS_POR_UNIDADE = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def entidade_do_dispositivo(device_id: str) -> str:
    """wgn001 -> urn:ngsi-ld:WineGuardNode:001 (padrão definido no cadastro)."""
    if not _ID_DISPOSITIVO.match(device_id):
        raise ValueError("device_id inválido (use o formato wgn001)")
    return f"urn:ngsi-ld:WineGuardNode:{device_id[3:]}"


# ------------------------------------------------------------------- datas
def para_iso(momento: datetime) -> str:
    """datetime -> '2026-10-07T12:00:00.000Z' (formato que o dashboard e o STH-Comet usam)."""
    u = momento.astimezone(timezone.utc)
    return u.strftime("%Y-%m-%dT%H:%M:%S.") + f"{u.microsecond // 1000:03d}Z"


def ler_iso(texto: str) -> datetime:
    """'2026-10-07T12:00:00.00Z' (também sem fração ou com +00:00) -> datetime com fuso UTC."""
    t = texto.strip().replace("Z", "+00:00")
    # Python antigo só aceita fração com 3 ou 6 dígitos: normaliza para 6
    t = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), t)
    momento = datetime.fromisoformat(t)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def janela(periodo: str, agora: datetime):
    """Devolve (inicio, fim, agrupamento) para '1h', '24h' ou '7d'."""
    if periodo not in PERIODOS:
        raise ValueError("periodo inválido (use 1h, 24h ou 7d)")
    tamanho, agrupamento = PERIODOS[periodo]
    return agora - tamanho, agora, agrupamento


# --------------------------------------------------------------- histórico
def pontos_do_sth(resposta: dict, inicio: datetime, fim: datetime) -> list:
    """
    Resposta agregada do STH-Comet (aggrMethod=sum) -> [{"t": ISO, "v": média}], em ordem de tempo.

    Cada bloco tem uma origem (início da hora ou do dia) e pontos com 'offset' (minuto ou hora dentro
    da origem), 'samples' (quantas leituras) e 'sum' (soma). A média é sum / samples.
    """
    try:
        blocos = resposta["contextResponses"][0]["contextElement"]["attributes"][0]["values"]
    except (KeyError, IndexError, TypeError):
        return []

    pontos = {}
    for bloco in blocos:
        origem = ler_iso(bloco["_id"]["origin"])
        passo = _SEGUNDOS_POR_UNIDADE.get(bloco["_id"].get("resolution", "minute"), 60)
        for p in bloco.get("points", []):
            if not p.get("samples"):
                continue
            quando = origem + timedelta(seconds=p["offset"] * passo)
            if quando < inicio - timedelta(seconds=passo) or quando > fim:
                continue  # o primeiro grupo pode começar um pouco antes do início pedido
            pontos[quando] = round(p["sum"] / p["samples"], 2)
    return [{"t": para_iso(q), "v": v} for q, v in sorted(pontos.items())]


# ------------------------------------------------------------------- atual
def _valor(entidade: dict, nome: str):
    atributo = entidade.get(nome)
    return atributo.get("value") if isinstance(atributo, dict) else None


def _modificado_em(entidade: dict):
    """
    Quando a leitura chegou.

    O Orion só muda o dateModified de uma variável quando o VALOR muda: com a leitura parada
    (simulador, adega estável) ele fica velho e o Node pareceria offline. Por isso vale o
    TimeInstant, que o IoT Agent grava a cada mensagem recebida. O dateModified das 3 variáveis
    fica de reserva (vale o mais recente dos dois).
    """
    datas = []
    instante = entidade.get("TimeInstant")
    if isinstance(instante, dict) and instante.get("value"):
        try:
            datas.append(ler_iso(instante["value"]))
        except ValueError:
            pass
    for nome in VARIAVEIS:
        atributo = entidade.get(nome)
        if isinstance(atributo, dict):
            meta = atributo.get("metadata", {}).get("dateModified", {})
            if meta.get("value"):
                datas.append(ler_iso(meta["value"]))
    return max(datas) if datas else None


def montar_atual(device_id: str, entidade, agora: datetime, offline_segundos: int = 30) -> dict:
    """
    Entidade do Orion (formato normalizado, com metadata dateModified) -> resposta de /atual.
    'entidade' é None quando o Orion não conhece o dispositivo (nunca enviou nada).

    estado: ok | alerta | offline | suspenso | aguardando
    """
    leituras = {v: (_valor(entidade, v) if entidade else None) for v in VARIAVEIS}
    ultima = _modificado_em(entidade) if entidade else None

    if ultima is None or all(x is None for x in leituras.values()):
        return {
            "deviceId": device_id, "estado": "aguardando", "state": None, "muted": 0, "firmware": None,
            **{v: None for v in VARIAVEIS}, "online": False, "rssi": None, "ultimaLeitura": None,
        }

    online = (agora - ultima).total_seconds() <= offline_segundos
    state = _valor(entidade, "state")
    if state == "suspenso":
        estado = "suspenso"
    elif not online:
        estado = "offline"
    elif state == "alerta":
        estado = "alerta"
    else:
        estado = "ok"

    return {
        "deviceId": device_id,
        "estado": estado,
        "state": state,
        "muted": int(_valor(entidade, "muted") or 0),
        "firmware": _valor(entidade, "firmware"),
        **leituras,
        "online": online,
        "rssi": _valor(entidade, "rssi"),
        "ultimaLeitura": para_iso(ultima),
    }


# ================================================================ cadastro
# (Backend 2) Regras para cadastrar, listar e resumir dispositivos. Também sem rede.
TIPO_ENTIDADE = "WineGuardNode"
PRESETS = ("guarda_geral", "longa_guarda", "espumante")
COMANDOS_DO_NODE = ("setTriggers", "alert", "mute", "suspend", "resume", "setInterval", "identify")
DESCRICAO_ASSINATURA = "Historico WineGuard no STH-Comet"

# Ultralight do Node: object_id -> (nome do atributo no Orion, tipo)
ATRIBUTOS_DO_NODE = (
    ("t", "temperature", "Number"), ("h", "humidity", "Number"), ("l", "luminosity", "Number"),
    ("st", "state", "Text"), ("mu", "muted", "Number"), ("rs", "rssi", "Number"), ("fw", "firmware", "Text"),
)

_ENTIDADE = re.compile(r"^urn:ngsi-ld:WineGuardNode:(\d{3,})$")
_SLUG = re.compile(r"^[a-z0-9_]{1,30}$")


def device_id_da_entidade(entidade_id):
    """
    urn:ngsi-ld:WineGuardNode:002 -> 'wgn002'.
    Devolve None para o que não é um dispositivo nosso (ex.: a entidade-fantasma 'WineGuardNode:wgn001'
    que o IoT Agent cria quando recebe dados de um device sem entity_name).
    """
    achou = _ENTIDADE.match(entidade_id or "")
    return f"wgn{achou.group(1)}" if achou else None


def device_id_do_numero(numero: int) -> str:
    return f"wgn{numero:03d}"


def proximo_numero(device_ids, minimo: int = 1) -> int:
    """Menor número seguro: maior já usado + 1 (nunca menor que 'minimo')."""
    usados = [int(d[3:]) for d in device_ids if d and _ID_DISPOSITIVO.match(d)]
    return max([minimo - 1, *usados]) + 1


# ------------------------------------------------------------------ adegas
def servicepath_da_nova_adega(nome: str) -> str:
    """'Adega do Porão' -> '/adega_do_porao'. O Orion só aceita letras, números e _ no servicepath."""
    texto = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")[:30].strip("_")
    if not slug:
        raise ValueError("nome da adega inválido (use letras ou números)")
    return "/" + slug


def adega_id(vinheria_id: str, servicepath: str) -> str:
    """('vin_demo', '/adega1') -> 'vin_demo/adega1' (formato do contrato)."""
    return f"{vinheria_id}{servicepath}"


def servicepath_da_adega(id_adega: str, vinheria_id: str) -> str:
    """'vin_demo/adega1' -> '/adega1'. Recusa adega de outra vinheria."""
    prefixo = vinheria_id + "/"
    if not isinstance(id_adega, str) or not id_adega.startswith(prefixo) or not _SLUG.match(id_adega[len(prefixo):]):
        raise ValueError("adegaId inválido (use o formato vinheria/adega, da mesma vinheria)")
    return "/" + id_adega[len(prefixo):]


def nome_da_adega(servicepath: str) -> str:
    """'/adega1' -> 'Adega 1' (nome de reserva quando não há nome gravado)."""
    texto = servicepath.strip("/").replace("_", " ")
    return re.sub(r"(?<=[A-Za-z])(?=\d)", " ", texto).title()


# ---------------------------------------------------------------- cadastro
def validar_cadastro(corpo) -> dict:
    """Valida o corpo do POST de dispositivos. Devolve {nome, preset, adegaId, novaAdega} limpo."""
    if not isinstance(corpo, dict):
        raise ValueError("corpo inválido")
    nome = str(corpo.get("nome") or "").strip()
    if not 1 <= len(nome) <= 60:
        raise ValueError("nome do dispositivo deve ter de 1 a 60 caracteres")
    preset = corpo.get("preset") or "guarda_geral"
    if preset not in PRESETS:
        raise ValueError(f"preset inválido. Use: {', '.join(PRESETS)}")
    id_adega = str(corpo.get("adegaId") or "").strip() or None
    nova = str(corpo.get("novaAdega") or "").strip() or None
    if bool(id_adega) == bool(nova):
        raise ValueError("informe adegaId (adega existente) OU novaAdega (nome), não os dois nem nenhum")
    if nova and len(nova) > 60:
        raise ValueError("nome da adega deve ter até 60 caracteres")
    return {"nome": nome, "preset": preset, "adegaId": id_adega, "novaAdega": nova}


def validar_nome(nome) -> str:
    nome = str(nome or "").strip()
    if not 1 <= len(nome) <= 60:
        raise ValueError("nome do dispositivo deve ter de 1 a 60 caracteres")
    return nome


# --------------------------------------------------- corpos para o FIWARE
def corpo_grupo(apikey: str, cbroker: str) -> dict:
    return {"services": [{"apikey": apikey, "cbroker": cbroker, "entity_type": TIPO_ENTIDADE, "resource": "/iot/d"}]}


def corpo_dispositivo(device_id: str, apikey: str, entity_name: str) -> dict:
    return {"devices": [{
        "device_id": device_id, "apikey": apikey, "entity_name": entity_name, "entity_type": TIPO_ENTIDADE,
        "protocol": "PDI-IoTA-UltraLight", "transport": "MQTT",
        "attributes": [{"object_id": o, "name": n, "type": t} for o, n, t in ATRIBUTOS_DO_NODE],
        "commands": [{"name": c, "type": "command"} for c in COMANDOS_DO_NODE],
    }]}


def corpo_assinatura(url_sth: str) -> dict:
    """
    Assinatura que manda o histórico ao STH-Comet. O TimeInstant entra na CONDIÇÃO (não nos atributos
    enviados): ele muda a cada mensagem, então o Orion notifica a cada leitura mesmo com o valor parado.
    """
    return {
        "description": DESCRICAO_ASSINATURA,
        "subject": {
            "entities": [{"idPattern": ".*", "type": TIPO_ENTIDADE}],
            "condition": {"attrs": [*VARIAVEIS, "TimeInstant"]},
        },
        "notification": {"http": {"url": url_sth}, "attrs": list(VARIAVEIS), "attrsFormat": "legacy"},
    }


def assinatura_precisa_atualizar(assinatura: dict) -> bool:
    """True para assinaturas antigas (criadas sem TimeInstant na condição)."""
    try:
        return "TimeInstant" not in assinatura["subject"]["condition"]["attrs"]
    except (KeyError, TypeError):
        return True


def metadados_do_dispositivo(nome: str, preset: str, id_adega: str, nome_adega: str, criado_em: str) -> dict:
    """Atributos extras gravados na entidade do Orion (é onde ficam nome, preset e adega)."""
    return {
        "nome": {"type": "Text", "value": nome},
        "preset": {"type": "Text", "value": preset},
        "adegaId": {"type": "Text", "value": id_adega},
        "adegaNome": {"type": "Text", "value": nome_adega},
        "criadoEm": {"type": "DateTime", "value": criado_em},
    }


# ----------------------------------------------------------- respostas
def servicepath_do_dispositivo(entidade, vinheria_id: str):
    """Servicepath gravado na entidade (via adegaId), ou None se ela não tem (ex.: wgn001 antigo)."""
    id_adega = _valor(entidade, "adegaId") if entidade else None
    if not id_adega:
        return None
    try:
        return servicepath_da_adega(id_adega, vinheria_id)
    except ValueError:
        return None


def montar_dispositivo(vinheria_id: str, entidade: dict, servicepath_padrao: str) -> dict:
    """Entidade do Orion -> {id, vinheriaId, adegaId, nome, preset, criadoEm} do contrato."""
    device_id = device_id_da_entidade(entidade["id"])
    criado = _valor(entidade, "criadoEm") or _valor(entidade, "dateCreated")
    return {
        "id": device_id,
        "vinheriaId": vinheria_id,
        "adegaId": _valor(entidade, "adegaId") or adega_id(vinheria_id, servicepath_padrao),
        "nome": _valor(entidade, "nome") or f"Dispositivo {device_id[3:]}",
        "preset": _valor(entidade, "preset") or "guarda_geral",
        "criadoEm": criado,
    }


def montar_resumo_item(atual: dict) -> dict:
    """
    Item de GET /vinherias/{id}/resumo a partir do resultado de montar_atual.
    alertasAtivos começa em 0; cadastro.resumo o substitui pela contagem real de alertas em andamento.
    """
    return {
        "deviceId": atual["deviceId"],
        "estado": atual["estado"],
        "ultimaLeitura": atual["ultimaLeitura"],
        "alertasAtivos": 0,
    }
