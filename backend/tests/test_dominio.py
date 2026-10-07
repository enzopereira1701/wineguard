"""
Testes das regras que não dependem de rede (app/dominio.py).

Rodar, na pasta backend:   python -m unittest discover -s tests -v
(ou, com pytest instalado:  pytest)
"""

import unittest
from datetime import datetime, timedelta, timezone

from app import dominio

AGORA = datetime(2026, 10, 7, 12, 0, 30, tzinfo=timezone.utc)


def entidade(temp=13.4, state="ok", segundos_atras=5, **extra):
    """Entidade do Orion no formato normalizado, com dateModified."""
    quando = (AGORA - timedelta(seconds=segundos_atras)).strftime("%Y-%m-%dT%H:%M:%S.00Z")
    meta = {"dateModified": {"type": "DateTime", "value": quando}}
    corpo = {
        "id": "urn:ngsi-ld:WineGuardNode:001", "type": "WineGuardNode",
        "temperature": {"type": "Number", "value": temp, "metadata": meta},
        "humidity": {"type": "Number", "value": 68.2, "metadata": meta},
        "luminosity": {"type": "Number", "value": 3, "metadata": meta},
        "state": {"type": "Text", "value": state, "metadata": meta},
        "muted": {"type": "Number", "value": 0, "metadata": meta},
        "rssi": {"type": "Number", "value": -64, "metadata": meta},
        "firmware": {"type": "Text", "value": "2.3", "metadata": meta},
    }
    corpo.update(extra)
    return corpo


class TestIdentificador(unittest.TestCase):
    def test_entidade(self):
        self.assertEqual(dominio.entidade_do_dispositivo("wgn001"), "urn:ngsi-ld:WineGuardNode:001")
        self.assertEqual(dominio.entidade_do_dispositivo("wgn1234"), "urn:ngsi-ld:WineGuardNode:1234")

    def test_invalidos(self):
        for ruim in ["", "wgn", "wgn1", "abc001", "wgn00a", "../wgn001", "wgn001/../x"]:
            with self.assertRaises(ValueError, msg=ruim):
                dominio.entidade_do_dispositivo(ruim)


class TestDatas(unittest.TestCase):
    def test_ler_iso(self):
        esperado = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
        for texto in ["2026-10-07T12:00:00Z", "2026-10-07T12:00:00.00Z", "2026-10-07T12:00:00.000Z",
                      "2026-10-07T12:00:00.000000+00:00", "2026-10-07T09:00:00-03:00", "2026-10-07T12:00:00"]:
            self.assertEqual(dominio.ler_iso(texto), esperado, texto)

    def test_para_iso(self):
        self.assertEqual(dominio.para_iso(AGORA), "2026-10-07T12:00:30.000Z")

    def test_janela(self):
        inicio, fim, agrup = dominio.janela("24h", AGORA)
        self.assertEqual(fim - inicio, timedelta(hours=24))
        self.assertEqual(agrup, "hour")
        self.assertEqual(dominio.janela("1h", AGORA)[2], "minute")
        with self.assertRaises(ValueError):
            dominio.janela("30d", AGORA)


class TestHistorico(unittest.TestCase):
    def resposta(self, blocos):
        return {"contextResponses": [{"contextElement": {"attributes": [{"name": "temperature", "values": blocos}]},
                                      "statusCode": {"code": "200"}}]}

    def test_media_por_minuto(self):
        # origem = início da hora; offset = minuto dentro da hora
        resp = self.resposta([{"_id": {"origin": "2026-10-07T11:00:00.000Z", "resolution": "minute"},
                               "points": [{"offset": 59, "samples": 4, "sum": 52.0},
                                          {"offset": 0, "samples": 0, "sum": 0}]},
                              {"_id": {"origin": "2026-10-07T12:00:00.000Z", "resolution": "minute"},
                               "points": [{"offset": 0, "samples": 2, "sum": 27.0}]}])
        inicio, fim = AGORA - timedelta(hours=1), AGORA
        pontos = dominio.pontos_do_sth(resp, inicio, fim)
        self.assertEqual(pontos, [{"t": "2026-10-07T11:59:00.000Z", "v": 13.0},
                                  {"t": "2026-10-07T12:00:00.000Z", "v": 13.5}])

    def test_por_hora_atravessando_dias_e_ordem(self):
        resp = self.resposta([{"_id": {"origin": "2026-10-07T00:00:00.000Z", "resolution": "hour"},
                               "points": [{"offset": 10, "samples": 1, "sum": 14.0}, {"offset": 2, "samples": 2, "sum": 26.0}]},
                              {"_id": {"origin": "2026-10-06T00:00:00.000Z", "resolution": "hour"},
                               "points": [{"offset": 23, "samples": 1, "sum": 12.0}]}])
        pontos = dominio.pontos_do_sth(resp, AGORA - timedelta(hours=24), AGORA)
        self.assertEqual([p["t"] for p in pontos],
                         ["2026-10-06T23:00:00.000Z", "2026-10-07T02:00:00.000Z", "2026-10-07T10:00:00.000Z"])
        self.assertEqual([p["v"] for p in pontos], [12.0, 13.0, 14.0])

    def test_ignora_pontos_fora_da_janela(self):
        resp = self.resposta([{"_id": {"origin": "2026-10-07T00:00:00.000Z", "resolution": "hour"},
                               "points": [{"offset": 1, "samples": 1, "sum": 99.0}, {"offset": 11, "samples": 1, "sum": 13.0}]}])
        pontos = dominio.pontos_do_sth(resp, AGORA - timedelta(hours=1), AGORA)
        self.assertEqual(pontos, [{"t": "2026-10-07T11:00:00.000Z", "v": 13.0}])

    def test_resposta_vazia_ou_estranha(self):
        for resp in [{}, {"contextResponses": []}, None, {"contextResponses": [{"contextElement": {"attributes": []}}]}]:
            self.assertEqual(dominio.pontos_do_sth(resp, AGORA - timedelta(hours=1), AGORA), [])


class TestAtual(unittest.TestCase):
    def test_ok(self):
        r = dominio.montar_atual("wgn001", entidade(), AGORA)
        self.assertEqual(r["estado"], "ok")
        self.assertTrue(r["online"])
        self.assertEqual((r["temperature"], r["humidity"], r["luminosity"]), (13.4, 68.2, 3))
        self.assertEqual((r["firmware"], r["rssi"], r["muted"], r["state"]), ("2.3", -64, 0, "ok"))
        self.assertEqual(r["ultimaLeitura"], "2026-10-07T12:00:25.000Z")
        self.assertEqual(r["deviceId"], "wgn001")

    def test_alerta(self):
        self.assertEqual(dominio.montar_atual("wgn001", entidade(state="alerta"), AGORA)["estado"], "alerta")

    def test_suspenso_vence_offline(self):
        r = dominio.montar_atual("wgn001", entidade(state="suspenso", segundos_atras=600), AGORA)
        self.assertEqual(r["estado"], "suspenso")

    def test_offline(self):
        r = dominio.montar_atual("wgn001", entidade(segundos_atras=31), AGORA)
        self.assertEqual((r["estado"], r["online"]), ("offline", False))
        self.assertEqual(r["temperature"], 13.4)  # mantém a última leitura conhecida

    def test_limite_de_30_segundos(self):
        self.assertEqual(dominio.montar_atual("wgn001", entidade(segundos_atras=30), AGORA)["estado"], "ok")

    def test_aguardando(self):
        r = dominio.montar_atual("wgn001", None, AGORA)
        self.assertEqual(r["estado"], "aguardando")
        self.assertEqual((r["temperature"], r["humidity"], r["luminosity"], r["ultimaLeitura"]), (None, None, None, None))
        self.assertFalse(r["online"])

    def test_entidade_criada_mas_sem_leituras(self):
        vazia = {"id": "x", "type": "WineGuardNode"}
        self.assertEqual(dominio.montar_atual("wgn001", vazia, AGORA)["estado"], "aguardando")

    def test_chaves_do_contrato(self):
        r = dominio.montar_atual("wgn001", entidade(), AGORA)
        self.assertEqual(set(r), {"deviceId", "estado", "state", "muted", "firmware", "temperature", "humidity",
                                  "luminosity", "online", "rssi", "ultimaLeitura"})


if __name__ == "__main__":
    unittest.main()
