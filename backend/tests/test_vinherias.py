"""
Testes do Backend 4: vinherias, adegas, suspensão e estabilidade.
Regras puras e fluxos completos contra o FIWARE falso (tests/fake_fiware.py).
Rodar, na pasta backend:   python -m unittest discover -s tests -v
"""

import unittest
from datetime import datetime, timedelta, timezone

try:
    from tests.fake_fiware import AGORA, VIN, FakeCliente, definir_leitura, semear
except ImportError:
    from fake_fiware import AGORA, VIN, FakeCliente, definir_leitura, semear

from app import cadastro, config, dominio, estabilidade, fiware, gatilhos, triggers, vigia, vinherias  # noqa: E402
from app import regras_vinheria as regras  # noqa: E402

LONGE = "2099-01-01"   # vencimento que nunca chega nos testes
PASSADO = "2020-01-01"


# ------------------------------------------------------------ regras puras
class TestIds(unittest.TestCase):
    def test_id_valido(self):
        for bom in ["vin_demo", "a", "vin_quinta_do_sol_2"]:
            self.assertTrue(regras.id_valido(bom), bom)
        for ruim in ["", "Vin", "vin demo", "vin-demo", "../x", "a/b", "x" * 51, None, 5]:
            self.assertFalse(regras.id_valido(ruim), str(ruim))

    def test_id_da_vinheria(self):
        self.assertEqual(regras.id_da_vinheria("Quinta do Sol"), "vin_quinta_do_sol")
        self.assertEqual(regras.id_da_vinheria("Adega São João!"), "vin_adega_sao_joao")
        self.assertEqual(regras.id_da_vinheria("Quinta do Sol", {"vin_quinta_do_sol"}), "vin_quinta_do_sol_2")
        self.assertEqual(regras.id_da_vinheria("Quinta do Sol", {"vin_quinta_do_sol", "vin_quinta_do_sol_2"}),
                         "vin_quinta_do_sol_3")
        for ruim in ["", "   ", "!!!"]:
            with self.assertRaises(ValueError):
                regras.id_da_vinheria(ruim)
        self.assertTrue(regras.id_valido(regras.id_da_vinheria("x" * 80)))

    def test_apikey(self):
        self.assertEqual(regras.gerar_apikey("Quinta do Sol", "a3f9"), "quintadosola3f9")
        self.assertEqual(regras.gerar_apikey("!!!", "a3f9"), "vina3f9")
        self.assertNotIn("/", regras.gerar_apikey("A/B c", "0000"))

    def test_entidade_ida_e_volta(self):
        self.assertEqual(regras.id_da_entidade(regras.entidade_da_vinheria("vin_demo")), "vin_demo")
        for ruim in ["urn:ngsi-ld:Vinheria:", "urn:ngsi-ld:Vinheria:A B", "x", None]:
            self.assertIsNone(regras.id_da_entidade(ruim))


class TestNovaVinheria(unittest.TestCase):
    def test_data_simples_e_iso(self):
        r = regras.validar_nova_vinheria({"nome": " Quinta ", "vencimento": "2026-11-30"})
        self.assertEqual((r["nome"], r["vencimento"]), ("Quinta", datetime(2026, 11, 30, tzinfo=timezone.utc)))
        r = regras.validar_nova_vinheria({"nome": "Q", "vencimento": "2026-11-30T15:00:00.000Z"})
        self.assertEqual(r["vencimento"], datetime(2026, 11, 30, 15, tzinfo=timezone.utc))

    def test_erros(self):
        ruins = [None, {}, {"nome": "", "vencimento": "2026-11-30"}, {"nome": "x" * 61, "vencimento": "2026-11-30"},
                 {"nome": "Q"}, {"nome": "Q", "vencimento": ""}, {"nome": "Q", "vencimento": "amanhã"},
                 {"nome": "Q", "vencimento": "2026-13-45"}]
        for corpo in ruins:
            with self.assertRaises(ValueError, msg=str(corpo)):
                regras.validar_nova_vinheria(corpo)


class TestVencimento(unittest.TestCase):
    def test_vencida(self):
        self.assertTrue(regras.vencida({"vencimento": "2026-10-07T00:00:00.000Z"}, AGORA))
        self.assertFalse(regras.vencida({"vencimento": "2026-10-09T00:00:00.000Z"}, AGORA))
        for sem_data in [{}, {"vencimento": None}, {"vencimento": "lixo"}]:
            self.assertFalse(regras.vencida(sem_data, AGORA))

    def test_renovar(self):
        futuro = AGORA + timedelta(days=5)
        self.assertEqual(regras.renovar_vencimento(futuro, AGORA), futuro)
        self.assertEqual(regras.renovar_vencimento(AGORA - timedelta(days=5), AGORA), AGORA + timedelta(days=30))
        self.assertEqual(regras.vencimento_de_ontem(AGORA), AGORA - timedelta(days=1))


class TestMontar(unittest.TestCase):
    def entidade(self, **extra):
        e = {"id": "urn:ngsi-ld:Vinheria:vin_demo", "nome": {"value": "Vinheria Demo"}, "apikey": {"value": "winedemo"},
             "vencimento": {"value": "2026-11-05T00:00:00.000Z"}, "status": {"value": "ativa"}}
        e.update(extra)
        return e

    def test_formato_do_contrato(self):
        self.assertEqual(regras.montar_vinheria(self.entidade(), 2), {
            "id": "vin_demo", "nome": "Vinheria Demo", "apikey": "winedemo",
            "vencimento": "2026-11-05T00:00:00.000Z", "status": "ativa", "suspensaEm": None, "dispositivos": 2})

    def test_sem_contagem_e_status_estranho(self):
        v = regras.montar_vinheria(self.entidade(status={"value": "xyz"}))
        self.assertNotIn("dispositivos", v)
        self.assertEqual(v["status"], "ativa")
        v = regras.montar_vinheria(self.entidade(status={"value": "suspensa"}, suspensaEm={"value": "2026-10-08T10:00:00.000Z"}))
        self.assertEqual((v["status"], v["suspensaEm"]), ("suspensa", "2026-10-08T10:00:00.000Z"))

    def test_ordem(self):
        itens = [{"id": "b", "criadaEm": "2026-10-02"}, {"id": "a", "criadaEm": "2026-10-02"}, {"id": "c", "criadaEm": "2026-10-01"}]
        self.assertEqual([i["id"] for i in regras.ordenar(itens)], ["c", "a", "b"])

    def test_adega(self):
        self.assertEqual(regras.entidade_da_adega("/porao_sul"), "urn:ngsi-ld:Adega:porao_sul")
        e = {"id": "x", **regras.corpo_adega("Porão Sul", "/porao_sul")}
        self.assertEqual(regras.montar_adega("vin_demo", e), {
            "id": "vin_demo/porao_sul", "vinheriaId": "vin_demo", "servicepath": "/porao_sul", "nome": "Porão Sul"})


class TestEstabilidadePura(unittest.TestCase):
    def resposta(self, campo, valores, origem="2026-10-08T00:00:00.000Z", resolucao="hour"):
        return {"contextResponses": [{"contextElement": {"attributes": [{"name": "temperature", "values": [
            {"_id": {"origin": origem, "resolution": resolucao},
             "points": [{"offset": i, "samples": 1, campo: v} for i, v in enumerate(valores)]}]}]}}]}

    def test_valores_do_sth(self):
        inicio, fim = AGORA - timedelta(hours=24), AGORA
        self.assertEqual(gatilhos.valores_do_sth(self.resposta("min", [12.7, 13.1]), "min", inicio, fim), [12.7, 13.1])
        self.assertEqual(gatilhos.valores_do_sth(self.resposta("max", [14.0]), "min", inicio, fim), [])  # outro campo
        for estranha in [{}, None, {"contextResponses": []}]:
            self.assertEqual(gatilhos.valores_do_sth(estranha, "min", inicio, fim), [])

    def test_ignora_fora_do_periodo_e_sem_amostras(self):
        inicio, fim = AGORA - timedelta(hours=24), AGORA
        r = self.resposta("max", [10, 11])
        r["contextResponses"][0]["contextElement"]["attributes"][0]["values"][0]["points"].append(
            {"offset": 20, "samples": 1, "max": 99})            # 20:00, depois do fim (12:00)
        r["contextResponses"][0]["contextElement"]["attributes"][0]["values"][0]["points"].append(
            {"offset": 3, "samples": 0, "max": 77})             # sem amostras
        self.assertEqual(gatilhos.valores_do_sth(r, "max", inicio, fim), [10, 11])

    def test_montar(self):
        r = gatilhos.montar_estabilidade("wgn001", [12.7, 13.0], [14.0, 14.1], 2)
        self.assertEqual(r, {"deviceId": "wgn001", "min": 12.7, "max": 14.1, "variacao": 1.4, "instavel": False, "limite": 2})
        self.assertTrue(gatilhos.montar_estabilidade("wgn001", [10], [13], 2)["instavel"])
        self.assertFalse(gatilhos.montar_estabilidade("wgn001", [10], [12], 2)["instavel"])  # 2 não passa de 2

    def test_sem_dados(self):
        for minimos, maximos in [([], []), ([12], []), ([], [14])]:
            r = gatilhos.montar_estabilidade("wgn001", minimos, maximos, 2)
            self.assertEqual((r["min"], r["max"], r["variacao"], r["instavel"]), (None, None, 0, False))


# ------------------------------------------------------------- com FIWARE falso
class CasoVin(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fiware._cache_servicepath.clear()
        self.fake = FakeCliente()
        semear(self.fake)
        self.estado = vigia.EstadoVigia()

    def agora(self, segundos=0):
        return AGORA + timedelta(seconds=segundos)

    async def criar(self, nome="Quinta do Sol", vencimento=LONGE):
        return await vinherias.criar(self.fake, {"nome": nome, "vencimento": vencimento}, AGORA)

    def comandos(self, nome=None, entidade=None):
        return [(e, c, v) for e, c, v in self.fake.comandos_valores
                if (nome is None or c == nome) and (entidade is None or e == entidade)]

    def tipos(self, tipo, service=None):
        return {k: v for k, v in self.fake.entidades.items() if v["type"] == tipo and (service is None or k[0] == service)}

    async def volta(self, segundos=0, **leitura):
        definir_leitura(self.fake, self.agora(segundos), **leitura)
        return await vigia.ciclo(self.fake, VIN, self.agora(segundos), self.estado)

    async def volta_suspensa(self, segundos=0, vinheria=VIN, **leitura):
        if leitura:
            definir_leitura(self.fake, self.agora(segundos), **leitura)
        return await vigia.ciclo_suspensa(self.fake, vinheria, self.agora(segundos), self.estado)


class TestExigir(CasoVin):
    async def test_vinheria_padrao_nasce_sozinha(self):
        v = await vinherias.exigir(self.fake, VIN)
        self.assertEqual((v["id"], v["apikey"], v["status"], v["nome"]), (VIN, "winedemo", "ativa", config.NOME_VINHERIA))
        adegas = await vinherias.listar_adegas(self.fake, VIN)
        self.assertEqual(adegas, [{"id": "vin_demo/adega1", "vinheriaId": VIN, "servicepath": "/adega1", "nome": "Adega 1"}])
        await vinherias.exigir(self.fake, VIN)
        self.assertEqual(len(self.tipos("Vinheria")), 1)
        self.assertEqual(len(self.tipos("Adega")), 1)

    async def test_desconhecida_e_invalida(self):
        for ruim in ["vin_outra", "../x", "VIN_DEMO", "", "a b"]:
            with self.assertRaises(vinherias.VinheriaDesconhecida, msg=ruim):
                await vinherias.exigir(self.fake, ruim)

    async def test_mesma_classe_no_cadastro(self):
        self.assertIs(cadastro.VinheriaDesconhecida, vinherias.VinheriaDesconhecida)
        self.assertIs(cadastro.VinheriaSuspensa, vinherias.VinheriaSuspensa)


class TestCriarEListar(CasoVin):
    async def test_criar(self):
        v = await self.criar()
        self.assertEqual((v["id"], v["nome"], v["status"], v["dispositivos"]), ("vin_quinta_do_sol", "Quinta do Sol", "ativa", 0))
        self.assertTrue(v["apikey"].startswith("quintadosol"))
        self.assertEqual(v["vencimento"], "2099-01-01T00:00:00.000Z")
        self.assertIsNone(v["suspensaEm"])
        self.assertEqual(set(v), {"id", "nome", "apikey", "vencimento", "status", "suspensaEm", "dispositivos"})
        self.assertEqual([a["id"] for a in await vinherias.listar_adegas(self.fake, v["id"])], ["vin_quinta_do_sol/adega1"])

    async def test_nome_repetido_ganha_sufixo_e_apikey_propria(self):
        a, b = await self.criar(), await self.criar()
        self.assertEqual((a["id"], b["id"]), ("vin_quinta_do_sol", "vin_quinta_do_sol_2"))
        self.assertNotEqual(a["apikey"], b["apikey"])

    async def test_dados_invalidos(self):
        with self.assertRaises(ValueError):
            await self.criar(vencimento="amanhã")
        with self.assertRaises(ValueError):
            await self.criar(nome="")
        self.assertEqual(self.tipos("Vinheria", config.ADMIN_SERVICE).keys() - {(config.ADMIN_SERVICE, "/", "urn:ngsi-ld:Vinheria:vin_demo")}, set())

    async def test_listar_com_contagem_e_ordem(self):
        await self.criar()
        itens = await vinherias.listar(self.fake)
        self.assertEqual([(i["id"], i["dispositivos"]) for i in itens], [("vin_demo", 1), ("vin_quinta_do_sol", 0)])
        self.assertNotIn("criadaEm", itens[0])
        self.assertEqual(set(itens[0]), {"id", "nome", "apikey", "vencimento", "status", "suspensaEm", "dispositivos"})

    async def test_listar_sem_contagem(self):
        itens = await vinherias.listar(self.fake, contar=False)
        self.assertNotIn("dispositivos", itens[0])


class TestDispositivosEmOutraVinheria(CasoVin):
    async def test_cadastro_usa_a_apikey_da_vinheria(self):
        v = await self.criar()
        r = await cadastro.cadastrar(self.fake, v["id"], {"nome": "X", "adegaId": f"{v['id']}/adega1"}, AGORA)
        self.assertEqual((r["config"]["deviceId"], r["config"]["apikey"]), ("wgn002", v["apikey"]))
        self.assertEqual(self.fake.dispositivos[(v["id"], "wgn002")]["apikey"], v["apikey"])
        self.assertIn((v["id"], "/adega1", v["apikey"]), self.fake.grupos)
        self.assertIn((v["id"], "/adega1", "urn:ngsi-ld:WineGuardNode:002"), self.fake.entidades)

    async def test_cada_vinheria_ve_so_os_seus(self):
        v = await self.criar()
        await cadastro.cadastrar(self.fake, v["id"], {"nome": "X", "adegaId": f"{v['id']}/adega1"}, AGORA)
        self.assertEqual([d["id"] for d in await cadastro.listar(self.fake, VIN)], ["wgn001"])
        self.assertEqual([d["id"] for d in await cadastro.listar(self.fake, v["id"])], ["wgn002"])
        self.assertEqual([i["deviceId"] for i in await cadastro.resumo(self.fake, v["id"], AGORA)], ["wgn002"])

    async def test_adega_de_outra_vinheria_e_recusada(self):
        v = await self.criar()
        with self.assertRaises(ValueError):
            await cadastro.cadastrar(self.fake, v["id"], {"nome": "X", "adegaId": "vin_demo/adega1"}, AGORA)

    async def test_nova_adega_vira_entidade_e_aparece_na_lista(self):
        await cadastro.cadastrar(self.fake, VIN, {"nome": "X", "novaAdega": "Porão Sul"}, AGORA)
        self.assertEqual([(a["id"], a["nome"]) for a in await vinherias.listar_adegas(self.fake, VIN)],
                         [("vin_demo/adega1", "Adega 1"), ("vin_demo/porao_sul", "Porão Sul")])

    async def test_falha_no_cadastro_nao_deixa_adega_pela_metade(self):
        await vinherias.exigir(self.fake, VIN)  # a vinheria padrão já nasceu
        self.fake.quebrar_metadados = True
        with self.assertRaises(fiware.FiwareIndisponivel):
            await cadastro.cadastrar(self.fake, VIN, {"nome": "X", "novaAdega": "Porão Sul"}, AGORA)
        self.assertEqual([a["id"] for a in await vinherias.listar_adegas(self.fake, VIN)], ["vin_demo/adega1"])

    async def test_ids_de_dispositivo_continuam_globais(self):
        v = await self.criar()
        a = await cadastro.cadastrar(self.fake, v["id"], {"nome": "X", "adegaId": f"{v['id']}/adega1"}, AGORA)
        b = await cadastro.cadastrar(self.fake, VIN, {"nome": "Y", "adegaId": "vin_demo/adega1"}, AGORA)
        self.assertEqual((a["config"]["deviceId"], b["config"]["deviceId"]), ("wgn002", "wgn003"))


class TestSuspensao(CasoVin):
    async def test_suspender(self):
        await vinherias.exigir(self.fake, VIN)
        v = await vinherias.suspender(self.fake, VIN, AGORA)
        self.assertEqual((v["status"], v["suspensaEm"]), ("suspensa", "2026-10-08T12:00:30.000Z"))
        self.assertEqual(self.comandos("suspend"), [("urn:ngsi-ld:WineGuardNode:001", "suspend", "")])
        with self.assertRaises(vinherias.VinheriaSuspensa):
            await vinherias.exigir(self.fake, VIN)
        self.assertEqual((await vinherias.exigir(self.fake, VIN, permitir_suspensa=True))["status"], "suspensa")

    async def test_suspender_de_novo_nao_repete_comandos(self):
        await vinherias.suspender(self.fake, VIN, AGORA)
        await vinherias.suspender(self.fake, VIN, AGORA)
        self.assertEqual(len(self.comandos("suspend")), 1)

    async def test_a_api_recusa_o_que_e_da_vinheria_suspensa(self):
        await vinherias.suspender(self.fake, VIN, AGORA)
        recusas = [cadastro.listar(self.fake, VIN), cadastro.resumo(self.fake, VIN, AGORA),
                   cadastro.cadastrar(self.fake, VIN, {"nome": "X", "adegaId": "vin_demo/adega1"}, AGORA),
                   cadastro.remover(self.fake, VIN, "wgn001"), cadastro.atualizar(self.fake, VIN, "wgn001", {"nome": "X"}),
                   triggers.obter(self.fake, VIN, "wgn001"), estabilidade.obter(self.fake, VIN, "wgn001", AGORA)]
        for corrotina in recusas:
            with self.assertRaises(vinherias.VinheriaSuspensa):
                await corrotina

    async def test_historico_e_dados_ficam_guardados(self):
        antes = dict(self.fake.entidades)
        await vinherias.suspender(self.fake, VIN, AGORA)
        for chave, valor in antes.items():
            self.assertIn(chave, self.fake.entidades)
            self.assertEqual(valor["type"], self.fake.entidades[chave]["type"])

    async def test_reativar_mantem_vencimento_em_dia(self):
        v = await self.criar()
        await vinherias.suspender(self.fake, v["id"], AGORA)
        r = await vinherias.reativar(self.fake, v["id"], AGORA)
        self.assertEqual((r["status"], r["vencimento"], r["suspensaEm"]), ("ativa", "2099-01-01T00:00:00.000Z", None))
        atual = await vinherias.exigir(self.fake, v["id"], agora=AGORA)
        self.assertEqual((atual["status"], atual["suspensaEm"]), ("ativa", None))

    async def test_reativar_vencida_renova_por_30_dias_e_manda_resume(self):
        await vinherias.simular_inadimplencia(self.fake, VIN, AGORA)
        r = await vinherias.reativar(self.fake, VIN, AGORA)
        self.assertEqual(r["vencimento"], "2026-11-07T12:00:30.000Z")
        self.assertEqual(self.comandos("resume"), [("urn:ngsi-ld:WineGuardNode:001", "resume", "")])
        self.assertEqual((await vinherias.exigir(self.fake, VIN, agora=AGORA))["status"], "ativa")

    async def test_simular_inadimplencia(self):
        v = await vinherias.simular_inadimplencia(self.fake, VIN, AGORA)
        self.assertEqual(v["status"], "suspensa")
        atual = await vinherias.exigir(self.fake, VIN, permitir_suspensa=True)
        self.assertEqual(atual["vencimento"], "2026-10-07T12:00:30.000Z")
        self.assertEqual(len(self.comandos("suspend")), 1)

    async def test_vencimento_passado_suspende_sozinho(self):
        v = await self.criar(vencimento=PASSADO)
        with self.assertRaises(vinherias.VinheriaSuspensa):
            await vinherias.exigir(self.fake, v["id"])
        itens = {i["id"]: i for i in await vinherias.listar(self.fake)}
        self.assertEqual(itens[v["id"]]["status"], "suspensa")
        self.assertEqual(itens["vin_demo"]["status"], "ativa")

    async def test_desconhecida(self):
        for funcao in (vinherias.suspender, vinherias.reativar, vinherias.simular_inadimplencia):
            with self.assertRaises(vinherias.VinheriaDesconhecida):
                await funcao(self.fake, "vin_outra", AGORA)


class TestVigiaComVinheriaSuspensa(CasoVin):
    async def test_fecha_alertas_e_confere_quem_ainda_publica(self):
        await self.volta(0, temperatura=16)                       # alerta aberto
        await vinherias.suspender(self.fake, VIN, self.agora(1))  # manda um suspend
        eventos = await self.volta_suspensa(2, temperatura=16)
        self.assertIn(("encerrar", "wgn001", "temperature", "acima"), eventos)
        self.assertTrue(all("fim" in a for a in self.tipos("Alerta").values()))
        self.assertEqual(len(self.comandos("suspend")), 1)         # cedo demais para reenviar
        await self.volta_suspensa(20, temperatura=16)
        self.assertEqual(len(self.comandos("suspend")), 2)         # o Node ainda publicava: reenvia

    async def test_nao_repete_o_suspend_a_cada_volta(self):
        await vinherias.suspender(self.fake, VIN, self.agora(0))
        await self.volta_suspensa(1, temperatura=13)
        n = len(self.comandos("suspend"))
        await self.volta_suspensa(6)                               # cedo demais
        await self.volta_suspensa(25)                              # espera ok, mas o Node nem publicou de novo
        self.assertEqual(len(self.comandos("suspend")), n)
        await self.volta_suspensa(45, temperatura=13)                            # publicou depois do comando: ignora a ordem
        self.assertEqual(len(self.comandos("suspend")), n + 1)

    async def test_node_parado_nao_recebe_nada(self):
        await vinherias.suspender(self.fake, VIN, self.agora(0))
        n = len(self.comandos("suspend"))
        await self.volta_suspensa(100, segundos_atras=90)          # sem leitura há 90 s: já parou
        self.assertEqual(len(self.comandos("suspend")), n)
        self.assertEqual(self.tipos("Alerta"), {})                 # e não abre alerta de offline

    async def test_reativar_empurra_os_triggers_de_novo(self):
        await self.volta(0)
        await vinherias.suspender(self.fake, VIN, self.agora(1))
        await self.volta_suspensa(2)
        await vinherias.reativar(self.fake, VIN, self.agora(3))
        antes = len(self.comandos("setTriggers"))
        await self.volta(10)
        self.assertEqual(len(self.comandos("setTriggers")), antes + 1)

    async def test_passo_percorre_as_vinherias(self):
        outra = await self.criar()
        await vinherias.suspender(self.fake, outra["id"], AGORA)
        definir_leitura(self.fake, AGORA, temperatura=16)
        eventos, erros = await vigia.passo(self.fake, AGORA, self.estado)
        self.assertEqual(erros, {})
        self.assertIn((VIN, ("abrir", "wgn001", "temperature", "acima")), eventos)
        self.assertEqual([e for e in eventos if e[0] == outra["id"]], [])

    async def test_passo_suspende_a_vencida(self):
        v = await self.criar(vencimento=PASSADO)
        await vigia.passo(self.fake, AGORA, self.estado)
        self.assertEqual((await vinherias.exigir(self.fake, v["id"], permitir_suspensa=True))["status"], "suspensa")

    async def test_passo_isola_o_erro_de_uma_vinheria(self):
        outra = await self.criar()
        original = fiware.listar_entidades

        async def quebrada(cliente, service, *args, **kwargs):
            if service == outra["id"]:
                raise fiware.FiwareIndisponivel("Orion: caiu")
            return await original(cliente, service, *args, **kwargs)

        fiware.listar_entidades = quebrada
        try:
            definir_leitura(self.fake, AGORA, temperatura=16)
            eventos, erros = await vigia.passo(self.fake, AGORA, self.estado)
        finally:
            fiware.listar_entidades = original
        self.assertEqual(list(erros), [outra["id"]])
        self.assertIn((VIN, ("abrir", "wgn001", "temperature", "acima")), eventos)


class TestEstabilidade(CasoVin):
    async def test_obter(self):
        self.fake.sth = {"min": [12.7, 13.0], "max": [14.0, 14.1]}
        r = await estabilidade.obter(self.fake, VIN, "wgn001", AGORA)
        self.assertEqual(r, {"deviceId": "wgn001", "min": 12.7, "max": 14.1, "variacao": 1.4, "instavel": False, "limite": 2})
        self.assertEqual(sorted(m for _, m in self.fake.sth_chamadas), ["max", "min"])

    async def test_instavel_e_limite_personalizado(self):
        self.fake.sth = {"min": [12.0], "max": [16.0]}
        self.assertTrue((await estabilidade.obter(self.fake, VIN, "wgn001", AGORA))["instavel"])
        corpo = gatilhos.triggers_do_preset("guarda_geral")
        corpo["estabilidadeMax"] = 5
        await triggers.salvar(self.fake, VIN, "wgn001", corpo)
        r = await estabilidade.obter(self.fake, VIN, "wgn001", AGORA)
        self.assertEqual((r["instavel"], r["limite"], r["variacao"]), (False, 5, 4.0))

    async def test_sem_dados(self):
        r = await estabilidade.obter(self.fake, VIN, "wgn001", AGORA)
        self.assertEqual((r["min"], r["max"], r["variacao"], r["instavel"]), (None, None, 0, False))

    async def test_dispositivo_inexistente(self):
        with self.assertRaises(cadastro.DispositivoNaoEncontrado):
            await estabilidade.obter(self.fake, VIN, "wgn099", AGORA)

    async def test_vigia_abre_e_encerra_o_alerta(self):
        self.fake.sth = {"min": [12.0], "max": [15.0]}             # variação 3 > 2
        eventos = await self.volta(0)
        self.assertIn(("abrir", "wgn001", "estabilidade", None), eventos)
        a = self.fake.entidades[(VIN, "/", "urn:ngsi-ld:Alerta:1")]
        self.assertEqual((a["variavel"]["value"], a["valor"]["value"], a["limite"]["value"]), ("estabilidade", 3.0, 2))
        self.assertNotIn("sentido", a)
        self.assertEqual((await cadastro.resumo(self.fake, VIN, AGORA))[0]["alertasAtivos"], 1)

        chamadas = len(self.fake.sth_chamadas)
        await self.volta(5)                                         # dentro do intervalo: nem consulta o STH
        self.assertEqual(len(self.fake.sth_chamadas), chamadas)
        self.assertEqual(len(self.tipos("Alerta")), 1)

        self.fake.sth = {"min": [12.0], "max": [13.5]}              # estabilizou
        eventos = await self.volta(65)
        self.assertIn(("encerrar", "wgn001", "estabilidade", None), eventos)
        self.assertIn("fim", a)

    async def test_vigia_nao_consulta_quem_esta_offline(self):
        await self.volta(0, segundos_atras=60)
        self.assertEqual(self.fake.sth_chamadas, [])

    async def test_falha_no_sth_nao_derruba_o_vigia(self):
        original = fiware.obter_extremos

        async def quebrada(*args, **kwargs):
            raise fiware.FiwareIndisponivel("STH-Comet: caiu")

        fiware.obter_extremos = quebrada
        try:
            eventos = await self.volta(0, temperatura=16)
        finally:
            fiware.obter_extremos = original
        self.assertIn(("abrir", "wgn001", "temperature", "acima"), eventos)

    async def test_dispositivo_apagado_fecha_o_alerta_de_estabilidade(self):
        self.fake.sth = {"min": [12.0], "max": [15.0]}
        await self.volta(0)
        await cadastro.remover(self.fake, VIN, "wgn001")
        eventos = await vigia.ciclo(self.fake, VIN, self.agora(5), self.estado)
        self.assertIn(("encerrar", "wgn001", "estabilidade", None), eventos)


if __name__ == "__main__":
    unittest.main()
