# Lista de materiais

Tudo para **um** WineGuard Node (um por adega). Sem solda: ligações com cabos Dupont e um protoboard como distribuidor de 3V3 e GND.

| # | Item | Qtd. | Função | Observação |
|---|---|---|---|---|
| 1 | ESP32 DevKit (30 pinos) | 1 | Microcontrolador com Wi-Fi | Gravação por USB (cabo de dados) |
| 2 | Sensor DHT22, módulo de 3 pinos | 1 | Temperatura e umidade | Precisão de ±0,5 °C. Montar longe do ESP32 e com ventilação |
| 3 | Sensor de luz LDR, módulo de 3 pinos (saída AO) | 1 | Luminosidade | Mede em % **relativa**, não em lux |
| 4 | Buzzer ativo, módulo de 3 pinos | 1 | Alerta sonoro | Tom fixo. O módulo usado apita com nível baixo |
| 5 | LED RGB KY-016 (cátodo comum) | 1 | Alerta visual por cor | Vermelho = temperatura, azul = umidade, verde = luz |
| 6 | Tela OLED SSD1306 128x64, I2C | 1 | Valores, alertas e estado | Endereço 0x3C |
| 7 | Botão, módulo de 3 pinos | 1 | Silenciar o buzzer (mudo) | A polaridade é detectada pelo firmware |
| 8 | Protoboard de 400 pontos | 1 | Distribui 3V3 e GND | Funciona como "hub" de alimentação |
| 9 | Cabos Dupont (macho-macho, macho-fêmea e fêmea-fêmea) | 1 kit | Ligações | Kit de 120 unidades |
| 10 | Cabo USB (de dados) | 1 | Alimentação e gravação | Cabo curto e de qualidade: cabo fino derruba a gravação |
| 11 | Caixa 3D (PLA) | 1 | Encapsulamento | Modelada pelo grupo e impressa pela faculdade; tampa removível por parafusos |
| 12 | Parafusos pequenos | Alguns | Fecham a tampa da caixa | |

**Fonte de alimentação:** 5 V por USB (pela porta do computador ou por um carregador de celular). O ESP32 gera os 3V3 dos módulos.

> Preços e links de compra: _(preencher com os valores pagos, se o professor pedir o custo do protótipo)_.

## Como a caixa organiza os componentes

- OLED, LED, DHT22 e botão ficam na tampa, ligados por cabos Dupont.
- O DHT22 fica afastado do ESP32 (que esquenta) e com abertura para o ar.
- O LDR fica separado do LED RGB, para o próprio LED não "enganar" o sensor.
