"""
Triggers de um dispositivo (Backend 3): ler, salvar no Orion e mandar ao Node.

Os triggers ficam no atributo 'triggers' da entidade do dispositivo. O PUT salva primeiro e depois
envia setTriggers ao Node; se o Node não confirmar (offline), os limites ficam salvos e o vigia
os reenvia quando ele voltar.
"""

import asyncio
from datetime import datetime, timezone

from . import cadastro, config, dominio, fiware, gatilhos


class NodeNaoConfirmou(Exception):
    """O Node não respondeu ao setTriggers a tempo (offline ou erro)."""


async def obter(cliente, vinheria_id: str, device_id: str) -> dict:
    cadastro._apikey(vinheria_id)
    entidade, servicepath = await cadastro._achar(cliente, vinheria_id, device_id)
    if entidade is None:
        raise cadastro.DispositivoNaoEncontrado(device_id)
    return gatilhos.triggers_da_entidade(
        await fiware.obter_atributos(cliente, dominio.entidade_do_dispositivo(device_id),
                                     "triggers,preset", vinheria_id, servicepath))


async def salvar(cliente, vinheria_id: str, device_id: str, corpo: dict) -> dict:
    """Valida, salva e envia ao Node. Devolve {recebido, deviceId, em} quando o Node confirma."""
    cadastro._apikey(vinheria_id)
    triggers = gatilhos.validar_triggers(corpo)
    entidade_id = dominio.entidade_do_dispositivo(device_id)
    entidade, servicepath = await cadastro._achar(cliente, vinheria_id, device_id)
    if entidade is None:
        raise cadastro.DispositivoNaoEncontrado(device_id)

    await fiware.gravar_metadados(cliente, vinheria_id, servicepath, entidade_id, {
        "triggers": {"type": "StructuredValue", "value": triggers},
        "preset": {"type": "Text", "value": triggers["preset"]},
    })

    antes = gatilhos.quando_o_status_mudou(
        await fiware.obter_atributos(cliente, entidade_id, "setTriggers_status", vinheria_id, servicepath),
        "setTriggers")
    await fiware.enviar_comando(cliente, entidade_id, "setTriggers", gatilhos.comando_set_triggers(triggers),
                                vinheria_id, servicepath)

    limite = asyncio.get_running_loop().time() + config.ESPERA_COMANDO_SEGUNDOS
    while True:
        situacao = gatilhos.estado_do_comando(
            await fiware.obter_atributos(cliente, entidade_id, "setTriggers_status", vinheria_id, servicepath),
            "setTriggers", antes)
        if situacao == "ok":
            return {"recebido": True, "deviceId": device_id, "em": dominio.para_iso(datetime.now(timezone.utc))}
        if situacao == "erro":
            raise NodeNaoConfirmou("o Node recusou os limites")
        if asyncio.get_running_loop().time() >= limite:
            raise NodeNaoConfirmou("o Node não confirmou o recebimento (está offline?). "
                                   "Os limites foram salvos e serão enviados quando ele voltar.")
        await asyncio.sleep(0.4)
