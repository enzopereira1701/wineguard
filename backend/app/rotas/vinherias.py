"""Vinherias, adegas e suspensão (formato do docs/api-contrato.md)."""

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Body, Depends

from .. import vinherias
from .leituras import cliente_http
from .util import executar

router = APIRouter(tags=["vinherias"])


async def _agora(funcao, cliente, vinheria_id):
    await funcao(cliente, vinheria_id, datetime.now(timezone.utc))
    return {"ok": True}


@router.get("/api/vinherias")
async def listar(cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Todas as vinherias, com a contagem de dispositivos. Quem passou do vencimento já vem suspensa."""
    return await executar(vinherias.listar(cliente))


@router.post("/api/vinherias", status_code=201)
async def criar(corpo: dict = Body(...), cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Cria a vinheria ({nome, vencimento 'AAAA-MM-DD'}) com a apikey dela e a 'Adega 1'."""
    return await executar(vinherias.criar(cliente, corpo, datetime.now(timezone.utc)))


@router.post("/api/vinherias/{vinheria_id}/suspender")
async def suspender(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Suspende: os Nodes recebem 'suspend' e a API recusa as consultas da vinheria. O histórico é preservado."""
    return await executar(_agora(vinherias.suspender, cliente, vinheria_id))


@router.post("/api/vinherias/{vinheria_id}/reativar")
async def reativar(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Reativa (renova o vencimento por 30 dias se já passou) e manda 'resume' aos Nodes."""
    return await executar(_agora(vinherias.reativar, cliente, vinheria_id))


@router.post("/api/vinherias/{vinheria_id}/simular-inadimplencia")
async def simular_inadimplencia(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Para a demonstração: vencimento = ontem e suspende."""
    return await executar(_agora(vinherias.simular_inadimplencia, cliente, vinheria_id))


@router.get("/api/vinherias/{vinheria_id}/adegas")
async def adegas(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Adegas da vinheria: [{id: 'vin_demo/adega1', vinheriaId, servicepath, nome}]."""
    async def buscar():
        await vinherias.exigir(cliente, vinheria_id, permitir_suspensa=True)
        return await vinherias.listar_adegas(cliente, vinheria_id)
    return await executar(buscar())
