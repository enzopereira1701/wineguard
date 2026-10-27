# Manual de operação

**WineGuard: monitoramento de adegas com IoT** · grupo marcha.dev · CP5 Vinheria Full · versão de 27/10/2026

Este manual ensina a **usar** o WineGuard no dia a dia: ligar o sistema, entender o que o Node avisa, operar o dashboard e resolver os problemas mais comuns. Para montar o sistema do zero, veja o [Manual de instalação](manual-instalacao.md).

## 1. Ligar o sistema (rotina do dia)

O laboratório da AWS desliga entre uma sessão e outra, e o **IP da instância muda a cada sessão**. Os dados (vinherias, dispositivos, histórico) são guardados e **não se perdem**.

1. **Start Lab** no AWS Academy. Espere o círculo ficar **verde** e copie o **IP público** da instância (console EC2).
2. Na instância, confira os contêineres: `sudo docker ps`. Devem estar **Up**: `fiware-mosquitto`, `fiware-iot-agent`, `fiware-orion`, `fiware-sth-comet`, `fiware-mongo-internal`, `fiware-mongo-historical` e `wineguard-backend`. Eles sobem sozinhos.
3. No computador, teste a API: `curl http://IP:8000/api/vinherias` (deve voltar um JSON).
4. Troque o IP novo nos dois lugares:
    - no **Node**: `MQTT_BROKER` do `config.h`, e **grave de novo** o firmware (veja o Manual de instalação, seção 4);
    - no **dashboard**: `frontend/.env` (`VITE_API_URL` e `VITE_MQTT_HOST`), e suba o painel com `npm run dev`.
5. Ligue o Node. Em alguns segundos ele aparece **online** no Painel.
6. Ao terminar: **End Lab**, para não gastar os créditos do laboratório.

> **Plano B:** se o Wi-Fi do local falhar, use o **hotspot do celular** (rede de 2,4 GHz) para o Node e o computador. Tenha também o vídeo gravado e a simulação do Wokwi abertos.

## 2. O Node: o que ele mostra e o que ele avisa

![Node montado na caixa](../hardware/fotos/node/montado-frente.jpg)

Na frente da caixa ficam o **botão de mudo**, a **tela OLED** e o **LED RGB**. O sensor de temperatura e umidade (DHT22) sai pelo topo.

Ao ligar, a tela mostra o logo do WineGuard e depois os valores de **temperatura, umidade e luminosidade**, com o estado: **tudo ok**, **alerta** ou **mudo**. Se perder a conexão, a tela mostra **OFFLINE (local)**.

### Como o Node avisa

A **cor do LED** e a **tela** dizem **qual variável** saiu do limite. O **LED** e o **som** dizem **para que lado**.

| Cor do LED | Variável |
|---|---|
| Vermelho | Temperatura |
| Azul | Umidade |
| Verde | Luminosidade |

| Situação | LED | Buzzer | Tela |
|---|---|---|---|
| **ALTA** (acima do limite) | Fixo na cor da variável | 1 bipe longo, repetido | "ALTA", o valor e o limite máximo |
| **BAIXA** (abaixo do limite) | Pisca junto com o som | 2 bipes e uma pausa | "BAIXA", o valor e o limite mínimo |

![Alerta de temperatura alta](../hardware/fotos/node/alerta-temperatura-alta.jpg)

Com **mais de uma variável** em alerta, o Node **alterna** entre elas (no mínimo 3 segundos em cada), com uma pausa de silêncio no meio. É normal ouvir 2 ou 3 bipes seguidos antes da troca.

### Silenciar o alarme (mudo)

- **No Node:** um aperto rápido no botão **silencia o buzzer** (aparece "MUDO" na tela). Outro aperto reativa. O **LED continua aceso**, para o alerta não passar despercebido.
- **No dashboard:** botão **Silenciar** (ou **Reativar som**) no Painel.
- O estado de mudo **fica guardado** no Node: se ele parecer calado, confira se não está mudo.

### Se a nuvem cair

O Node guarda os limites na própria memória. Se ficar **mais de 15 segundos** sem a nuvem, ele passa a **avaliar os limites sozinho** (a tela mostra "OFFLINE (local)") e **continua alertando**. Quando a conexão volta, ele volta a obedecer ao sistema, sem ninguém mexer.

## 3. O dashboard, tela a tela

Abra o painel no navegador (normalmente `http://localhost:5173`). No topo, escolha a **vinheria** no seletor. As telas ficam na barra de navegação (no celular, na barra de baixo).

### Painel

![Painel](../docs/prints/painel-em-alerta_1.png)

Mostra **um dispositivo por vez** (os outros aparecem como chips). Os alertas ativos ficam no topo, e abaixo estão os quatro cartões: **temperatura, umidade, luminosidade** e **estabilidade das últimas 24 horas**, cada um com o selo "Normal" ou "Acima/Abaixo do limite". Os gráficos mostram **1 hora, 24 horas ou 7 dias** e atualizam a cada 5 segundos.

| Botão | O que faz |
|---|---|
| **Pausar / Retomar** | Congela e volta a atualização automática, para você olhar com calma |
| **Silenciar / Reativar som** | Liga ou desliga o buzzer do Node |
| **Identificar Node** | O Node pisca e apita, para você achá-lo entre vários |

### Dispositivos

![Dispositivos](../docs/prints/dispositivos.png)

Lista os Nodes da vinheria, com o estado (online, offline, em alerta), o preset de guarda, a última leitura e o número de alertas ativos. Para **cadastrar** um Node, clique em **Novo dispositivo**, dê um nome e escolha a adega: o painel mostra o bloco de configuração para colar no `config.h`. Também dá para **editar** o nome e **remover** o dispositivo.

### Triggers (os limites de alerta)

![Triggers](../docs/prints/triggers_1.png)

Define a faixa permitida de cada variável (mínimo e máximo).

- **Usar referência:** escolha um preset de **guarda**: *Guarda geral* (10 a 15 °C, 60 a 75 %, luz até 10 %), *Longa guarda* (11 a 14 °C, 65 a 75 %, luz até 5 %) ou *Espumante* (9 a 13 °C, 65 a 80 %, luz até 5 %).
- **Personalizar:** digite os próprios valores. Se o valor fugir da referência de guarda, o painel avisa (por exemplo, "Acima de 24 °C o vinho envelhece cedo demais") e pede confirmação em **Salvar mesmo assim**.
- **Salvar e enviar ao Node:** o limite vai para o Node e o painel mostra **"Recebido pelo Node às HH:MM. Os novos limites já estão valendo."** Se o Node não responder, os limites ficam salvos e são reenviados quando ele voltar.

> Os presets são de **guarda**, não de servir, e são recomendações de especialistas, não uma norma oficial. O sensor de luz mede em porcentagem **relativa**; calibre com a adega fechada e apagada.

### Alertas

![Alertas](../docs/prints/alertas.png)

A linha do tempo de todos os alertas, com **início, fim e duração** ("em andamento" quando ainda está aberto). Há filtros por **tipo**, **situação** e **dispositivo**. Os tipos são: temperatura, umidade e luminosidade (acima ou abaixo do limite), **instabilidade** (a temperatura variou mais de 2 °C em 24 horas) e **Node offline** (30 segundos sem leitura).

Um alerta **fecha sozinho** quando a leitura volta ao normal.

### Vinherias

![Vinherias](../docs/prints/vinherias.png)

Cada vinheria tem suas adegas e dispositivos, com os dados **separados** das outras.

| Ação | O que faz |
|---|---|
| **Nova vinheria** | Cria a vinheria com nome e vencimento da mensalidade (opcional; o padrão é 90 dias) |
| **Usar esta vinheria** | Troca a vinheria que o painel está mostrando |
| **Suspender** | Os Nodes apagam LED e buzzer e param de enviar; o painel mostra o aviso de **serviço suspenso**. O histórico fica guardado |
| **Reativar** | Os Nodes voltam a funcionar |
| **Simular inadimplência** | Vence o vencimento e suspende, para demonstração |

> O painel **não tem login**: qualquer pessoa com o endereço consegue ver e alterar as vinherias. É uma demonstração; num sistema real, só o administrador da plataforma faria isso.

## 4. Manutenção

**Atualizar o backend** (depois de mudar o código no GitHub). Na instância:

```bash
cd ~/wineguard && git pull
cd ~/fiware && sudo docker compose up -d --build wineguard-backend
```

**Ver o que o backend está fazendo:** `sudo docker logs --tail 20 wineguard-backend`.

**Reiniciar um serviço:** `sudo docker restart fiware-iot-agent` (por exemplo). Depois de reiniciar o **Mosquitto**, reinicie também o **IoT Agent**.

**Disco da instância** (6,7 GB). Os logs do IoT Agent crescem porque ele roda em modo DEBUG. Para conferir e limpar:

```bash
df -h /
sudo sh -c 'du -h /var/lib/docker/containers/*/*-json.log' | sort -h | tail -3
sudo sh -c 'truncate -s 0 /var/lib/docker/containers/ID_DO_CONTEINER*/*-json.log'
```

Isso só zera o texto do log, **não** apaga dados. **Nunca apague os volumes do Docker**: é neles que ficam as vinherias, os dispositivos e o histórico.

**Um backend só.** Se o contêiner da instância estiver no ar, não rode outro backend no computador: dois backends duplicam os alertas.

## 5. Problemas e soluções

| Problema | Causa provável | O que fazer |
|---|---|---|
| Painel mostra o Node **offline** | O Node está desligado, sem Wi-Fi, ou com o IP antigo | Veja o monitor serial: a linha `Conectando ao broker` deve mostrar o IP **do dia**. Se não, atualize o `config.h` e grave de novo |
| O Node envia, mas o painel continua offline | O Mosquitto foi reiniciado e o IoT Agent ficou sem assinatura | `sudo docker restart fiware-iot-agent` |
| Gravei o IP novo e o Node usa o antigo | A Arduino IDE abriu outra cópia do sketch | Abra o `.ino` direto da pasta do repositório e grave de novo |
| Dashboard vazio ou com erro | `VITE_API_URL` errado, backend fora do ar ou `.env` alterado sem reiniciar | `sudo docker ps` na instância; confira o `.env`; pare e suba o `npm run dev` |
| `curl` ou o painel não alcançam a API | IP antigo, ou porta **8000** fechada | Use o IP do dia e confira o Security Group (22, 1883 e 8000) |
| O Node não faz barulho | Está **mudo** (botão ou painel) | Aperte o botão ou use **Reativar som**. O LED continua funcionando |
| Wi-Fi fraco ou caindo | O sinal (RSSI) abaixo de uns -85 dBm | Aproxime o Node do roteador ou use o hotspot do celular |
| Alerta aparece em dobro | Há dois backends rodando | Pare o do computador e deixe só o contêiner |
| "Serviço suspenso" no painel | A vinheria foi suspensa (ou o vencimento passou) | Em **Vinherias**, clique em **Reativar** |
| Os limites não "chegam" ao Node | O Node está offline | Os limites ficam salvos e são reenviados quando ele voltar |
| Falha ao gravar o firmware (`Invalid head of packet`) | Cabo USB ruim ou velocidade alta | Baixe o **Upload Speed** para 115200 e use um cabo curto, **de dados** |

## 6. Limitações conhecidas

- **Sem login:** qualquer pessoa com o endereço do painel vê e altera as vinherias.
- O MQTT e a plataforma funcionam **sem senha e sem TLS**: quem souber a `apikey` consegue publicar dados.
- O sensor de luz mede em porcentagem **relativa**, não em lux.
- O DHT22 tem margem de **±0,5 °C**.
- O buzzer diferencia **o sentido** (alta ou baixa), mas **não a variável**: ela é identificada pelo LED e pela tela.
- O IP da instância muda a cada sessão e é trocado **à mão**.
