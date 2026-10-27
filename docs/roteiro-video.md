# Roteiro do vídeo: WineGuard

**Duração alvo:** cerca de 5 minutos. **Formato:** gravação de tela do dashboard + imagens do Node, com narração. Sem enrolação: cada bloco tem um objetivo e um tempo.

## Antes de gravar (checklist)

- [ ] Start Lab feito, IP do dia no `config.h` (Node regravado) e no `frontend/.env`.
- [ ] Node ligado, **online** no Painel e **sem mute** (aperte o botão e confira no OLED).
- [ ] Dashboard aberto no PC, na vinheria de demonstração, janela em tela cheia.
- [ ] Celular perto para filmar o Node (luz boa, fundo limpo).
- [ ] Fechar abas, notificações e qualquer janela que mostre senha, IP completo ou `config.h`.
- [ ] Gravar em blocos separados: é mais fácil refazer um bloco do que o vídeo inteiro.

## Roteiro

Cada vez que um **diferencial** aparece, entra na tela uma etiqueta "Diferencial" com o nome dele (lista completa em [`diferenciais.md`](diferenciais.md)).

| Tempo | Imagem | Fala (sugestão) |
|---|---|---|
| 0:00 a 0:15 | Logo e foto do Node na caixa | "Somos o grupo marcha.dev, e este é o WineGuard: monitoramento de adegas com IoT. Cada adega ganha um Node que mede o ambiente e avisa quando o vinho está em risco." |
| 0:15 a 0:35 | Animação do problema (temperatura, umidade e luz) | "O vinho estraga quando a temperatura sobe demais, a umidade sai da faixa ou a luz bate na garrafa. Em uma adega pequena, ninguém acompanha isso o dia todo. O WineGuard faz esse acompanhamento, vinte e quatro horas por dia." |
| 0:35 a 1:05 | Diagrama de arquitetura animado, bloco por bloco (IoT, Back-end e Application) | "Seguimos a arquitetura do FIWARE Descomplicado, em três blocos: IoT, Back-end e Application. No bloco IoT, o Node, um ESP32, publica as leituras por MQTT. O IoT Agent converte os dados e o Orion guarda o estado atual. O STH-Comet guarda o histórico. Nosso backend em FastAPI, em contêiner na mesma instância da AWS, consulta o FIWARE, avalia os limites a cada cinco segundos e registra os alertas. E o dashboard em React mostra tudo isso." |
| 1:05 a 1:35 | Node de perto (OLED, LED, botão) · **Diferencial: alerta em três canais** | "No Node, a tela OLED mostra temperatura, umidade e luminosidade. O LED RGB indica qual variável saiu do limite: vermelho para temperatura, azul para umidade e verde para luz. O buzzer indica o sentido: um bipe longo para acima do limite, dois bipes curtos para abaixo. Esse é o nosso primeiro diferencial: três canais, cada um com um significado. E um botão silencia o alarme." |
| 1:35 a 2:00 | Painel com o Node online · **Diferencial: alerta de estabilidade** | "No Painel, vemos o Node online, as leituras ao vivo e os gráficos de uma hora, vinte e quatro horas ou sete dias. Também vemos a estabilidade da temperatura: o sistema alerta quando ela varia mais de dois graus em vinte e quatro horas, mesmo dentro da faixa, porque o que mais prejudica o vinho é a temperatura que sobe e desce." |
| 2:00 a 3:00 | **Demo ao vivo**: Triggers, Node alertando, Alertas · **Diferenciais: referências de guarda e ajuste com confirmação** | "Vou provocar um alerta. Em Triggers, escolho uma referência de guarda, com fontes citadas e avisos quando um valor não faz sentido, e clico em Salvar e enviar ao Node. O painel confirma que o Node recebeu. Agora o valor passa do limite: o LED acende, o buzzer toca e o alerta aparece no painel. Em Alertas, ele fica registrado, com início, tipo e dispositivo. Quando a leitura volta ao normal, o alerta fecha sozinho." |
| 3:00 a 3:30 | Telas Dispositivos e Vinherias · **Diferencial: várias vinherias isoladas** | "Em Dispositivos, cadastramos um Node novo, e o painel gera o bloco de configuração para o firmware. Em Vinherias, cada adega tem os seus dados separados. Se a assinatura vence, a vinheria é suspensa: os Nodes param de alertar e a API recusa consultas, mas o histórico fica guardado." |
| 3:30 a 3:45 | Node em modo local (ou animação) · **Diferencial: continua protegendo sem a nuvem** | "Se a nuvem cair, o Node não fica cego: depois de quinze segundos, ele avalia os limites sozinho e continua alertando. Quando a conexão volta, ele volta a obedecer ao sistema." |
| 3:45 a 4:20 | Lista animada dos cinco diferenciais | "Para resumir, são cinco diferenciais: o alerta em três canais, com a cor indicando a variável e o som indicando o sentido; o Node que continua protegendo sem a nuvem; várias vinherias isoladas, com suspensão por inadimplência; referências de guarda com fontes e avisos ao digitar; e o alerta de estabilidade, que olha a variação das últimas vinte e quatro horas. Todos estão descritos, com a forma de provar cada um, na página de diferenciais do repositório." |
| 4:20 a 4:50 | GitHub: README e pasta `docs` | "Todo o código, os manuais de instalação e de operação e a documentação estão no GitHub. O backend tem cento e setenta e seis testes automatizados. Usamos como base o material FIWARE Descomplicado, do professor Fábio Cabrini, e contamos com apoio de IA. Obrigado." |

## Dicas de gravação

- Fale devagar e termine cada bloco com um respiro de 1 segundo (facilita cortar).
- Mostre o Node e o painel **na mesma tomada** na demo, para provar que o alerta é real.
- Se o alerta demorar, aqueça o sensor com a mão e espere: o backend avalia a cada 5 segundos.
- Depois de gravar: subir no YouTube como **não listado**, colar o link em `video/link.md` e commitar.

## Plano B

Se o Node falhar na gravação, use o Wokwi (LDR e DHT22) para a parte do alerta e diga isso na narração.
