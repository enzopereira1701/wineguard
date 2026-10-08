"""
FIWARE falso para os testes: imita só o que importa do Orion (porta 1026) e do IoT Agent (4041),
tudo em memória. Não substitui o teste com o lab ligado.
"""

import copy
import json as jsonlib
import sys
import types
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# httpx/dotenv só são necessários com a API de verdade; aqui bastam atrapalhos se não estiverem instalados
try:
    import httpx  # noqa: F401
except ImportError:  # pragma: no cover
    _h = types.ModuleType("httpx")
    _h.HTTPError = type("HTTPError", (Exception,), {})
    _h.AsyncClient = object
    sys.modules["httpx"] = _h
try:
    import dotenv  # noqa: F401
except ImportError:  # pragma: no cover
    _d = types.ModuleType("dotenv")
    _d.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = _d

from app import config, dominio  # noqa: E402

AGORA = datetime(2026, 10, 8, 12, 0, 30, tzinfo=timezone.utc)
VIN = "vin_demo"


class Resp:
    def __init__(self, status, corpo=None):
        self.status_code = status
        self._corpo = corpo
        self.text = jsonlib.dumps(corpo) if corpo is not None else ""

    def json(self):
        return self._corpo


class FakeCliente:
    """Orion (porta 1026) e IoT Agent (4041) em memória."""

    def __init__(self):
        self.entidades = {}      # (service, servicepath, id) -> {"type":..., atributos...}
        self.assinaturas = []    # dicts com _service e _sp
        self.grupos = set()      # (service, servicepath, apikey)
        self.dispositivos = {}   # (service, device_id) -> corpo registrado
        self.comandos = []       # (entidade, [comandos])
        self.quebrar_metadados = False
        self.falhar_comandos = False
        self.responder = "ok"    # como o Node responde aos comandos: ok | erro | pendente | nada
        self.comandos_valores = []   # (entidade, comando, valor)
        self._seq = 0
        self._relogio = datetime(2026, 10, 8, 9, 0, 0, tzinfo=timezone.utc)

    def _carimbo(self):
        """Hora do Orion para o dateModified: cada escrita é 1 s mais nova que a anterior."""
        self._relogio += timedelta(seconds=1)
        return self._relogio.strftime("%Y-%m-%dT%H:%M:%S.00Z")

    async def request(self, metodo, url, params=None, json=None, headers=None):
        u = urlparse(url)
        service, sp = headers["fiware-service"], headers["fiware-servicepath"]
        if u.port == 1026:
            return self._orion(metodo, u.path, params or {}, json, service, sp)
        if u.port == 4041:
            return self._iota(metodo, u.path, json, service, sp)
        raise AssertionError(f"porta inesperada: {url}")

    # ---- Orion
    def _orion(self, m, caminho, params, corpo, service, sp):
        admin = service == config.ADMIN_SERVICE
        if caminho == "/v2/entities" and m == "GET":
            saida = []
            for (s, p, i), a in self.entidades.items():
                if s != service or (sp != "/#" and p != sp):
                    continue
                if params.get("id") and i != params["id"]:
                    continue
                if params.get("type") and a["type"] != params["type"]:
                    continue
                saida.append({"id": i, **copy.deepcopy(a)})
            return Resp(200, saida)
        if caminho == "/v2/entities" and m == "POST":
            if self.quebrar_metadados and not admin:
                return Resp(500, {"error": "InternalServerError"})
            chave = (service, sp, corpo["id"])
            if chave in self.entidades:
                return Resp(422, {"error": "Unprocessable"})
            self.entidades[chave] = {k: v for k, v in corpo.items() if k != "id"}
            return Resp(201)
        if caminho.startswith("/v2/entities/"):
            resto = caminho[len("/v2/entities/"):]
            if resto.endswith("/attrs"):
                chave = (service, sp, resto[:-len("/attrs")])
                if chave not in self.entidades:
                    return Resp(404, {"error": "NotFound"})
                if m == "POST":
                    if self.quebrar_metadados and not admin:
                        return Resp(500, {"error": "InternalServerError"})
                    self.entidades[chave].update(copy.deepcopy(corpo))
                    return Resp(204)
                if m == "PATCH":
                    if self.falhar_comandos:
                        return Resp(500, {"error": "InternalServerError"})
                    self.comandos.append((chave[2], list(corpo)))
                    for nome, atributo in corpo.items():
                        self.comandos_valores.append((chave[2], nome, atributo.get("value")))
                        # o IoT Agent grava <comando>_status quando o Node responde
                        situacao = {"ok": "OK", "erro": "ERROR", "pendente": "PENDING"}.get(self.responder)
                        if situacao:
                            self.entidades[chave][f"{nome}_status"] = {
                                "type": "commandStatus", "value": situacao,
                                "metadata": {"dateModified": {"type": "DateTime", "value": self._carimbo()}}}
                    return Resp(204)
            else:
                chave = (service, sp, resto)
                if m == "GET":
                    if chave not in self.entidades:
                        return Resp(404, {"error": "NotFound"})
                    return Resp(200, {"id": resto, **copy.deepcopy(self.entidades[chave])})
                if m == "DELETE":
                    return Resp(204) if self.entidades.pop(chave, None) is not None else Resp(404)
        if caminho == "/v2/subscriptions":
            if m == "GET":
                return Resp(200, [{k: v for k, v in s.items() if not k.startswith("_")}
                                  for s in self.assinaturas if s["_service"] == service and s["_sp"] == sp])
            if m == "POST":
                self._seq += 1
                self.assinaturas.append({"id": f"sub{self._seq}", "_service": service, "_sp": sp, **copy.deepcopy(corpo)})
                return Resp(201)
        if caminho.startswith("/v2/subscriptions/") and m == "PATCH":
            ident = caminho.rsplit("/", 1)[1]
            for s in self.assinaturas:
                if s["id"] == ident:
                    s.update(copy.deepcopy(corpo))
                    return Resp(204)
            return Resp(404)
        raise AssertionError(f"Orion: rota não simulada {m} {caminho}")

    # ---- IoT Agent
    def _iota(self, m, caminho, corpo, service, sp):
        if caminho == "/iot/services" and m == "POST":
            chave = (service, sp, corpo["services"][0]["apikey"])
            if chave in self.grupos:
                return Resp(409)
            self.grupos.add(chave)
            return Resp(201)
        if caminho == "/iot/devices" and m == "POST":
            d = corpo["devices"][0]
            if (service, sp, d["apikey"]) not in self.grupos:
                return Resp(400, {"name": "MISSING_GROUP"})
            if (service, d["device_id"]) in self.dispositivos:
                return Resp(409)
            self.dispositivos[(service, d["device_id"])] = d
            return Resp(201)
        if caminho.startswith("/iot/devices/") and m == "DELETE":
            chave = (service, caminho.rsplit("/", 1)[1])
            return Resp(204) if self.dispositivos.pop(chave, None) is not None else Resp(404)
        raise AssertionError(f"IoT Agent: rota não simulada {m} {caminho}")


def semear(fake):
    """Estado de partida: wgn001 como está hoje (criado à mão, sem nome, assinatura antiga) + fantasma."""
    instante = (AGORA - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%S.00Z")
    fake.entidades[(VIN, "/adega1", "urn:ngsi-ld:WineGuardNode:001")] = {
        "type": "WineGuardNode",
        "temperature": {"type": "Number", "value": 13.4, "metadata": {}},
        "humidity": {"type": "Number", "value": 68.2, "metadata": {}},
        "luminosity": {"type": "Number", "value": 3, "metadata": {}},
        "state": {"type": "Text", "value": "ok", "metadata": {}},
        "TimeInstant": {"type": "DateTime", "value": instante, "metadata": {}},
    }
    fake.entidades[(VIN, "/adega1", "WineGuardNode:wgn001")] = {"type": "WineGuardNode"}
    fake.grupos.add((VIN, "/adega1", "winedemo"))
    fake.dispositivos[(VIN, "wgn001")] = {}
    fake.assinaturas.append({
        "id": "sub0", "_service": VIN, "_sp": "/adega1", "description": dominio.DESCRICAO_ASSINATURA,
        "subject": {"entities": [{"idPattern": ".*", "type": "WineGuardNode"}],
                    "condition": {"attrs": ["temperature", "humidity", "luminosity"]}},
        "notification": {"http": {"url": config.STH_NOTIFY_INTERNO}, "attrs": ["temperature"], "attrsFormat": "legacy"},
    })


def definir_leitura(fake, agora, device="wgn001", servicepath="/adega1", temperatura=13.4, umidade=68.2,
                    luz=3, state="ok", segundos_atras=5, service=VIN):
    """Põe uma leitura (chegada há 'segundos_atras' segundos) na entidade do dispositivo."""
    instante = (agora - timedelta(seconds=segundos_atras)).strftime("%Y-%m-%dT%H:%M:%S.00Z")
    entidade = fake.entidades.setdefault((service, servicepath, f"urn:ngsi-ld:WineGuardNode:{device[3:]}"),
                                         {"type": "WineGuardNode"})
    entidade.update({
        "temperature": {"type": "Number", "value": temperatura, "metadata": {}},
        "humidity": {"type": "Number", "value": umidade, "metadata": {}},
        "luminosity": {"type": "Number", "value": luz, "metadata": {}},
        "state": {"type": "Text", "value": state, "metadata": {}},
        "TimeInstant": {"type": "DateTime", "value": instante, "metadata": {}},
    })
