# Roteiro do vídeo: WineGuard

**Duração alvo:** 4 a 5 minutos. **Formato:** gravação de tela do dashboard + imagens do Node, com narração. Sem enrolação: cada bloco tem um objetivo e um tempo.

## Antes de gravar (checklist)

- [ ] Start Lab feito, IP do dia no `config.h` (Node regravado) e no `frontend/.env`.
- [ ] Node ligado, **online** no Painel e **sem mute** (aperte o botão e confira no OLED).
- [ ] Dashboard aberto no PC, na vinheria de demonstração, janela em tela cheia.
- [ ] Celular perto para filmar o Node (luz boa, fundo limpo).
- [ ] Fechar abas, notificações e qualquer janela que mostre senha, IP completo ou `config.h`.
- [ ] Gravar em blocos separados: é mais fácil refazer um bloco do que o vídeo inteiro.

## Roteiro

| Tempo | Imagem | Fala (sugestão) |
|---|---|---|
| 0:00 a 0:20 | Logo e foto do Node na caixa | "Somos o grupo marcha.dev e este é o WineGuard: monitoramento de adegas com IoT. Cada adega ganha um Node que mede o ambiente e avisa quando o vinho está em risco." |
| 0:20 a 0:50 | Foto da adega ou do Node + arquitetura (`docs/arquitetura.png`) | "Vinho estraga com temperatura alta, umidade fora da faixa e luz. Em uma adega pequena ninguém acompanha isso o dia todo. Nossa solução: um ESP32 com sensor de temperatura e umidade (DHT22), sensor de luz (LDR), OLED, LED RGB e buzzer, que envia os dados por MQTT para uma plataforma FIWARE na AWS." |
| 0:50 a 1:30 | Diagrama de arquitetura, apontando camada por camada | "O Node publica por MQTT. O IoT Agent converte para NGSI e o Orion guarda o estado atual. O STH-Comet guarda o histórico. Nosso backend em FastAPI, rodando em contêiner na mesma instância, consulta o FIWARE, avalia os limites a cada 5 segundos e registra os alertas. O dashboard em React consome essa API." |
| 1:30 a 2:00 | Foto do Node de perto (OLED, LED, botão) | "No Node, a tela mostra temperatura, umidade e luminosidade. O LED RGB indica qual variável saiu do limite: vermelho, azul ou verde. O buzzer indica o sentido: um bipe longo para acima do limite, dois bipes curtos para abaixo. Um botão silencia o alarme." |
| 2:00 a 2:30 | Painel do dashboard com o Node online | "No Painel vemos o Node online, as leituras ao vivo, a estabilidade da temperatura nas últimas 24 horas e os gráficos de 1 hora, 24 horas ou 7 dias." |
| 2:30 a 3:30 | **Demo ao vivo**: aquecer o sensor (mão ou secador) ou baixar o limite em Triggers | "Vou provocar um alerta. Em Triggers escolho uma referência de guarda, como Guarda geral, ou digito os limites e clico em Salvar e enviar ao Node. O painel confirma que o Node recebeu. Agora o Node sai da faixa: o LED acende, o buzzer toca e o alerta aparece no painel e em Alertas, com início, tipo e dispositivo. Quando a leitura volta ao normal, o alerta fecha sozinho." |
| 3:30 a 4:00 | Telas Dispositivos e Vinherias | "Em Dispositivos cadastramos um Node novo: o painel mostra o bloco do `config.h`. Em Vinherias temos várias adegas com dados separados e a suspensão por inadimplência: o Node para de alertar e a API recusa consultas daquela vinheria." |
| 4:00 a 4:30 | Node + terminal ou painel | "Se a nuvem cair, o Node avalia os limites sozinho depois de 15 segundos e continua alertando. Quando a conexão volta, ele volta a obedecer ao sistema." |
| 4:30 a 5:00 | Tela de créditos ou README | "O código, os manuais de instalação e operação e a documentação estão no GitHub. O backend tem 176 testes automatizados. Este projeto usa o material FIWARE Descomplicado do professor Fábio Cabrini e foi feito com apoio de IA. Obrigado." |

## Dicas de gravação

- Fale devagar e termine cada bloco com um respiro de 1 segundo (facilita cortar).
- Mostre o Node e o painel **na mesma tomada** na demo, para provar que o alerta é real.
- Se o alerta demorar, aqueça o sensor com a mão e espere: o backend avalia a cada 5 segundos.
- Depois de gravar: subir no YouTube como **não listado**, colar o link em `video/link.md` e commitar.

## Plano B

Se o Node falhar na gravação, use o Wokwi (LDR e DHT22) para a parte do alerta e diga isso na narração.
