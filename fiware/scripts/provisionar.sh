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
#   bash provisionar.sh vin_santacruz /adega2 santacruz 002
#
# Cada vinheria = um "service" (isolamento de dados multi-tenant).
# Cada adega     = um "servicepath".
# Cada Node      = device_id wgn<numero>.
# Rodar de novo e seguro: "409 Conflict" so quer dizer que ja existe.
# ============================================================

SERVICE="${1:-vin_demo}"
SERVICEPATH="${2:-/adega1}"
APIKEY="${3:-winedemo}"
NUM="${4:-001}"

DEVICE_ID="wgn${NUM}"
ENTITY="urn:ngsi-ld:WineGuardNode:${NUM}"
IOTA="http://localhost:4041"
ORION="http://localhost:1026"

# envia um POST e mostra so o codigo HTTP (e o corpo se houver erro)
post() {
  local url="$1" body="$2" resp code text
  resp=$(curl -sS -w "\n%{http_code}" -X POST "$url" \
    -H "fiware-service: ${SERVICE}" \
    -H "fiware-servicepath: ${SERVICEPATH}" \
    -H "Content-Type: application/json" \
    -d "$body")
  code=$(echo "$resp" | tail -n1)
  text=$(echo "$resp" | sed '$d')
  echo "   -> HTTP ${code}"
  if [ "$code" != "201" ] && [ -n "$text" ]; then echo "   ${text}"; fi
}

echo "Vinheria (service):  ${SERVICE}"
echo "Adega (servicepath): ${SERVICEPATH}"
echo "Apikey:              ${APIKEY}"
echo "Dispositivo:         ${DEVICE_ID}  (${ENTITY})"
echo

echo "1/3 Criando service group..."
post "${IOTA}/iot/services" "{\"services\":[{\"apikey\":\"${APIKEY}\",\"cbroker\":\"http://fiware-orion:1026\",\"entity_type\":\"WineGuardNode\",\"resource\":\"/iot/d\"}]}"

echo "2/3 Criando dispositivo ${DEVICE_ID}..."
post "${IOTA}/iot/devices" "{\"devices\":[{\"device_id\":\"${DEVICE_ID}\",\"entity_name\":\"${ENTITY}\",\"entity_type\":\"WineGuardNode\",\"protocol\":\"PDI-IoTA-UltraLight\",\"transport\":\"MQTT\",\"attributes\":[{\"object_id\":\"t\",\"name\":\"temperature\",\"type\":\"Number\"},{\"object_id\":\"h\",\"name\":\"humidity\",\"type\":\"Number\"},{\"object_id\":\"l\",\"name\":\"luminosity\",\"type\":\"Number\"},{\"object_id\":\"st\",\"name\":\"state\",\"type\":\"Text\"},{\"object_id\":\"mu\",\"name\":\"muted\",\"type\":\"Number\"},{\"object_id\":\"rs\",\"name\":\"rssi\",\"type\":\"Number\"},{\"object_id\":\"fw\",\"name\":\"firmware\",\"type\":\"Text\"}],\"commands\":[{\"name\":\"setTriggers\",\"type\":\"command\"},{\"name\":\"alert\",\"type\":\"command\"},{\"name\":\"mute\",\"type\":\"command\"},{\"name\":\"suspend\",\"type\":\"command\"},{\"name\":\"resume\",\"type\":\"command\"},{\"name\":\"setInterval\",\"type\":\"command\"},{\"name\":\"identify\",\"type\":\"command\"}]}]}"

echo "3/3 Criando assinatura do STH-Comet (historico)..."
post "${ORION}/v2/subscriptions" "{\"description\":\"Historico WineGuard no STH-Comet\",\"subject\":{\"entities\":[{\"idPattern\":\".*\",\"type\":\"WineGuardNode\"}],\"condition\":{\"attrs\":[\"temperature\",\"humidity\",\"luminosity\"]}},\"notification\":{\"http\":{\"url\":\"http://fiware-sth-comet:8666/notify\"},\"attrs\":[\"temperature\",\"humidity\",\"luminosity\"],\"attrsFormat\":\"legacy\"}}"

echo
echo "Pronto. No firmware (config.h) use:"
echo "  API_KEY   \"${APIKEY}\""
echo "  DEVICE_ID \"${DEVICE_ID}\""
