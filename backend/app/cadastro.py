"""
Cadastro de dispositivos (Backend 2): junta as regras (dominio) com as chamadas ao FIWARE (fiware).

Cadastrar um dispositivo =
  1. escolher a adega (existente, ou nova -> novo servicepath)
  2. garantir o grupo (apikey) no IoT Agent e a assinatura do STH-Comet na adega
  3. reservar um device_id novo (wgn002, wgn003...) e registrá-lo no IoT Agent COM apikey
  4. gravar nome, preset e adega na entidade do Orion
Se o passo 4 falhar, o passo 3 é desfeito (não sobra dispositivo pela metade).
"""

from datetime import datetime

from . import alertas, config, dominio, fiware, gatilhos


class VinheriaDesconhecida(Exception):
    pass


class DispositivoNaoEncontrado(Exception):
    pass


def _apikey(vinheria_id: str) -> str:
    apikey = config.apikey_da_vinheria(vinheria_id)
    if not apikey:
        raise VinheriaDesconhecida(vinheria_id)
    return apikey


def so_dispositivos(entidades):
    """Descarta o que não é WineGuardNode:NNN (ex.: entidade-fantasma do IoT Agent), em ordem de id."""
    itens = [(dominio.device_id_da_entidade(e.get("id")), e) for e in entidades]
    return sorted(((d, e) for d, e in itens if d), key=lambda par: par[0])


async def listar(cliente, vinheria_id: str) -> list:
    _apikey(vinheria_id)
    entidades = await fiware.listar_entidades(cliente, vinheria_id)
    return [dominio.montar_dispositivo(vinheria_id, e, config.FIWARE_SERVICEPATH) for _, e in so_dispositivos(entidades)]


async def resumo(cliente, vinheria_id: str, agora: datetime) -> list:
    """Estado de todos os dispositivos da vinheria numa chamada só."""
    _apikey(vinheria_id)
    entidades = await fiware.listar_entidades(cliente, vinheria_id)
    ativos = gatilhos.contar_ativos(await alertas.listar(cliente, vinheria_id, "ativos"))
    itens = []
    for d, e in so_dispositivos(entidades):
        item = dominio.montar_resumo_item(dominio.montar_atual(d, e, agora, config.OFFLINE_SEGUNDOS))
        item["alertasAtivos"] = ativos.get(d, 0)
        itens.append(item)
    return itens


async def cadastrar(cliente, vinheria_id: str, corpo: dict, agora: datetime) -> dict:
    apikey = _apikey(vinheria_id)
    dados = dominio.validar_cadastro(corpo)

    # --- qual adega?
    if dados["novaAdega"]:
        servicepath = dominio.servicepath_da_nova_adega(dados["novaAdega"])
        if await fiware.listar_entidades(cliente, vinheria_id, servicepath) or servicepath == config.FIWARE_SERVICEPATH:
            raise ValueError("já existe uma adega com esse nome")
        nome_adega = dados["novaAdega"]
    else:
        servicepath = dominio.servicepath_da_adega(dados["adegaId"], vinheria_id)
        da_adega = await fiware.listar_entidades(cliente, vinheria_id, servicepath)
        if not da_adega and servicepath != config.FIWARE_SERVICEPATH:
            raise ValueError("adega não encontrada")
        nome_adega = next((dominio._valor(e, "adegaNome") for e in da_adega if dominio._valor(e, "adegaNome")),
                          dominio.nome_da_adega(servicepath))
    id_adega = dominio.adega_id(vinheria_id, servicepath)

    # --- infraestrutura da adega (idempotente)
    await fiware.garantir_grupo(cliente, vinheria_id, servicepath, apikey)
    await fiware.garantir_assinatura_sth(cliente, vinheria_id, servicepath)

    # --- device_id novo e registro COM apikey
    todas = await fiware.listar_entidades(cliente, vinheria_id)
    minimo = dominio.proximo_numero(d for d, _ in so_dispositivos(todas))
    device_id = None
    for _ in range(5):
        numero = await fiware.reservar_numero(cliente, minimo)
        candidato = dominio.device_id_do_numero(numero)
        if await fiware.registrar_dispositivo(cliente, vinheria_id, servicepath, candidato, apikey):
            device_id = candidato
            break
        minimo = numero + 1  # id já existia no IoT Agent: tenta o seguinte
    if device_id is None:
        raise fiware.FiwareIndisponivel("não foi possível reservar um device_id livre")

    # --- nome, preset e adega ficam na entidade
    entidade_id = dominio.entidade_do_dispositivo(device_id)
    metadados = dominio.metadados_do_dispositivo(
        dados["nome"], dados["preset"], id_adega, nome_adega, dominio.para_iso(agora))
    try:
        await fiware.gravar_metadados(cliente, vinheria_id, servicepath, entidade_id, metadados)
    except fiware.FiwareIndisponivel:
        try:
            await fiware.apagar_dispositivo(cliente, vinheria_id, servicepath, device_id)
        except fiware.FiwareIndisponivel:
            pass  # o erro original é o que importa
        raise
    fiware.lembrar_servicepath(vinheria_id, device_id, servicepath)

    return {
        "dispositivo": dominio.montar_dispositivo(vinheria_id, {"id": entidade_id, **metadados}, servicepath),
        "config": {"deviceId": device_id, "apikey": apikey, "nomeVinheria": config.NOME_VINHERIA,
                   "nomeAdega": nome_adega},
    }


async def _achar(cliente, vinheria_id: str, device_id: str):
    """(entidade, servicepath) do dispositivo; entidade é None se o Orion não o conhece."""
    servicepath = await fiware.resolver_servicepath(cliente, device_id, vinheria_id)
    entidade = await fiware.obter_entidade(cliente, dominio.entidade_do_dispositivo(device_id),
                                           vinheria_id, servicepath)
    return entidade, servicepath


async def atualizar(cliente, vinheria_id: str, device_id: str, corpo: dict) -> dict:
    """Renomeia o dispositivo. Trocar de adega ainda não é suportado."""
    _apikey(vinheria_id)
    entidade_id = dominio.entidade_do_dispositivo(device_id)
    entidade, servicepath = await _achar(cliente, vinheria_id, device_id)
    if entidade is None:
        raise DispositivoNaoEncontrado(device_id)
    atual = dominio.montar_dispositivo(vinheria_id, entidade, servicepath)

    novo_adega = (corpo or {}).get("adegaId")
    if novo_adega and novo_adega != atual["adegaId"]:
        raise ValueError("mudar o dispositivo de adega ainda não é suportado")
    if "nome" not in (corpo or {}):
        raise ValueError("informe o nome")
    nome = dominio.validar_nome(corpo["nome"])

    await fiware.gravar_metadados(cliente, vinheria_id, servicepath, entidade_id,
                                  {"nome": {"type": "Text", "value": nome}})
    return {**atual, "nome": nome}


async def remover(cliente, vinheria_id: str, device_id: str) -> None:
    """
    Tira o dispositivo do IoT Agent e do Orion. Antes manda 'suspend' ao Node (se der): sem isso um Node
    ainda ligado continuaria publicando e o IoT Agent o cadastraria sozinho de novo.
    """
    _apikey(vinheria_id)
    entidade_id = dominio.entidade_do_dispositivo(device_id)
    entidade, servicepath = await _achar(cliente, vinheria_id, device_id)
    if entidade is not None:
        try:
            await fiware.enviar_comando(cliente, entidade_id, "suspend", "", vinheria_id, servicepath)
        except fiware.FiwareIndisponivel:
            pass
    apagados = await fiware.apagar_dispositivo(cliente, vinheria_id, servicepath, device_id)
    if entidade is None and apagados == 0:
        raise DispositivoNaoEncontrado(device_id)
