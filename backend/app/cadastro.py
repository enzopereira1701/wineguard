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

from . import alertas, config, dominio, fiware, gatilhos, vinherias


VinheriaDesconhecida = vinherias.VinheriaDesconhecida
VinheriaSuspensa = vinherias.VinheriaSuspensa


class DispositivoNaoEncontrado(Exception):
    pass


async def _apikey(cliente, vinheria_id: str) -> str:
    """apikey da vinheria. Levanta VinheriaDesconhecida (404) ou VinheriaSuspensa (403)."""
    return (await vinherias.exigir(cliente, vinheria_id))["apikey"]


so_dispositivos = dominio.so_dispositivos


async def listar(cliente, vinheria_id: str) -> list:
    await _apikey(cliente, vinheria_id)
    entidades = await fiware.listar_entidades(cliente, vinheria_id)
    return [dominio.montar_dispositivo(vinheria_id, e, config.FIWARE_SERVICEPATH) for _, e in so_dispositivos(entidades)]


async def resumo(cliente, vinheria_id: str, agora: datetime) -> list:
    """Estado de todos os dispositivos da vinheria numa chamada só."""
    await _apikey(cliente, vinheria_id)
    entidades = await fiware.listar_entidades(cliente, vinheria_id)
    ativos = gatilhos.contar_ativos(await alertas.listar(cliente, vinheria_id, "ativos"))
    itens = []
    for d, e in so_dispositivos(entidades):
        item = dominio.montar_resumo_item(dominio.montar_atual(d, e, agora, config.OFFLINE_SEGUNDOS))
        item["alertasAtivos"] = ativos.get(d, 0)
        itens.append(item)
    return itens


async def cadastrar(cliente, vinheria_id: str, corpo: dict, agora: datetime) -> dict:
    apikey = await _apikey(cliente, vinheria_id)
    dados = dominio.validar_cadastro(corpo)

    # --- qual adega?
    criar_adega = False
    if dados["novaAdega"]:
        servicepath = dominio.servicepath_da_nova_adega(dados["novaAdega"])
        if await vinherias.obter_adega(cliente, vinheria_id, servicepath) \
                or await fiware.listar_entidades(cliente, vinheria_id, servicepath):
            raise ValueError("já existe uma adega com esse nome")
        nome_adega, criar_adega = dados["novaAdega"], True
    else:
        servicepath = dominio.servicepath_da_adega(dados["adegaId"], vinheria_id)
        adega = await vinherias.obter_adega(cliente, vinheria_id, servicepath)
        if adega is not None:
            nome_adega = dominio._valor(adega, "nome") or dominio.nome_da_adega(servicepath)
        elif await fiware.listar_entidades(cliente, vinheria_id, servicepath):  # adega antiga, sem registro
            nome_adega = dominio.nome_da_adega(servicepath)
        else:
            raise ValueError("adega não encontrada")
    id_adega = dominio.adega_id(vinheria_id, servicepath)

    # --- infraestrutura da adega (idempotente)
    await fiware.garantir_grupo(cliente, vinheria_id, servicepath, apikey)
    await fiware.garantir_assinatura_sth(cliente, vinheria_id, servicepath)

    # --- device_id novo e registro COM apikey
    # o id é global: olha os dispositivos de TODAS as vinherias (o contador pode estar começando agora)
    usados = [d for d, _ in so_dispositivos(await fiware.listar_entidades(cliente, vinheria_id))]
    for v in await vinherias.listar(cliente, agora, contar=False):
        if v["id"] != vinheria_id:
            usados += [d for d, _ in so_dispositivos(await fiware.listar_entidades(cliente, v["id"]))]
    minimo = dominio.proximo_numero(usados)
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
    if criar_adega:
        await vinherias.garantir_adega(cliente, vinheria_id, servicepath, nome_adega)
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
    await _apikey(cliente, vinheria_id)
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
    await _apikey(cliente, vinheria_id)
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
