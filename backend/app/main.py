"""
WineGuard Cloud: backend (marcha.dev)

Ponte entre o dashboard (React) e o FIWARE:
  - lê o último valor no Orion (porta 1026)
  - lê o histórico no STH-Comet (porta 8666)
  - envia comandos ao Node pelo Orion

Rodar (na pasta backend, com o ambiente virtual ativo):
    uvicorn app.main:app --reload
Documentação interativa:  http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .rotas import comandos, leituras

app = FastAPI(title="WineGuard Cloud", version="0.2.0")

# CORS: deixa o dashboard (React) chamar esta API a partir do navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leituras.router)
app.include_router(comandos.router)


@app.get("/saude", tags=["geral"])
async def saude():
    """Confere se a API está no ar e para onde ela aponta."""
    return {"status": "ok", "fiware_host": config.FIWARE_HOST, "service": config.FIWARE_SERVICE,
            "servicepath": config.FIWARE_SERVICEPATH}
