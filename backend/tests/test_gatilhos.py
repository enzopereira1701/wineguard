"""Testes das regras de triggers e alertas que não dependem de rede (app/gatilhos.py)."""

import unittest
from datetime import datetime, timedelta, timezone

try:
    from tests.fake_fiware import AGORA  # noqa: F401  (também prepara os atrapalhos de httpx/dotenv)
except ImportError:
    from fake_fiware import AGORA  # noqa: F401

from app import dominio, gatilhos  # noqa: E402

T0 = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)


def faixas(**mudancas):
    base = {"preset": "guarda_geral", "modo": "personalizado", "temp": {"min": 10, "max": 15},
            "umid": {"min": 60, "max": 75}, "luz": {"min": 0, "max": 10}, "estabilidadeMax": 2, "luzEscuro": None}
    base.update(mudancas)
    return base


class TestPresets(unittest.TestCase):
    def test_mesmos_presets_do_dominio(self):
        self.assertEqual(set(gatilhos.PRESETS_TRIGGERS), set(dominio.PRESETS))

    def test_valores_do_dashboard(self):
        self.assertEqual(gatilhos.triggers_do_preset("espumante")["temp"], {"min": 9, "max": 13})
        self.assertEqual(gatilhos.triggers_do_preset("longa_guarda")["luz"], {"min": 0, "max": 5})
        g = gatilhos.triggers_do_preset("guarda_geral")
        self.assertEqual((g["modo"], g["estabilidadeMax"], g["luzEscuro"]), ("referencia", 2, None))

    def test_preset_desconhecido_cai_no_padrao(self):
        for ruim in [None, "xyz", 5]:
            self.assertEqual(gatilhos.triggers_do_preset(ruim)["preset"], "guarda_geral")


class TestValidar(unittest.TestCase):
    def test_ok(self):
        r = gatilhos.validar_triggers(faixas())
        self.assertEqual(r, faixas())

    def test_estabilidade_padrao_e_luz_escuro(self):
        r = gatilhos.validar_triggers(faixas(estabilidadeMax=None, luzEscuro=7))
        self.assertEqual((r["estabilidadeMax"], r["luzEscuro"]), (2, 7))

    def test_erros(self):
        ruins = [
            None, [], {}, faixas(preset="x"), faixas(modo="x"), faixas(temp=None),
            faixas(temp={"min": 15, "max": 15}), faixas(temp={"min": 16, "max": 15}),
            faixas(temp={"min": -30, "max": 15}), faixas(temp={"min": 10, "max": 70}),
            faixas(umid={"min": 60, "max": 101}), faixas(luz={"min": -1, "max": 10}),
            faixas(temp={"min": "10", "max": 15}), faixas(temp={"min": None, "max": 15}),
            faixas(temp={"min": True, "max": 15}), faixas(temp={"min": float("nan"), "max": 15}),
            faixas(estabilidadeMax=0), faixas(estabilidadeMax=25), faixas(luzEscuro=101), faixas(luzEscuro="x"),
        ]
        for corpo in ruins:
            with self.assertRaises(ValueError, msg=str(corpo)):
                gatilhos.validar_triggers(corpo)

    def test_comando_set_triggers(self):
        self.assertEqual(gatilhos.comando_set_triggers(faixas()), "10,15,60,75,0,10")
        t = faixas(temp={"min": 11.5, "max": 14.25})
        self.assertEqual(gatilhos.comando_set_triggers(t), "11.5,14.25,60,75,0,10")


class TestTriggersDaEntidade(unittest.TestCase):
    def test_gravados_valem(self):
        e = {"triggers": {"type": "StructuredValue", "value": faixas(temp={"min": 8, "max": 20})}}
        self.assertEqual(gatilhos.triggers_da_entidade(e)["temp"], {"min": 8, "max": 20})

    def test_sem_gravados_usa_o_preset(self):
        e = {"preset": {"type": "Text", "value": "espumante"}}
        self.assertEqual(gatilhos.triggers_da_entidade(e)["preset"], "espumante")
        self.assertEqual(gatilhos.triggers_da_entidade({})["preset"], "guarda_geral")
        self.assertEqual(gatilhos.triggers_da_entidade(None)["preset"], "guarda_geral")

    def test_gravados_estragados_caem_no_preset(self):
        e = {"triggers": {"value": {"preset": "x"}}, "preset": {"value": "longa_guarda"}}
        self.assertEqual(gatilhos.triggers_da_entidade(e)["preset"], "longa_guarda")


class TestAvaliar(unittest.TestCase):
    """Mesma regra do firmware (avalia): entra ao passar do limite, sai com histerese."""

    def temp(self, valor, atual=None):
        return gatilhos.avaliar(valor, 10, 15, 0.5, atual)

    def test_dentro_da_faixa(self):
        for v in (10, 12.5, 15):  # os limites em si ainda são faixa
            self.assertIsNone(self.temp(v))

    def test_entra(self):
        self.assertEqual(self.temp(15.1), "acima")
        self.assertEqual(self.temp(9.9), "abaixo")

    def test_acima_so_sai_com_histerese(self):
        self.assertEqual(self.temp(15.0, "acima"), "acima")
        self.assertEqual(self.temp(14.6, "acima"), "acima")
        self.assertIsNone(self.temp(14.5, "acima"))
        self.assertIsNone(self.temp(12, "acima"))

    def test_abaixo_so_sai_com_histerese(self):
        self.assertEqual(self.temp(10.2, "abaixo"), "abaixo")
        self.assertIsNone(self.temp(10.5, "abaixo"))

    def test_oscilando_em_cima_do_limite_nao_pisca(self):
        estado, trocas = None, 0
        for v in [14.9, 15.1, 14.9, 15.1, 14.8, 15.2, 14.7]:
            novo = self.temp(v, estado)
            trocas += novo != estado
            estado = novo
        self.assertEqual(trocas, 1)  # abriu uma vez e ficou

    def test_umidade_e_luz(self):
        self.assertEqual(gatilhos.avaliar(76, 60, 75, 2.0, None), "acima")
        self.assertEqual(gatilhos.avaliar(74, 60, 75, 2.0, "acima"), "acima")
        self.assertIsNone(gatilhos.avaliar(73, 60, 75, 2.0, "acima"))
        self.assertIsNone(gatilhos.avaliar(0, 0, 10, 2.0, None))  # luz minima 0 nunca fica "abaixo"

    def test_limites_por_variavel(self):
        t = faixas()
        self.assertEqual(gatilhos.limites(t, "temperature"), (10, 15))
        self.assertEqual(gatilhos.limites(t, "humidity"), (60, 75))
        self.assertEqual(gatilhos.limites(t, "luminosity"), (0, 10))


class TestComandos(unittest.TestCase):
    def test_alerta(self):
        self.assertEqual(gatilhos.comando_alerta("temperature", "acima", True), "t,high,1")
        self.assertEqual(gatilhos.comando_alerta("humidity", "abaixo", True), "h,low,1")
        self.assertEqual(gatilhos.comando_alerta("luminosity", "acima", False), "l,high,0")

    def test_estado_do_comando(self):
        def ent(valor, quando):
            return {"setTriggers_status": {"type": "commandStatus", "value": valor,
                                           "metadata": {"dateModified": {"type": "DateTime", "value": quando}}}}
        self.assertEqual(gatilhos.estado_do_comando(None, "setTriggers"), "pendente")
        self.assertEqual(gatilhos.estado_do_comando({}, "setTriggers"), "pendente")
        self.assertEqual(gatilhos.estado_do_comando(ent("OK", "2026-10-08T12:00:05.000Z"), "setTriggers"), "ok")
        self.assertEqual(gatilhos.estado_do_comando(ent("PENDING", "2026-10-08T12:00:05.000Z"), "setTriggers"), "pendente")
        self.assertEqual(gatilhos.estado_do_comando(ent("ERROR", "2026-10-08T12:00:05.000Z"), "setTriggers"), "erro")

    def test_status_velho_nao_conta(self):
        antigo = {"setTriggers_status": {"value": "OK", "metadata": {"dateModified": {"value": "2026-10-08T12:00:00.000Z"}}}}
        self.assertEqual(gatilhos.estado_do_comando(antigo, "setTriggers", T0), "pendente")      # igual: é o anterior
        self.assertEqual(gatilhos.estado_do_comando(antigo, "setTriggers", T0 - timedelta(seconds=1)), "ok")
        self.assertEqual(gatilhos.quando_o_status_mudou(antigo, "setTriggers"), T0)
        self.assertIsNone(gatilhos.quando_o_status_mudou({}, "setTriggers"))

    def test_status_sem_data_com_referencia_e_pendente(self):
        sem_data = {"setTriggers_status": {"value": "OK"}}
        self.assertEqual(gatilhos.estado_do_comando(sem_data, "setTriggers", T0), "pendente")


class TestReconciliar(unittest.TestCase):
    def test_sem_divergencia(self):
        self.assertFalse(gatilhos.precisa_reconciliar(True, "alerta", T0, None))
        self.assertFalse(gatilhos.precisa_reconciliar(False, "ok", T0, None))

    def test_nunca_comandou_e_diverge(self):
        self.assertTrue(gatilhos.precisa_reconciliar(True, "ok", T0, None))

    def test_espera_entre_reenvios(self):
        leitura = T0 - timedelta(seconds=1)
        self.assertFalse(gatilhos.precisa_reconciliar(True, "ok", T0, T0 - timedelta(seconds=10), leitura))
        self.assertTrue(gatilhos.precisa_reconciliar(True, "ok", T0, T0 - timedelta(seconds=20), leitura))
        self.assertTrue(gatilhos.precisa_reconciliar(False, "alerta", T0, T0 - timedelta(seconds=20), leitura))

    def test_leitura_anterior_ao_comando_nao_conta(self):
        comando = T0 - timedelta(seconds=20)
        for leitura in (None, comando - timedelta(seconds=5), comando, comando + timedelta(seconds=2)):
            self.assertFalse(gatilhos.precisa_reconciliar(True, "ok", T0, comando, leitura), str(leitura))
        self.assertTrue(gatilhos.precisa_reconciliar(True, "ok", T0, comando, comando + timedelta(seconds=3)))

    def test_suspenso_ou_desconhecido_nao_reconcilia(self):
        for estado in ("suspenso", None, "aguardando"):
            self.assertFalse(gatilhos.precisa_reconciliar(True, estado, T0, None))


class TestAlertas(unittest.TestCase):
    def entidade(self, n, **attrs):
        e = {"id": gatilhos.entidade_do_alerta(n)}
        for k, v in attrs.items():
            if v is not None:
                e[k] = {"type": "Text", "value": v}
        return e

    def test_ids(self):
        self.assertEqual(gatilhos.entidade_do_alerta(12), "urn:ngsi-ld:Alerta:12")
        self.assertEqual(gatilhos.numero_do_alerta("urn:ngsi-ld:Alerta:12"), 12)
        for ruim in ["urn:ngsi-ld:Alerta:x", "Alerta:1", "", None]:
            self.assertIsNone(gatilhos.numero_do_alerta(ruim))

    def test_corpo_so_com_o_que_existe(self):
        c = gatilhos.corpo_alerta("wgn001", "offline", None, None, None, T0)
        self.assertEqual(set(c), {"deviceId", "variavel", "inicio"})
        c = gatilhos.corpo_alerta("wgn001", "temperature", "acima", 15.8, 15, T0)
        self.assertEqual((c["sentido"]["value"], c["valor"]["value"], c["limite"]["value"]), ("acima", 15.8, 15))
        self.assertEqual(c["inicio"]["value"], "2026-10-08T12:00:00.000Z")

    def test_montar_no_formato_do_contrato(self):
        e = self.entidade(12, deviceId="wgn001", variavel="temperature", sentido="acima", inicio="2026-10-08T12:00:00.000Z")
        e["valor"] = {"type": "Number", "value": 15.8}
        e["limite"] = {"type": "Number", "value": 15}
        self.assertEqual(gatilhos.montar_alerta("vin_demo", e), {
            "id": 12, "vinheriaId": "vin_demo", "deviceId": "wgn001", "variavel": "temperature", "sentido": "acima",
            "valor": 15.8, "limite": 15, "inicio": "2026-10-08T12:00:00.000Z", "fim": None})

    def lista(self):
        def a(n, dev, inicio, fim=None):
            return {"id": n, "deviceId": dev, "inicio": inicio, "fim": fim}
        return [a(1, "wgn001", "2026-10-08T10:00:00.000Z", "2026-10-08T10:05:00.000Z"),
                a(2, "wgn002", "2026-10-08T11:00:00.000Z"),
                a(3, "wgn001", "2026-10-08T12:00:00.000Z")]

    def test_filtros_e_ordem(self):
        ids = lambda **kw: [x["id"] for x in gatilhos.filtrar_alertas(self.lista(), **kw)]
        self.assertEqual(ids(), [3, 2, 1])
        self.assertEqual(ids(estado="ativos"), [3, 2])
        self.assertEqual(ids(estado="encerrados"), [1])
        self.assertEqual(ids(device_id="wgn001"), [3, 1])
        self.assertEqual(ids(estado="ativos", device_id="wgn002"), [2])
        with self.assertRaises(ValueError):
            gatilhos.filtrar_alertas(self.lista(), estado="xyz")

    def test_contar_ativos(self):
        self.assertEqual(gatilhos.contar_ativos(self.lista()), {"wgn001": 1, "wgn002": 1})
        self.assertEqual(gatilhos.contar_ativos([]), {})


if __name__ == "__main__":
    unittest.main()
