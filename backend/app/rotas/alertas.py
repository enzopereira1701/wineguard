"""Histórico de alertas da vinheria (formato do docs/api-contrato.md)."""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query

from .. import alertas, vinherias
from .leituras import cliente_http
from .util import executar

router = APIRouter(tags=["alertas"])


async def _listar(cliente, vinheria_id, estado, device_id):
    await vinherias.exigir(cliente, vinheria_id)
    return await alertas.listar(cliente, vinheria_id, estado, device_id)


@router.get("/api/vinherias/{vinheria_id}/alertas")
async def listar(
    vinheria_id: str,
    estado: str = Query("todos", description="todos, ativos ou encerrados"),
    deviceId: Optional[str] = None,
    cliente: httpx.AsyncClient = Depends(cliente_http),
):
    """Alertas do mais novo para o mais antigo. 'fim' vazio = em andamento."""
    return await executar(_listar(cliente, vinheria_id, estado, deviceId))
