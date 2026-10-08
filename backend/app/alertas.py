"""
Alertas guardados no Orion (Backend 3): sem banco de dados, cada alerta é uma entidade 'Alerta'
no service da vinheria, no servicepath '/' (assim não se mistura com as adegas).

Em andamento = sem o atributo 'fim'. O id é numérico, de um contador global que só cresce.
"""

from datetime import datetime

from . import fiware, gatilhos
from .dominio import para_iso

TIPO = "Alerta"
SERVICEPATH = "/"
ATRIBUTOS = "deviceId,variavel,sentido,valor,limite,inicio,fim"


async def abrir(cliente, vinheria_id: str, device_id: str, variavel: str, sentido, valor, limite,
                agora: datetime) -> str:
    """Registra o começo de um alerta e devolve o id da entidade."""
    numero = await fiware.reservar_numero(cliente, 1, "alertas")
    entidade = gatilhos.entidade_do_alerta(numero)
    await fiware.criar_entidade(cliente, vinheria_id, SERVICEPATH, entidade, TIPO,
                                gatilhos.corpo_alerta(device_id, variavel, sentido, valor, limite, agora))
    return entidade


async def encerrar(cliente, vinheria_id: str, entidade: str, agora: datetime):
    """Marca o fim do alerta (se a entidade sumiu, não faz nada)."""
    await fiware.gravar_metadados(cliente, vinheria_id, SERVICEPATH, entidade,
                                  {"fim": {"type": "DateTime", "value": para_iso(agora)}},
                                  tipo=TIPO, criar=False)


async def listar(cliente, vinheria_id: str, estado: str = "todos", device_id=None) -> list:
    """Alertas da vinheria no formato do contrato, do mais novo para o mais antigo."""
    entidades = await fiware.listar_entidades(cliente, vinheria_id, SERVICEPATH, tipo=TIPO, attrs=ATRIBUTOS)
    itens = [gatilhos.montar_alerta(vinheria_id, e) for e in entidades]
    return gatilhos.filtrar_alertas(itens, estado, device_id)
