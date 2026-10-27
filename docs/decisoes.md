# WineGuard: decisões do projeto

Ficha de decisões do **CP5 Vinheria Full** (marcha.dev). Cole este arquivo no começo de uma conversa nova com o Claude para retomar de onde paramos.

- **Grupo:** marcha.dev
- **Produto:** WineGuard
  - **Node:** o hardware (ESP32 com sensores e atuadores), um por adega
  - **Cloud:** a plataforma (FIWARE, backend e banco de dados do Orion)
  - **Dashboard:** o site em React
- **Entrega e hands-on:** 30/10/2026
- **Integrantes:** Enzo Pereira, Raphael Mascarenhas, Yannick Davila e Alysson Souto
- **Última atualização desta ficha:** 11/10/2026

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
- `AVALIACAO_LOCAL_SEMPRE`: 1 no firmware da bancada (era para o período sem backend). O backend já existe (09/10): **voltar para 0 no teste ponta a ponta (15/10)** e regravar o Node. No Wokwi já está 0.
- Limites padrão do Node (até receber os do backend): temperatura 10 a 15 °C, umidade 60 a 75 %, luz 0 a 10 %.
- Logo do OLED: escudo com cacho, 45x64 px, 1 bit (`icones.h`).
- Bibliotecas: PubSubClient, Adafruit GFX, Adafruit SSD1306, DHT sensor library (e a Adafruit Unified Sensor). Pacote **esp32 3.3.x**. **Anotar as versões** em `hardware/firmware/README.md`.
- Gravação na bancada: se aparecer `Invalid head of packet (0x80)`, baixar o **Upload Speed** para 115200 e trocar o cabo USB.
- **Estado (06/10):** o Node físico foi montado e roda sem nuvem (OLED, LED, buzzer, botão, DHT22 e LDR). Falta testar com a nuvem e a caixa.
- **Estado (09/10):** o Node físico (`wgn005`, cadastrado pela API na `vin_demo`) foi testado **com a nuvem**: conecta no Wi-Fi de 2,4 GHz, publica, recebe `setTriggers`, `alert`, `suspend` e `resume`, e grava histórico contínuo no STH-Comet. Falta a caixa 3D.
- O ESP32 só conecta em Wi-Fi de **2,4 GHz** (no roteador do grupo é a rede sem o sufixo "5g").

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
- **Vinherias (Backend 4, validado no FIWARE real em 09/10):** vinheria e adega são entidades `Vinheria` (service `wineguard_admin`) e `Adega`. A `vin_demo` (apikey `winedemo`) nasce sozinha. `POST /api/vinherias` cria a vinheria com id `vin_<nome>`, **apikey própria** (`<nome><4 hex>`), vencimento (padrão 90 dias) e uma "Adega 1". O cadastro de dispositivo usa a apikey da vinheria.
- **O `device_id` é global** (um contador só para todas as vinherias): o MQTT identifica o Node só por `apikey` + `device_id`, então `wgn004` na Quinta do Sol e `wgn005` na `vin_demo` nunca se repetem.
- **Suspensão:** `suspender` manda `suspend` a todos os Nodes e a API passa a responder **403** para a vinheria; o vigia encerra os alertas e reenvia `suspend` a quem ainda publicar. `reativar` manda `resume` (e, se o vencimento já passou, renova por 30 dias). `simular-inadimplencia` coloca o vencimento em ontem e suspende. Vencimento vencido suspende sozinho.
- **Estabilidade:** `GET /api/dispositivos/{id}/estabilidade` (mínimo e máximo das últimas 24 h pelo STH-Comet, `aggrMethod=min/max`). O vigia confere a cada 60 s e abre o alerta `estabilidade` quando a variação passa do `estabilidadeMax` (padrão 2 °C). Não avalia Node offline.
- **Onde roda:** na instância, como contêiner (segunda 19/10), ou no PC durante o desenvolvimento. **Só um processo** do backend por vez (dois vigias duplicam os alertas).
- Python instalado: 3.14.3. No Git Bash, `python` cai na Microsoft Store; **usar `py`**.
- **Lacunas do histórico:** a API devolve só os pontos que existem (sem preencher buracos, para não inventar dados). O dashboard quebra a linha do gráfico onde o intervalo entre dois pontos passa de 1,5 vez o passo (1 min na janela de 1 h; 1 h em 24 h e 7 d) e ignora esses vazios nas contas de mínimo e máximo.

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

**Pilha (a mesma dos projetos do grupo, ex.: `loja_gamer`):** React 19 com Vite (JavaScript), React Router 7, Tailwind CSS 4 e Recharts. **Não será publicado**: roda no PC do grupo (`npm run dev` ou build local) e é aberto na hora da apresentação. Funciona em PC e celular (navbar fixa e translúcida no PC; barra inferior no celular). PWA se sobrar tempo.

**Estado (11/10):** o front-end está **ligado ao backend real** (`VITE_USE_MOCK=false`) e **testado em todas as telas com dados do FIWARE**, no PC e no celular (modo dispositivo do Chrome). O gráfico quebra a linha nas lacunas do histórico e mostra pontos nas leituras isoladas. Ele roda hoje em `~/Desktop/wineguard-dashboard`; entra no repositório em `frontend/` em 16/10 (com `.env` fora do Git e `.env.example` genérico).

**Dados:** nenhuma tela busca dados direto. Tudo passa por `src/services/api.js`, que usa o simulador (`VITE_USE_MOCK=true`) ou o backend (`VITE_API_URL`). O formato das respostas é o **contrato** em `docs/api-contrato.md`.

**Site de apresentação (decidido em 15/10): não haverá site separado.** A tela Início do próprio dashboard já apresenta o problema, a solução, as cinco camadas, o modelo de vinherias, os alertas e a equipe. O site em React que o Raphael começou (`RaphaelMascarenhasLima/WineGuard`, com Início e Como funciona prontos e Node, Dashboard e Projeto só com título) fica de lado e **não entra na entrega**. Se o enunciado ou o professor pedirem um portfólio à parte, retomar: o pacote de conteúdo (`portfolio-conteudo.zip`) já tem os textos e as fotos.

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
- Logo horizontal (emblema e palavra) para a navbar: pronta (`wineguard-logo-horizontal.svg` e `.png`).

---

## 8. Docker Compose (decidido em 10/10)

- **Um compose único nosso**, baseado no do professor (dar o crédito), na raiz do repositório.
- Sobe: Mosquitto, IoT Agent, Orion, STH-Comet, dois MongoDB e o **backend** (`Dockerfile` do backend, código vindo do GitHub com `git clone` na instância).
- **Sem DuckDNS, sem Caddy e sem HTTPS.** Sem nome, o HTTPS não é possível, e a Vercel não é usada, então não há conteúdo misto. O dashboard roda no PC (`http://localhost`) e chama o backend em `http://<IP do dia>:8000`.
- **Prática fixa em toda sessão do lab: colocar o IP novo em tudo que precisa:** `backend/.env` (`FIWARE_HOST`, só se o backend rodar no PC), `MQTT_BROKER` do `config.h` do Node físico (e regravar), `MQTT_BROKER` do `config.h` do Wokwi, e o endereço da API no dashboard.
- Portas abertas no final: **1883** (Node) e **8000** (backend). As 1026, 4041 e 8666 deixam de ficar públicas (o backend fala com o FIWARE pela rede interna do Docker). A 27017 nunca fica aberta.
- Versões fixas das imagens, volumes nomeados (os dados sobrevivem ao End Lab), `restart: unless-stopped`, configuração por `.env` (com `.env.example`).
- Mosquitto com `mosquitto.conf` no repositório.
- Comando atual na AWS: `docker compose` (com espaço). Pode ser preciso instalar `docker-compose-plugin`.

---

## 9. Documentação

- **README (GitHub):** emblema, problema e solução, prints e foto do Node, arquitetura em camadas (percepção, comunicação, plataforma, aplicação, apresentação), modelo de vinherias, hardware, protocolo, referências de guarda, como rodar, estrutura do repositório, **limitações e evolução**, créditos (FIWARE Descomplicado do prof. Fábio Cabrini, uso de IA) e equipe.
- **Manuais (decidido em 27/10, o professor quer impresso):** **dois** documentos, `docs/manual-instalacao.md` (6 páginas em PDF) e `docs/manual-operacao.md` (7 páginas), com o mesmo conteúdo em Markdown (Git) e em PDF A4 (impressão). Têm capa, esquema de ligação, fotos do Node, prints do dashboard, tabelas de problemas e rodapé com página. Os PDFs ficam fora do Git (gerados a partir do `.md`).
- A fonte dos manuais fica em Markdown em `docs/`; o PDF é gerado a partir dela (Chromium/Playwright).
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
- O IP do Learner Lab muda a cada sessão; o IP novo é colocado à mão em tudo que precisa (sem DuckDNS).
- Sem HTTPS: o dashboard e a API falam em HTTP, e o dashboard não é publicado.
- As referências de guarda são recomendações de especialistas, não uma norma.

**Evolução prevista:** login por usuário, perfis (admin e vinheria), tokens, banco relacional, MQTT com TLS, cancelamento com carência, exportação em CSV, WiFiManager e alertas externos.

---

## 12. Estado e cronograma

### Pronto
- Repositório e estrutura; identidade visual
- **Firmware 2.3** testado na bancada (sem nuvem) e no Wokwi; esquema de ligação e lista de materiais
- FIWARE na AWS com dados e histórico (8666), e comando `mute` testado (com o Wokwi)
- `provisionar.sh` com cadastro correto (com `apikey`)
- **Dashboard (front-end)** rodando no PC com dados de demonstração, redesenhado (navegação, cartões, imagens, rodapé), com contrato da API
- Todas as definições deste documento
- **Backend 1** (FastAPI): leitura atual e histórico, testados com dados reais do Orion e do STH-Comet (07/10)
- Conta DuckDNS criada (`wineguard-cp5.duckdns.org`), **sem uso** a partir de 10/10
- **Backend 2, 3 e 4** no GitHub, com 176 testes e validados no FIWARE real (09/10): cadastro com apikey, triggers com confirmação do Node, vigia de alertas, vinherias, adegas, suspensão e estabilidade
- **Node físico `wgn005` na nuvem** (09/10): envia, recebe comandos e grava histórico
- **Teste ponta a ponta com o Node físico na caixa** (15/10): `wgn005` montado na caixa, `AVALIACAO_LOCAL_SEMPRE` em 0, backend e dashboard no PC contra a nuvem. Validados: telemetria, mute (dashboard e botão), alertas ALTA (LED fixo, bipe longo) e BAIXA (LED pisca, 2 bipes) com OLED, rodízio entre variáveis, alerta fechando ao voltar ao normal, queda e retorno do broker
- **Node na nuvem e celular (24/10):** Node regravado com o IP do dia, RSSI de -57 a -75 dBm (repetidor), `setTriggers`, `alert`, `mute` e `identify` validados; limites alterados pelo dashboard com confirmação do Node, alerta fechando e reabrindo; dashboard aberto num celular de verdade pela rede local
- **Backend volta sozinho após o Start Lab (20/10):** o contêiner subiu com os do FIWARE, a API respondeu do PC no IP novo e o dashboard carregou os dados (que sobrevivem ao End Lab)
- **Backend na instância (18/10):** contêiner `wineguard-backend` (porta 8000) no compose do FIWARE por um `docker-compose.override.yml`, falando com Orion e STH-Comet por `host.docker.internal`; portas 1026, 4041, 8666 e 27017 fechadas no Security Group (ficam 22, 1883 e 8000); dashboard do repositório (`frontend/`) rodou contra a nuvem
- **Dashboard ligado ao backend real e validado** (11/10): painel, comandos (mute e identificar), triggers com confirmação, dispositivos (cadastro, edição, remoção), alertas com filtros, vinherias (nova com vencimento opcional, suspender, reativar), página Suspenso, Início e layout no celular

### Falta
- **Dashboard:** já está no GitHub (`frontend/`). Não será publicado. Falta só testar "simular inadimplência" com um Node real ligado e os presets/avisos de Triggers com o Node físico.
- **Node:** conferir o mute antes da demo (o botão guarda o estado; reativar pelo dashboard se estiver mudo).
- **Hardware:** esquema de ligação final (a figura do manual). Caixa montada, teste ponta a ponta feito e fotos em `hardware/fotos/` (15/10).
- **Nuvem:** nada pendente de código. Ensaio completo do dia (Start Lab até a demo) pode ser repetido na semana do hands-on.
- **Documentação:** README completo e READMEs de backend, frontend e firmware (feitos em 27/10); diagrama de arquitetura atualizado (23f04a) e manuais de instalação e operação (6eedab7, 27/10). `docker-compose.yml` vazio da raiz apagado (27/10) e roteiros do vídeo e do hands-on prontos (`docs/roteiro-video.md`, `docs/roteiro-handson.md`). Falta gravar o vídeo (link em `video/link.md`) e ensaiar.

### Cronograma (8 a 30/10)
| Período | Foco |
|---|---|
| 7 a 9/10 | **Feito:** Backend 1 a 4 e Node físico na nuvem |
| 10 e 11/10 | **Feito:** margem do backend, decisão sobre as lacunas e dashboard ligado ao backend real e validado (adiantou 12 a 14/10) |
| 12 a 18/10 | **Feito:** folga (12 a 14), teste ponta a ponta com o Node na caixa (15), dashboard no GitHub, prints, `wgn001` e `wgn003` removidos (16), margem (17) e, em 18/10, o backend na instância e as portas 1026, 4041 e 8666 fechadas (adiantou 19 e 20) |
| 19 a 25/10 | **Feito:** backend voltando sozinho após o Start Lab (20) e, em 24/10, Node regravado com o IP do dia, testes na nuvem (identificar, triggers, mute) e dashboard no celular. Ponto de corte em 25/10 (sem código novo a partir daí) |
| 26 a 29/10 | **Feito (27/10):** README e READMEs menores. Diagrama (023f04a) e manuais (6eedab7) prontos. Compose da raiz apagado e roteiros prontos. **Falta:** gravar o vídeo, ensaiar e entregar no Forms (29) |
| 30/10 | Hands-on (até 1h30: chegar 30 minutos antes para ligar o lab e trocar o IP) |

**Se apertar, cortar nesta ordem:** PWA; calibração da luz; o backend na instância (ficando com ele no PC); telas de vinherias e suspensão no dashboard (o backend já tem).

O hands-on vale 40 % e o front 20 %: o mínimo que não pode falhar é o Node enviando dados reais, o dashboard com cadastro, gráficos do STH-Comet e ajuste de triggers, e o alarme disparando por ordem do sistema.

---

## 13. Rotina do dia da apresentação

Chegar **30 minutos antes** (o hands-on dura até 1h30).
1. **Start Lab**, esperar a bolinha verde e copiar o **IP público** da instância.
2. Conferir os contêineres (`sudo docker ps`): FIWARE e backend no ar.
3. Trocar o IP em tudo: `MQTT_BROKER` do `config.h` do Node (e **regravar**), do Wokwi e o endereço da API no dashboard (e `backend/.env`, só se o backend rodar no PC).
4. Abrir o dashboard no PC e ligar o Node: ele deve aparecer online.
5. Plano B: hotspot do celular (2,4 GHz), vídeo gravado e o Wokwi aberto.
6. Ao terminar: **End Lab**.

---

## 14. Aprendizados da Parte B (07/10/2026): primeiro teste com dados reais

**Online/offline usa o `TimeInstant`, não o `dateModified`.**
O Orion só atualiza o `dateModified` de uma variável quando o valor muda. Com a leitura parada
(simulador ou adega estável) o Node parecia offline mesmo enviando. O IoT Agent grava o
`TimeInstant` a cada mensagem, então o backend usa ele e deixa o `dateModified` de reserva.

**Cada dispositivo MQTT precisa de um `clientId` único.**
Dois clientes com o mesmo `clientId` se derrubam em loop no Mosquitto. A simulação do Wokwi usa
o sufixo `_sim` (`wineguard_wgn001_sim`) para não brigar com o ESP32 físico.

**O histórico do STH-Comet tem lacunas.**
O STH só grava quando o Orion avisa que algo mudou. Com `TimeInstant` na condição da assinatura o histórico ficou contínuo (um ponto por minuto, confirmado com o Wokwi e com o Node físico); os buracos que sobram são de Node offline ou vinheria suspensa. **Decisão (11/10):** a API devolve só pontos reais e o dashboard quebra a linha (ver seção 4).

**O Wokwi desacelera em aba escondida.**
Para testar, deixar a janela do Wokwi visível ao lado do `/docs`. É só do simulador.

**Operação do lab:** os containers sobem sozinhos quando o lab liga e o cadastro do `wgn001`
sobrevive ao reinício; só o IP muda (atualizar `FIWARE_HOST` e `MQTT_BROKER`).

---

## 15. Aprendizados de 08 a 11/10/2026: Backend 2 a 4, Node físico e dashboard

- **O comando espera a confirmação do Node.** O `PUT /triggers` responde 200 quando o Node confirma pelo `cmdexe`; sem confirmação em 8 s responde 504 (os limites ficam salvos e são reenviados quando o Node voltar). No Wokwi lento ou com a janela escondida isso dá 504; na placa física responde em poucos segundos.
- **O `device_id` precisa ser único no sistema todo,** não só dentro da vinheria (ver seção 4). O primeiro cadastro numa vinheria nova olha os dispositivos de todas.
- **Um Node suspenso não publica nada,** nem `st|suspenso`. A API usa o estado guardado da vinheria, e o vigia reenvia `suspend` a quem ainda publicar.
- **Reativar com o Node reconectando** pode exigir repetir o `reativar` (o `resume` chega quando o Node volta ao broker). No Wokwi lento é comum; na placa física é raro.
- **Os dados do FIWARE sobrevivem ao End Lab** (volumes do Mongo): vinherias, dispositivos, alertas e histórico continuam no dia seguinte. Só o IP muda.
- **Só um processo do backend por vez:** dois vigias duplicariam os alertas.
- **O `config.h` de verdade fica fora do GitHub** (tem a senha do Wi-Fi). Não colar prints dele em lugares compartilhados.
- **O gráfico não liga pontos separados por lacuna.** O histórico só traz pontos reais; o dashboard preenche a grade de tempo com vazios (a linha quebra) e desenha um ponto nas leituras isoladas, senão o gráfico de 7 dias (um ponto por hora) parece vazio. O eixo X tem margem nas pontas para o último ponto não ser cortado.
- **Wokwi lento gera muitos "Node offline" curtos** (13 s a 4 min) e 504 nos comandos. Manter a janela do Wokwi visível e, só para ele, `ESPERA_COMANDO_SEGUNDOS=20` no `backend/.env`. **Remover para a placa física e o hands-on.**
- **`.env` do dashboard** (`VITE_USE_MOCK=false`, `VITE_API_URL`, `VITE_MQTT_HOST`) é lido só ao iniciar o `npm run dev`: reiniciar depois de mudar o IP.
- **Modal:** efeito que depende de função recriada a cada render devolve o foco ao primeiro campo a cada letra. O `Modal` guarda `onFechar` em uma ref.
- **Alertas antigos ficam abertos** enquanto a condição existir (ex.: temperatura do wgn001 acima do limite por 2 dias). Dispositivo de teste sem Node (ex.: `wgn003`) gera "Node offline" eterno: remover antes da demo.
- **Vinheria nova:** vencimento é opcional (padrão 90 dias). Dispositivo novo em outra vinheria recebe a apikey dela e o próximo `device_id` livre do sistema.

### 15/10/2026: teste ponta a ponta com o Node na caixa
- **A IDE trabalhava numa cópia do firmware diferente da do repositório** (e mais antiga, sem o `CLIENT_SUFIXO`). Editar o `config.h` do repositório não mudou o que foi gravado: o Node tentou o IP velho. Daqui em diante: abrir o sketch **direto da pasta do repositório** na IDE, com o `config.h` de bancada lá (ele é ignorado pelo Git). Não copiar o `.ino` da IDE por cima do repositório.
- **A IDE reformata a indentação** e deixa o `git diff` enorme. Para ver a mudança real: `git --no-pager diff -w --ignore-cr-at-eol <arquivo>`.
- **Limites e mute ficam na memória do Node (NVS).** Trocar os triggers pelo dashboard muda o que ele guarda, e o mute do botão persiste depois de regravar. Para voltar ao padrão do firmware: Arduino IDE → Tools → Erase All Flash Before Sketch Upload → Enabled, gravar, e voltar para Disabled.
- **Com `AVALIACAO_LOCAL_SEMPRE 0`** quem decide o alerta é o backend (comandos `alert`). Se o broker cair, depois de 15 s o Node avalia sozinho (OLED "OFFLINE (local)") e mantém LED e som. Ao reconectar, volta a obedecer ao backend, sem intervenção.
- **Depois de reiniciar o Mosquitto, reiniciar o IoT Agent** (`sudo docker restart fiware-iot-agent`). Sem isso o Node reconecta e envia, mas os dados não chegam ao Orion e o painel continua "offline". Vale para o plano B do dia.
- **Som do alerta:** ALTA = bipe longo repetido (com `ALTA_CONTINUO 0`), LED fixo; BAIXA = 2 bipes e pausa, LED pisca. Com mais de um alerta, o rodízio fica no mínimo 3 s em cada variável (ouvem-se ~3 bipes longos antes da troca e da pausa de silêncio).
- **Wi-Fi na caixa:** RSSI entre -70 e -83 dBm (fraco). Ficar de olho; se cair, afastar a antena de fios e metal ou aproximar do roteador.
- **Hotspot do celular** continua sendo o plano B (2,4 GHz).

### 16/10/2026: dashboard no GitHub e limpeza do lab
- **Dashboard em `frontend/`** (commit a2df1b6) e prints em `docs/prints/` (55c05fb). O `package.json` do repositório era um placeholder vazio e o `vercel.json` foi removido (sem Vercel).
- **Ao copiar uma pasta para o repositório, usar `tar` com `--exclude`** (`node_modules`, `.env`, `.git`, `dist`, `*.zip`) e conferir com `git status --short -uall` antes do `git add`. Apareceram duas sobras (uma cópia aninhada do dashboard e um `docs/` duplicado), apagadas antes do commit.
- **`wgn001` (Wokwi) e `wgn003` (Sensor B) removidos pelo dashboard:** o contador de alertas caiu de 6 para 4 e os "Node offline" deles sumiram. A vinheria ficou só com o Node Bancada (`wgn005`).
- **Node regravado com a pasta do repositório** (IP do dia 100.30.193.84 confirmado no Serial). O mute antigo persistia (`mu|1`) e foi reativado pelo dashboard.
- **Wi-Fi:** RSSI de -87 a -93 dBm naquela manhã (pior que os -70 a -83 de 15/10). Se persistir, aproximar o Node do roteador ou usar o hotspot.

### 18/10/2026: backend na instância
- **Onde fica cada coisa na instância:** o compose do professor está em `~/fiware` (clone do repositório dele, não editado) e o nosso código em `~/wineguard` (`git clone` do GitHub; atualizar com `git pull`). O serviço do backend entra por `~/fiware/docker-compose.override.yml`, copiado de `fiware/docker-compose.backend.yml` do repositório.
- **Subir ou atualizar:** `cd ~/wineguard && git pull`, depois `cd ~/fiware && sudo docker compose up -d --build wineguard-backend`. Log: `sudo docker logs --tail 20 wineguard-backend`.
- **Configuração:** `~/wineguard/backend/.env` (fora do GitHub), com `FIWARE_HOST=host.docker.internal`. O backend monta as URLs do Orion, STH-Comet e IoT Agent a partir de um host só, e no Docker cada serviço tem um nome; por isso ele usa as portas publicadas no host pela ponte do Docker (`extra_hosts: host.docker.internal:host-gateway`). Por ser por dentro, as portas podem ficar fechadas no Security Group.
- **Só um backend por vez:** com o contêiner no ar, não rodar `uvicorn` no PC (dois vigias duplicam os alertas).
- **O IP do dia não entra na instância:** quem muda de IP é o PC (`frontend/.env`: `VITE_API_URL` e `VITE_MQTT_HOST`) e o Node (`MQTT_BROKER` no `config.h`). O `.env` do backend na instância não muda.
- **Rotas:** os dispositivos de uma vinheria saem em `/api/vinherias/{id}/dispositivos` (não existe `/api/dispositivos` sozinho); leitura em `/api/dispositivos/{id}/atual`.
- **Instalação do front:** se o `npm install` for interrompido no Windows, apagar `node_modules` (`rm -rf node_modules`) e instalar de novo sem apertar nada.
- **O download de `.md` do navegador falhou duas vezes (arquivo de 0 bytes);** arquivos `.zip` funcionam. Mandar documentos num zip.
- **Mute:** a última leitura do `wgn005` (16/10) ainda mostrava `muted: 1`; conferir e reativar quando o Node voltar a ligar.

### 20/10/2026: Start Lab com o backend já na instância
- Depois do Start Lab, `sudo docker ps` já mostra o `wineguard-backend` com `Up` (política `restart: unless-stopped`): não precisa subir nada à mão. Os Security Group e os dados também sobrevivem.
- Rotina da sessão: pegar o IP novo, `curl http://<IP>:8000/api/vinherias` do PC e atualizar `frontend/.env` (`VITE_API_URL` e `VITE_MQTT_HOST`). O Node leva o IP novo no `config.h`.

### 24/10/2026: Node na nuvem, celular e disco da instância
- **Rotina do dia, testada:** Start Lab, `curl http://<IP>:8000/api/vinherias`, trocar `MQTT_BROKER` no `config.h` (pasta do repositório) e gravar, `frontend/.env` com o IP, `npm run dev`. O Serial deve mostrar o IP novo, `Conectado ao broker MQTT!`, `setTriggers` e `alert` recebidos.
- **Wi-Fi:** com o repetidor (rede 2,4 GHz com sufixo `_EXT`) o RSSI ficou entre -57 e -75 dBm. O nome da rede vai exatamente igual no `WIFI_SSID` do `config.h`. Na faculdade o Wi-Fi é bom; o hotspot do celular continua sendo o plano B.
- **Mute pelo botão** fica guardado no Node (`mu|1`) e aparece mudo no painel; reativar com "Reativar som". Não é falha.
- **Celular de verdade:** `npm run dev -- --host` mostra uma linha `Network: http://192.168.x.x:5173/`; o celular, no mesmo Wi-Fi, abre esse endereço. Para o backend aceitar essa origem, o `CORS_ORIGINS` do `.env` da instância ficou `*` (sem login, é só demonstração); depois de mudar o `.env`: `sudo docker compose up -d --force-recreate wineguard-backend` em `~/fiware`.
- **Disco da instância (6,7 GB):** estava em 84%. O Docker usa pouco (imagens de 2,2 GB e volumes de 20 MB). O que cresce são os logs dos contêineres em DEBUG: o do IoT Agent chegou a 288 MB. Esvaziado com `sudo sh -c 'truncate -s 0 /var/lib/docker/containers/<id>*/*-json.log'` (sem tocar nos dados); o disco foi para 78%. Não apagar volumes.

### 27/10/2026: README e READMEs menores
- **README da raiz reescrito** com o estado real (tudo pronto e testado), fotos do Node, prints do dashboard, "Como rodar" completo (computador e instância) e limitações atualizadas. READMEs do backend, frontend e firmware atualizados; `backend/.env.example` e `config.example.h` sem menção a DuckDNS e Vercel.
- **Arquivos `.md` não baixam direito do navegador** (0 bytes); mandar em `.zip`. Antes de commitar um arquivo copiado, conferir `wc -l` e o `git diff --stat`.
- **Diagrama** `docs/arquitetura.png` refeito sem Vercel e HTTPS (023f04a). **Manuais** de instalação e operação publicados (6eedab7); PDFs enviados ao usuário para imprimir.
- **`docker-compose.yml` vazio da raiz apagado:** a instalação usa o compose do professor (`~/fiware`) mais o nosso override `fiware/docker-compose.backend.yml`, como explica o README.
- **Roteiros:** `docs/roteiro-video.md` (4 a 5 min) e `docs/roteiro-handson.md` (apresentação de 12 min, no máximo 15, feita por **uma pessoa**). O PDF `roteiro-apresentador.pdf` foi gerado só para estudo e não vai para o Git.
