// Constantes do WineGuard: variáveis monitoradas, períodos, rotas e tempos.
// Mexa aqui (e não nas telas) para mudar nomes, unidades ou cores.

/**
 * @typedef {'temperature'|'humidity'|'luminosity'} Variavel
 * @typedef {{ id: Variavel, rotulo: string, unidade: string, decimais: number,
 *             cor: string, corLed: string,
 *             icone: string, chave: 'temp'|'umid'|'luz' }} InfoVariavel
 */

/** @type {Record<Variavel, InfoVariavel>} */
export const VARIAVEIS = {
  temperature: {
    id: 'temperature',
    rotulo: 'Temperatura',
    unidade: '°C',
    decimais: 1,
    cor: '#c2452d', // mesma cor do LED vermelho
    corLed: 'vermelho',
    icone: 'termometro',
    chave: 'temp',
  },
  humidity: {
    id: 'humidity',
    rotulo: 'Umidade',
    unidade: '%',
    decimais: 0,
    cor: '#2f6f9f', // LED azul
    corLed: 'azul',
    icone: 'gota',
    chave: 'umid',
  },
  luminosity: {
    id: 'luminosity',
    rotulo: 'Luminosidade',
    unidade: '%',
    decimais: 0,
    cor: '#5b8a3a', // LED verde
    corLed: 'verde',
    icone: 'sol',
    chave: 'luz',
  },
}

/** Ordem em que as variáveis aparecem nas telas. */
export const LISTA_VARIAVEIS = /** @type {Variavel[]} */ (['temperature', 'humidity', 'luminosity'])

/** Folga para sair do alerta (as mesmas do firmware do Node). */
export const HISTERESE = { temperature: 0.5, humidity: 2, luminosity: 2 }

/** Períodos do seletor de gráficos. `pontos` = quantas leituras o gráfico mostra. */
export const PERIODOS = [
  { id: '1h', rotulo: '1 hora', ms: 60 * 60 * 1000, pontos: 60 },
  { id: '24h', rotulo: '24 horas', ms: 24 * 60 * 60 * 1000, pontos: 96 },
  { id: '7d', rotulo: '7 dias', ms: 7 * 24 * 60 * 60 * 1000, pontos: 84 },
]

export const INTERVALO_ATUALIZACAO_MS = 5000 // o backend consulta o Orion a cada 5 s
export const OFFLINE_APOS_MS = 30000 // 30 s sem leitura = Node offline
export const ESTABILIDADE_LIMITE_PADRAO = 2 // °C de variação em 24 h

/** Telas com atalho na navegação. `bottom` = aparece na barra inferior do celular. */
export const ROTAS = [
  { caminho: '/painel', rotulo: 'Painel', icone: 'painel' },
  { caminho: '/dispositivos', rotulo: 'Dispositivos', icone: 'chip' },
  { caminho: '/triggers', rotulo: 'Triggers', icone: 'ajustes' },
  { caminho: '/alertas', rotulo: 'Alertas', icone: 'sino' },
  { caminho: '/vinherias', rotulo: 'Vinherias', icone: 'predio' },
]

/** Estados que um dispositivo pode ter na interface. */
export const ESTADOS = {
  ok: { rotulo: 'Normal', tom: 'ok' },
  alerta: { rotulo: 'Em alerta', tom: 'alerta' },
  offline: { rotulo: 'Offline', tom: 'neutro' },
  suspenso: { rotulo: 'Suspenso', tom: 'atencao' },
  aguardando: { rotulo: 'Aguardando', tom: 'neutro' },
}

/** Tipos de alerta do histórico (além das 3 variáveis). */
export const TIPOS_ALERTA = {
  temperature: { rotulo: 'Temperatura', icone: 'termometro', cor: VARIAVEIS.temperature.cor },
  humidity: { rotulo: 'Umidade', icone: 'gota', cor: VARIAVEIS.humidity.cor },
  luminosity: { rotulo: 'Luminosidade', icone: 'sol', cor: VARIAVEIS.luminosity.cor },
  estabilidade: { rotulo: 'Estabilidade', icone: 'onda', cor: '#8a6a2f' },
  offline: { rotulo: 'Node offline', icone: 'sinal', cor: '#6e5f55' },
}
