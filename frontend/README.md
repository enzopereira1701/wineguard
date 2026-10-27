# WineGuard Dashboard

Front-end do WineGuard (marcha.dev): React 19, React Router 7, Tailwind CSS 4 e Recharts, com Vite.
Fala com o backend FastAPI (`../backend`) e também roda sozinho, com dados de demonstração gerados no navegador.
**Não é publicado**: roda no computador do grupo e é aberto na apresentação.

## Rodar

```bash
npm install
cp .env.example .env     # no Windows: copie o arquivo e renomeie para .env
npm run dev
```

Abra o endereço que aparece no terminal (normalmente http://localhost:5173). Para abrir no celular, no mesmo Wi-Fi:
`npm run dev -- --host` e use o endereço `Network:`.

## Configuração (`.env`)

O `.env` **não vai para o GitHub**. O IP da instância da AWS muda a cada sessão do lab: troque-o aqui.

| Variável | Para quê |
|---|---|
| `VITE_USE_MOCK` | `true` usa o simulador do navegador (`src/services/mock.js`); `false` chama o backend |
| `VITE_API_URL` | Endereço do backend, ex.: `http://localhost:8000` ou `http://<IP da instância>:8000` |
| `VITE_MQTT_HOST` | IP da instância; aparece no bloco de configuração do Node (tela Dispositivos) |

Depois de mudar o `.env`, pare e suba o `npm run dev` de novo.

Os caminhos da API estão em `src/services/api.js` (o único lugar que acessa dados) e os formatos de resposta em `../docs/api-contrato.md`.

## Telas

Início, Painel, Dispositivos, Triggers, Alertas, Vinherias e Suspenso (mais a página de erro). Prints em `../docs/prints/`.

## Estrutura

```
public/            logo, favicons e ícones do PWA
src/
  assets/          imagens da tela Início
  components/      peças reutilizáveis (Botao, Modal, gráficos, Header...)
  context/         estado global (vinheria, dispositivo, avisos)
  css/             animações
  data/            constantes, presets de guarda, fontes, equipe
  hooks/           usePolling, useAgora, useApp
  pages/           uma por tela (Home, Painel, Dispositivos, Triggers, Alertas, Vinherias, Suspenso, Error)
  services/        api.js (único ponto de acesso a dados) e mock.js
  utils/           funções puras (formatação, avaliação, validação, estabilidade...)
  App.jsx          layout e rotas
  index.css        Tailwind e tokens de design
  main.jsx         ponto de entrada
```

Os nomes dos integrantes ficam em `src/data/equipe.js`.
