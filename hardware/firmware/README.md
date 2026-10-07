# Firmware do WineGuard Node

Código do ESP32 em Arduino (`wineguard_node/wineguard_node.ino`). Versão atual: **2.3**.

## O que o firmware faz

- Lê temperatura e umidade (DHT22) e luminosidade (LDR, em % relativa).
- Avalia os limites sozinho (com histerese) e avisa por **LED RGB**, **buzzer** e **tela OLED**.
- Publica a telemetria por MQTT (Ultralight 2.0) e obedece aos comandos da nuvem.
- Se a nuvem sumir por mais de 15 s, continua alertando com os limites guardados na memória.
- Silencia o buzzer pelo botão ou por comando.

Arquitetura (FreeRTOS): o `loop()` cuida de Wi-Fi, MQTT, sensores e telemetria; uma tarefa cuida do botão, do LED e do buzzer
(a cada 2 ms); outra cuida da tela. Assim o alarme não trava quando a rede cai.

## Arquivos

| Arquivo | Para quê |
|---|---|
| `wineguard_node.ino` | O firmware |
| `icones.h` | Ícones 16x16 e 32x32 da tela e o logo da abertura (1 bit) |
| `config.example.h` | Modelo do `config.h` (Wi-Fi, nuvem, dispositivo e ajustes da bancada) |
| `config.h` | **Seu** arquivo, criado a partir do exemplo. **Não vai para o GitHub** |

## Como gravar na placa

1. Instale a **Arduino IDE** e, no Gerenciador de Placas, o pacote **esp32 (Espressif Systems)**.
2. Instale as bibliotecas (Ferramentas, Gerenciar Bibliotecas), aceitando as dependências:

   | Biblioteca | Versão usada |
   |---|---|
   | PubSubClient | 2.8 |
   | Adafruit GFX Library | 1.12.6 |
   | Adafruit SSD1306 | 2.5.17 |
   | DHT sensor library | 1.4.7 |
   | Adafruit Unified Sensor (dependência) | 1.1.15 |
   | Adafruit BusIO (dependência) | 1.17.4 |

   Para ver as versões instaladas: Gerenciar Bibliotecas, filtro "Instaladas". Pacote esp32 usado na bancada: **3.3.11**.
3. Copie `config.example.h` para `config.h` (mesma pasta) e preencha. Na bancada, `SIMULACAO_WOKWI` é **0**.
4. Selecione a placa **DOIT ESP32 DEVKIT V1** (na bancada; a **ESP32 Dev Module** também funciona) e a porta COM.
5. Grave. Se aparecer `Invalid head of packet (0x80)`, baixe o **Upload Speed** para 115200, use um cabo USB curto e de dados,
   ligado direto no computador, e feche outros programas que usem a porta.

## Opções do `config.h`

| Opção | Padrão | Quando mudar |
|---|---|---|
| `SIMULACAO_WOKWI` | (obrigatória) | 1 no Wokwi, **0 na bancada** |
| `BUZZER_ATIVO_EM_LOW` | 0 | **1** se o buzzer apitar direto em repouso (o módulo usado apita com nível baixo) |
| `ALTA_CONTINUO` | 1 | **0** para o alerta alto ser 1 bipe longo repetido, em vez de tom contínuo |
| `LDR_INVERTIDO` | 1 | 0 se o valor de luz **subir** ao cobrir o sensor |
| `BOTAO_PRESSIONADO` | detectado sozinho | `LOW` ou `HIGH`, só se a detecção errar |

## Alertas

| | LED | Buzzer | Tela |
|---|---|---|---|
| **ALTA** (acima do limite) | Fixo na cor da variável | 1 bipe longo repetido (ou tom contínuo) | "ALTA", valor e limite máximo |
| **BAIXA** (abaixo do limite) | Pisca junto com o som | 2 bipes e uma pausa | "BAIXA", valor e limite mínimo |

Cor do LED: **vermelho** = temperatura, **azul** = umidade, **verde** = luminosidade. Com mais de uma variável em alerta, o Node alterna
entre elas (mínimo 3 s em cada) com uma pausa de silêncio de 0,7 s. O botão silencia só o buzzer.

## Limites padrão

Valem até o Node receber os limites do backend (preset **Guarda geral**): temperatura 10 a 15 °C, umidade 60 a 75 %, luz 0 a 10 %.
Com a plataforma ligada, o backend manda `setTriggers`, e o Node guarda os novos valores na memória.

## Telemetria e comandos

```
Telemetria  t|24.5|h|60.0|l|35|st|ok|mu|0|rs|-60|fw|2.3
Comandos    <DEVICE_ID>@<comando>|<parametros>
            setTriggers|tmin,tmax,hmin,hmax,lmin,lmax     alert|<t|h|l>,<high|low>,<1|0>
            mute|<1|0>      suspend|      resume|      setInterval|<segundos>      identify|
```

## Histórico de versões

| Versão | O que mudou |
|---|---|
| 2.0 | Base: FreeRTOS, OLED, LED RGB, buzzer, mudo, failsafe |
| 2.1 | Sinal do LDR corrigido (0 % escuro, 100 % muita luz); limites padrão iguais ao preset Guarda geral |
| 2.2 | Botão lido na tarefa dos atuadores (não perde aperto quando a rede trava) |
| 2.3 | Botão detecta a polaridade sozinho e confirma o aperto por 20 ms; bipes novos: ALTA 1 bipe longo (ou contínuo), BAIXA 2 bipes |

## Antes da entrega

- `AVALIACAO_LOCAL_SEMPRE` está em **1** (o Node avalia sozinho, mesmo conectado). Quando o backend estiver no ar, mude para **0**,
  para o Node só obedecer aos comandos `alert` (e avaliar sozinho apenas se ficar offline).
