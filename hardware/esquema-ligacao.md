# Esquema de ligação do WineGuard Node

![Esquema de ligação](esquema-ligacao.png)

O desenho é **lógico**: mostra quem liga em quem, e não a posição física dos pinos na placa. Todos os módulos são alimentados em
**3V3**, distribuído por um protoboard. **Nunca ligue 5 V nos módulos**: os pinos do ESP32 não toleram 5 V.

## Tabela de ligações

| Módulo | Pino do módulo | Liga em | Observação |
|---|---|---|---|
| **DHT22** (3 pinos) | VCC | 3V3 | |
| | GND | GND | |
| | DATA (S) | **D5** | |
| **LDR** (3 pinos) | VCC | 3V3 | |
| | GND | GND | |
| | AO | **D34** | Entrada analógica (ADC1). O D34 só é entrada |
| **Buzzer ativo** (3 pinos) | VCC | 3V3 | |
| | GND | GND | |
| | S | **D18** | O módulo usado apita com nível baixo |
| **LED RGB KY-016** | R | **D25** | Vermelho = temperatura |
| | G | **D26** | Verde = luminosidade |
| | B | **D27** | Azul = umidade |
| | GND | GND | Cátodo comum |
| **OLED SSD1306** (I2C) | VCC | 3V3 | |
| | GND | GND | |
| | SDA | **D21** | |
| | SCL | **D22** | Endereço I2C 0x3C |
| **Botão de mudo** (3 pinos) | VCC | 3V3 | |
| | GND | GND | |
| | S | **D14** | O firmware detecta a polaridade ao ligar |

## Cuidados

- **Confira os rótulos impressos nos módulos.** A ordem dos pinos (VCC, GND, sinal) muda entre fabricantes.
- **LED RGB:** o módulo KY-016 costuma trazer os resistores de proteção. Se o seu for um LED RGB solto, ligue um resistor de ~220 Ω em
  série em cada cor (como no circuito do Wokwi).
- **Não aperte o botão ao ligar o Node:** é nesse momento que o firmware descobre a polaridade do módulo.
- **Rede:** o Wi-Fi do ESP32 é só de 2,4 GHz.

## Como testar a montagem (um componente por vez)

1. **OLED:** ao ligar, aparece o logo do WineGuard. Se a tela ficar apagada, confira SDA e SCL.
2. **DHT22:** com o monitor serial a 115200, a temperatura e a umidade aparecem na tela. Aqueça o sensor com a mão para ver mudar.
3. **LDR:** cubra o sensor com a mão e olhe o valor de luz. O esperado é **cair** ao cobrir. Se **subir**, coloque
   `#define LDR_INVERTIDO 0` no `config.h`.
4. **LED e buzzer:** com o ambiente fora dos limites (a sala costuma passar de 15 °C), o LED vermelho acende fixo e o buzzer toca.
   Se o buzzer tocar direto em repouso, coloque `#define BUZZER_ATIVO_EM_LOW 1`.
5. **Botão:** um aperto rápido liga o mudo (aparece "MUDO" na tela) e outro desliga.
