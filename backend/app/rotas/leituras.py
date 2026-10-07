"""Rotas de leitura: valor atual e histórico (formato do docs/api-contrato.md)."""

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import config, dominio, fiware

router = APIRouter(prefix="/api/dispositivos", tags=["leituras"])


async def cliente_http():
    """Um cliente HTTP por pedido (os testes trocam este por um falso)."""
    async with httpx.AsyncClient(timeout=10) as cliente:
        yield cliente


def _entidade(device_id: str) -> str:
    try:
        return dominio.entidade_do_dispositivo(device_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{device_id}/atual")
async def valor_atual(device_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Última leitura de cada variável e o estado do dispositivo (vem do Orion)."""
    entidade = _entidade(device_id)
    try:
        dados = await fiware.obter_entidade(cliente, entidade)
    except fiware.FiwareIndisponivel as exc:
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")
    return dominio.montar_atual(device_id, dados, datetime.now(timezone.utc), config.OFFLINE_SEGUNDOS)


@router.get("/{device_id}/historico")
async def historico(
    device_id: str,
    periodo: str = Query("1h", description="1h, 24h ou 7d"),
    cliente: httpx.AsyncClient = Depends(cliente_http),
):
    """
    Histórico das 3 variáveis (para os gráficos do dashboard), vindo do STH-Comet.
    Cada ponto é a média de um minuto (1h) ou de uma hora (24h e 7d).
    """
    entidade = _entidade(device_id)
    try:
        inicio, fim, agrupamento = dominio.janela(periodo, datetime.now(timezone.utc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        respostas = await fiware.obter_historico(cliente, entidade, inicio, fim, agrupamento)
    except fiware.FiwareIndisponivel as exc:
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")

    return {
        "deviceId": device_id,
        **{v: dominio.pontos_do_sth(respostas[v], inicio, fim) for v in dominio.VARIAVEIS},
    }
