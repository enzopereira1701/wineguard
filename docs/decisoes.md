# WineGuard: decisões do projeto

Ficha de decisões do **CP5 Vinheria Full** (marcha.dev). Cole este arquivo no começo de uma conversa nova com o Claude para retomar de onde paramos.

- **Grupo:** marcha.dev
- **Produto:** WineGuard
  - **Node:** o hardware (ESP32 com sensores e atuadores), um por adega
  - **Cloud:** a plataforma (FIWARE, backend e banco de dados do Orion)
  - **Dashboard:** o site em React
- **Entrega e hands-on:** 30/10/2026
- **Integrantes:** _(preencher)_
- **Última atualização desta ficha:** 06/10/2026

---

## 1. Escopo

**Dentro:** monitoramento de temperatura, umidade e luminosidade; alertas por LED RGB, buzzer e OLED; dashboard com cadastro de dispositivos, gráficos pela API 8666 do STH-Comet e ajuste de triggers; várias vinherias, cada uma com suas adegas e dispositivos; suspensão de uma vinheria por inadimplência.

**Fora (decidido):** WiFiManager, índice de conservação, Telegram, login com usuário e senha, banco de dados relacional, exportação em CSV, cancelamento de vinheria (fica como evolução).

---

## 2. Hardware (WineGuard Node)

ESP32 DevKit de 30 pinos, sem solda, com protoboard pequeno como distribuidor de 3V3 e GND e cabos Dupont.

| Componente | Pino do ESP32 | Observação |
|---|---|---|
| DHT22 (módulo de 3 pinos) | D5 | No Wokwi e na bancada |
| LDR (módulo de 3 pinos, saída AO) | D34 | ADC1. Valor em % **relativo** (não é lux). O sinal do módulo é invertido (escuro = número alto) e o firmware inverte |
| Buzzer ativo (módulo de 3 pinos) | D18 | Não muda de tom. O módulo usado apita com nível **baixo** (`BUZZER_ATIVO_EM_LOW 1`) |
| LED RGB KY-016 (cátodo comum) | D25 (R), D26 (G), D27 (B) | Cores dos dados |
| OLED SSD1306 128x64 I2C | D21 (SDA), D22 (SCL) | Endereço 0x3C |
| Botão de mute (módulo de 3 pinos) | D14 | A polaridade é detectada sozinha ao ligar (não apertar o botão nessa hora) |
| Teclado AD (só para teste) | D35 | Não vai no produto final |

**Cores dos dados** (iguais no LED, nos gráficos e nos cartões): temperatura = vermelho, umidade = azul, luminosidade = verde.

### Comportamento dos alertas (firmware 2.3, ajustado na bancada)
- **Qual variável:** pela **cor do LED** (vermelho = temperatura, azul = umidade, verde = luz) e pela **tela do OLED** (nome, `[cor do LED]`, ALTA ou BAIXA, valor, limite violado e posição no rodízio).
- **Qual sentido:** **ALTA** = LED **fixo** e o buzzer em **bipe longo** (0,6 s, pausa de 0,6 s; com `ALTA_CONTINUO 1` vira tom contínuo). **BAIXA** = LED **pisca junto** com o buzzer, em **2 bipes** de 0,3 s e uma pausa de 1 s.
- **Decisão de 06/10:** o padrão de bipes por variável (1, 2 ou 3 bipes) foi **abandonado**. Bipes de 80 a 150 ms se misturavam no buzzer físico e um deles se perdia. O som passou a dizer o **sentido**, e a variável vem do LED e da tela.
- **Limitação conhecida:** quem não enxerga o LED nem a tela não distingue a variável pelo som. Decidido deixar assim (não é requisito do CP5) e registrar no README. O aviso do dashboard é textual.
- Com mais de um alerta, alterna entre as variáveis (mínimo 3 s em cada, e só ao fim de um ciclo do padrão) com uma **pausa de 0,7 s** de silêncio total (LED, buzzer e tela). Por isso, com várias variáveis em alerta, o bipe longo da alta aparece em grupos (ex.: 3 seguidos).
- **Mute:** botão no Node ou comando; silencia só o buzzer, o LED continua. O botão é lido na tarefa dos atuadores (não perde aperto quando a rede trava o `loop()`), confirma o aperto por ~20 ms e o estado é guardado na memória (NVS).
- **Suspenso:** apaga LED e buzzer, para de publicar e mostra "Servico suspenso".
- **Failsafe:** sem MQTT por mais de 15 s, o Node avalia sozinho com os triggers guardados na memória.

### Firmware (`hardware/firmware/wineguard_node/`)
- **Versão 2.3**, Arduino IDE (o enunciado pede o `.ino`). A pasta e o arquivo têm o mesmo nome, `wineguard_node`.
- Histórico: 2.0 (base); 2.1 sinal do LDR corrigido e limites padrão iguais ao preset "Guarda geral"; 2.2 botão numa tarefa própria; 2.3 botão detecta a polaridade sozinho, bipes novos.
- FreeRTOS: `loop()` cuida de rede, sensores e telemetria; uma tarefa para botão, LED e buzzer (tick de 2 ms); outra para o OLED.
- `config.h` com credenciais **fora do GitHub**; só o `config.example.h` vai. Opções: `SIMULACAO_WOKWI` (1 no Wokwi, **0 na bancada**), `BUZZER_ATIVO_EM_LOW`, `ALTA_CONTINUO`, `LDR_INVERTIDO` e `BOTAO_PRESSIONADO` (opcional).
- `AVALIACAO_LOCAL_SEMPRE`: 1 enquanto não há backend. **Voltar para 0** quando o backend entrar.
- Limites padrão do Node (até receber os do backend): temperatura 10 a 15 °C, umidade 60 a 75 %, luz 0 a 10 %.
- Logo do OLED: escudo com cacho, 45x64 px, 1 bit (`icones.h`).
- Bibliotecas: PubSubClient, Adafruit GFX, Adafruit SSD1306, DHT sensor library (e a Adafruit Unified Sensor). Pacote **esp32 3.3.x**. **Anotar as versões** em `hardware/firmware/README.md`.
- Gravação na bancada: se aparecer `Invalid head of packet (0x80)`, baixar o **Upload Speed** para 115200 e trocar o cabo USB.
- **Estado (06/10):** o Node físico foi montado e roda sem nuvem (OLED, LED, buzzer, botão, DHT22 e LDR). Falta testar com a nuvem e a caixa.

### Caixa 3D
Molde de papelão pronto. Um amigo modelou, e a faculdade imprime (previsto para o fim da semana de 06/10). Tampa removível por parafusos. DHT22 longe do ESP32 e com ventilação; LDR separado do LED.

---

## 3. Plataforma (FIWARE na AWS)

- **AWS Learner Lab**, instância `t3.medium` (Ubuntu). Conta Azure for Students (US$ 100) de reserva.
- O lab desliga e **o IP muda a cada sessão**. Clicar em **End Lab** ao terminar, para não gastar crédito. Os containers voltam sozinhos.
- FIWARE do professor (material "FIWARE Descomplicado", Prof. Fábio H. Cabrini), em Docker: Mosquitto, IoT Agent UL, Orion 3.11.0, STH-Comet e dois MongoDB. **Não tem Cygnus**: o STH-Comet recebe os dados por assinatura do Orion.
- Portas hoje: 1883 (MQTT), 1026 (Orion), 4041 (IoT Agent), 8666 (STH-Comet). A 27017 (MongoDB) **não deve ficar aberta**.

### Várias vinherias
| Conceito | No FIWARE |
|---|---|
| Vinheria | `fiware-service` (ex.: `vin_demo`) |
| Adega | `fiware-servicepath` (ex.: `/adega1`) |
| Node | `device_id` `wgn001` e `apikey` por vinheria |
| Entidade no Orion | `urn:ngsi-ld:WineGuardNode:001` |

Atributos: `temperature`, `humidity`, `luminosity`, `state` (ok, alerta ou suspenso), `muted`, `rssi`, `firmware`.

### Protocolo MQTT (Ultralight 2.0)
- Tópicos: `/<apikey>/<device_id>/attrs` (dados), `/cmd` (comandos) e `/cmdexe` (resposta).
- Telemetria: `t|24.5|h|60.0|l|35|st|ok|mu|0|rs|-60|fw|2.0`
- Comandos (`<device>@<comando>|<parâmetros>`): `setTriggers` (tmin,tmax,hmin,hmax,lmin,lmax), `alert` (variável,sentido,liga), `mute`, `suspend`, `resume`, `setInterval`, `identify`.

### Cadastro e lições aprendidas
- `fiware/scripts/provisionar.sh [service] [servicepath] [apikey] [numero]`: cadastra o grupo, o dispositivo e a assinatura do STH-Comet, e é seguro rodar de novo.
- **O dispositivo precisa ser cadastrado COM `apikey`.** Sem ela, o IoT Agent não reconhece o cadastro, cria um dispositivo novo sozinho e grava as leituras em outra entidade, com os nomes crus (`t`, `h`, `l`).
- Apagar um dispositivo **não impede** o Node de publicar: o IoT Agent o recria. Só remover o service group corta de verdade.
- Provado nos dois sentidos: dados chegam ao STH-Comet (8666) e o comando `mute` chega ao Node.

---

## 4. Backend

- **Python (FastAPI)** com `requirements.txt`, código comentado.
- **Sem banco de dados e sem login.** Vinherias, adegas, triggers e alertas ficam como entidades no **Orion**. Um único site para todos, **sem autenticação**: é demonstração, e isso vai documentado como limitação.
- O backend **consulta o Orion a cada 5 s** e avalia os triggers (o Node só obedece, como o enunciado pede). Ao sair da faixa manda `alert`; ao voltar, desliga.
- Histerese: 0,5 °C na temperatura; 2 % na umidade e na luz.
- Reconciliação: se o `state` do Node divergir do que o backend espera, reenvia os alertas.
- **Node offline:** 30 s sem leitura. Vira um alerta no histórico, com início e fim.
- **Suspensão de vinheria:** estados `ativa` e `suspensa`, com vencimento. Ao suspender, manda `suspend` aos Nodes; a API recusa consultas daquela vinheria; o histórico é preservado. Botão manual, suspensão automática por vencimento e "simular inadimplência" para a demonstração.
- Cadastro de dispositivo: o backend escolhe o próximo `wgn###`, cadastra no IoT Agent **com apikey**, garante a assinatura e devolve o bloco do `config.h`.
- Remover um dispositivo: manda `suspend`, apaga o cadastro e a entidade (limitação: se o ESP32 continuar publicando, ele é recriado).
- Python instalado: 3.14.3. No Git Bash, `python` cai na Microsoft Store; **usar `py`**.

---

## 5. Triggers e referências de guarda

O usuário escolhe **Usar referência** ou **Personalizar**. As referências aparecem sempre (faixa sombreada nos gráficos e nas barras).

### Presets (de **guarda**, não de servir)
Os valores de servir (branco 8–12, tinto 15–18) não valem para o monitoramento da adega.

| Preset | Temperatura | Umidade | Luz máx. |
|---|---|---|---|
| Guarda geral (tinto, branco, rosé) | alerta 10–15 °C, alvo 12–14 | alerta 60–75 %, alvo 65–70 | 10 % |
| Longa guarda | alerta 11–14 °C, alvo 12–13 | alerta 65–75 %, alvo 65–70 | 5 % |
| Espumante | alerta 9–13 °C, alvo 10–12 | alerta 65–80 %, alvo 70–80 | 5 % |
| Personalizado | livre | livre | livre |

Os números de **alerta** são adaptação nossa a partir das fontes. A luz é em % **relativa** (o LDR não mede lux).

### Avisos ao digitar valores
| Nível | Quando | Efeito |
|---|---|---|
| Bloqueia | mínimo ≥ máximo; valor impossível | Não salva |
| Aviso forte | temp. máx. > 24 °C ou mín. < 4 °C; umidade fora de 40–85 % | Pede confirmação |
| Aviso leve | fora da faixa do preset | Mostra a referência |
| Faixa estreita | temperatura com menos de 1 °C | Avisa (DHT22 tem ±0,5 °C) |
| Faixa larga | mais que o dobro da referência | Avisa que o alerta demora |

### Três extras (decididos)
1. **Alerta de estabilidade:** variação de temperatura > 2 °C em 24 h, usando os dados agregados (mínimo e máximo) do STH-Comet.
2. **Calibração da luz:** botão "marcar o valor atual como escuro normal".
3. **Troca de preset com confirmação:** mostra os valores de antes e depois.

### Fontes (citar no README)
O que achamos são recomendações de especialistas, **não uma norma oficial**. Falta conferir a Embrapa Uva e Vinho e a ABS.
- Decanter: https://www.decanter.com/learn/how-to/how-to-store-wine-video-tutorial-54233
- Decanter, umidade: https://www.decanter.com/?p=458610
- Jancis Robinson: https://jancisrobinson.com/ja/node/8317
- EuroCave, vinho: https://www.eurocave.com/en/six-pieces-of-advice-for-storing-wine
- EuroCave, champagne: https://www.eurocave.com/en/eurocave-expert-advice/tips-for-properly-storing-champagne
- Nicolas Feuillatte: https://nicolas-feuillatte.com/en/blogs/articles/la-conservation-du-champagne-quelle-temperature-et-autres-astuces
- Forbes Brasil: https://forbes.com.br/forbeswsb/2025/09/como-armazenar-vinho-em-casa-dicas-para-tintos-brancos-e-espumantes/

---

## 6. Dashboard

**Pilha (a mesma dos projetos do grupo, ex.: `loja_gamer`):** React 19 com Vite (JavaScript), React Router 7, Tailwind CSS 4 e Recharts. Publicado na **Vercel**; funciona em PC e celular (navbar fixa e translúcida no PC; barra inferior no celular). PWA se sobrar tempo.

**Estado (06/10):** o front-end está **construído e testado com dados de demonstração** (simulador de sensores no navegador), com guia passo a passo em PDF e prévia publicada. O projeto de referência está em `frontend/` (quando for enviado ao repositório). Falta ligar ao backend e rodar o `npm install`/`npm run dev` no PC do grupo (o visual com Tailwind e os gráficos reais ainda não foram vistos).

**Dados:** nenhuma tela busca dados direto. Tudo passa por `src/services/api.js`, que usa o simulador (`VITE_USE_MOCK=true`) ou o backend (`VITE_API_URL`). O formato das respostas é o **contrato** em `docs/api-contrato.md`.

**Site de apresentação:** um integrante do grupo faz um site em React à parte para apresentar o problema e a solução. **Não substitui o dashboard** (cadastro, gráficos do STH-Comet e ajuste de triggers são exigidos pelo enunciado). Pode virar a tela Início do mesmo projeto.

Telas:
1. **Início:** o problema, a solução, o modelo (vinheria, adega, Node) e a equipe.
2. **Painel:** **um dispositivo por vez**, seletor com contagem ("1 de 3 dispositivos"), faixa de chips dos outros e "+ Adicionar dispositivo". Quatro cartões (temperatura, umidade, luz e estabilidade 24 h) e quatro gráficos (um por variável e um combinado com dois eixos), atualização a cada 5 s, faixa de referência sombreada e triggers tracejados.
3. **Dispositivos:** cadastro, edição e remoção, status, e o bloco para o `config.h`.
4. **Triggers:** presets, referência e personalizado, avisos, calibração da luz, estabilidade, "Salvar e enviar ao Node" com confirmação de recebimento, e o botão Fontes.
5. **Alertas:** linha do tempo (temperatura, umidade, luz, estabilidade e Node offline), com filtros.
6. **Vinherias:** cadastro, vencimento, suspender e reativar (com confirmação) e "simular inadimplência".
7. **Suspenso:** aviso quando a vinheria escolhida está suspensa. Mais a página 404.

---

## 7. Identidade visual

- **Emblema:** escudo bordô (o guardião) com cacho de 6 uvas em creme, folhas e antena de sinal em ouro.
- Cores: bordô `#6B1E2E` (marca), ouro `#B08D4A` (só decoração, contraste 2,7:1), ouro escuro `#8A6A2F`, creme `#F4EEE6` (fundo), papel `#FBF8F3` (cartões), texto `#2B1B17`, texto secundário `#6E5F55`.
- O amarelo de atenção do sistema deve ser **outro tom**, para não confundir com o ouro da marca.
- Tipografia: **Playfair Display** nos títulos e na palavra "wineguard"; **Lato** no texto e nos números (`tabular-nums`).
- Slogan: "Cada garrafa no ponto certo."
- Arquivos em `frontend/public/`: `wineguard-emblema.svg`, `-floreio.svg` (capa), `-mono.svg`, `wineguard-simbolo-compacto.svg` (navbar, favicon, OLED), `wineguard-icone-app.svg`, `icon-192.png`, `icon-512.png`, `favicon-32.png`, `favicon-48.png`.
- A imagem de referência foi gerada com apoio de IA e **redesenhada em SVG**. Registrar isso no README.
- Falta: logo horizontal (emblema e palavra) para a navbar.

---

## 8. Docker Compose

- **Um compose único nosso**, baseado no do professor (dar o crédito), na raiz do repositório.
- Sobe: Mosquitto, IoT Agent, Orion, STH-Comet, dois MongoDB, o **backend**, um **proxy Caddy** (HTTPS automático) e um serviço **DuckDNS** que mantém o nome apontando para o IP do lab.
- Versões fixas das imagens, volumes nomeados, `restart: unless-stopped`, configuração por `.env` (com `.env.example`).
- O backend fala com o FIWARE pela rede interna do Docker. No final ficam abertas só **1883, 80 e 443**. As portas 1026, 4041, 8666 e 27017 deixam de ficar públicas.
- Mosquitto com `mosquitto.conf` no repositório.
- Os dois lados (ESP32 e Vercel) usam o **nome DuckDNS**, nunca o IP.
- A conferir no lab ligado: ler o compose do professor na máquina; imagens do DuckDNS e do Caddy; liberar 80 e 443.
- Comando atual na AWS: `docker compose` (com espaço). Pode ser preciso instalar `docker-compose-plugin`.

---

## 9. Documentação

- **README (GitHub):** emblema, problema e solução, prints e foto do Node, arquitetura em camadas (percepção, comunicação, plataforma, aplicação, apresentação), modelo de vinherias, hardware, protocolo, referências de guarda, como rodar, estrutura do repositório, **limitações e evolução**, créditos (FIWARE Descomplicado do prof. Fábio Cabrini, uso de IA) e equipe.
- **Manual impresso:** **um PDF único**, A4, com guia rápido de 1 página, instalação (hardware e software) e operação. **Sem fotos**: ilustrações esquemáticas desenhadas, preto e branco, passos numerados, caixas Atenção e Dica, listas com caixinha, links por extenso e QR code, capa, sumário e rodapé.
- A fonte do manual fica em Markdown em `docs/`, e o PDF é gerado no fim. As figuras do esquema de ligação e da caixa só depois da montagem e do modelo 3D prontos.
- Outros: `docs/arquitetura.png`, `docs/referencias.md`, `hardware/firmware/README.md`, `hardware/lista-de-materiais.md`, `hardware/esquema-ligacao.png`.
- Entrega no Forms: link do GitHub com o `.ino`, nomes, descrição, arquitetura, manuais, código do dashboard comentado com `requirements.txt`, link do Wokwi (LDR e DHT22) e o vídeo.

---

## 10. React + Vite: como o grupo cria o projeto

React: biblioteca de JavaScript criada por Jordan Walke (2011) e lançada pelo Facebook (2013). Componentes viram páginas; o `index.html` é renderizado pelo `main.jsx` e mostra o `App.jsx`. Arquivos `.jsx` misturam HTML e JavaScript.

**Pré-requisitos:** VS Code; Node.js na versão **LTS** (nodejs.org); npm. No PC do grupo: Node v24.19.0 e npm 11.17.0.

**Passo a passo do grupo**
1. Criar a pasta do projeto e abri-la no VS Code.
2. Abrir o terminal.
3. Rodar `npm create vite@latest .`
4. Escolher o framework **React**.
5. Escolher a variante **JavaScript**.
6. Escolher o **ESLint** para analisar a sintaxe.
7. Escolher instalar as dependências e rodar o projeto automaticamente (Yes), ou fazer manualmente (No).
8. Clicar no link que aparece no terminal e o projeto abre.

**Limpar a estrutura**
- `public/`: apagar as imagens do modelo (**no WineGuard, manter** os arquivos `wineguard-*`, `icon-*` e `favicon-*`, e só apagar o `vite.svg`).
- `src/assets/`: apagar as imagens.
- `src/App.css`: apagar o arquivo.
- `src/index.css`: apagar **só o conteúdo**.
- `src/App.jsx`: apagar o conteúdo, digitar `rafce` (snippet) e usar fragments `<> </>`.

**Extensões do VS Code:** Material Icon Theme; ES7 React/Redux/Styled-components snippets.

**Pilha dos projetos do grupo** (vista no `package.json` do `loja_gamer`): React 19, `react-router-dom` 7, Tailwind CSS 4 (`@tailwindcss/vite`), Vite 8 e ESLint 10. O WineGuard acrescenta o Recharts. Instalar com `npm install react-router-dom tailwindcss @tailwindcss/vite recharts`.

**Pastas de `src/` no `loja_gamer`:** `assets`, `components` (Footer, GameCard, Header), `css`, `pages` (Contato, Error, Home, Jogos, Login), `App.jsx`, `index.css`, `main.jsx`. O WineGuard segue essa base e acrescenta `context`, `data`, `hooks`, `services` e `utils`.

**Estrutura do projeto**
- `public/`: arquivos públicos (imagens).
- `src/`: onde fica o código. `assets/` (mídias), `App.jsx` (componente principal), `App.css`, `index.css`, `main.jsx` (renderiza o `index.html` no `App.jsx`).
- `.gitignore`, `eslint.config.js`, `index.html`, `package.json` (informações e pacotes), `README.md`, `vite.config.js`.

### Atenção no WineGuard: a pasta `frontend/` já tem arquivos
Ela já contém `public/` (com o emblema e os ícones), `vercel.json`, `package.json` (vazio) e `src/`. Ao rodar `npm create vite@latest .`, o Vite avisa que a pasta **não está vazia** e oferece:
- **Remove existing files and continue:** apaga os arquivos da pasta (menos o `.git`). **Não escolher.**
- **Ignore files and continue:** mantém o que existe. **Esta é a opção.**
- **Cancel.**

Depois, conferir que o `public/` e o `vercel.json` continuam lá. Outra opção, mais segura: criar o projeto numa pasta temporária e copiar o conteúdo para `frontend/`.

---

## 11. Limitações (para o README)

- Sem autenticação: qualquer pessoa com o link vê e altera qualquer vinheria. A suspensão é demonstração.
- O multi-tenant organiza os dados, mas **não os protege** entre vinherias.
- MQTT sem usuário, senha e TLS: quem souber a `apikey` consegue publicar.
- FIWARE sem TLS e sem autenticação (stack feita para prova de conceito).
- O LDR mede em % relativa, não em lux.
- O DHT22 tem margem de ±0,5 °C.
- O IoT Agent recria dispositivos apagados enquanto o ESP32 continuar publicando.
- O IP do Learner Lab muda a cada sessão (mitigado com o DuckDNS).
- As referências de guarda são recomendações de especialistas, não uma norma.

**Evolução prevista:** login por usuário, perfis (admin e vinheria), tokens, banco relacional, MQTT com TLS, cancelamento com carência, exportação em CSV, WiFiManager e alertas externos.

---

## 12. Estado e cronograma

### Pronto
- Repositório e estrutura; identidade visual
- **Firmware 2.3** testado na bancada (sem nuvem) e no Wokwi; esquema de ligação e lista de materiais
- FIWARE na AWS com dados e histórico (8666), e comando `mute` testado (com o Wokwi)
- `provisionar.sh` com cadastro correto (com `apikey`)
- **Dashboard (front-end)** com dados de demonstração, guia em PDF e contrato da API
- Todas as definições deste documento

### Falta
- **Backend (FastAPI):** tudo. É o caminho crítico.
- **Dashboard:** rodar no PC do grupo, corrigir o que aparecer, ligar ao backend e publicar na Vercel.
- **Hardware:** testar o Node com a nuvem; montar na caixa 3D (a faculdade imprime); fotos.
- **Nuvem:** conta DuckDNS; `docker-compose.yml`, Caddy (HTTPS); fechar portas; testar parar e iniciar o lab.
- **Documentação:** manuais em PDF, README completo (feito, com partes "em construção"), vídeo, roteiro do pitch e ensaios.

### Cronograma (8 a 30/10)
| Período | Foco |
|---|---|
| 6 a 11/10 | Dashboard rodando no PC; Node na bancada com a nuvem; início do backend (leitura, cadastro, comandos, triggers e loop de alertas) |
| 12 a 18/10 | Backend completo (vinherias, suspensão, estabilidade); integração do front; teste ponta a ponta com o Node físico; `AVALIACAO_LOCAL_SEMPRE` em 0 |
| 19 a 25/10 | DuckDNS, Compose, Caddy, HTTPS; Vercel; testes na nuvem e no celular; ponto de corte em 25/10 |
| 26 a 29/10 | README, diagrama, manuais em PDF, vídeo, roteiro e ensaios; entrega no Forms |
| 30/10 | Hands-on |

**Se apertar, cortar nesta ordem:** PWA e logo horizontal; alerta de estabilidade; calibração da luz; compose completo (ficando com o do professor e um manual de subida); suspensão automática por vencimento (fica o botão manual); vinherias e suspensão inteiras.

O hands-on vale 40 % e o front 20 %: o mínimo que não pode falhar é o Node enviando dados reais, o dashboard com cadastro, gráficos do STH-Comet e ajuste de triggers, e o alarme disparando por ordem do sistema.

---

## 13. Rotina do dia da apresentação

1. Iniciar o lab e a instância, e esperar o DuckDNS atualizar o nome.
2. Conferir que os containers estão no ar e que o dashboard abre.
3. Ligar o Node e confirmar que ele aparece online.
4. Plano B: hotspot do celular, vídeo gravado e o Wokwi aberto.
5. Ao terminar: **End Lab**.
