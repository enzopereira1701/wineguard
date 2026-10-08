"""
Testes do Backend 3 contra o FIWARE falso: o vigia (alertas), os triggers e o resumo.
Rodar, na pasta backend:   python -m unittest discover -s tests -v
"""

import unittest
from datetime import timedelta

try:
    from tests.fake_fiware import AGORA, VIN, FakeCliente, definir_leitura, semear
except ImportError:
    from fake_fiware import AGORA, VIN, FakeCliente, definir_leitura, semear

from app import alertas, cadastro, config, fiware, gatilhos, triggers, vigia  # noqa: E402

ALERTA_1 = (VIN, "/", "urn:ngsi-ld:Alerta:1")


class CasoVigia(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fiware._cache_servicepath.clear()
        self.fake = FakeCliente()
        semear(self.fake)
        self.estado = vigia.EstadoVigia()
        self.espera = config.ESPERA_COMANDO_SEGUNDOS
        config.ESPERA_COMANDO_SEGUNDOS = 0.3

    def tearDown(self):
        config.ESPERA_COMANDO_SEGUNDOS = self.espera

    def agora(self, segundos=0):
        return AGORA + timedelta(seconds=segundos)

    async def volta(self, segundos=0, estado=None, **leitura):
        """Põe uma leitura no wgn001 (segundos depois de AGORA) e roda uma volta do vigia."""
        momento = self.agora(segundos)
        definir_leitura(self.fake, momento, **leitura)
        return await vigia.ciclo(self.fake, VIN, momento, estado or self.estado)

    def comandos(self, nome=None):
        return [(c, v) for _, c, v in self.fake.comandos_valores if nome is None or c == nome]

    def alertas_guardados(self):
        return {k[2]: v for k, v in self.fake.entidades.items() if v["type"] == "Alerta"}


class TestAlertasDeSensor(CasoVigia):
    async def test_dentro_da_faixa_so_empurra_os_triggers(self):
        eventos = await self.volta()
        self.assertEqual(self.alertas_guardados(), {})
        self.assertEqual(self.comandos(), [("setTriggers", "10,15,60,75,0,10")])
        self.assertNotIn("abrir", [e[0] for e in eventos])

    async def test_abre_alerta_acima_e_comanda_o_node(self):
        eventos = await self.volta(temperatura=16)
        self.assertIn(("abrir", "wgn001", "temperature", "acima"), eventos)
        self.assertIn(("alert", "t,high,1"), self.comandos())
        a = self.fake.entidades[ALERTA_1]
        self.assertEqual((a["deviceId"]["value"], a["variavel"]["value"], a["sentido"]["value"]),
                         ("wgn001", "temperature", "acima"))
        self.assertEqual((a["valor"]["value"], a["limite"]["value"]), (16, 15))
        self.assertNotIn("fim", a)

    async def test_nao_repete_o_alerta_a_cada_volta(self):
        await self.volta(0, temperatura=16)
        await self.volta(5, temperatura=16.2, state="alerta")
        await self.volta(10, temperatura=16.4, state="alerta")
        self.assertEqual(len(self.alertas_guardados()), 1)
        self.assertEqual(self.comandos("alert"), [("alert", "t,high,1")])

    async def test_histerese_para_encerrar(self):
        await self.volta(0, temperatura=16)
        eventos = await self.volta(5, temperatura=14.8, state="alerta")   # só 0,2 para dentro: continua
        self.assertEqual([e for e in eventos if e[0] == "encerrar"], [])
        self.assertNotIn("fim", self.fake.entidades[ALERTA_1])
        eventos = await self.volta(10, temperatura=14.4, state="alerta")  # 0,6 para dentro: encerra
        self.assertIn(("encerrar", "wgn001", "temperature", "acima"), eventos)
        self.assertIn("fim", self.fake.entidades[ALERTA_1])
        self.assertEqual(self.comandos("alert")[-1], ("alert", "t,high,0"))

    async def test_abaixo(self):
        eventos = await self.volta(temperatura=9)
        self.assertIn(("abrir", "wgn001", "temperature", "abaixo"), eventos)
        self.assertIn(("alert", "t,low,1"), self.comandos())
        self.assertEqual(self.fake.entidades[ALERTA_1]["limite"]["value"], 10)
        await self.volta(5, temperatura=10.5, state="alerta")
        self.assertIn("fim", self.fake.entidades[ALERTA_1])
        self.assertEqual(self.comandos("alert")[-1], ("alert", "t,low,0"))

    async def test_umidade_e_luz(self):
        eventos = await self.volta(umidade=80, luz=12)
        self.assertIn(("abrir", "wgn001", "humidity", "acima"), eventos)
        self.assertIn(("abrir", "wgn001", "luminosity", "acima"), eventos)
        self.assertIn(("alert", "h,high,1"), self.comandos())
        self.assertIn(("alert", "l,high,1"), self.comandos())
        self.assertEqual(len(self.alertas_guardados()), 2)

    async def test_triggers_personalizados_valem(self):
        corpo = gatilhos.triggers_do_preset("guarda_geral")
        corpo.update(modo="personalizado", temp={"min": 8, "max": 20})
        definir_leitura(self.fake, self.agora(), temperatura=16)
        await triggers.salvar(self.fake, VIN, "wgn001", corpo)
        eventos = await self.volta(5, temperatura=16)
        self.assertNotIn("abrir", [e[0] for e in eventos])

    async def test_falha_no_comando_nao_derruba_o_vigia(self):
        self.fake.falhar_comandos = True
        eventos = await self.volta(temperatura=16)
        self.assertIn(("abrir", "wgn001", "temperature", "acima"), eventos)  # o alerta fica registrado
        self.assertEqual(self.comandos(), [])


class TestSituacoes(CasoVigia):
    async def test_offline_abre_e_encerra(self):
        eventos = await self.volta(segundos_atras=60)
        self.assertIn(("abrir", "wgn001", "offline", None), eventos)
        a = self.fake.entidades[ALERTA_1]
        self.assertEqual(a["variavel"]["value"], "offline")
        self.assertNotIn("sentido", a)
        eventos = await self.volta(5, segundos_atras=60)  # continua offline: não duplica
        self.assertEqual(len(self.alertas_guardados()), 1)
        eventos = await self.volta(10)                      # voltou
        self.assertIn(("encerrar", "wgn001", "offline", None), eventos)
        self.assertIn("fim", self.fake.entidades[ALERTA_1])

    async def test_volta_do_offline_reenvia_os_triggers(self):
        await self.volta()
        await self.volta(60, segundos_atras=60)
        antes = len(self.comandos("setTriggers"))
        await self.volta(70)
        self.assertEqual(len(self.comandos("setTriggers")), antes + 1)

    async def test_aguardando_nao_gera_nada(self):
        await cadastro.cadastrar(self.fake, VIN, {"nome": "Novo", "adegaId": "vin_demo/adega1"}, AGORA)
        self.fake.entidades.pop((VIN, "/adega1", "urn:ngsi-ld:WineGuardNode:001"))
        eventos = await vigia.ciclo(self.fake, VIN, AGORA, self.estado)
        self.assertEqual(eventos, [])
        self.assertEqual(self.alertas_guardados(), {})

    async def test_suspenso_fecha_alertas_sem_comandar(self):
        await self.volta(0, temperatura=16)
        enviados = len(self.fake.comandos_valores)
        eventos = await self.volta(5, temperatura=16, state="suspenso")
        self.assertIn(("encerrar", "wgn001", "temperature", "acima"), eventos)
        self.assertIn("fim", self.fake.entidades[ALERTA_1])
        self.assertEqual(len(self.fake.comandos_valores), enviados)

    async def test_dispositivo_apagado_fecha_o_alerta(self):
        await self.volta(0, temperatura=16)
        await cadastro.remover(self.fake, VIN, "wgn001")
        eventos = await vigia.ciclo(self.fake, VIN, self.agora(5), self.estado)
        self.assertIn(("encerrar", "wgn001", "temperature", "acima"), eventos)
        self.assertIn("fim", self.fake.entidades[ALERTA_1])

    async def test_reiniciar_a_api_nao_duplica_nem_perde(self):
        await self.volta(0, temperatura=16)
        novo = vigia.EstadoVigia()                       # a API reiniciou: memória zerada
        eventos = await self.volta(5, estado=novo, temperatura=16, state="alerta")
        self.assertNotIn("abrir", [e[0] for e in eventos])
        self.assertEqual(len(self.alertas_guardados()), 1)
        self.assertIn(("alert", "t,high,1"), self.comandos())   # reenviou o alerta ao Node
        eventos = await self.volta(10, estado=novo, temperatura=14, state="alerta")
        self.assertIn(("encerrar", "wgn001", "temperature", "acima"), eventos)  # e ainda sabe encerrar


class TestReconciliacao(CasoVigia):
    async def test_node_em_ok_com_alerta_esperado_reenvia(self):
        await self.volta(0, temperatura=16)
        eventos = await self.volta(5, temperatura=16, state="ok")    # cedo demais: espera
        self.assertNotIn(("reconciliar", "wgn001"), eventos)
        eventos = await self.volta(20, temperatura=16, state="ok")
        self.assertIn(("reconciliar", "wgn001"), eventos)
        self.assertEqual(self.comandos("alert")[-3:], [("alert", "t,high,1"), ("alert", "h,high,0"), ("alert", "l,high,0")])

    async def test_node_em_alerta_sem_alerta_esperado_desliga(self):
        await self.volta(0, temperatura=13)
        eventos = await self.volta(20, temperatura=13, state="alerta")
        self.assertIn(("reconciliar", "wgn001"), eventos)
        self.assertEqual(self.comandos("alert"), [("alert", "t,high,0"), ("alert", "h,high,0"), ("alert", "l,high,0")])

    async def test_nao_reenvia_a_cada_volta(self):
        await self.volta(0, temperatura=13)
        await self.volta(20, temperatura=13, state="alerta")
        n = len(self.comandos("alert"))
        await self.volta(25, temperatura=13, state="alerta")
        self.assertEqual(len(self.comandos("alert")), n)


class TestResumoEListagem(CasoVigia):
    async def test_resumo_conta_alertas_de_verdade(self):
        await self.volta(umidade=80, luz=12)
        itens = await cadastro.resumo(self.fake, VIN, AGORA)
        self.assertEqual(itens[0]["deviceId"], "wgn001")
        self.assertEqual(itens[0]["alertasAtivos"], 2)

    async def test_listar_alertas(self):
        await self.volta(0, temperatura=16)
        await self.volta(5, temperatura=14, state="alerta")           # encerra o 1
        await self.volta(10, temperatura=14, luz=12, state="ok")      # abre o 2 (luz)
        todos = await alertas.listar(self.fake, VIN)
        self.assertEqual([a["id"] for a in todos], [2, 1])
        self.assertEqual([a["id"] for a in await alertas.listar(self.fake, VIN, "ativos")], [2])
        self.assertEqual([a["id"] for a in await alertas.listar(self.fake, VIN, "encerrados")], [1])
        self.assertEqual(await alertas.listar(self.fake, VIN, "todos", "wgn999"), [])
        self.assertEqual(set(todos[0]), {"id", "vinheriaId", "deviceId", "variavel", "sentido", "valor", "limite", "inicio", "fim"})
        with self.assertRaises(ValueError):
            await alertas.listar(self.fake, VIN, "xyz")

    async def test_alertas_nao_aparecem_como_dispositivos(self):
        await self.volta(0, temperatura=16)
        itens = await cadastro.listar(self.fake, VIN)
        self.assertEqual([i["id"] for i in itens], ["wgn001"])


class TestTriggersServico(CasoVigia):
    def corpo(self, **mudancas):
        base = gatilhos.triggers_do_preset("espumante")
        base.update(mudancas)
        return base

    async def test_obter_padrao_e_do_preset(self):
        self.assertEqual((await triggers.obter(self.fake, VIN, "wgn001"))["preset"], "guarda_geral")
        r = await cadastro.cadastrar(self.fake, VIN, {"nome": "B", "preset": "espumante", "adegaId": "vin_demo/adega1"}, AGORA)
        t = await triggers.obter(self.fake, VIN, r["config"]["deviceId"])
        self.assertEqual((t["preset"], t["temp"]), ("espumante", {"min": 9, "max": 13}))

    async def test_salvar_grava_envia_e_confirma(self):
        r = await triggers.salvar(self.fake, VIN, "wgn001", self.corpo())
        self.assertEqual((r["recebido"], r["deviceId"]), (True, "wgn001"))
        self.assertRegex(r["em"], r"^\d{4}-\d\d-\d\dT.*Z$")
        self.assertEqual(self.comandos("setTriggers"), [("setTriggers", "9,13,65,80,0,5")])
        t = await triggers.obter(self.fake, VIN, "wgn001")
        self.assertEqual((t["preset"], t["temp"]), ("espumante", {"min": 9, "max": 13}))
        entidade = self.fake.entidades[(VIN, "/adega1", "urn:ngsi-ld:WineGuardNode:001")]
        self.assertEqual(entidade["preset"]["value"], "espumante")

    async def test_node_nao_responde_mas_os_limites_ficam_salvos(self):
        self.fake.responder = "nada"
        with self.assertRaises(triggers.NodeNaoConfirmou):
            await triggers.salvar(self.fake, VIN, "wgn001", self.corpo())
        self.assertEqual((await triggers.obter(self.fake, VIN, "wgn001"))["preset"], "espumante")

    async def test_status_de_comando_anterior_nao_confirma(self):
        await triggers.salvar(self.fake, VIN, "wgn001", self.corpo())      # deixa um OK antigo na entidade
        self.fake.responder = "pendente"
        with self.assertRaises(triggers.NodeNaoConfirmou):
            await triggers.salvar(self.fake, VIN, "wgn001", self.corpo(modo="personalizado"))

    async def test_node_recusa(self):
        self.fake.responder = "erro"
        with self.assertRaises(triggers.NodeNaoConfirmou):
            await triggers.salvar(self.fake, VIN, "wgn001", self.corpo())

    async def test_invalido_nao_envia_nada(self):
        with self.assertRaises(ValueError):
            await triggers.salvar(self.fake, VIN, "wgn001", self.corpo(temp={"min": 15, "max": 10}))
        self.assertEqual(self.fake.comandos_valores, [])

    async def test_dispositivo_inexistente_e_vinheria_desconhecida(self):
        with self.assertRaises(cadastro.DispositivoNaoEncontrado):
            await triggers.salvar(self.fake, VIN, "wgn099", self.corpo())
        with self.assertRaises(cadastro.DispositivoNaoEncontrado):
            await triggers.obter(self.fake, VIN, "wgn099")
        with self.assertRaises(cadastro.VinheriaDesconhecida):
            await triggers.obter(self.fake, "vin_outra", "wgn001")


if __name__ == "__main__":
    unittest.main()
