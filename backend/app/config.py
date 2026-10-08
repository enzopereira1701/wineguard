"""Configuração do backend. Tudo vem de variáveis de ambiente (arquivo .env)."""

import os

from dotenv import load_dotenv

load_dotenv()  # lê o arquivo .env da pasta de onde o servidor foi iniciado

FIWARE_HOST = os.getenv("FIWARE_HOST", "localhost")
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "vin_demo")
FIWARE_SERVICEPATH = os.getenv("FIWARE_SERVICEPATH", "/adega1")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
OFFLINE_SEGUNDOS = int(os.getenv("OFFLINE_SEGUNDOS", "30"))

# --- Cadastro de dispositivos (Backend 2)
# apikey do grupo de dispositivos da vinheria: vai no tópico MQTT (/<apikey>/<device_id>/attrs)
APIKEY = os.getenv("FIWARE_APIKEY", "winedemo")
NOME_VINHERIA = os.getenv("NOME_VINHERIA", "Vinheria Demo")
# Serviço "de administração": guarda o contador global de dispositivos (ids nunca se repetem)
ADMIN_SERVICE = os.getenv("ADMIN_SERVICE", "wineguard_admin")

ORION_URL = f"http://{FIWARE_HOST}:1026"
STH_URL = f"http://{FIWARE_HOST}:8666"
IOTA_URL = f"http://{FIWARE_HOST}:4041"
TIPO_ENTIDADE = "WineGuardNode"

# Endereços que o IoT Agent e o Orion usam ENTRE OS CONTAINERS (rede interna do Docker)
CBROKER_INTERNO = os.getenv("CBROKER_INTERNO", "http://fiware-orion:1026")
STH_NOTIFY_INTERNO = os.getenv("STH_NOTIFY_INTERNO", "http://fiware-sth-comet:8666/notify")


def apikey_da_vinheria(vinheria_id: str):
    """
    apikey da vinheria, ou None se a vinheria não existe.
    Por enquanto só a vinheria padrão é conhecida; o cadastro de vinherias chega no Backend 4.
    """
    return APIKEY if vinheria_id == FIWARE_SERVICE else None
