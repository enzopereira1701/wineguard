# WineGuard Cloud (backend)

API em FastAPI que liga o dashboard ao FIWARE. **Etapa atual: Backend 1** (leitura atual e histórico, mais o envio de comandos).

## Rodar

Na pasta `backend`, no Git Bash (Windows):

```bash
py -m venv .venv                      # cria o ambiente virtual (uma vez)
source .venv/Scripts/activate         # ativa (aparece "(.venv)" no começo da linha)
pip install -r requirements.txt       # instala as bibliotecas (uma vez)
cp .env.example .env                  # e edite o .env (FIWARE_HOST)
uvicorn app.main:app --reload         # sobe a API em http://127.0.0.1:8000
```

Documentação interativa: <http://127.0.0.1:8000/docs>. Para ativar o ambiente em outro dia, só o `source .venv/Scripts/activate`.

## Rotas desta etapa

| Rota | O que faz |
|---|---|
| `GET /saude` | A API está no ar e aponta para onde |
| `GET /api/dispositivos/{id}/atual` | Última leitura e estado (`ok`, `alerta`, `offline`, `suspenso`, `aguardando`) |
| `GET /api/dispositivos/{id}/historico?periodo=1h\|24h\|7d` | Séries de temperatura, umidade e luz (média por minuto ou por hora) |
| `POST /api/dispositivos/{id}/comando` | Manda `mute`, `identify`, etc. ao Node |

O formato das respostas está em `docs/api-contrato.md` (na raiz do repositório).

## Estrutura

```
backend/
├─ app/
│  ├─ main.py          cria a API, o CORS e registra as rotas
│  ├─ config.py        variáveis do .env
│  ├─ dominio.py       regras puras (id, janelas de tempo, médias, estado). Sem rede
│  ├─ fiware.py        chamadas ao Orion e ao STH-Comet
│  └─ rotas/           leituras.py e comandos.py (as rotas)
├─ tests/              testes das regras de dominio.py
├─ diagnostico.py      mostra as respostas cruas do FIWARE (sem instalar nada)
├─ requirements.txt    bibliotecas
└─ .env.example        modelo do .env
```

## Testes

```bash
python -m unittest discover -s tests -v
```

## Quando algo não funciona

`python diagnostico.py` mostra a resposta crua do Orion e do STH-Comet e diz se o problema é a rede, o cadastro ou o formato.
