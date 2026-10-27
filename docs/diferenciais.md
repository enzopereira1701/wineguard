# Diferenciais do WineGuard

Esta página reúne o que o WineGuard faz além do básico (medir e mostrar), com **onde ver** e **como provar** cada ponto. Tudo aqui existe no repositório e foi testado: se algo não está pronto, não está nesta lista.

## Os cinco principais

| # | Diferencial | O que é | Por que importa |
|---|---|---|---|
| 1 | **Alerta em três canais, com significado** | A **cor do LED** diz a variável (vermelho = temperatura, azul = umidade, verde = luz), o **som** diz o sentido (um bipe longo = acima do limite; dois bipes = abaixo) e a **tela OLED** mostra variável, ALTA ou BAIXA, valor e limite violado. As mesmas cores aparecem nos gráficos do dashboard | Quem está diante da adega entende o que houve sem abrir o painel |
| 2 | **Continua protegendo sem a nuvem** | Sem MQTT por mais de 15 s, o Node avalia os limites sozinho (a tela mostra "OFFLINE (local)"), usando os valores guardados na memória. Quando a conexão volta, ele volta a obedecer ao backend | Uma queda de Wi-Fi ou de servidor não deixa o vinho sem proteção |
| 3 | **Várias vinherias isoladas, com suspensão** | Cada vinheria tem a sua apikey, as suas adegas e os seus Nodes, e os dados não se misturam. A suspensão (manual, por vencimento ou simulada) apaga LED e buzzer dos Nodes, e a API passa a recusar consultas daquela vinheria (403), preservando o histórico | É um produto para vários clientes, com controle de assinatura |
| 4 | **Referências de guarda com fontes e avisos** | Presets de **guarda** (Guarda geral, Longa guarda e Espumante), não de servir, com fontes citadas. O painel bloqueia valores impossíveis, pede confirmação para valores perigosos e avisa faixas estreitas ou largas demais. Trocar de preset mostra os valores de antes e depois | O usuário não precisa ser sommelier para configurar bem |
| 5 | **Alerta de estabilidade** | O backend olha o mínimo e o máximo das últimas 24 h (pelo STH-Comet) e alerta se a temperatura variou mais de 2 °C, mesmo dentro da faixa | O que mais prejudica o vinho é a temperatura que sobe e desce, não só o valor |

## Os de apoio

| # | Diferencial | O que é |
|---|---|---|
| 6 | **Ajuste remoto com confirmação** | Os limites vão do painel ao Node e o painel mostra "Recebido pelo Node às HH:MM. Os novos limites já estão valendo." Se o Node estiver fora, os limites ficam salvos e são reenviados quando ele voltar. O Node guarda limites, mudo, suspensão e intervalo na memória (NVS), e sobrevive a reinícios |
| 7 | **Calibração da luz** | O LDR mede em porcentagem relativa. Com a adega fechada e apagada, um clique registra o "escuro normal" e ajusta o limite de luz |
| 8 | **Cadastro e identificação pelo painel** | "Novo dispositivo" escolhe o próximo `wgn###`, cadastra no IoT Agent com apikey e devolve o bloco do `config.h`. "Identificar Node" faz o Node piscar e apitar para achá-lo entre vários |
| 9 | **Operação robusta** | Backend em contêiner com reinício automático (volta sozinho depois do Start Lab), 176 testes automatizados, histerese para o alerta não oscilar no limite e reconciliação (reenvia os comandos se o estado do Node divergir) |
| 10 | **Hardware completo e testado** | Node físico em caixa impressa em 3D, com esquema de ligação, lista de materiais e simulação no Wokwi, testado de ponta a ponta com a nuvem real |
| 11 | **Documentação e transparência** | README, manual de instalação e manual de operação (para impressão), diagrama de arquitetura, registro de decisões, referências citadas e **limitações assumidas por escrito** |

## Onde ver e como provar

| # | Onde ver | Como provar |
|---|---|---|
| 1 | README, "Como o Node avisa"; Manual de operação, seção 2; `hardware/firmware/` | Provocar um alerta de temperatura e olhar o Node (LED, bipe, OLED) e o painel |
| 2 | Manual de operação, "Se a nuvem cair"; `hardware/firmware/README.md` | Cortar a conexão do Node (hotspot ou Mosquitto) e ver "OFFLINE (local)" depois de 15 s |
| 3 | README, "Várias vinherias"; tela **Vinherias** | **Simular inadimplência**, ver o aviso de serviço suspenso e **Reativar** |
| 4 | README, "Referências de guarda"; `docs/referencias.md`; tela **Triggers** | Escolher um preset, digitar um valor extremo e ver o aviso; trocar de preset e ver a confirmação |
| 5 | Tela **Painel** (selo de estabilidade) e **Alertas** | Alerta de tipo estabilidade no histórico; `GET /api/dispositivos/{id}/estabilidade` |
| 6 | Tela **Triggers**, botão "Salvar e enviar ao Node" | Salvar e ver o aviso "Recebido pelo Node" |
| 7 | Tela **Triggers**, calibração da luz | Clicar em calibrar e ver o limite de luz mudar |
| 8 | Tela **Dispositivos** | "Novo dispositivo" e "Identificar Node" |
| 9 | `backend/tests/`, `fiware/docker-compose.backend.yml` | `pytest` no backend; reiniciar a instância e ver o contêiner voltar |
| 10 | `hardware/` e `simulacao/` | Node físico na apresentação; Wokwi aberto |
| 11 | `docs/` e README | Abrir os manuais e a seção "Limitações e evolução" |

## O que NÃO é diferencial (e dizemos)

Sem login, MQTT sem senha e sem TLS, luz em porcentagem relativa e IP da instância que muda a cada Start Lab. Estão em [Limitações e evolução](../README.md#limitações-e-evolução).
