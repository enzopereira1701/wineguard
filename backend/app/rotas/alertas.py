"""Histórico de alertas da vinheria (formato do docs/api-contrato.md)."""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import alertas, cadastro, fiware
from .leituras import cliente_http

router = APIRouter(tags=["alertas"])


@router.get("/api/vinherias/{vinheria_id}/alertas")
async def listar(
    vinheria_id: str,
    estado: str = Query("todos", description="todos, ativos ou encerrados"),
    deviceId: Optional[str] = None,
    cliente: httpx.AsyncClient = Depends(cliente_http),
):
    """Alertas do mais novo para o mais antigo. 'fim' vazio = em andamento."""
    try:
        cadastro._apikey(vinheria_id)
        return await alertas.listar(cliente, vinheria_id, estado, deviceId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except cadastro.VinheriaDesconhecida:
        raise HTTPException(status_code=404, detail="vinheria não encontrada")
    except fiware.FiwareIndisponivel as exc:
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")
