# WineGuard Cloud (backend)

API em FastAPI que liga o dashboard ao FIWARE. **Etapa atual: Backend 2** (cadastro de dispositivos no IoT Agent com apikey, resumo da vinheria e comandos), sobre o Backend 1 (leitura atual e histórico).

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
| `GET /api/vinherias/{id}/dispositivos` | Lista os dispositivos de todas as adegas da vinheria |
| `POST /api/vinherias/{id}/dispositivos` | Cadastra: registra no IoT Agent **com apikey** e devolve `{dispositivo, config:{deviceId, apikey, ...}}`. Informe `adegaId` **ou** `novaAdega` |
| `PATCH /api/dispositivos/{id}` | Renomeia (`nome`). Trocar de adega ainda não é suportado (400) |
| `DELETE /api/dispositivos/{id}` | Manda `suspend`, remove do IoT Agent e do Orion |
| `GET /api/vinherias/{id}/resumo` | Estado de cada dispositivo numa chamada só |

As rotas por dispositivo aceitam `?vinheriaId=` (padrão: `FIWARE_SERVICE`). A adega do dispositivo é descoberta pelo atributo `adegaId` gravado na entidade do Orion.

### Como o cadastro funciona

Vinheria = `fiware-service`; adega = `fiware-servicepath`. Cadastrar um dispositivo: (1) escolhe a adega (`novaAdega "Porão Sul"` vira o servicepath `/porao_sul`); (2) garante o grupo (apikey) no IoT Agent e a assinatura do STH-Comet naquela adega; (3) reserva um `device_id` novo (`wgn002`, `wgn003`...) e registra no IoT Agent; (4) grava nome, preset e adega na entidade do Orion. Se o passo 4 falha, o 3 é desfeito.

- O contador de ids é **global** (entidade `Contador` no service `wineguard_admin`) e só cresce: um id apagado nunca volta, porque o MQTT identifica o Node só por `apikey` + `device_id`.
- A assinatura do STH agora leva `TimeInstant` na condição, para o histórico gravar a cada leitura (assinaturas antigas são atualizadas no próximo cadastro).
- Rode a API em **um processo só** (o contador usa uma trava em memória).
- `alertasAtivos` do resumo é provisório (1 se o estado é `alerta`); o Backend 3 conta os alertas de verdade.

O formato das respostas está em `docs/api-contrato.md` (na raiz do repositório).

## Estrutura

```
backend/
├─ app/
│  ├─ main.py          cria a API, o CORS e registra as rotas
│  ├─ config.py        variáveis do .env
│  ├─ dominio.py       regras puras (ids, adegas, janelas de tempo, médias, estado, corpos do FIWARE). Sem rede
│  ├─ fiware.py        chamadas ao Orion, STH-Comet e IoT Agent
│  ├─ cadastro.py      fluxo de cadastro, listagem, resumo, renomear e remover
│  └─ rotas/           leituras.py, comandos.py e dispositivos.py (as rotas)
├─ tests/              regras de dominio.py e o cadastro completo contra um FIWARE falso
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
