"""Envio de comandos ao Node (mute, identify, ...)."""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import config, dominio, fiware, vinherias
from .leituras import cliente_http
from .util import executar

router = APIRouter(prefix="/api/dispositivos", tags=["comandos"])

# Comandos que o Node aceita (ver o firmware: executaComando)
COMANDOS = set(dominio.COMANDOS_DO_NODE)


class Comando(BaseModel):
    comando: str        # ex.: "mute"
    valor: str = ""     # ex.: "1"  |  "t,high,1"  |  "12,16,60,75,0,10"


@router.post("/{device_id}/comando")
async def enviar_comando(device_id: str, corpo: Comando, vinheriaId: Optional[str] = None,
                         cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Manda um comando ao Node pelo caminho API -> Orion -> IoT Agent -> MQTT -> ESP32."""
    if corpo.comando not in COMANDOS:
        raise HTTPException(status_code=400, detail=f"comando inválido. Use: {sorted(COMANDOS)}")

    async def enviar():
        entidade = dominio.entidade_do_dispositivo(device_id)
        service = vinheriaId or config.FIWARE_SERVICE
        await vinherias.exigir(cliente, service)
        servicepath = await fiware.resolver_servicepath(cliente, device_id, service)
        await fiware.enviar_comando(cliente, entidade, corpo.comando, corpo.valor, service, servicepath)
        return {"enviado": True}
    return await executar(enviar())
