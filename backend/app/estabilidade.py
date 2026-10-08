"""
Estabilidade da temperatura (Backend 4): a variação (máximo menos mínimo) das últimas 24 h, pelos
dados agregados do STH-Comet. Passou do limite (estabilidadeMax dos triggers, padrão 2 °C) = instável.
"""

from datetime import datetime, timedelta

from . import cadastro, dominio, fiware, gatilhos, vinherias


async def da_entidade(cliente, vinheria_id: str, device_id: str, servicepath: str, limite, agora: datetime) -> dict:
    inicio = agora - timedelta(hours=24)
    resp_min, resp_max = await fiware.obter_extremos(
        cliente, dominio.entidade_do_dispositivo(device_id), inicio, agora, vinheria_id, servicepath)
    return gatilhos.montar_estabilidade(
        device_id,
        gatilhos.valores_do_sth(resp_min, "min", inicio, agora),
        gatilhos.valores_do_sth(resp_max, "max", inicio, agora),
        limite)


async def obter(cliente, vinheria_id: str, device_id: str, agora: datetime) -> dict:
    """Corpo de GET /dispositivos/{id}/estabilidade."""
    await vinherias.exigir(cliente, vinheria_id)
    entidade, servicepath = await cadastro._achar(cliente, vinheria_id, device_id)
    if entidade is None:
        raise cadastro.DispositivoNaoEncontrado(device_id)
    completa = await fiware.obter_atributos(cliente, dominio.entidade_do_dispositivo(device_id),
                                            "triggers,preset", vinheria_id, servicepath)
    limite = gatilhos.triggers_da_entidade(completa)["estabilidadeMax"]
    return await da_entidade(cliente, vinheria_id, device_id, servicepath, limite, agora)
