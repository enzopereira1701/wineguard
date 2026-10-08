"""Tradução dos erros do backend em respostas HTTP (usada por todas as rotas)."""

import httpx
from fastapi import HTTPException

from .. import cadastro, fiware, triggers, vinherias


async def executar(corrotina):
    """Roda a corrotina e troca cada erro conhecido pelo status HTTP certo, com {detail} em português."""
    try:
        return await corrotina
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except vinherias.VinheriaDesconhecida:
        raise HTTPException(status_code=404, detail="vinheria não encontrada")
    except vinherias.VinheriaSuspensa:
        raise HTTPException(status_code=403, detail="Vinheria suspensa por inadimplência. Regularize o pagamento para voltar a usar o serviço.")
    except cadastro.DispositivoNaoEncontrado:
        raise HTTPException(status_code=404, detail="dispositivo não encontrado")
    except triggers.NodeNaoConfirmou as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except fiware.FiwareIndisponivel as exc:
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")
    except httpx.HTTPError as exc:  # rede fora de fiware.py (não deveria acontecer)
        raise HTTPException(status_code=502, detail=f"FIWARE indisponível: {exc}")
