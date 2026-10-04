#!/usr/bin/env bash
# ============================================================
# provisionar.sh - WineGuard (marcha.dev)
# Cadastra no FIWARE uma vinheria (service), o dispositivo (Node)
# e a assinatura que manda o historico para o STH-Comet.
#
# Rode DENTRO da maquina onde o FIWARE esta (usa localhost).
#
# Uso:
#   bash provisionar.sh [service] [servicepath] [apikey] [numero]
#
# Exemplos:
#   bash provisionar.sh                                  # vin_demo /adega1 winedemo 001
#   bash provisionar.sh vin_santacruz /adega1 santacruz 001
#
# Cada vinheria = um "service" (isolamento de dados multi-tenant).
# Cada adega     = um "servicepath".
# Cada Node      = device_id wgn<numero>.
#
# IMPORTANTE: o dispositivo e cadastrado COM a apikey. Sem ela, o IoT Agent
# nao reconhece o cadastro quando chega a primeira mensagem MQTT, cria um
# dispositivo novo sozinho (sem o mapeamento t -> temperature etc.) e as
# leituras vao para uma entidade errada.
#
# Pode rodar de novo: o script apaga o cadastro antigo do dispositivo (e a
# entidade no Orion) antes de criar. O historico no STH-Comet e mantido.
# ============================================================

SERVICE="${1:-vin_demo}"
SERVICEPATH="${2:-/adega1}"
APIKEY="${3:-winedemo}"
NUM="${4:-001}"

DEVICE_ID="wgn${NUM}"
ENTITY="urn:ngsi-ld:WineGuardNode:${NUM}"
ENTITY_AUTO="WineGuardNode:${DEVICE_ID}"   # nome que o IoT Agent cria sozinho
IOTA="http://localhost:4041"
ORION="http://localhost:1026"

H1="fiware-service: ${SERVICE}"
H2="fiware-servicepath: ${SERVICEPATH}"

# envia um POST e mostra so o codigo HTTP (e o corpo se houver erro)
post() {
  local url="$1" body="$2" resp code text
  resp=$(curl -sS -w "\n%{http_code}" -X POST "$url" \
    -H "$H1" -H "$H2" -H "Content-Type: application/json" -d "$body")
  code=$(echo "$resp" | tail -n1)
  text=$(echo "$resp" | sed '$d')
  echo "   -> HTTP ${code}"
  if [ "$code" != "201" ] && [ -n "$text" ]; then echo "   ${text}"; fi
}

# envia um DELETE e devolve so o codigo HTTP
del() {
  curl -s -o /dev/null -w "%{http_code}" -X DELETE "$1" -H "$H1" -H "$H2"
}

echo "Vinheria (service):  ${SERVICE}"
echo "Adega (servicepath): ${SERVICEPATH}"
echo "Apikey:              ${APIKEY}"
echo "Dispositivo:         ${DEVICE_ID}  (${ENTITY})"
echo

echo "0/4 Limpando cadastros antigos do dispositivo..."
# pode haver mais de um registro com o mesmo id (o cadastrado e o criado
# automaticamente), por isso repete ate o IoT Agent responder 404
for i in 1 2 3 4; do
  code=$(del "${IOTA}/iot/devices/${DEVICE_ID}")
  echo "   dispositivo ${DEVICE_ID}: HTTP ${code}"
  [ "$code" = "404" ] && break
done
echo "   entidade ${ENTITY}: HTTP $(del "${ORION}/v2/entities/${ENTITY}?type=WineGuardNode")"
echo "   entidade ${ENTITY_AUTO}: HTTP $(del "${ORION}/v2/entities/${ENTITY_AUTO}?type=WineGuardNode")"

# assinaturas antigas do historico (evita historico gravado em duplicidade)
SUBS=$(curl -s "${ORION}/v2/subscriptions?limit=100" -H "$H1" -H "$H2" | python3 -c '
import sys, json
try:
    for s in json.load(sys.stdin):
        if str(s.get("description", "")).startswith("Historico WineGuard"):
            print(s["id"])
except Exception:
    pass')
for id in $SUBS; do
  echo "   assinatura ${id}: HTTP $(del "${ORION}/v2/subscriptions/${id}")"
done
echo

echo "1/4 Criando service group..."
post "${IOTA}/iot/services" "{\"services\":[{\"apikey\":\"${APIKEY}\",\"cbroker\":\"http://fiware-orion:1026\",\"entity_type\":\"WineGuardNode\",\"resource\":\"/iot/d\"}]}"

echo "2/4 Criando dispositivo ${DEVICE_ID} (com apikey)..."
post "${IOTA}/iot/devices" "{\"devices\":[{\"device_id\":\"${DEVICE_ID}\",\"apikey\":\"${APIKEY}\",\"entity_name\":\"${ENTITY}\",\"entity_type\":\"WineGuardNode\",\"protocol\":\"PDI-IoTA-UltraLight\",\"transport\":\"MQTT\",\"attributes\":[{\"object_id\":\"t\",\"name\":\"temperature\",\"type\":\"Number\"},{\"object_id\":\"h\",\"name\":\"humidity\",\"type\":\"Number\"},{\"object_id\":\"l\",\"name\":\"luminosity\",\"type\":\"Number\"},{\"object_id\":\"st\",\"name\":\"state\",\"type\":\"Text\"},{\"object_id\":\"mu\",\"name\":\"muted\",\"type\":\"Number\"},{\"object_id\":\"rs\",\"name\":\"rssi\",\"type\":\"Number\"},{\"object_id\":\"fw\",\"name\":\"firmware\",\"type\":\"Text\"}],\"commands\":[{\"name\":\"setTriggers\",\"type\":\"command\"},{\"name\":\"alert\",\"type\":\"command\"},{\"name\":\"mute\",\"type\":\"command\"},{\"name\":\"suspend\",\"type\":\"command\"},{\"name\":\"resume\",\"type\":\"command\"},{\"name\":\"setInterval\",\"type\":\"command\"},{\"name\":\"identify\",\"type\":\"command\"}]}]}"

echo "3/4 Criando assinatura do STH-Comet (historico)..."
post "${ORION}/v2/subscriptions" "{\"description\":\"Historico WineGuard no STH-Comet\",\"subject\":{\"entities\":[{\"idPattern\":\".*\",\"type\":\"WineGuardNode\"}],\"condition\":{\"attrs\":[\"temperature\",\"humidity\",\"luminosity\"]}},\"notification\":{\"http\":{\"url\":\"http://fiware-sth-comet:8666/notify\"},\"attrs\":[\"temperature\",\"humidity\",\"luminosity\"],\"attrsFormat\":\"legacy\"}}"

echo "4/4 Conferindo dispositivos cadastrados..."
curl -s "${IOTA}/iot/devices" -H "$H1" -H "$H2" | grep -o '"count":[0-9]*\|"device_id":"[^"]*"\|"entity_name":"[^"]*"\|"apikey":"[^"]*"'

echo
echo "Pronto. Deve aparecer count 1, com apikey ${APIKEY}."
echo "No firmware (config.h) use:"
echo "  API_KEY   \"${APIKEY}\""
echo "  DEVICE_ID \"${DEVICE_ID}\""
