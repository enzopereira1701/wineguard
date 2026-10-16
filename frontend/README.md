# WineGuard Dashboard

Front-end do WineGuard (marcha.dev): React 19, React Router 7, Tailwind CSS 4 e Recharts, com Vite.
Funciona sozinho, com dados de demonstração gerados no navegador. Quando o backend FastAPI estiver
pronto, basta trocar uma variável do `.env`.

## Rodar

```bash
npm install
cp .env.example .env     # no Windows: copie o arquivo e renomeie para .env
npm run dev
```

Abra o endereço que aparece no terminal (normalmente http://localhost:5173).

## Dados de demonstração x backend

| `.env` | O que acontece |
|---|---|
| `VITE_USE_MOCK=true` | usa `src/services/mock.js` (simulador de sensores e banco em memória) |
| `VITE_USE_MOCK=false` | chama o backend em `VITE_API_URL`; os caminhos estão em `src/services/api.js` |

Os formatos de resposta estão em `docs/api-contrato.md`.

## Estrutura

```
public/            logo, favicons e ícones do PWA
src/
  assets/          mídias (vazia por enquanto)
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

## Observações

- O `eslint.config.js` não vem neste zip: o Vite o gera ao criar o projeto. Use o do seu projeto.
- Não foi possível instalar as bibliotecas no ambiente em que este código foi escrito. A lógica foi testada
  (funções, simulador e telas no navegador, com versões simplificadas do Router e do Recharts), mas o visual com
  Tailwind e os gráficos reais devem ser conferidos no primeiro `npm run dev`.
- Os nomes dos integrantes ficam em `src/data/equipe.js`.
