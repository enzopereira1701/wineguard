# WineGuard Cloud (backend)

API em FastAPI que liga o dashboard ao FIWARE. **Etapa atual: Backend 3** (triggers, alertas e o vigia que avalia tudo a cada 5 s), sobre o Backend 2 (cadastro de dispositivos no IoT Agent com apikey e resumo) e o Backend 1 (leitura atual, histórico e comandos).

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
| `GET /api/vinherias/{id}/resumo` | Estado de cada dispositivo numa chamada só (`alertasAtivos` é a contagem real) |
| `GET /api/dispositivos/{id}/triggers` | Triggers em vigor (se nunca definidos, os do preset do dispositivo) |
| `PUT /api/dispositivos/{id}/triggers` | Valida, salva, manda `setTriggers` ao Node e responde `{recebido, deviceId, em}` quando ele confirma. Sem confirmação: 504 (os limites ficam salvos e são reenviados quando o Node voltar) |
| `GET /api/vinherias/{id}/alertas?estado=todos\|ativos\|encerrados&deviceId=` | Histórico de alertas, do mais novo para o mais antigo (`fim: null` = em andamento) |

As rotas por dispositivo aceitam `?vinheriaId=` (padrão: `FIWARE_SERVICE`). A adega do dispositivo é descoberta pelo atributo `adegaId` gravado na entidade do Orion.

### Como o cadastro funciona

Vinheria = `fiware-service`; adega = `fiware-servicepath`. Cadastrar um dispositivo: (1) escolhe a adega (`novaAdega "Porão Sul"` vira o servicepath `/porao_sul`); (2) garante o grupo (apikey) no IoT Agent e a assinatura do STH-Comet naquela adega; (3) reserva um `device_id` novo (`wgn002`, `wgn003`...) e registra no IoT Agent; (4) grava nome, preset e adega na entidade do Orion. Se o passo 4 falha, o 3 é desfeito.

- O contador de ids é **global** (entidade `Contador` no service `wineguard_admin`) e só cresce: um id apagado nunca volta, porque o MQTT identifica o Node só por `apikey` + `device_id`.
- A assinatura do STH agora leva `TimeInstant` na condição, para o histórico gravar a cada leitura (assinaturas antigas são atualizadas no próximo cadastro).
- Rode a API em **um processo só** (o contador usa uma trava em memória).

### Triggers, alertas e o vigia (Backend 3)

- **Triggers** ficam no atributo `triggers` da entidade do dispositivo no Orion (sem banco de dados). O `PUT` valida (mínimo < máximo, dentro do que o sensor mede), salva e envia `setTriggers|tmin,tmax,hmin,hmax,lmin,lmax`. A confirmação vem do `setTriggers_status` que o IoT Agent grava quando o Node responde no `cmdexe`.
- **O vigia** roda em segundo plano junto com a API e, a cada 5 s, lê o Orion e avalia cada dispositivo. O Node só obedece:
  - saiu da faixa: abre um alerta e manda `alert|t,high,1` (ou `low`; `h` umidade, `l` luz);
  - voltou com histerese (0,5 °C na temperatura; 2 % na umidade e na luz): encerra e manda `alert|...,0`;
  - 30 s sem leitura: alerta `offline`, com começo e fim;
  - suspenso: encerra os alertas do dispositivo;
  - Node que volta, ou API que reinicia: reenvia os triggers e os alertas em andamento;
  - o `state` do Node diverge do esperado por mais de 15 s: reenvia os alertas (reconciliação).
- **Alertas** são entidades `Alerta` no Orion (service da vinheria, servicepath `/`), com id de um contador global. Em andamento = sem o atributo `fim`. Reiniciar a API não perde nem duplica alertas: o vigia relê os que estão em andamento.
- Variáveis de ambiente: `VIGIA_ATIVO` (`0` desliga o vigia), `INTERVALO_VIGIA` (segundos, padrão 5), `ESPERA_COMANDO_SEGUNDOS` (padrão 8), `RECONCILIAR_SEGUNDOS` (padrão 15).
- O alerta de **estabilidade** (variação > 2 °C em 24 h) é avaliado pelo vigia a cada `ESTABILIDADE_INTERVALO` s (padrão 60), com o mínimo e o máximo das últimas 24 h do STH-Comet. O limite é o `estabilidadeMax` dos triggers.

### Vinherias, adegas, suspensão e estabilidade (Backend 4)

| Rota | O que faz |
|---|---|
| `GET /api/vinherias` | Lista as vinherias (com `apikey`, `status`, `vencimento`, contagens) |
| `POST /api/vinherias` | `{nome, vencimento?}` cria a vinheria (id `vin_<nome>`, apikey própria, "Adega 1") |
| `GET /api/vinherias/{id}/adegas` | Adegas da vinheria |
| `POST /api/vinherias/{id}/suspender` | Manda `suspend` a todos os Nodes e passa a recusar consultas (403) |
| `POST /api/vinherias/{id}/reativar` | Manda `resume`; se o vencimento passou, renova por 30 dias |
| `POST /api/vinherias/{id}/simular-inadimplencia` | Vence o vencimento (ontem) e suspende (para a demonstração) |
| `GET /api/dispositivos/{id}/estabilidade` | `{deviceId, min, max, variacao, instavel, limite}` das últimas 24 h |

- Vinheria e adega são entidades no Orion (service `wineguard_admin` e na própria vinheria). A vinheria padrão (`vin_demo`, apikey `winedemo`) nasce sozinha.
- Vinheria suspensa (ou com vencimento vencido, suspensa sozinha): a API responde **403**; o vigia encerra os alertas e reenvia `suspend` a quem ainda publicar.
- Variáveis: `VENCIMENTO_PADRAO_DIAS` (90) e `ESTABILIDADE_INTERVALO` (60).

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
│  ├─ gatilhos.py      regras puras de triggers e alertas (presets, validação, histerese, comandos). Sem rede
│  ├─ alertas.py       alertas guardados no Orion
│  ├─ triggers.py      ler, salvar e enviar triggers ao Node (espera a confirmação)
│  ├─ vigia.py         o loop de 5 s que avalia os triggers e comanda o Node
│  └─ rotas/           leituras, comandos, dispositivos, triggers e alertas (as rotas)
├─ tests/              regras puras, cadastro, triggers e vigia contra um FIWARE falso (tests/fake_fiware.py)
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
