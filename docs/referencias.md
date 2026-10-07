# Referências de guarda de vinho

Os limites dos presets do WineGuard vêm de recomendações de especialistas e de fabricantes de adegas. **Não são uma norma oficial.**
Os valores de **alerta** (a faixa em que o Node dispara) são uma **adaptação do grupo** a partir dessas fontes; o **alvo** é onde a maioria
delas concorda. A luz é medida em % **relativa** (o LDR não mede em lux).

## Presets (de guarda, não de servir)

Os valores de servir (branco 8 a 12 °C, tinto 15 a 18 °C) não valem para a adega: a temperatura de **guarda** é quase a mesma
para tinto, branco e rosé.

| Preset | Temperatura | Umidade | Luz máx. |
|---|---|---|---|
| **Guarda geral** (tinto, branco, rosé) | alerta 10 a 15 °C, alvo 12 a 14 | alerta 60 a 75 %, alvo 65 a 70 | 10 % |
| **Longa guarda** | alerta 11 a 14 °C, alvo 12 a 13 | alerta 65 a 75 %, alvo 65 a 70 | 5 % |
| **Espumante** | alerta 9 a 13 °C, alvo 10 a 12 | alerta 65 a 80 %, alvo 70 a 80 | 5 % |

Além dos presets, o usuário pode **personalizar** os limites. O dashboard avisa quando os valores fogem da referência:
**bloqueia** (valor impossível ou mínimo maior que o máximo), **aviso forte** com confirmação (temperatura acima de 24 °C ou abaixo
de 4 °C; umidade abaixo de 40 % ou acima de 85 %) e **aviso leve** (fora da faixa do preset).

## Estabilidade

As fontes apontam que a **variação** de temperatura faz mais mal ao vinho do que um valor fixo um pouco fora do ideal. O sistema
avisa quando a temperatura varia mais de **2 °C em 24 horas** (limite configurável).

## Fontes

- Decanter, como guardar vinho: https://www.decanter.com/learn/how-to/how-to-store-wine-video-tutorial-54233
- Decanter, qual a melhor umidade: https://www.decanter.com/?p=458610
- Jancis Robinson: https://jancisrobinson.com/ja/node/8317
- EuroCave, dicas de guarda de vinho: https://www.eurocave.com/en/six-pieces-of-advice-for-storing-wine
- EuroCave, champagne: https://www.eurocave.com/en/eurocave-expert-advice/tips-for-properly-storing-champagne
- Nicolas Feuillatte: https://nicolas-feuillatte.com/en/blogs/articles/la-conservation-du-champagne-quelle-temperature-et-autres-astuces
- Forbes Brasil: https://forbes.com.br/forbeswsb/2025/09/como-armazenar-vinho-em-casa-dicas-para-tintos-brancos-e-espumantes/

## Fontes institucionais brasileiras

Foram consultados o material da **Embrapa Uva e Vinho** e o da **ABS (Associação Brasileira de Sommeliers)**.
O que encontramos trata da **elaboração** do vinho (por exemplo, a temperatura da fermentação malolática e boas
práticas de produção) e não da **guarda** da garrafa engarrafada. Por isso não foram usados para definir as faixas do sistema.

## Limitações

- As faixas são recomendações, e não uma norma. O usuário pode escolher "Personalizado" e ajustar.
- O DHT22 tem margem de ±0,5 °C, e por isso o sistema avisa quando a faixa de temperatura fica mais estreita que 1 °C.
- O LDR mede luz em porcentagem relativa, e não em lux.