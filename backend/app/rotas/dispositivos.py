"""Cadastro de dispositivos e resumo da vinheria (formato do docs/api-contrato.md)."""

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Body, Depends

from .. import cadastro, config
from .leituras import cliente_http
from .util import executar

router = APIRouter(tags=["dispositivos"])


@router.get("/api/vinherias/{vinheria_id}/dispositivos")
async def listar(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Dispositivos de todas as adegas da vinheria."""
    return await executar(cadastro.listar(cliente, vinheria_id))


@router.post("/api/vinherias/{vinheria_id}/dispositivos", status_code=201)
async def cadastrar(vinheria_id: str, corpo: dict = Body(...), cliente: httpx.AsyncClient = Depends(cliente_http)):
    """
    Cadastra um dispositivo: registra no IoT Agent (com apikey) e devolve a configuração
    (deviceId + apikey) que o Node precisa. Informe adegaId OU novaAdega.
    """
    return await executar(cadastro.cadastrar(cliente, vinheria_id, corpo, datetime.now(timezone.utc)))


@router.patch("/api/dispositivos/{device_id}")
async def atualizar(device_id: str, corpo: dict = Body(...), vinheriaId: Optional[str] = None,
                    cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Renomeia o dispositivo."""
    return await executar(cadastro.atualizar(cliente, vinheriaId or config.FIWARE_SERVICE, device_id, corpo))


@router.delete("/api/dispositivos/{device_id}")
async def remover(device_id: str, vinheriaId: Optional[str] = None,
                  cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Remove o dispositivo do IoT Agent e do Orion."""
    await executar(cadastro.remover(cliente, vinheriaId or config.FIWARE_SERVICE, device_id))
    return {"ok": True}


@router.get("/api/vinherias/{vinheria_id}/resumo")
async def resumo(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Estado de cada dispositivo (ok, alerta, offline, suspenso, aguardando) numa chamada só."""
    return await executar(cadastro.resumo(cliente, vinheria_id, datetime.now(timezone.utc)))
