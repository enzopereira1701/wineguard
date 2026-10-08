"""
Regras de vinherias e adegas (Backend 4) que NÃO dependem de rede nem do FastAPI.

Vinheria = fiware-service. Cada uma é uma entidade 'Vinheria' no service de administração; cada adega
(fiware-servicepath) é uma entidade 'Adega' no service da própria vinheria. Testado em tests/test_vinherias.py.
"""

import re
import unicodedata
from datetime import datetime, timedelta, timezone

from .dominio import ler_iso, para_iso, _valor

DIAS_RENOVACAO = 30
STATUS = ("ativa", "suspensa")

_ID_VINHERIA = re.compile(r"^[a-z0-9_]{1,50}$")            # vira o header fiware-service: nada fora disto
_ENTIDADE_VINHERIA = re.compile(r"^urn:ngsi-ld:Vinheria:([a-z0-9_]{1,50})$")
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


# --------------------------------------------------------------- vinherias
def id_valido(vinheria_id) -> bool:
    return isinstance(vinheria_id, str) and bool(_ID_VINHERIA.match(vinheria_id))


def entidade_da_vinheria(vinheria_id: str) -> str:
    return f"urn:ngsi-ld:Vinheria:{vinheria_id}"


def id_da_entidade(entidade_id):
    achou = _ENTIDADE_VINHERIA.match(entidade_id or "")
    return achou.group(1) if achou else None


def id_da_vinheria(nome: str, existentes=()) -> str:
    """'Quinta do Sol' -> 'vin_quinta_do_sol' (e 'vin_quinta_do_sol_2' se o nome já existe)."""
    base = _slug(nome)[:30].strip("_")
    if not base:
        raise ValueError("nome da vinheria inválido (use letras ou números)")
    candidato, n = f"vin_{base}", 2
    while candidato in existentes:
        candidato, n = f"vin_{base}_{n}", n + 1
    return candidato


def gerar_apikey(nome: str, aleatorio: str) -> str:
    """apikey legível para digitar no Node: 'Quinta do Sol' + 'a3f9' -> 'quintadosola3f9'."""
    base = _slug(nome).replace("_", "")[:12] or "vin"
    return base + aleatorio


def validar_nova_vinheria(corpo) -> dict:
    """Corpo do POST /vinherias: {nome, vencimento 'AAAA-MM-DD' (ou ISO)}. Devolve {nome, vencimento: datetime UTC}."""
    if not isinstance(corpo, dict):
        raise ValueError("corpo inválido")
    nome = str(corpo.get("nome") or "").strip()
    if not 1 <= len(nome) <= 60:
        raise ValueError("nome da vinheria deve ter de 1 a 60 caracteres")
    texto = str(corpo.get("vencimento") or "").strip()
    try:
        if _DATA.match(texto):
            vencimento = datetime.strptime(texto, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            vencimento = ler_iso(texto)
    except ValueError:
        raise ValueError("vencimento inválido (use AAAA-MM-DD)")
    return {"nome": nome, "vencimento": vencimento}


def corpo_vinheria(nome: str, apikey: str, vencimento: datetime, agora: datetime) -> dict:
    return {
        "nome": {"type": "Text", "value": nome},
        "apikey": {"type": "Text", "value": apikey},
        "vencimento": {"type": "DateTime", "value": para_iso(vencimento)},
        "status": {"type": "Text", "value": "ativa"},
        "criadaEm": {"type": "DateTime", "value": para_iso(agora)},
    }


def montar_vinheria(entidade: dict, dispositivos=None) -> dict:
    """Entidade 'Vinheria' do Orion -> objeto do contrato (dispositivos só quando se sabe a contagem)."""
    status = _valor(entidade, "status")
    vinheria = {
        "id": id_da_entidade(entidade["id"]),
        "nome": _valor(entidade, "nome"),
        "apikey": _valor(entidade, "apikey"),
        "vencimento": _valor(entidade, "vencimento"),
        "status": status if status in STATUS else "ativa",
        "suspensaEm": _valor(entidade, "suspensaEm"),
    }
    if dispositivos is not None:
        vinheria["dispositivos"] = dispositivos
    return vinheria


def vencida(vinheria: dict, agora: datetime) -> bool:
    """Passou do vencimento? (sem data legível, não vence)"""
    try:
        return ler_iso(vinheria["vencimento"]) < agora
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def renovar_vencimento(vencimento: datetime, agora: datetime) -> datetime:
    """Reativar com a mensalidade em dia mantém a data; vencida, renova por 30 dias a partir de agora."""
    return agora + timedelta(days=DIAS_RENOVACAO) if vencimento < agora else vencimento


def vencimento_de_ontem(agora: datetime) -> datetime:
    return agora - timedelta(days=1)


def ordenar(vinherias: list) -> list:
    """Mais antigas primeiro (a demo fica no topo)."""
    return sorted(vinherias, key=lambda v: (v.get("criadaEm") or "", v["id"]))


# ------------------------------------------------------------------ adegas
def entidade_da_adega(servicepath: str) -> str:
    """'/porao_sul' -> 'urn:ngsi-ld:Adega:porao_sul'."""
    return f"urn:ngsi-ld:Adega:{servicepath.strip('/')}"


def corpo_adega(nome: str, servicepath: str) -> dict:
    return {"nome": {"type": "Text", "value": nome}, "servicepath": {"type": "Text", "value": servicepath}}


def montar_adega(vinheria_id: str, entidade: dict) -> dict:
    """Entidade 'Adega' -> {id: 'vin_demo/adega1', vinheriaId, servicepath, nome}."""
    servicepath = _valor(entidade, "servicepath")
    return {
        "id": f"{vinheria_id}{servicepath}",
        "vinheriaId": vinheria_id,
        "servicepath": servicepath,
        "nome": _valor(entidade, "nome"),
    }
