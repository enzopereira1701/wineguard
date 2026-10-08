"""
Vigia (Backend 3 e 4): a cada poucos segundos lê o Orion e avalia os triggers de cada dispositivo.

O Node só obedece (como pede o enunciado); quem decide é o backend:
  - saiu da faixa  -> abre um alerta e manda 'alert|t,high,1' ao Node
  - voltou (com histerese) -> encerra o alerta e manda 'alert|t,high,0'
  - 30 s sem leitura -> alerta 'offline' (começo e fim no histórico)
  - variação da temperatura em 24 h acima do limite -> alerta 'estabilidade' (conferido a cada 60 s)
  - Node voltou ou o backend reiniciou -> reenvia os triggers e os alertas em andamento
  - o 'state' do Node diverge do esperado -> reenvia os alertas (só se ele publicou depois do último comando)
  - vinheria suspensa -> encerra os alertas e manda 'suspend' a quem ainda publica
  - vinheria vencida -> suspende (feito em vinherias.listar)
Alertas em andamento são lidos do Orion na primeira volta, então reiniciar a API não perde nada.
Rode a API em UM processo só (dois vigias abririam alertas duplicados).
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from . import alertas, config, dominio, estabilidade, fiware, gatilhos, vinherias

log = logging.getLogger("wineguard.vigia")

TODOS_OS_ALERTAS = (*dominio.VARIAVEIS, "estabilidade", "offline")


class EstadoVigia:
    """O que o vigia lembra entre uma volta e outra (só memória: o resto está no Orion)."""

    def __init__(self):
        self.ativos = {}               # (vinheria, device, variavel) -> {"entidade", "sentido"}
        self.carregado = set()         # vinherias cujos alertas em andamento já foram lidos
        self.ultimo_comando = {}       # (vinheria, device) -> datetime do último comando enviado
        self.online = {}               # (vinheria, device) -> True se estava ativo na volta anterior
        self.ultima_estabilidade = {}  # (vinheria, device) -> datetime da última conferência


class Contexto:
    """Uma volta do vigia numa vinheria: junta o que as etapas precisam (cliente, hora, estado, eventos)."""

    def __init__(self, cliente, vinheria_id: str, agora: datetime, estado: EstadoVigia):
        self.cliente, self.vinheria_id, self.agora, self.estado = cliente, vinheria_id, agora, estado
        self.eventos = []

    async def comando(self, device_id, servicepath, nome, valor):
        self.estado.ultimo_comando[(self.vinheria_id, device_id)] = self.agora
        try:
            await fiware.enviar_comando(self.cliente, dominio.entidade_do_dispositivo(device_id), nome, valor,
                                        self.vinheria_id, servicepath)
            self.eventos.append(("comando", device_id, nome, valor))
        except fiware.FiwareIndisponivel as exc:
            log.warning("comando %s para %s falhou: %s", nome, device_id, exc)

    async def abrir(self, device_id, variavel, sentido, valor, limite):
        entidade = await alertas.abrir(self.cliente, self.vinheria_id, device_id, variavel, sentido, valor,
                                       limite, self.agora)
        self.estado.ativos[(self.vinheria_id, device_id, variavel)] = {"entidade": entidade, "sentido": sentido}
        self.eventos.append(("abrir", device_id, variavel, sentido))

    async def fechar(self, device_id, variavel):
        ativo = self.estado.ativos.pop((self.vinheria_id, device_id, variavel), None)
        if ativo:
            await alertas.encerrar(self.cliente, self.vinheria_id, ativo["entidade"], self.agora)
            self.eventos.append(("encerrar", device_id, variavel, ativo["sentido"]))
        return ativo

    def ativo(self, device_id, variavel):
        return self.estado.ativos.get((self.vinheria_id, device_id, variavel))


async def _carregar(cliente, vinheria_id: str, estado: EstadoVigia):
    if vinheria_id in estado.carregado:
        return
    for a in await alertas.listar(cliente, vinheria_id, "ativos"):
        chave = (vinheria_id, a["deviceId"], a["variavel"])
        if chave not in estado.ativos:  # (a lista vem do mais novo: vale o mais novo)
            estado.ativos[chave] = {"entidade": gatilhos.entidade_do_alerta(a["id"]), "sentido": a["sentido"]}
    estado.carregado.add(vinheria_id)


def _servicepath(entidade, vinheria_id: str) -> str:
    return dominio.servicepath_do_dispositivo(entidade, vinheria_id) or config.FIWARE_SERVICEPATH


async def _estabilidade(ctx: Contexto, device_id: str, servicepath: str, triggers: dict):
    """Conferência da variação em 24 h (a cada ESTABILIDADE_INTERVALO s, para não sobrecarregar o STH)."""
    chave = (ctx.vinheria_id, device_id)
    ultima = ctx.estado.ultima_estabilidade.get(chave)
    if ultima is not None and (ctx.agora - ultima).total_seconds() < config.ESTABILIDADE_INTERVALO:
        return
    ctx.estado.ultima_estabilidade[chave] = ctx.agora
    try:
        r = await estabilidade.da_entidade(ctx.cliente, ctx.vinheria_id, device_id, servicepath,
                                           triggers["estabilidadeMax"], ctx.agora)
    except fiware.FiwareIndisponivel as exc:
        log.warning("estabilidade de %s: %s", device_id, exc)
        return
    aberto = ctx.ativo(device_id, "estabilidade")
    if r["instavel"] and not aberto:
        await ctx.abrir(device_id, "estabilidade", None, r["variacao"], r["limite"])
    elif not r["instavel"] and aberto:
        await ctx.fechar(device_id, "estabilidade")


async def _dispositivo(ctx: Contexto, device_id: str, entidade: dict):
    estado, vin = ctx.estado, ctx.vinheria_id
    chave = (vin, device_id)
    servicepath = _servicepath(entidade, vin)
    atual = dominio.montar_atual(device_id, entidade, ctx.agora, config.OFFLINE_SEGUNDOS)
    situacao = atual["estado"]

    if situacao == "aguardando":
        return
    if situacao == "offline":
        if not ctx.ativo(device_id, "offline"):
            await ctx.abrir(device_id, "offline", None, None, None)
        estado.online[chave] = False
        return
    await ctx.fechar(device_id, "offline")
    if situacao == "suspenso":      # o Node já apagou os alertas dele; só fecha o histórico
        for variavel in (*dominio.VARIAVEIS, "estabilidade"):
            await ctx.fechar(device_id, variavel)
        return

    # ---- ativo (ok ou alerta)
    recem_chegou = not estado.online.get(chave)
    estado.online[chave] = True
    triggers = gatilhos.triggers_da_entidade(entidade)
    if recem_chegou:
        await ctx.comando(device_id, servicepath, "setTriggers", gatilhos.comando_set_triggers(triggers))

    for variavel in dominio.VARIAVEIS:
        valor = atual[variavel]
        if valor is None:
            continue
        minimo, maximo = gatilhos.limites(triggers, variavel)
        ativo = ctx.ativo(device_id, variavel)
        anterior = ativo["sentido"] if ativo else None
        novo = gatilhos.avaliar(valor, minimo, maximo, gatilhos.HISTERESE[variavel], anterior)
        if novo != anterior:
            if anterior:
                await ctx.fechar(device_id, variavel)
                await ctx.comando(device_id, servicepath, "alert", gatilhos.comando_alerta(variavel, anterior, False))
            if novo:
                await ctx.abrir(device_id, variavel, novo, valor, maximo if novo == "acima" else minimo)
                await ctx.comando(device_id, servicepath, "alert", gatilhos.comando_alerta(variavel, novo, True))
        elif recem_chegou and anterior:
            await ctx.comando(device_id, servicepath, "alert", gatilhos.comando_alerta(variavel, anterior, True))

    await _estabilidade(ctx, device_id, servicepath, triggers)

    # ---- reconciliação: o Node diz o mesmo que o backend espera?
    em_alerta = {v: ctx.ativo(device_id, v)["sentido"] for v in dominio.VARIAVEIS if ctx.ativo(device_id, v)}
    if gatilhos.precisa_reconciliar(bool(em_alerta), atual["state"], ctx.agora, estado.ultimo_comando.get(chave),
                                    dominio.ler_iso(atual["ultimaLeitura"]), config.RECONCILIAR_SEGUNDOS):
        ctx.eventos.append(("reconciliar", device_id))
        for variavel in dominio.VARIAVEIS:
            sentido = em_alerta.get(variavel)
            await ctx.comando(device_id, servicepath, "alert",
                              gatilhos.comando_alerta(variavel, sentido or "acima", sentido is not None))


async def ciclo(cliente, vinheria_id: str, agora: datetime, estado: EstadoVigia) -> list:
    """Uma volta do vigia para uma vinheria ativa. Devolve a lista de eventos (para o log e os testes)."""
    ctx = Contexto(cliente, vinheria_id, agora, estado)
    await _carregar(cliente, vinheria_id, estado)
    presentes = set()
    for device_id, entidade in dominio.so_dispositivos(await fiware.listar_entidades(cliente, vinheria_id)):
        presentes.add(device_id)
        await _dispositivo(ctx, device_id, entidade)

    # dispositivos apagados: fecha o que ficou em andamento
    for (vin, device_id, variavel) in list(estado.ativos):
        if vin == vinheria_id and device_id not in presentes:
            await ctx.fechar(device_id, variavel)
            estado.online.pop((vin, device_id), None)
            estado.ultima_estabilidade.pop((vin, device_id), None)
    return ctx.eventos


async def ciclo_suspensa(cliente, vinheria_id: str, agora: datetime, estado: EstadoVigia) -> list:
    """
    Volta numa vinheria suspensa: encerra todos os alertas e confere se os Nodes pararam. Quem ainda
    publica (estava offline na hora da suspensão, ou ignorou o comando) recebe 'suspend' de novo.
    """
    ctx = Contexto(cliente, vinheria_id, agora, estado)
    await _carregar(cliente, vinheria_id, estado)
    for (vin, device_id, variavel) in list(estado.ativos):
        if vin == vinheria_id:
            await ctx.fechar(device_id, variavel)
    for device_id, entidade in dominio.so_dispositivos(await fiware.listar_entidades(cliente, vinheria_id)):
        chave = (vinheria_id, device_id)
        estado.online.pop(chave, None)           # ao reativar, o Node volta a receber os triggers
        estado.ultima_estabilidade.pop(chave, None)
        atual = dominio.montar_atual(device_id, entidade, agora, config.OFFLINE_SEGUNDOS)
        if atual["estado"] not in ("ok", "alerta"):
            continue                             # parado (suspenso, offline ou nunca enviou): nada a fazer
        ultimo = estado.ultimo_comando.get(chave)
        leitura = dominio.ler_iso(atual["ultimaLeitura"])
        if ultimo is None or ((agora - ultimo).total_seconds() >= config.RECONCILIAR_SEGUNDOS
                              and (leitura - ultimo).total_seconds() >= 3):
            await ctx.comando(device_id, _servicepath(entidade, vinheria_id), "suspend", "")
    return ctx.eventos


async def passo(cliente, agora: datetime, estado: EstadoVigia):
    """
    Uma volta em todas as vinherias. Devolve (eventos, erros): eventos = [(vinheria, evento)];
    erros = {vinheria: texto} (o erro de uma vinheria não impede as outras).
    """
    eventos, erros = [], {}
    for vinheria in await vinherias.listar(cliente, agora, contar=False):
        vinheria_id = vinheria["id"]
        funcao = ciclo_suspensa if vinheria["status"] == "suspensa" else ciclo
        try:
            eventos += [(vinheria_id, e) for e in await funcao(cliente, vinheria_id, agora, estado)]
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            erros[vinheria_id] = f"{type(exc).__name__}: {exc}"
    return eventos, erros


async def executar(estado: EstadoVigia = None):
    """O loop de verdade (roda em segundo plano enquanto a API está de pé)."""
    estado = estado or EstadoVigia()
    ultimo_erro = {}
    while True:
        erros = {}
        try:
            async with httpx.AsyncClient(timeout=10) as cliente:
                eventos, erros = await passo(cliente, datetime.now(timezone.utc), estado)
            for vinheria_id, e in eventos:
                if e[0] != "comando":
                    log.info("%s %s", vinheria_id, e)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # FIWARE fora do ar, rede... tenta de novo na próxima volta
            erros = {"*": f"{type(exc).__name__}: {exc}"}
        for chave, texto in erros.items():
            if ultimo_erro.get(chave) != texto:  # não repete a mesma mensagem a cada 5 s
                log.warning("vigia (%s): %s", chave, texto)
        ultimo_erro = erros
        await asyncio.sleep(config.INTERVALO_VIGIA)
