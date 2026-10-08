"""
Testes do cadastro (Backend 2).

1) Regras puras (dominio.py).
2) Fluxo completo (cadastro.py + fiware.py) contra um FIWARE falso em memória, que imita só o que
   importa do Orion (1026) e do IoT Agent (4041). Não substitui o teste com o lab ligado.

Rodar, na pasta backend:   python -m unittest discover -s tests -v
"""

import copy
import json as jsonlib
import sys
import types
import unittest
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

from app import cadastro, config, dominio, fiware  # noqa: E402

AGORA = datetime(2026, 10, 8, 12, 0, 30, tzinfo=timezone.utc)
VIN = "vin_demo"


# ---------------------------------------------------------------- regras puras
class TestIdsEAdegas(unittest.TestCase):
    def test_device_id_da_entidade(self):
        self.assertEqual(dominio.device_id_da_entidade("urn:ngsi-ld:WineGuardNode:002"), "wgn002")
        for fantasma in ["WineGuardNode:wgn001", "urn:ngsi-ld:Contador:dispositivos", "", None]:
            self.assertIsNone(dominio.device_id_da_entidade(fantasma))

    def test_proximo_numero(self):
        self.assertEqual(dominio.proximo_numero([]), 1)
        self.assertEqual(dominio.proximo_numero(["wgn001", "wgn007"]), 8)
        self.assertEqual(dominio.proximo_numero(["wgn001"], minimo=5), 5)
        self.assertEqual(dominio.device_id_do_numero(2), "wgn002")
        self.assertEqual(dominio.device_id_do_numero(1234), "wgn1234")

    def test_servicepath_da_nova_adega(self):
        self.assertEqual(dominio.servicepath_da_nova_adega("Adega do Porão"), "/adega_do_porao")
        self.assertEqual(dominio.servicepath_da_nova_adega("  Sala 2 / Fundos! "), "/sala_2_fundos")
        for ruim in ["", "   ", "!!!"]:
            with self.assertRaises(ValueError):
                dominio.servicepath_da_nova_adega(ruim)

    def test_adega_ida_e_volta(self):
        self.assertEqual(dominio.adega_id(VIN, "/adega1"), "vin_demo/adega1")
        self.assertEqual(dominio.servicepath_da_adega("vin_demo/adega1", VIN), "/adega1")
        for ruim in ["outra/adega1", "vin_demo/", "vin_demo/a/b", "vin_demo/ADEGA", "adega1", None, "vin_demo/../x"]:
            with self.assertRaises(ValueError, msg=str(ruim)):
                dominio.servicepath_da_adega(ruim, VIN)

    def test_nome_da_adega(self):
        self.assertEqual(dominio.nome_da_adega("/adega1"), "Adega 1")
        self.assertEqual(dominio.nome_da_adega("/porao_sul"), "Porao Sul")


class TestValidacao(unittest.TestCase):
    def test_ok_com_padroes(self):
        r = dominio.validar_cadastro({"nome": "  Sensor A ", "adegaId": "vin_demo/adega1"})
        self.assertEqual(r, {"nome": "Sensor A", "preset": "guarda_geral", "adegaId": "vin_demo/adega1", "novaAdega": None})

    def test_nova_adega(self):
        r = dominio.validar_cadastro({"nome": "A", "preset": "espumante", "novaAdega": "Porão", "adegaId": ""})
        self.assertEqual((r["novaAdega"], r["adegaId"], r["preset"]), ("Porão", None, "espumante"))

    def test_erros(self):
        casos = [None, {}, {"nome": "", "adegaId": "x"}, {"nome": "x" * 61, "adegaId": "x"},
                 {"nome": "A", "preset": "xyz", "adegaId": "x"},
                 {"nome": "A"}, {"nome": "A", "adegaId": "x", "novaAdega": "y"}]
        for c in casos:
            with self.assertRaises(ValueError, msg=str(c)):
                dominio.validar_cadastro(c)


class TestCorpos(unittest.TestCase):
    def test_dispositivo_leva_apikey_e_comandos(self):
        d = dominio.corpo_dispositivo("wgn002", "winedemo", "urn:ngsi-ld:WineGuardNode:002")["devices"][0]
        self.assertEqual((d["apikey"], d["device_id"], d["transport"]), ("winedemo", "wgn002", "MQTT"))
        self.assertEqual(len(d["commands"]), 7)
        self.assertEqual([a["object_id"] for a in d["attributes"]], ["t", "h", "l", "st", "mu", "rs", "fw"])

    def test_grupo(self):
        g = dominio.corpo_grupo("winedemo", "http://fiware-orion:1026")["services"][0]
        self.assertEqual((g["apikey"], g["resource"], g["entity_type"]), ("winedemo", "/iot/d", "WineGuardNode"))

    def test_assinatura_com_timeinstant_so_na_condicao(self):
        a = dominio.corpo_assinatura("http://x/notify")
        self.assertIn("TimeInstant", a["subject"]["condition"]["attrs"])
        self.assertNotIn("TimeInstant", a["notification"]["attrs"])
        self.assertFalse(dominio.assinatura_precisa_atualizar(a))

    def test_assinatura_antiga_precisa_atualizar(self):
        antiga = {"subject": {"condition": {"attrs": ["temperature", "humidity", "luminosity"]}}}
        self.assertTrue(dominio.assinatura_precisa_atualizar(antiga))
        self.assertTrue(dominio.assinatura_precisa_atualizar({}))


class TestRespostas(unittest.TestCase):
    def test_dispositivo_antigo_usa_reservas(self):
        r = dominio.montar_dispositivo(VIN, {"id": "urn:ngsi-ld:WineGuardNode:001"}, "/adega1")
        self.assertEqual(r, {"id": "wgn001", "vinheriaId": VIN, "adegaId": "vin_demo/adega1",
                             "nome": "Dispositivo 001", "preset": "guarda_geral", "criadoEm": None})

    def test_dispositivo_com_metadados(self):
        meta = dominio.metadados_do_dispositivo("Sensor", "espumante", "vin_demo/porao", "Porão", "2026-10-08T12:00:00.000Z")
        r = dominio.montar_dispositivo(VIN, {"id": "urn:ngsi-ld:WineGuardNode:003", **meta}, "/adega1")
        self.assertEqual((r["nome"], r["preset"], r["adegaId"], r["criadoEm"]),
                         ("Sensor", "espumante", "vin_demo/porao", "2026-10-08T12:00:00.000Z"))

    def test_resumo_item(self):
        atual = {"deviceId": "wgn001", "estado": "alerta", "ultimaLeitura": "t"}
        self.assertEqual(dominio.montar_resumo_item(atual),
                         {"deviceId": "wgn001", "estado": "alerta", "ultimaLeitura": "t", "alertasAtivos": 1})
        atual["estado"] = "ok"
        self.assertEqual(dominio.montar_resumo_item(atual)["alertasAtivos"], 0)


# ------------------------------------------------------------- FIWARE falso
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
        self._seq = 0

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
                    self.comandos.append((chave[2], list(corpo)))
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


class CasoComFiware(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fiware._cache_servicepath.clear()
        self.fake = FakeCliente()
        semear(self.fake)

    async def cadastrar(self, **corpo):
        base = {"nome": "Sensor", "adegaId": "vin_demo/adega1"}
        base.update(corpo)
        return await cadastro.cadastrar(self.fake, VIN, base, AGORA)


class TestCadastrar(CasoComFiware):
    async def test_adega_existente(self):
        r = await self.cadastrar(nome="Sensor B", preset="espumante")
        self.assertEqual(r["config"], {"deviceId": "wgn002", "apikey": "winedemo",
                                       "nomeVinheria": config.NOME_VINHERIA, "nomeAdega": "Adega 1"})
        self.assertEqual(r["dispositivo"], {"id": "wgn002", "vinheriaId": VIN, "adegaId": "vin_demo/adega1",
                                            "nome": "Sensor B", "preset": "espumante",
                                            "criadoEm": "2026-10-08T12:00:30.000Z"})
        registrado = self.fake.dispositivos[(VIN, "wgn002")]
        self.assertEqual(registrado["apikey"], "winedemo")
        self.assertEqual(registrado["entity_name"], "urn:ngsi-ld:WineGuardNode:002")
        entidade = self.fake.entidades[(VIN, "/adega1", "urn:ngsi-ld:WineGuardNode:002")]
        self.assertEqual(entidade["nome"]["value"], "Sensor B")

    async def test_assinatura_antiga_ganha_timeinstant(self):
        await self.cadastrar()
        self.assertEqual(len(self.fake.assinaturas), 1)
        self.assertIn("TimeInstant", self.fake.assinaturas[0]["subject"]["condition"]["attrs"])

    async def test_nova_adega_cria_servicepath_grupo_e_assinatura(self):
        r = await self.cadastrar(adegaId=None, novaAdega="Porão Sul")
        self.assertEqual(r["dispositivo"]["adegaId"], "vin_demo/porao_sul")
        self.assertEqual(r["config"]["nomeAdega"], "Porão Sul")
        self.assertIn((VIN, "/porao_sul", "winedemo"), self.fake.grupos)
        self.assertTrue(any(s["_sp"] == "/porao_sul" and "TimeInstant" in s["subject"]["condition"]["attrs"]
                            for s in self.fake.assinaturas))
        self.assertIn((VIN, "/porao_sul", "urn:ngsi-ld:WineGuardNode:002"), self.fake.entidades)

    async def test_segundo_dispositivo_na_adega_nova_reusa_o_nome(self):
        await self.cadastrar(adegaId=None, novaAdega="Porão Sul")
        r = await self.cadastrar(nome="Outro", adegaId="vin_demo/porao_sul")
        self.assertEqual((r["dispositivo"]["id"], r["config"]["nomeAdega"]), ("wgn003", "Porão Sul"))

    async def test_nova_adega_com_nome_repetido(self):
        await self.cadastrar(adegaId=None, novaAdega="Porão Sul")
        with self.assertRaises(ValueError):
            await self.cadastrar(adegaId=None, novaAdega="porao sul")
        with self.assertRaises(ValueError):
            await self.cadastrar(adegaId=None, novaAdega="Adega1")  # colide com o servicepath padrão

    async def test_ids_nunca_se_repetem(self):
        a = await self.cadastrar()
        await cadastro.remover(self.fake, VIN, a["config"]["deviceId"])
        b = await self.cadastrar()
        self.assertEqual((a["config"]["deviceId"], b["config"]["deviceId"]), ("wgn002", "wgn003"))

    async def test_erros_de_entrada(self):
        with self.assertRaises(ValueError):
            await self.cadastrar(adegaId="vin_demo/nao_existe")
        with self.assertRaises(ValueError):
            await self.cadastrar(adegaId="outra/adega1")
        with self.assertRaises(ValueError):
            await self.cadastrar(novaAdega="X")  # adegaId E novaAdega
        with self.assertRaises(ValueError):
            await self.cadastrar(nome="")
        self.assertEqual(len(self.fake.dispositivos), 1)  # nada foi registrado

    async def test_vinheria_desconhecida(self):
        with self.assertRaises(cadastro.VinheriaDesconhecida):
            await cadastro.cadastrar(self.fake, "vin_outra", {"nome": "A", "adegaId": "vin_outra/x"}, AGORA)

    async def test_id_ja_existente_no_iot_agent_tenta_o_proximo(self):
        self.fake.dispositivos[(VIN, "wgn002")] = {}  # existe no IoT Agent mas sem entidade no Orion
        r = await self.cadastrar()
        self.assertEqual(r["config"]["deviceId"], "wgn003")

    async def test_falha_ao_gravar_desfaz_o_registro(self):
        self.fake.quebrar_metadados = True
        with self.assertRaises(fiware.FiwareIndisponivel):
            await self.cadastrar()
        self.assertNotIn((VIN, "wgn002"), self.fake.dispositivos)
        self.assertEqual(list(self.fake.dispositivos), [(VIN, "wgn001")])

    async def test_dois_cadastros_ao_mesmo_tempo_recebem_ids_diferentes(self):
        import asyncio
        rs = await asyncio.gather(self.cadastrar(nome="A"), self.cadastrar(nome="B"), self.cadastrar(nome="C"))
        ids = sorted(r["config"]["deviceId"] for r in rs)
        self.assertEqual(ids, ["wgn002", "wgn003", "wgn004"])


class TestListarEResumir(CasoComFiware):
    async def test_listar_ignora_fantasma_e_usa_reservas(self):
        await self.cadastrar(nome="Sensor B")
        itens = await cadastro.listar(self.fake, VIN)
        self.assertEqual([i["id"] for i in itens], ["wgn001", "wgn002"])
        self.assertEqual(itens[0]["nome"], "Dispositivo 001")
        self.assertEqual(itens[1]["nome"], "Sensor B")
        for i in itens:
            self.assertEqual(set(i), {"id", "vinheriaId", "adegaId", "nome", "preset", "criadoEm"})

    async def test_listar_junta_todas_as_adegas(self):
        await self.cadastrar(adegaId=None, novaAdega="Porão Sul")
        itens = await cadastro.listar(self.fake, VIN)
        self.assertEqual({i["adegaId"] for i in itens}, {"vin_demo/adega1", "vin_demo/porao_sul"})

    async def test_resumo(self):
        await self.cadastrar()
        itens = await cadastro.resumo(self.fake, VIN, AGORA)
        self.assertEqual([i["deviceId"] for i in itens], ["wgn001", "wgn002"])
        self.assertEqual(itens[0]["estado"], "ok")
        self.assertEqual(itens[1]["estado"], "aguardando")  # cadastrado mas ainda sem leitura
        self.assertEqual(set(itens[0]), {"deviceId", "estado", "ultimaLeitura", "alertasAtivos"})

    async def test_vinheria_desconhecida(self):
        with self.assertRaises(cadastro.VinheriaDesconhecida):
            await cadastro.resumo(self.fake, "vin_outra", AGORA)
        with self.assertRaises(cadastro.VinheriaDesconhecida):
            await cadastro.listar(self.fake, "vin_outra")


class TestAtualizarERemover(CasoComFiware):
    async def test_renomear(self):
        r = await self.cadastrar()
        novo = await cadastro.atualizar(self.fake, VIN, "wgn002", {"nome": "  Novo nome "})
        self.assertEqual((novo["nome"], novo["id"]), ("Novo nome", "wgn002"))
        itens = await cadastro.listar(self.fake, VIN)
        self.assertEqual(itens[1]["nome"], "Novo nome")
        self.assertEqual(r["dispositivo"]["preset"], itens[1]["preset"])

    async def test_renomear_aceita_mesma_adega_e_recusa_outra(self):
        await self.cadastrar()
        await cadastro.atualizar(self.fake, VIN, "wgn002", {"nome": "X", "adegaId": "vin_demo/adega1"})
        with self.assertRaises(ValueError):
            await cadastro.atualizar(self.fake, VIN, "wgn002", {"nome": "X", "adegaId": "vin_demo/outra"})
        with self.assertRaises(ValueError):
            await cadastro.atualizar(self.fake, VIN, "wgn002", {"nome": ""})

    async def test_atualizar_inexistente(self):
        with self.assertRaises(cadastro.DispositivoNaoEncontrado):
            await cadastro.atualizar(self.fake, VIN, "wgn099", {"nome": "X"})

    async def test_remover_limpa_tudo_e_suspende_antes(self):
        await self.cadastrar()
        await cadastro.remover(self.fake, VIN, "wgn002")
        self.assertEqual(self.fake.comandos, [("urn:ngsi-ld:WineGuardNode:002", ["suspend"])])
        self.assertNotIn((VIN, "wgn002"), self.fake.dispositivos)
        self.assertNotIn((VIN, "/adega1", "urn:ngsi-ld:WineGuardNode:002"), self.fake.entidades)
        with self.assertRaises(cadastro.DispositivoNaoEncontrado):
            await cadastro.remover(self.fake, VIN, "wgn002")

    async def test_remover_wgn001_apaga_tambem_a_entidade_fantasma(self):
        await cadastro.remover(self.fake, VIN, "wgn001")
        self.assertEqual(self.fake.entidades, {})

    async def test_remover_em_adega_nova(self):
        await self.cadastrar(adegaId=None, novaAdega="Porão Sul")
        fiware._cache_servicepath.clear()
        await cadastro.remover(self.fake, VIN, "wgn002")
        self.assertNotIn((VIN, "/porao_sul", "urn:ngsi-ld:WineGuardNode:002"), self.fake.entidades)

    async def test_id_invalido(self):
        with self.assertRaises(ValueError):
            await cadastro.remover(self.fake, VIN, "../x")


class TestResolverServicepath(CasoComFiware):
    async def test_acha_a_adega_pelo_adegaid(self):
        await self.cadastrar(adegaId=None, novaAdega="Porão Sul")
        fiware._cache_servicepath.clear()
        self.assertEqual(await fiware.resolver_servicepath(self.fake, "wgn002", VIN), "/porao_sul")

    async def test_dispositivo_antigo_usa_o_padrao_e_fica_em_cache(self):
        self.assertEqual(await fiware.resolver_servicepath(self.fake, "wgn001", VIN), "/adega1")
        antes = len(self.fake.entidades)
        self.fake.entidades.clear()
        self.assertEqual(await fiware.resolver_servicepath(self.fake, "wgn001", VIN), "/adega1")  # cache
        self.assertEqual(antes, 2)

    async def test_desconhecido_cai_no_padrao(self):
        self.assertEqual(await fiware.resolver_servicepath(self.fake, "wgn050", VIN), config.FIWARE_SERVICEPATH)


if __name__ == "__main__":
    unittest.main()
