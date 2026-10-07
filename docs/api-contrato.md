# Contrato da API do WineGuard

Este é o formato que o dashboard espera do backend (FastAPI). O mock (`src/services/mock.js`) já devolve
exatamente isto. Todos os caminhos começam em `VITE_API_URL`. Erros: status 4xx/5xx com `{ "detail": "mensagem" }`.

Datas em ISO 8601 (`2026-10-06T14:35:00.000Z`). Nomes de campos em inglês só para as variáveis do FIWARE
(`temperature`, `humidity`, `luminosity`); o resto está em português.

## Vinherias

| Método e caminho | Corpo | Resposta |
|---|---|---|
| `GET /api/vinherias` | | lista de vinherias |
| `POST /api/vinherias` | `{ "nome": "Quinta do Sol", "vencimento": "2026-11-30" }` | a vinheria criada |
| `POST /api/vinherias/{id}/suspender` | | `{ "ok": true }` |
| `POST /api/vinherias/{id}/reativar` | | `{ "ok": true }` (renova o vencimento por 30 dias se já passou) |
| `POST /api/vinherias/{id}/simular-inadimplencia` | | `{ "ok": true }` (vencimento = ontem e suspende) |

```json
{
  "id": "vin_demo", "nome": "Vinheria Demo", "apikey": "winedemo",
  "vencimento": "2026-11-05T00:00:00.000Z", "status": "ativa",
  "suspensaEm": null, "dispositivos": 2
}
```

`status` é `"ativa"` ou `"suspensa"`. `id` = `fiware-service`; `apikey` = apikey do service group.

## Adegas e dispositivos

| Método e caminho | Resposta |
|---|---|
| `GET /api/vinherias/{id}/adegas` | `[{ "id": "vin_demo/adega1", "vinheriaId": "vin_demo", "servicepath": "/adega1", "nome": "Adega 1" }]` |
| `GET /api/vinherias/{id}/dispositivos` | `[{ "id": "wgn001", "vinheriaId": "vin_demo", "adegaId": "vin_demo/adega1", "nome": "Adega principal", "preset": "guarda_geral", "criadoEm": "..." }]` |
| `POST /api/vinherias/{id}/dispositivos` | veja abaixo |
| `PATCH /api/dispositivos/{id}` (corpo `{ "nome", "adegaId" }`) | o dispositivo atualizado |
| `DELETE /api/dispositivos/{id}` | `{ "ok": true }` |
| `GET /api/vinherias/{id}/resumo` | estado de cada dispositivo (veja abaixo) |

Cadastro: corpo `{ "vinheriaId", "adegaId", "novaAdega", "nome", "preset" }`. Use `adegaId` OU `novaAdega` (o outro vai `null`).
O backend gera o próximo `wgn###`, cadastra no IoT Agent COM `apikey` e devolve:

```json
{
  "dispositivo": { "id": "wgn005", "vinheriaId": "vin_demo", "adegaId": "vin_demo/adega1", "nome": "Cave", "preset": "espumante", "criadoEm": "..." },
  "config": { "deviceId": "wgn005", "apikey": "winedemo", "nomeVinheria": "Vinheria Demo", "nomeAdega": "Adega 1" }
}
```

Resumo:

```json
[{ "deviceId": "wgn001", "estado": "ok", "ultimaLeitura": "2026-10-06T14:35:00.000Z", "alertasAtivos": 0 }]
```

`estado`: `"ok"`, `"alerta"`, `"offline"` (30 s sem leitura), `"suspenso"` ou `"aguardando"` (nunca enviou leitura).

## Leituras

`GET /api/dispositivos/{id}/atual`

```json
{
  "deviceId": "wgn001", "estado": "ok", "state": "ok", "muted": 0, "firmware": "2.0",
  "temperature": 13.4, "humidity": 68.2, "luminosity": 3, "online": true,
  "rssi": -64, "ultimaLeitura": "2026-10-06T14:35:00.000Z"
}
```

Para `aguardando`, as três leituras vêm `null`.

`GET /api/dispositivos/{id}/historico?periodo=1h|24h|7d` (do STH-Comet, porta 8666)

```json
{ "deviceId": "wgn001",
  "temperature": [{ "t": "2026-10-06T13:35:00.000Z", "v": 13.2 }],
  "humidity":    [{ "t": "2026-10-06T13:35:00.000Z", "v": 68.0 }],
  "luminosity":  [{ "t": "2026-10-06T13:35:00.000Z", "v": 3 }] }
```

Cada série em ordem crescente de `t`. Pontos esperados: 1h = 60, 24h = 96, 7d = 84 (pode vir menos). O dashboard junta as
três séries por proximidade de tempo (2 s), então pequenas diferenças de milissegundos não atrapalham.

`GET /api/dispositivos/{id}/estabilidade` (mínimo e máximo da temperatura em 24 h, via agregação do STH-Comet)

```json
{ "deviceId": "wgn001", "min": 12.7, "max": 14.1, "variacao": 1.4, "instavel": false, "limite": 2 }
```

## Triggers

`GET /api/dispositivos/{id}/triggers` e `PUT /api/dispositivos/{id}/triggers` (mesmo formato):

```json
{
  "preset": "guarda_geral", "modo": "referencia",
  "temp": { "min": 10, "max": 15 }, "umid": { "min": 60, "max": 75 }, "luz": { "min": 0, "max": 10 },
  "estabilidadeMax": 2, "luzEscuro": null
}
```

`preset`: `guarda_geral`, `longa_guarda` ou `espumante`. `modo`: `referencia` ou `personalizado`. O `PUT` valida, guarda, manda
`setTriggers|tmin,tmax,hmin,hmax,lmin,lmax` ao Node e responde quando ele confirmar (cmdexe):

```json
{ "recebido": true, "deviceId": "wgn001", "em": "2026-10-06T14:36:00.000Z" }
```

## Alertas

`GET /api/vinherias/{id}/alertas?estado=todos|ativos|encerrados&deviceId=wgn001` (do mais novo para o mais antigo)

```json
[{ "id": 12, "vinheriaId": "vin_demo", "deviceId": "wgn001", "variavel": "temperature",
   "sentido": "acima", "valor": 15.8, "limite": 15,
   "inicio": "2026-10-04T10:00:00.000Z", "fim": null }]
```

`variavel`: `temperature`, `humidity`, `luminosity`, `estabilidade` ou `offline`. `sentido`: `acima`, `abaixo` ou `null`.
`fim: null` = em andamento. Em `estabilidade`, `valor` é a variação em °C e `limite` é o máximo aceito.

## Comandos

`POST /api/dispositivos/{id}/comando` com `{ "comando": "mute", "valor": "1" }` -> `{ "enviado": true }`.
Comandos aceitos: `mute` ("1" liga, "0" desliga), `identify`, `suspend`, `resume`, `setInterval`, `alert`, `setTriggers`.
