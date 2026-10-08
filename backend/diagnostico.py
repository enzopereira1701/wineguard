"""
Diagnóstico do FIWARE (sem FastAPI, sem instalar nada): mostra a resposta CRUA do Orion e do STH-Comet.

Use quando algo não aparece na API: este script diz se o problema é a rede, o cadastro ou o formato.

    python diagnostico.py            # usa wgn001
    python diagnostico.py wgn002
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


def ler_env():
    """Lê o .env (se existir) e as variáveis de ambiente."""
    valores = {}
    if os.path.exists(".env"):
        for linha in open(".env", encoding="utf-8"):
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                valores[k.strip()] = v.strip()
    return {**valores, **{k: v for k, v in os.environ.items() if k.startswith("FIWARE_")}}


def pedir(url, cab):
    req = urllib.request.Request(url, headers=cab)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # rede, DNS, porta fechada...
        return None, f"{type(e).__name__}: {e}"


def mostrar(titulo, status, corpo):
    print(f"\n=== {titulo}\nHTTP {status}")
    try:
        print(json.dumps(json.loads(corpo), indent=2, ensure_ascii=False)[:2500])
    except ValueError:
        print(corpo[:600])


env = ler_env()
host = env.get("FIWARE_HOST", "localhost")
cab = {"fiware-service": env.get("FIWARE_SERVICE", "vin_demo"), "fiware-servicepath": env.get("FIWARE_SERVICEPATH", "/adega1")}
device = sys.argv[1] if len(sys.argv) > 1 else "wgn001"
entidade = f"urn:ngsi-ld:WineGuardNode:{device[3:]}"
print(f"FIWARE em {host} | service={cab['fiware-service']} servicepath={cab['fiware-servicepath']} | {device}")

s, c = pedir(f"http://{host}:1026/version", {})
mostrar("Orion: versão (porta 1026)", s, c)

s, c = pedir(f"http://{host}:1026/v2/entities/{entidade}?type=WineGuardNode&attrs=temperature,state&metadata=dateModified", cab)
mostrar(f"Orion: entidade {entidade}", s, c)

s, c = pedir(f"http://{host}:4041/iot/about", {})
mostrar("IoT Agent (porta 4041)", s, c)

s, c = pedir(f"http://{host}:4041/iot/devices", cab)
mostrar("IoT Agent: dispositivos deste service/servicepath", s, c)

s, c = pedir(f"http://{host}:1026/v2/entities?type=WineGuardNode&limit=1000&attrs=nome,adegaId", {**cab, "fiware-servicepath": "/#"})
mostrar("Orion: entidades de TODAS as adegas (servicepath /#)", s, c)

s, c = pedir(f"http://{host}:1026/v2/subscriptions?limit=100", cab)
mostrar("Orion: assinaturas (confira se a condição tem TimeInstant)", s, c)

fim = datetime.now(timezone.utc)
ini = fim - timedelta(hours=1)
fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.000Z")
url = (f"http://{host}:8666/STH/v1/contextEntities/type/WineGuardNode/id/{entidade}/attributes/temperature"
       f"?aggrMethod=sum&aggrPeriod=minute&dateFrom={fmt(ini)}&dateTo={fmt(fim)}")
s, c = pedir(url, cab)
mostrar("STH-Comet: média por minuto da última hora (temperature)", s, c)

print("\nSe o HTTP veio como 'None': a porta está fechada no Security Group da AWS, o lab está desligado ou o IP/nome está errado.")
print("Se for 404 na entidade: o Node ainda não enviou nada com este service/servicepath (rode o provisionar.sh e ligue o Wokwi/Node).")
