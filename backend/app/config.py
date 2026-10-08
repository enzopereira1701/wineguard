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

# --- Triggers e alertas (Backend 3)
# Liga o vigia: o loop que avalia os triggers a cada INTERVALO_VIGIA segundos (0 = desligado)
VIGIA_ATIVO = os.getenv("VIGIA_ATIVO", "1") not in ("0", "false", "False", "")
INTERVALO_VIGIA = max(2, int(os.getenv("INTERVALO_VIGIA", "5")))
# Quanto o PUT /triggers espera o Node confirmar (cmdexe) antes de desistir
ESPERA_COMANDO_SEGUNDOS = float(os.getenv("ESPERA_COMANDO_SEGUNDOS", "8"))
# Segundos sem o estado do Node bater com o esperado, antes de reenviar os alertas
RECONCILIAR_SEGUNDOS = int(os.getenv("RECONCILIAR_SEGUNDOS", "15"))


def vinherias_conhecidas() -> list:
    """Vinherias que o vigia acompanha. Por enquanto só a padrão; o Backend 4 traz o cadastro."""
    return [FIWARE_SERVICE]
