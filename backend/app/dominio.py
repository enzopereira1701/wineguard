"""
Regras do WineGuard que NÃO dependem de rede nem do FastAPI.

Ficam separadas das rotas para poderem ser testadas sozinhas (veja tests/).
Aqui: validar o id do dispositivo, montar a janela de tempo do histórico,
transformar a resposta do STH-Comet em pontos e montar a resposta "atual".
"""

import re
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
