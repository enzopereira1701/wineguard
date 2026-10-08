"""
Regras de triggers e alertas (Backend 3) que NÃO dependem de rede nem do FastAPI.

Aqui: presets, validação dos triggers, a avaliação com histerese (a mesma do firmware),
o texto dos comandos para o Node e a montagem dos alertas. Testado em tests/test_gatilhos.py.
"""

import math
import re
from datetime import datetime

from .dominio import VARIAVEIS, ler_iso, para_iso, _valor

# Presets de GUARDA (iguais aos do dashboard, src/data/presets.js): faixa de alerta de cada variável
PRESETS_TRIGGERS = {
    "guarda_geral": {"temp": (10, 15), "umid": (60, 75), "luz": (0, 10)},
    "longa_guarda": {"temp": (11, 14), "umid": (65, 75), "luz": (0, 5)},
    "espumante": {"temp": (9, 13), "umid": (65, 80), "luz": (0, 5)},
}
PRESET_PADRAO = "guarda_geral"
MODOS = ("referencia", "personalizado")
ESTABILIDADE_PADRAO = 2

CHAVE_DA_VARIAVEL = {"temperature": "temp", "humidity": "umid", "luminosity": "luz"}
LETRA = {"temperature": "t", "humidity": "h", "luminosity": "l"}          # letra do comando 'alert'
DIRECAO = {"acima": "high", "abaixo": "low"}
HISTERESE = {"temperature": 0.5, "humidity": 2.0, "luminosity": 2.0}      # folga para sair do alerta
LIMITES_FISICOS = {"temp": (-20, 60), "umid": (0, 100), "luz": (0, 100)}
NOMES = {"temp": "temperatura", "umid": "umidade", "luz": "luminosidade"}

ESTADOS_DE_ALERTA = ("todos", "ativos", "encerrados")
_ALERTA = re.compile(r"^urn:ngsi-ld:Alerta:(\d+)$")


# ---------------------------------------------------------------- triggers
def triggers_do_preset(preset) -> dict:
    """Triggers iniciais (modo 'referencia') de um preset; preset desconhecido cai no padrão."""
    nome = preset if preset in PRESETS_TRIGGERS else PRESET_PADRAO
    faixas = PRESETS_TRIGGERS[nome]
    return {
        "preset": nome, "modo": "referencia",
        **{chave: {"min": lo, "max": hi} for chave, (lo, hi) in faixas.items()},
        "estabilidadeMax": ESTABILIDADE_PADRAO, "luzEscuro": None,
    }


def _numero(valor, nome: str):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ValueError(f"{nome}: informe um número")
    return valor


def validar_triggers(corpo) -> dict:
    """
    Valida o corpo do PUT /triggers e devolve os triggers limpos.
    Bloqueia o que o dashboard também bloqueia: faltando valor, fora do que o sensor mede, mínimo >= máximo.
    (Os avisos fortes e leves, como 'acima de 24 °C', são só da tela.)
    """
    if not isinstance(corpo, dict):
        raise ValueError("corpo inválido")
    preset = corpo.get("preset")
    if preset not in PRESETS_TRIGGERS:
        raise ValueError(f"preset inválido. Use: {', '.join(PRESETS_TRIGGERS)}")
    modo = corpo.get("modo")
    if modo not in MODOS:
        raise ValueError(f"modo inválido. Use: {', '.join(MODOS)}")

    limpo = {"preset": preset, "modo": modo}
    for chave, (baixo, alto) in LIMITES_FISICOS.items():
        faixa = corpo.get(chave)
        if not isinstance(faixa, dict):
            raise ValueError(f"{NOMES[chave]}: informe o mínimo e o máximo")
        minimo = _numero(faixa.get("min"), f"{NOMES[chave]} (mínimo)")
        maximo = _numero(faixa.get("max"), f"{NOMES[chave]} (máximo)")
        if minimo < baixo or maximo > alto:
            raise ValueError(f"{NOMES[chave]}: use valores entre {baixo} e {alto}")
        if minimo >= maximo:
            raise ValueError(f"{NOMES[chave]}: o mínimo precisa ser menor que o máximo")
        limpo[chave] = {"min": minimo, "max": maximo}

    estab = corpo.get("estabilidadeMax")
    estab = ESTABILIDADE_PADRAO if estab is None else _numero(estab, "estabilidade")
    if not 0 < estab <= 24:
        raise ValueError("estabilidade: use um valor maior que 0 e até 24 °C")
    limpo["estabilidadeMax"] = estab

    escuro = corpo.get("luzEscuro")
    if escuro is not None:
        escuro = _numero(escuro, "luz escuro")
        if not 0 <= escuro <= 100:
            raise ValueError("luz escuro: use um valor entre 0 e 100")
    limpo["luzEscuro"] = escuro
    return limpo


def triggers_da_entidade(entidade) -> dict:
    """
    Triggers em vigor: os gravados na entidade (atributo 'triggers'); se não há, ou estão
    estragados, os do preset do dispositivo.
    """
    gravado = _valor(entidade, "triggers") if entidade else None
    if isinstance(gravado, dict):
        try:
            return validar_triggers(gravado)
        except ValueError:
            pass
    return triggers_do_preset(_valor(entidade, "preset") if entidade else None)


def limites(triggers: dict, variavel: str):
    """(mínimo, máximo) de 'temperature', 'humidity' ou 'luminosity'."""
    faixa = triggers[CHAVE_DA_VARIAVEL[variavel]]
    return faixa["min"], faixa["max"]


def _formatar(numero) -> str:
    return f"{numero:g}"


def comando_set_triggers(triggers: dict) -> str:
    """Valor do comando setTriggers: tmin,tmax,hmin,hmax,lmin,lmax."""
    partes = []
    for chave in ("temp", "umid", "luz"):
        partes += [_formatar(triggers[chave]["min"]), _formatar(triggers[chave]["max"])]
    return ",".join(partes)


# ---------------------------------------------------------------- avaliação
def avaliar(valor: float, minimo: float, maximo: float, histerese: float, atual):
    """
    Estado do alerta de uma variável: None, 'acima' ou 'abaixo'. Mesma regra do firmware:
    entra ao passar do limite; só sai quando volta pelo menos 'histerese' para dentro da faixa
    (evita ligar e desligar o alerta quando o valor oscila em cima do limite).
    """
    if atual is None:
        if valor > maximo:
            return "acima"
        if valor < minimo:
            return "abaixo"
        return None
    if atual == "acima":
        return None if valor <= maximo - histerese else "acima"
    return None if valor >= minimo + histerese else "abaixo"


def comando_alerta(variavel: str, sentido: str, ligar: bool) -> str:
    """Valor do comando alert: 't,high,1' (liga) ou 't,high,0' (desliga)."""
    return f"{LETRA[variavel]},{DIRECAO[sentido]},{1 if ligar else 0}"


def precisa_reconciliar(esperado_alerta: bool, state_do_node, agora: datetime, ultimo_comando, espera: int = 15) -> bool:
    """
    O Node diz 'alerta' quando devia estar 'ok' (ou o contrário)? Só confirma a divergência depois de
    'espera' segundos do último comando enviado: o Node leva até um ciclo de telemetria para refletir.
    """
    if state_do_node not in ("ok", "alerta"):
        return False
    if (state_do_node == "alerta") == esperado_alerta:
        return False
    return ultimo_comando is None or (agora - ultimo_comando).total_seconds() >= espera


def estado_do_comando(entidade, comando: str, depois_de=None) -> str:
    """
    'pendente', 'ok' ou 'erro' para um comando enviado ao Node. O IoT Agent grava <comando>_status
    na entidade (PENDING e depois OK ou ERROR quando o Node responde no cmdexe).
    'depois_de' (datetime lido do Orion antes do envio) descarta o status de um comando anterior.
    """
    atributo = entidade.get(f"{comando}_status") if entidade else None
    if not isinstance(atributo, dict):
        return "pendente"
    if depois_de is not None:
        quando = (atributo.get("metadata") or {}).get("dateModified", {}).get("value")
        try:
            if not quando or ler_iso(quando) <= depois_de:
                return "pendente"
        except ValueError:
            return "pendente"
    valor = str(atributo.get("value", "")).upper()
    if valor == "OK":
        return "ok"
    if valor in ("ERROR", "ERRO"):
        return "erro"
    return "pendente"


def quando_o_status_mudou(entidade, comando: str):
    """datetime do dateModified do <comando>_status (ou None): é o 'antes' do estado_do_comando."""
    atributo = entidade.get(f"{comando}_status") if entidade else None
    quando = ((atributo or {}).get("metadata") or {}).get("dateModified", {}).get("value") if isinstance(atributo, dict) else None
    try:
        return ler_iso(quando) if quando else None
    except ValueError:
        return None


# ------------------------------------------------------------------ alertas
def entidade_do_alerta(numero: int) -> str:
    return f"urn:ngsi-ld:Alerta:{numero}"


def numero_do_alerta(entidade_id):
    achou = _ALERTA.match(entidade_id or "")
    return int(achou.group(1)) if achou else None


def corpo_alerta(device_id: str, variavel: str, sentido, valor, limite, agora: datetime) -> dict:
    """Atributos da entidade 'Alerta' no Orion. Sem 'fim' = em andamento; sentido/valor/limite ausentes = null."""
    corpo = {
        "deviceId": {"type": "Text", "value": device_id},
        "variavel": {"type": "Text", "value": variavel},
        "inicio": {"type": "DateTime", "value": para_iso(agora)},
    }
    if sentido is not None:
        corpo["sentido"] = {"type": "Text", "value": sentido}
    if valor is not None:
        corpo["valor"] = {"type": "Number", "value": valor}
    if limite is not None:
        corpo["limite"] = {"type": "Number", "value": limite}
    return corpo


def montar_alerta(vinheria_id: str, entidade: dict) -> dict:
    """Entidade 'Alerta' do Orion -> item de GET /vinherias/{id}/alertas."""
    return {
        "id": numero_do_alerta(entidade["id"]),
        "vinheriaId": vinheria_id,
        "deviceId": _valor(entidade, "deviceId"),
        "variavel": _valor(entidade, "variavel"),
        "sentido": _valor(entidade, "sentido"),
        "valor": _valor(entidade, "valor"),
        "limite": _valor(entidade, "limite"),
        "inicio": _valor(entidade, "inicio"),
        "fim": _valor(entidade, "fim"),
    }


def filtrar_alertas(alertas: list, estado: str = "todos", device_id=None) -> list:
    """Filtra por estado e dispositivo; do mais novo para o mais antigo."""
    if estado not in ESTADOS_DE_ALERTA:
        raise ValueError(f"estado inválido. Use: {', '.join(ESTADOS_DE_ALERTA)}")
    itens = [
        a for a in alertas
        if a["id"] is not None
        and (device_id is None or a["deviceId"] == device_id)
        and (estado == "todos" or (estado == "ativos") == (a["fim"] is None))
    ]
    return sorted(itens, key=lambda a: (a["inicio"] or "", a["id"]), reverse=True)


def contar_ativos(alertas: list) -> dict:
    """{deviceId: quantos alertas em andamento}."""
    contagem = {}
    for a in alertas:
        if a["fim"] is None and a["deviceId"]:
            contagem[a["deviceId"]] = contagem.get(a["deviceId"], 0) + 1
    return contagem
