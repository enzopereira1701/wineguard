"""
Conversa com o FIWARE (Orion e STH-Comet).

Por que o dashboard não chama o FIWARE direto? O Orion e o STH-Comet exigem os headers
fiware-service e fiware-servicepath e não liberam CORS para o navegador. O dashboard fala só
com esta API, e ela fala com o FIWARE.
"""

import asyncio
from datetime import datetime

import httpx

from . import config
from .dominio import VARIAVEIS, para_iso


class FiwareIndisponivel(Exception):
    """Rede caiu, FIWARE fora do ar ou respondeu com erro inesperado."""


def cabecalhos() -> dict:
    """Definem de qual vinheria (service) e adega (servicepath) vem o dado."""
    return {"fiware-service": config.FIWARE_SERVICE, "fiware-servicepath": config.FIWARE_SERVICEPATH}


async def obter_entidade(cliente: httpx.AsyncClient, entidade: str):
    """
    Última leitura do dispositivo no Orion. Devolve None se o Orion não conhece a entidade
    (o Node ainda nunca enviou dados).
    O metadata dateModified diz QUANDO cada variável foi atualizada (usado para saber se está online).
    """
    try:
        r = await cliente.get(
            f"{config.ORION_URL}/v2/entities/{entidade}",
            params={
                "type": config.TIPO_ENTIDADE,
                "attrs": "temperature,humidity,luminosity,state,muted,rssi,firmware",
                "metadata": "dateModified",
            },
            headers=cabecalhos(),
        )
    except httpx.HTTPError as exc:
        raise FiwareIndisponivel(f"Orion: {type(exc).__name__} {exc}") from exc
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise FiwareIndisponivel(f"Orion respondeu {r.status_code}: {r.text[:200]}")
    return r.json()


async def _historico_variavel(cliente, entidade, variavel, inicio: datetime, fim: datetime, agrupamento: str):
    try:
        r = await cliente.get(
            f"{config.STH_URL}/STH/v1/contextEntities/type/{config.TIPO_ENTIDADE}/id/{entidade}/attributes/{variavel}",
            params={
                "aggrMethod": "sum",          # com 'samples' dá a média: sum / samples
                "aggrPeriod": agrupamento,
                "dateFrom": para_iso(inicio),
                "dateTo": para_iso(fim),
            },
            headers=cabecalhos(),
        )
    except httpx.HTTPError as exc:
        raise FiwareIndisponivel(f"STH-Comet: {exc}") from exc
    if r.status_code == 404:
        return {}  # nenhuma leitura guardada ainda
    if r.status_code != 200:
        raise FiwareIndisponivel(f"STH-Comet respondeu {r.status_code}: {r.text[:200]}")
    return r.json()


async def obter_historico(cliente, entidade: str, inicio: datetime, fim: datetime, agrupamento: str) -> dict:
    """As 3 variáveis de uma vez (busca em paralelo). Devolve {variavel: resposta_do_sth}."""
    respostas = await asyncio.gather(
        *[_historico_variavel(cliente, entidade, v, inicio, fim, agrupamento) for v in VARIAVEIS]
    )
    return dict(zip(VARIAVEIS, respostas))


async def enviar_comando(cliente, entidade: str, comando: str, valor: str):
    """API -> Orion -> IoT Agent -> MQTT -> ESP32. O Node responde em cmdexe."""
    try:
        r = await cliente.patch(
            f"{config.ORION_URL}/v2/entities/{entidade}/attrs",
            params={"type": config.TIPO_ENTIDADE},
            json={comando: {"type": "command", "value": valor}},
            headers=cabecalhos(),
        )
    except httpx.HTTPError as exc:
        raise FiwareIndisponivel(f"Orion: {exc}") from exc
    if r.status_code not in (200, 204):
        raise FiwareIndisponivel(f"Orion respondeu {r.status_code}: {r.text[:200]}")
