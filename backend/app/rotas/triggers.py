"""Triggers de um dispositivo: ler e salvar (salvar também envia ao Node e espera a confirmação)."""

from typing import Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException

from .. import cadastro, config, fiware, triggers
from .leituras import cliente_http

router = APIRouter(prefix="/api/dispositivos", tags=["triggers"])


async def _executar(corrotina):
    try:
        return await corrotina
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (cadastro.VinheriaDesconhecida, cadastro.DispositivoNaoEncontrado):
        raise HTTPException(status_code=404, detail="dispositivo não encontrado")
    except triggers.NodeNaoConfirmou as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except fiware.FiwareIndisponivel as exc:
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")


@router.get("/{device_id}/triggers")
async def obter(device_id: str, vinheriaId: Optional[str] = None, cliente: httpx.AsyncClient = Depends(cliente_http)):
    """Triggers em vigor (se nunca foram definidos, os do preset do dispositivo)."""
    return await _executar(triggers.obter(cliente, vinheriaId or config.FIWARE_SERVICE, device_id))


@router.put("/{device_id}/triggers")
async def salvar(device_id: str, corpo: dict = Body(...), vinheriaId: Optional[str] = None,
                 cliente: httpx.AsyncClient = Depends(cliente_http)):
    """
    Valida, salva e manda setTriggers ao Node. Responde {recebido, deviceId, em} quando o Node confirma;
    se ele não confirmar, responde 504 (os limites ficam salvos e são reenviados quando ele voltar).
    """
    return await _executar(triggers.salvar(cliente, vinheriaId or config.FIWARE_SERVICE, device_id, corpo))
