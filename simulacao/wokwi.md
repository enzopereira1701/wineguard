# Simulação no Wokwi

**Projeto:** https://wokwi.com/projects/476972184977904641

Simula o WineGuard Node completo: ESP32, DHT22, LDR, LED RGB, buzzer, tela OLED e botão de mudo. O LDR e o DHT22 do
enunciado do CP5 estão no circuito.

## Arquivos desta pasta

| Arquivo | Para quê |
|---|---|
| `diagram.json` | O circuito (cole na aba `diagram.json` do Wokwi). Já inclui a ligação do monitor serial |
| `libraries.txt` | As bibliotecas (cole na aba `libraries.txt`) |

O código é o mesmo `hardware/firmware/wineguard_node/` (arquivos `.ino` e `icones.h`).

## Como usar

1. Abra o link do projeto (ou crie um e cole os arquivos).
2. Na aba `config.h` do Wokwi, use os valores abaixo (o IP muda a cada sessão do laboratório da AWS):

```cpp
#define SIMULACAO_WOKWI 1
#define WIFI_SSID     "Wokwi-GUEST"
#define WIFI_PASSWORD ""
#define MQTT_BROKER   "IP_ATUAL_DA_MAQUINA"
#define MQTT_PORT     1883
#define API_KEY       "winedemo"
#define DEVICE_ID     "wgn001"
#define NOME_VINHERIA "Vinheria Demo"
#define NOME_ADEGA    "Adega 1"
```

3. Clique em Play. Mexa no controle de **lux** do LDR e na temperatura e umidade do DHT22 para disparar os alertas.
4. Sem nuvem (para testar só o alarme), troque o `MQTT_BROKER` por qualquer endereço: o Node entra em modo local depois de ~15 s.

## Observação

No Wokwi o buzzer toca por `tone()` (precisa de um sinal oscilando). Na placa física o buzzer é **ativo** e basta ligar e desligar
o pino. É o que o `SIMULACAO_WOKWI` escolhe no código.
