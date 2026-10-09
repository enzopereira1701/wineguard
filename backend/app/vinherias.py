"""
Vinherias e adegas (Backend 4): ficam como entidades no Orion, sem banco de dados.

- 'Vinheria' no service de administração (ADMIN_SERVICE): nome, apikey, vencimento, status, suspensaEm.
- 'Adega' no service da própria vinheria, servicepath '/': nome e servicepath.
A vinheria padrão (FIWARE_SERVICE, 'vin_demo') nasce sozinha no primeiro uso, com a 'Adega 1'.

Suspensa (inadimplência ou botão): os Nodes recebem 'suspend', e a API recusa as consultas da vinheria
(403) até reativar. O histórico no STH-Comet é preservado.
"""

import secrets
from datetime import datetime, timedelta, timezone

from . import config, dominio, fiware, regras_vinheria as regras

TIPO = "Vinheria"
TIPO_ADEGA = "Adega"
SERVICEPATH = "/"
ATRIBUTOS = "nome,apikey,vencimento,status,suspensaEm,criadaEm"


class VinheriaDesconhecida(Exception):
    pass


class VinheriaSuspensa(Exception):
    pass


async def _entidade(cliente, vinheria_id: str):
    return await fiware.obter_atributos(cliente, regras.entidade_da_vinheria(vinheria_id), ATRIBUTOS,
                                        config.ADMIN_SERVICE, SERVICEPATH, TIPO)


async def garantir_padrao(cliente, agora=None):
    """Cria a vinheria padrão e a adega padrão se ainda não existem."""
    agora = agora or datetime.now(timezone.utc)
    vencimento = agora + timedelta(days=config.VENCIMENTO_PADRAO_DIAS)
    corpo = regras.corpo_vinheria(config.NOME_VINHERIA, config.APIKEY, vencimento, agora)
    try:
        await fiware.criar_entidade(cliente, config.ADMIN_SERVICE, SERVICEPATH,
                                    regras.entidade_da_vinheria(config.FIWARE_SERVICE), TIPO, corpo)
    except fiware.FiwareIndisponivel:
        if await _entidade(cliente, config.FIWARE_SERVICE) is None:  # não foi corrida: o erro é de verdade
            raise
        return
    await garantir_adega(cliente, config.FIWARE_SERVICE, config.FIWARE_SERVICEPATH, "Adega 1")


async def exigir(cliente, vinheria_id: str, permitir_suspensa: bool = False, agora=None,
                 verificar_vencimento: bool = True) -> dict:
    """
    A vinheria (sem a contagem de dispositivos). VinheriaDesconhecida se não existe;
    VinheriaSuspensa se está suspensa, ou se o vencimento passou (nesse caso suspende na hora).
    """
    if not regras.id_valido(vinheria_id):
        raise VinheriaDesconhecida(vinheria_id)
    entidade = await _entidade(cliente, vinheria_id)
    if entidade is None and vinheria_id == config.FIWARE_SERVICE:
        await garantir_padrao(cliente, agora)
        entidade = await _entidade(cliente, vinheria_id)
    if entidade is None:
        raise VinheriaDesconhecida(vinheria_id)
    vinheria = regras.montar_vinheria(entidade)
    agora = agora or datetime.now(timezone.utc)
    if verificar_vencimento and vinheria["status"] == "ativa" and regras.vencida(vinheria, agora):
        vinheria = await suspender(cliente, vinheria_id, agora)
    if vinheria["status"] == "suspensa" and not permitir_suspensa:
        raise VinheriaSuspensa(vinheria_id)
    return vinheria


async def listar(cliente, agora=None, contar: bool = True) -> list:
    """Todas as vinherias (com a contagem de dispositivos). Suspende as que passaram do vencimento."""
    agora = agora or datetime.now(timezone.utc)
    entidades = await fiware.listar_entidades(cliente, config.ADMIN_SERVICE, SERVICEPATH, tipo=TIPO, attrs=ATRIBUTOS)
    if not any(regras.id_da_entidade(e["id"]) == config.FIWARE_SERVICE for e in entidades):
        await garantir_padrao(cliente, agora)
        entidades = await fiware.listar_entidades(cliente, config.ADMIN_SERVICE, SERVICEPATH, tipo=TIPO,
                                                   attrs=ATRIBUTOS)
    itens = []
    for e in entidades:
        vinheria = regras.montar_vinheria(e)
        vinheria["criadaEm"] = dominio._valor(e, "criadaEm")
        if vinheria["status"] == "ativa" and regras.vencida(vinheria, agora):
            vinheria = {**await suspender(cliente, vinheria["id"], agora), "criadaEm": vinheria["criadaEm"]}
        if contar:
            vinheria["dispositivos"] = len(dominio.so_dispositivos(
                await fiware.listar_entidades(cliente, vinheria["id"])))
        itens.append(vinheria)
    return [{k: v for k, v in i.items() if k != "criadaEm"} for i in regras.ordenar(itens)]


async def criar(cliente, corpo: dict, agora: datetime) -> dict:
    """Cria a vinheria com a apikey dela e a 'Adega 1'. Os dispositivos entram pelo cadastro de dispositivos."""
    dados = regras.validar_nova_vinheria(corpo)
    existentes = {v["id"] for v in await listar(cliente, agora, contar=False)}
    vinheria_id = regras.id_da_vinheria(dados["nome"], existentes)
    apikey = regras.gerar_apikey(dados["nome"], secrets.token_hex(2))
    vencimento = dados["vencimento"] or agora + timedelta(days=config.VENCIMENTO_PADRAO_DIAS)
    atributos = regras.corpo_vinheria(dados["nome"], apikey, vencimento, agora)
    entidade = regras.entidade_da_vinheria(vinheria_id)
    await fiware.criar_entidade(cliente, config.ADMIN_SERVICE, SERVICEPATH, entidade, TIPO, atributos)
    await garantir_adega(cliente, vinheria_id, "/adega1", "Adega 1")
    return regras.montar_vinheria({"id": entidade, **atributos}, 0)


async def _comandar_todos(cliente, vinheria_id: str, comando: str):
    """Manda o comando a todos os Nodes da vinheria. Falha de um não impede os outros."""
    for device_id, entidade in dominio.so_dispositivos(await fiware.listar_entidades(cliente, vinheria_id)):
        servicepath = dominio.servicepath_do_dispositivo(entidade, vinheria_id) or config.FIWARE_SERVICEPATH
        try:
            await fiware.enviar_comando(cliente, dominio.entidade_do_dispositivo(device_id), comando, "",
                                        vinheria_id, servicepath)
        except fiware.FiwareIndisponivel:
            pass  # offline agora: o vigia reenvia o 'suspend' quando ele voltar


async def _gravar(cliente, vinheria_id: str, atributos: dict):
    await fiware.gravar_metadados(cliente, config.ADMIN_SERVICE, SERVICEPATH,
                                  regras.entidade_da_vinheria(vinheria_id), atributos, tipo=TIPO, criar=False)


async def suspender(cliente, vinheria_id: str, agora=None) -> dict:
    """Suspende a vinheria e manda 'suspend' aos Nodes. Se já está suspensa, não muda nada."""
    agora = agora or datetime.now(timezone.utc)
    vinheria = await exigir(cliente, vinheria_id, permitir_suspensa=True, agora=agora, verificar_vencimento=False)
    if vinheria["status"] == "suspensa":
        return vinheria
    await _gravar(cliente, vinheria_id, {
        "status": {"type": "Text", "value": "suspensa"},
        "suspensaEm": {"type": "DateTime", "value": dominio.para_iso(agora)},
    })
    await _comandar_todos(cliente, vinheria_id, "suspend")
    return {**vinheria, "status": "suspensa", "suspensaEm": dominio.para_iso(agora)}


async def reativar(cliente, vinheria_id: str, agora=None) -> dict:
    """Reativa: renova o vencimento por 30 dias se já passou e manda 'resume' aos Nodes."""
    agora = agora or datetime.now(timezone.utc)
    vinheria = await exigir(cliente, vinheria_id, permitir_suspensa=True, agora=agora, verificar_vencimento=False)
    vencimento = regras.renovar_vencimento(dominio.ler_iso(vinheria["vencimento"]), agora)
    await _gravar(cliente, vinheria_id, {
        "status": {"type": "Text", "value": "ativa"},
        "vencimento": {"type": "DateTime", "value": dominio.para_iso(vencimento)},
    })
    await fiware.apagar_atributo(cliente, config.ADMIN_SERVICE, SERVICEPATH,
                                 regras.entidade_da_vinheria(vinheria_id), "suspensaEm", TIPO)
    await _comandar_todos(cliente, vinheria_id, "resume")
    return {**vinheria, "status": "ativa", "vencimento": dominio.para_iso(vencimento), "suspensaEm": None}


async def simular_inadimplencia(cliente, vinheria_id: str, agora=None) -> dict:
    """Para a demonstração: vencimento = ontem e suspende."""
    agora = agora or datetime.now(timezone.utc)
    await exigir(cliente, vinheria_id, permitir_suspensa=True, agora=agora, verificar_vencimento=False)
    await _gravar(cliente, vinheria_id, {
        "vencimento": {"type": "DateTime", "value": dominio.para_iso(regras.vencimento_de_ontem(agora))}})
    return await suspender(cliente, vinheria_id, agora)


# ------------------------------------------------------------------ adegas
async def garantir_adega(cliente, vinheria_id: str, servicepath: str, nome: str):
    """Cria a adega (ou a atualiza, se já existe)."""
    await fiware.gravar_metadados(cliente, vinheria_id, SERVICEPATH, regras.entidade_da_adega(servicepath),
                                  regras.corpo_adega(nome, servicepath), tipo=TIPO_ADEGA)


async def obter_adega(cliente, vinheria_id: str, servicepath: str):
    """Entidade da adega, ou None."""
    return await fiware.obter_atributos(cliente, regras.entidade_da_adega(servicepath), "nome,servicepath",
                                        vinheria_id, SERVICEPATH, TIPO_ADEGA)


async def listar_adegas(cliente, vinheria_id: str) -> list:
    entidades = await fiware.listar_entidades(cliente, vinheria_id, SERVICEPATH, tipo=TIPO_ADEGA,
                                              attrs="nome,servicepath")
    return sorted((regras.montar_adega(vinheria_id, e) for e in entidades), key=lambda a: a["id"])
