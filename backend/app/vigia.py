"""
Vigia (Backend 3): a cada poucos segundos lê o Orion e avalia os triggers de cada dispositivo.

O Node só obedece (como pede o enunciado); quem decide é o backend:
  - saiu da faixa  -> abre um alerta e manda 'alert|t,high,1' ao Node
  - voltou (com histerese) -> encerra o alerta e manda 'alert|t,high,0'
  - 30 s sem leitura -> alerta 'offline' (começo e fim no histórico)
  - Node voltou ou o backend reiniciou -> reenvia os triggers e os alertas em andamento
  - o 'state' do Node diverge do esperado por mais de RECONCILIAR_SEGUNDOS -> reenvia
Alertas em andamento são lidos do Orion na primeira volta, então reiniciar a API não perde nada.
Rode a API em UM processo só (dois vigias abririam alertas duplicados).
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from . import alertas, cadastro, config, dominio, fiware, gatilhos

log = logging.getLogger("wineguard.vigia")


class EstadoVigia:
    """O que o vigia lembra entre uma volta e outra (só memória: o resto está no Orion)."""

    def __init__(self):
        self.ativos = {}           # (vinheria, device, variavel) -> {"entidade", "sentido"}
        self.carregado = set()     # vinherias cujos alertas em andamento já foram lidos
        self.ultimo_comando = {}   # (vinheria, device) -> datetime do último comando enviado
        self.online = {}           # (vinheria, device) -> True se estava ativo na volta anterior


async def _carregar(cliente, vinheria_id: str, estado: EstadoVigia):
    if vinheria_id in estado.carregado:
        return
    for a in await alertas.listar(cliente, vinheria_id, "ativos"):
        chave = (vinheria_id, a["deviceId"], a["variavel"])
        if chave not in estado.ativos:  # (a lista vem do mais novo: vale o mais novo)
            estado.ativos[chave] = {"entidade": gatilhos.entidade_do_alerta(a["id"]), "sentido": a["sentido"]}
    estado.carregado.add(vinheria_id)


async def ciclo(cliente, vinheria_id: str, agora: datetime, estado: EstadoVigia) -> list:
    """Uma volta do vigia para uma vinheria. Devolve a lista de eventos (para o log e os testes)."""
    eventos = []
    await _carregar(cliente, vinheria_id, estado)
    entidades = await fiware.listar_entidades(cliente, vinheria_id)
    presentes = set()

    async def comando(device_id, servicepath, nome, valor):
        estado.ultimo_comando[(vinheria_id, device_id)] = agora
        try:
            await fiware.enviar_comando(cliente, dominio.entidade_do_dispositivo(device_id), nome, valor,
                                        vinheria_id, servicepath)
            eventos.append(("comando", device_id, nome, valor))
        except fiware.FiwareIndisponivel as exc:
            log.warning("comando %s para %s falhou: %s", nome, device_id, exc)

    async def abrir(device_id, variavel, sentido, valor, limite):
        entidade = await alertas.abrir(cliente, vinheria_id, device_id, variavel, sentido, valor, limite, agora)
        estado.ativos[(vinheria_id, device_id, variavel)] = {"entidade": entidade, "sentido": sentido}
        eventos.append(("abrir", device_id, variavel, sentido))

    async def fechar(device_id, variavel):
        ativo = estado.ativos.pop((vinheria_id, device_id, variavel), None)
        if ativo:
            await alertas.encerrar(cliente, vinheria_id, ativo["entidade"], agora)
            eventos.append(("encerrar", device_id, variavel, ativo["sentido"]))
        return ativo

    for device_id, entidade in cadastro.so_dispositivos(entidades):
        presentes.add(device_id)
        chave = (vinheria_id, device_id)
        servicepath = dominio.servicepath_do_dispositivo(entidade, vinheria_id) or config.FIWARE_SERVICEPATH
        atual = dominio.montar_atual(device_id, entidade, agora, config.OFFLINE_SEGUNDOS)
        situacao = atual["estado"]

        if situacao == "aguardando":
            continue
        if situacao == "offline":
            if (vinheria_id, device_id, "offline") not in estado.ativos:
                await abrir(device_id, "offline", None, None, None)
            estado.online[chave] = False
            continue
        await fechar(device_id, "offline")
        if situacao == "suspenso":      # o Node já apagou os alertas dele; só fecha o histórico
            for variavel in dominio.VARIAVEIS:
                await fechar(device_id, variavel)
            continue

        # ---- ativo (ok ou alerta)
        recem_chegou = not estado.online.get(chave)
        estado.online[chave] = True
        triggers = gatilhos.triggers_da_entidade(entidade)
        if recem_chegou:
            await comando(device_id, servicepath, "setTriggers", gatilhos.comando_set_triggers(triggers))

        for variavel in dominio.VARIAVEIS:
            valor = atual[variavel]
            if valor is None:
                continue
            minimo, maximo = gatilhos.limites(triggers, variavel)
            ativo = estado.ativos.get((vinheria_id, device_id, variavel))
            anterior = ativo["sentido"] if ativo else None
            novo = gatilhos.avaliar(valor, minimo, maximo, gatilhos.HISTERESE[variavel], anterior)
            if novo != anterior:
                if anterior:
                    await fechar(device_id, variavel)
                    await comando(device_id, servicepath, "alert", gatilhos.comando_alerta(variavel, anterior, False))
                if novo:
                    await abrir(device_id, variavel, novo, valor, maximo if novo == "acima" else minimo)
                    await comando(device_id, servicepath, "alert", gatilhos.comando_alerta(variavel, novo, True))
            elif recem_chegou and anterior:
                await comando(device_id, servicepath, "alert", gatilhos.comando_alerta(variavel, anterior, True))

        # ---- reconciliação: o Node diz o mesmo que o backend espera?
        em_alerta = {v: estado.ativos[(vinheria_id, device_id, v)]["sentido"]
                     for v in dominio.VARIAVEIS if (vinheria_id, device_id, v) in estado.ativos}
        if gatilhos.precisa_reconciliar(bool(em_alerta), atual["state"], agora,
                                        estado.ultimo_comando.get(chave), config.RECONCILIAR_SEGUNDOS):
            eventos.append(("reconciliar", device_id))
            for variavel in dominio.VARIAVEIS:
                sentido = em_alerta.get(variavel)
                await comando(device_id, servicepath, "alert",
                              gatilhos.comando_alerta(variavel, sentido or "acima", sentido is not None))

    # dispositivos apagados: fecha o que ficou em andamento
    for (vin, device_id, variavel) in list(estado.ativos):
        if vin == vinheria_id and device_id not in presentes:
            await fechar(device_id, variavel)
            estado.online.pop((vin, device_id), None)
    return eventos


async def executar(estado: EstadoVigia = None):
    """O loop de verdade (roda em segundo plano enquanto a API está de pé)."""
    estado = estado or EstadoVigia()
    ultimo_erro = {}
    while True:
        for vinheria_id in config.vinherias_conhecidas():
            try:
                async with httpx.AsyncClient(timeout=10) as cliente:
                    eventos = await ciclo(cliente, vinheria_id, datetime.now(timezone.utc), estado)
                for e in eventos:
                    if e[0] != "comando":
                        log.info("%s %s", vinheria_id, e)
                ultimo_erro.pop(vinheria_id, None)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # FIWARE fora do ar, rede... tenta de novo na próxima volta
                texto = f"{type(exc).__name__}: {exc}"
                if ultimo_erro.get(vinheria_id) != texto:  # não repete a mesma mensagem a cada 5 s
                    log.warning("vigia (%s): %s", vinheria_id, texto)
                    ultimo_erro[vinheria_id] = texto
        await asyncio.sleep(config.INTERVALO_VIGIA)
