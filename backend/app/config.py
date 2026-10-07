"""Configuração do backend. Tudo vem de variáveis de ambiente (arquivo .env)."""

import os

from dotenv import load_dotenv

load_dotenv()  # lê o arquivo .env da pasta de onde o servidor foi iniciado

FIWARE_HOST = os.getenv("FIWARE_HOST", "localhost")
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "vin_demo")
FIWARE_SERVICEPATH = os.getenv("FIWARE_SERVICEPATH", "/adega1")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
OFFLINE_SEGUNDOS = int(os.getenv("OFFLINE_SEGUNDOS", "30"))

ORION_URL = f"http://{FIWARE_HOST}:1026"
STH_URL = f"http://{FIWARE_HOST}:8666"
TIPO_ENTIDADE = "WineGuardNode"
