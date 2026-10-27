# Roteiro do hands-on (30/10/2026)

**Apresentação:** 12 minutos, no máximo 15. **Regra:** mostrar funcionando logo no começo e explicar enquanto mostra. O que passar disso fica para as perguntas.

## Divisão sugerida

| Tempo | Parte | Quem |
|---|---|---|
| 0:00 a 1:30 | Problema e solução | Enzo |
| 1:30 a 3:30 | Node (hardware e firmware) | Raphael |
| 3:30 a 5:30 | Plataforma e backend | Yannick |
| 5:30 a 11:00 | Demo ao vivo no dashboard | Alysson |
| 11:00 a 12:00 | Limitações, evolução e encerramento | Enzo |
| 12:00 em diante | Perguntas | todos |

Ajuste os nomes como o grupo preferir.

## Antes de começar (chegar 30 min antes)

1. **Start Lab**, esperar a bolinha verde e copiar o **IP público**.
2. `sudo docker ps` na instância: mosquitto, iot-agent, orion, sth-comet, mongo e `wineguard-backend` com **Up**.
3. Trocar o IP: `MQTT_BROKER` do `config.h` (e **regravar o Node pela pasta do repositório**), `frontend/.env` (`VITE_API_URL`, `VITE_MQTT_HOST`) e o Wokwi.
4. `curl http://IP:8000/saude` e abrir o dashboard com `npm run dev`.
5. Ligar o Node: ele deve aparecer **online**. Conferir que **não está mudo**.
6. Deixar abertos: dashboard, `docs/arquitetura.png`, terminal da instância, README, vídeo e Wokwi. Manuais impressos na mesa. Plano B: hotspot do celular em 2,4 GHz.
7. Rodar **um só backend** (o da instância).

## Roteiro

### 1. Problema e solução (1:30)
- "Vinho estraga com temperatura, umidade e luz fora da faixa, e em adega pequena ninguém acompanha isso o dia todo."
- "O WineGuard põe um Node em cada adega. Ele mede, avisa na hora e manda tudo para a nuvem, onde o dashboard mostra e registra os alertas."
- Mostrar `docs/arquitetura.png` por 15 segundos.

### 2. Node (2 min)
- ESP32, DHT22, LDR, OLED, LED RGB, buzzer e botão de mudo.
- Publica por MQTT e recebe comandos (limites, mudo, intervalo), guardados na memória do Node.
- LED por variável: vermelho temperatura, azul umidade, verde luz. Buzzer pelo sentido: 1 bipe longo = acima, 2 bipes = abaixo.

### 3. Plataforma e backend (2 min)
- Na instância, `sudo docker ps`: FIWARE (Mosquitto, IoT Agent, Orion, STH-Comet) e o backend FastAPI em contêiner.
- "O FIWARE guarda os dados; o backend avalia os limites a cada 5 segundos, abre e fecha alertas e controla as vinherias." Citar os 176 testes.

### 4. Demo ao vivo (5:30)
1. **Painel (45 s):** Node online, leituras, gráficos e estabilidade.
2. **Alerta (2 min):** em **Triggers**, escolher o preset **Guarda geral** e clicar em **Salvar e enviar ao Node**; mostrar o "Recebido pelo Node". Aquecer o sensor com a mão ou baixar o limite até alertar. Mostrar LED, bipe e OLED no Node e o alerta no Painel e em **Alertas**.
3. **Silenciar (30 s):** apertar o botão do Node e mostrar o estado no painel.
4. **Dispositivos (45 s):** mostrar o bloco de cadastro de um Node novo.
5. **Vinherias (1 min):** **Simular inadimplência**, mostrar o aviso de serviço suspenso e **Reativar**.

Se faltar tempo, corte o passo 4. O passo 2 é o principal.

### 5. Limitações e encerramento (1 min)
- "Se a nuvem cair, o Node avalia os limites sozinho depois de 15 segundos."
- Limitações: sem login, MQTT sem senha e sem TLS, luz em porcentagem relativa, DHT22 com ±0,5 °C, IP muda a cada Start Lab.
- Evolução: autenticação, TLS, notificações no celular.
- "Código, manuais e documentação estão no GitHub."

## Perguntas prováveis

- *Por que MQTT?* É leve, serve ao ESP32 e é o protocolo do IoT Agent usado na disciplina.
- *Por que um backend próprio?* O FIWARE guarda os dados; o backend decide alertas, vinherias e suspensão.
- *E se a nuvem cair?* O Node avalia os limites sozinho.
- *Como instalar do zero?* Pelo Manual de instalação, em `docs/manual-instalacao.md` e impresso.
- *Onde fica o histórico?* No STH-Comet, em volumes do Docker que sobrevivem ao End Lab.

## Se algo falhar

| Problema | Ação |
|---|---|
| Node não fica online | Conferir o IP no `config.h` (regravar), o Wi-Fi 2,4 GHz e o monitor serial |
| Node envia mas o painel fica offline | `sudo docker restart fiware-iot-agent` |
| Painel vazio ou com erro | `VITE_API_URL` errado ou backend parado: `sudo docker ps` |
| Sem Wi-Fi no local | Hotspot do celular; se não der, vídeo e Wokwi |
| Alerta duplicado | Há dois backends rodando: parar o do PC |
| Node mudo | Apertar o botão ou usar Reativar som no painel |

## Ao terminar

**End Lab** para não gastar créditos. Nunca apagar os volumes do Docker.
