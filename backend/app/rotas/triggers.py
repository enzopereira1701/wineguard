"""Triggers de um dispositivo: ler e salvar (salvar também envia ao Node e espera a confirmação)."""

from typing import Optional

import httpx
from fastapi import APIRouter, Body, Depends

from .. import config, triggers
from .leituras import cliente_http
from .util import executar

router = APIRouter(prefix="/api/dispositivos", tags=["triggers"])


@router.get("/{device_id}/triggers")
async def obter(device_id: str, vinheriaId: Optional[str] = None, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Triggers em vigor (se nunca foram definidos, os do preset do dispositivo)."""
    return await executar(triggers.obter(cliente, vinheriaId or config.FIWARE_SERVICE, device_id))


@router.put("/{device_id}/triggers")
async def salvar(device_id: str, corpo: dict = Body(...), vinheriaId: Optional[str] = None,
                 cliente: httpx.AsyncClient = Depends(cliente_http)):
    """
    Valida, salva e manda setTriggers ao Node. Responde {recebido, deviceId, em} quando o Node confirma;
    se ele não confirmar, responde 504 (os limites ficam salvos e são reenviados quando ele voltar).
    """
    return await executar(triggers.salvar(cliente, vinheriaId or config.FIWARE_SERVICE, device_id, corpo))
