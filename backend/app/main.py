"""
WineGuard Cloud: backend (marcha.dev)

Ponte entre o dashboard (React) e o FIWARE:
  - lê o último valor no Orion (porta 1026)
  - lê o histórico no STH-Comet (porta 8666)
  - envia comandos ao Node pelo Orion
  - cadastra dispositivos no IoT Agent (porta 4041) e resume o estado da vinheria
  - guarda os triggers de cada dispositivo e os envia ao Node
  - vigia: a cada 5 s avalia os triggers, abre/encerra alertas e comanda o Node

Rodar (na pasta backend, com o ambiente virtual ativo):
    uvicorn app.main:app --reload
Documentação interativa:  http://127.0.0.1:8000/docs
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, vigia
from .rotas import alertas, comandos, dispositivos, leituras, triggers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s", datefmt="%H:%M:%S")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Liga o vigia (avaliação dos triggers a cada poucos segundos) junto com a API."""
    tarefa = asyncio.create_task(vigia.executar()) if config.VIGIA_ATIVO else None
    try:
        yield
    finally:
        if tarefa:
            tarefa.cancel()


app = FastAPI(title="WineGuard Cloud", version="0.4.0", lifespan=ciclo_de_vida)

# CORS: deixa o dashboard (React) chamar esta API a partir do navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leituras.router)
app.include_router(comandos.router)
app.include_router(dispositivos.router)
app.include_router(triggers.router)
app.include_router(alertas.router)


@app.get("/saude", tags=["geral"])
async def saude():
    """Confere se a API está no ar e para onde ela aponta."""
    return {"status": "ok", "fiware_host": config.FIWARE_HOST, "service": config.FIWARE_SERVICE,
            "servicepath": config.FIWARE_SERVICEPATH, "vigia": config.VIGIA_ATIVO}
