// Copie este arquivo para "config.h" (na mesma pasta) e preencha.
// O config.h NAO vai para o GitHub: ele guarda a sua senha de Wi-Fi e o endereco da nuvem.
#ifndef CONFIG_H
#define CONFIG_H

// 1 = simulacao no Wokwi, 0 = placa fisica (bancada)
#define SIMULACAO_WOKWI 1

// Wi-Fi. No Wokwi use "Wokwi-GUEST" e senha vazia.
// Na bancada: rede de 2,4 GHz (o ESP32 nao conecta em 5 GHz).
// Para testar SEM nuvem, use uma rede que nao existe (ex.: "sem_rede"): o Node nem tenta conectar
// e continua alertando com os limites guardados.
#define WIFI_SSID     "Wokwi-GUEST"
#define WIFI_PASSWORD ""

// Nome (ou IP) da maquina na nuvem onde roda o Mosquitto. Com DuckDNS o nome nao muda.
#define MQTT_BROKER   "seu-nome.duckdns.org"
#define MQTT_PORT     1883

// Mesmos valores cadastrados no FIWARE (veja fiware/scripts/provisionar.sh)
#define API_KEY       "sua_apikey"
#define DEVICE_ID     "wgn001"

#define NOME_VINHERIA "Vinheria Demo"
#define NOME_ADEGA    "Adega 1"

// ---------------- Ajustes da bancada (todos opcionais) ----------------

// Buzzer ativo de 3 pinos: a maioria dos modulos apita com nivel BAIXO.
// Se o buzzer apitar direto em repouso, use 1.
// #define BUZZER_ATIVO_EM_LOW 1

// Alerta ALTO: 0 = 1 bipe longo repetido (padrao do projeto na bancada); 1 = tom continuo.
// #define ALTA_CONTINUO 0

// LDR: o padrao e 1 (escuro = numero alto no modulo; o firmware inverte).
// Use 0 se o valor de luz SUBIR ao cobrir o sensor com a mao.
// #define LDR_INVERTIDO 0

// Botao de mudo: a polaridade e detectada sozinha ao ligar (nao aperte o botao nessa hora).
// So force se a deteccao errar: LOW = aperta leva o pino a LOW, HIGH = aperta leva a HIGH.
// #define BOTAO_PRESSIONADO LOW

#endif
