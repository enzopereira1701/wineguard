"""Cadastro de dispositivos e resumo da vinheria (formato do docs/api-contrato.md)."""

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException

from .. import cadastro, config, fiware
from .leituras import cliente_http

router = APIRouter(tags=["dispositivos"])


async def _executar(corrotina):
    """Traduz os erros do cadastro em respostas HTTP."""
    try:
        return await corrotina
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except cadastro.VinheriaDesconhecida:
        raise HTTPException(status_code=404, detail="vinheria não encontrada")
    except cadastro.DispositivoNaoEncontrado:
        raise HTTPException(status_code=404, detail="dispositivo não encontrado")
    except fiware.FiwareIndisponivel as exc:
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")


@router.get("/api/vinherias/{vinheria_id}/dispositivos")
async def listar(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Dispositivos de todas as adegas da vinheria."""
    return await _executar(cadastro.listar(cliente, vinheria_id))


@router.post("/api/vinherias/{vinheria_id}/dispositivos", status_code=201)
async def cadastrar(vinheria_id: str, corpo: dict = Body(...), cliente: httpx.AsyncClient = Depends(cliente_http)):
    """
    Cadastra um dispositivo: registra no IoT Agent (com apikey) e devolve a configuração
    (deviceId + apikey) que o Node precisa. Informe adegaId OU novaAdega.
    """
    return await _executar(cadastro.cadastrar(cliente, vinheria_id, corpo, datetime.now(timezone.utc)))


@router.patch("/api/dispositivos/{device_id}")
async def atualizar(device_id: str, corpo: dict = Body(...), vinheriaId: Optional[str] = None,
                    cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Renomeia o dispositivo."""
    return await _executar(cadastro.atualizar(cliente, vinheriaId or config.FIWARE_SERVICE, device_id, corpo))


@router.delete("/api/dispositivos/{device_id}")
async def remover(device_id: str, vinheriaId: Optional[str] = None,
                  cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Remove o dispositivo do IoT Agent e do Orion."""
    await _executar(cadastro.remover(cliente, vinheriaId or config.FIWARE_SERVICE, device_id))
    return {"ok": True}


@router.get("/api/vinherias/{vinheria_id}/resumo")
async def resumo(vinheria_id: str, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Estado de cada dispositivo (ok, alerta, offline, suspenso, aguardando) numa chamada só."""
    return await _executar(cadastro.resumo(cliente, vinheria_id, datetime.now(timezone.utc)))
