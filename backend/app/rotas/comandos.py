"""Envio de comandos ao Node (mute, identify, ...). Vem do rascunho anterior; triggers e alertas entram no Backend 3."""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import config, dominio, fiware
from .leituras import cliente_http

router = APIRouter(prefix="/api/dispositivos", tags=["comandos"])

# Comandos que o Node aceita (ver o firmware: executaComando)
COMANDOS = {"setTriggers", "alert", "mute", "suspend", "resume", "setInterval", "identify"}


class Comando(BaseModel):
    comando: str        # ex.: "mute"
    valor: str = ""     # ex.: "1"  |  "t,high,1"  |  "12,16,60,75,0,10"


@router.post("/{device_id}/comando")
async def enviar_comando(device_id: str, corpo: Comando, vinheriaId: Optional[str] = None,
                         cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Manda um comando ao Node pelo caminho API -> Orion -> IoT Agent -> MQTT -> ESP32."""
    if corpo.comando not in COMANDOS:
        raise HTTPException(status_code=400, detail=f"comando inválido. Use: {sorted(COMANDOS)}")
    try:
        entidade = dominio.entidade_do_dispositivo(device_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        service = vinheriaId or config.FIWARE_SERVICE
        servicepath = await fiware.resolver_servicepath(cliente, device_id, service)
        await fiware.enviar_comando(cliente, entidade, corpo.comando, corpo.valor, service, servicepath)
    except fiware.FiwareIndisponivel as exc:
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")
    return {"enviado": True}
