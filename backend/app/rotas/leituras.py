"""Rotas de leitura: valor atual, histórico e estabilidade (formato do docs/api-contrato.md)."""

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query

from .. import config, dominio, estabilidade, fiware, vinherias
from .util import executar

router = APIRouter(prefix="/api/dispositivos", tags=["leituras"])


async def cliente_http():
    """Um cliente HTTP por pedido (os testes trocam este por um falso)."""
    async with httpx.AsyncClient(timeout=10) as cliente:
        yield cliente


async def _atual(cliente, device_id, vinheria_id):
    entidade = dominio.entidade_do_dispositivo(device_id)
    await vinherias.exigir(cliente, vinheria_id)
    servicepath = await fiware.resolver_servicepath(cliente, device_id, vinheria_id)
    dados = await fiware.obter_entidade(cliente, entidade, vinheria_id, servicepath)
    return dominio.montar_atual(device_id, dados, datetime.now(timezone.utc), config.OFFLINE_SEGUNDOS)


async def _historico(cliente, device_id, periodo, vinheria_id):
    entidade = dominio.entidade_do_dispositivo(device_id)
    inicio, fim, agrupamento = dominio.janela(periodo, datetime.now(timezone.utc))
    await vinherias.exigir(cliente, vinheria_id)
    servicepath = await fiware.resolver_servicepath(cliente, device_id, vinheria_id)
    respostas = await fiware.obter_historico(cliente, entidade, inicio, fim, agrupamento, vinheria_id, servicepath)
    return {
        "deviceId": device_id,
        **{v: dominio.pontos_do_sth(respostas[v], inicio, fim) for v in dominio.VARIAVEIS},
    }


@router.get("/{device_id}/atual")
async def valor_atual(device_id: str, vinheriaId: Optional[str] = None,
                      cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Última leitura de cada variável e o estado do dispositivo (vem do Orion)."""
    return await executar(_atual(cliente, device_id, vinheriaId or config.FIWARE_SERVICE))


@router.get("/{device_id}/historico")
async def historico(
    device_id: str,
    periodo: str = Query("1h", description="1h, 24h ou 7d"),
    vinheriaId: Optional[str] = None,
    cliente: httpx.AsyncClient = Depends(cliente_http),
):
    """
    Histórico das 3 variáveis (para os gráficos do dashboard), vindo do STH-Comet.
    Cada ponto é a média de um minuto (1h) ou de uma hora (24h e 7d).
    """
    return await executar(_historico(cliente, device_id, periodo, vinheriaId or config.FIWARE_SERVICE))


@router.get("/{device_id}/estabilidade")
async def obter_estabilidade(device_id: str, vinheriaId: Optional[str] = None,
                             cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Mínimo e máximo da temperatura em 24 h (STH-Comet), a variação e se passou do limite."""
    async def buscar():
        dominio.entidade_do_dispositivo(device_id)  # valida o formato (ValueError -> 400)
        return await estabilidade.obter(cliente, vinheriaId or config.FIWARE_SERVICE, device_id,
                                        datetime.now(timezone.utc))
    return await executar(buscar())
