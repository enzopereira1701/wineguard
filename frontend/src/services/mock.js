// "Banco de dados" e simulador de sensores em memória.
// Serve para o dashboard funcionar SEM backend. Quando o backend FastAPI estiver
// pronto, ele passa a responder no lugar deste arquivo (veja services/api.js).
//
// O que ele simula:
//  - vinherias, adegas e dispositivos de exemplo
//  - leituras que oscilam de forma suave e previsível (função do tempo)
//  - cenários para testar alertas (temperatura alta, Node offline, etc.)
//  - a avaliação dos triggers com histerese, que gera o histórico de alertas
//    (é a mesma lógica que o backend vai ter)
import { HISTERESE, LISTA_VARIAVEIS, OFFLINE_APOS_MS, PERIODOS, VARIAVEIS } from '../data/constantes'
import { PRESETS, triggersDoPreset } from '../data/presets'
import { ABAIXO, ACIMA, NORMAL, avaliarVariavel } from '../utils/avaliacao'
import { calcularEstabilidade } from '../utils/estabilidade'
import { apikeyDaVinheria, idDaVinheria, proximoIdDispositivo } from '../utils/ids'

const MIN = 60 * 1000
const HORA = 60 * MIN
const DIA = 24 * HORA
const iso = (ms) => new Date(ms).toISOString()
const doisPi = 2 * Math.PI

// ------------------------------------------------------------------ base de dados
const db = {
  vinherias: [],
  adegas: [],
  dispositivos: [],
  triggers: {}, // por deviceId
  sim: {}, // estado do simulador, por deviceId
  alertas: [],
  proximoAlerta: 1,
}

// Valor "normal" de cada preset (onde as leituras ficam quando está tudo bem)
const BASE = {
  guarda_geral: { temperature: 13, humidity: 68, luminosity: 3 },
  longa_guarda: { temperature: 12.5, humidity: 67, luminosity: 2 },
  espumante: { temperature: 11, humidity: 75, luminosity: 2 },
}

function registrarDispositivo(d) {
  db.dispositivos.push(d)
  db.triggers[d.id] = triggersDoPreset(d.preset)
  db.sim[d.id] = {
    cenario: 'normal',
    desde: 0,
    semente: db.dispositivos.length * 7.31,
    mudo: false,
    base: BASE[d.preset] ?? BASE.guarda_geral,
    estados: { temperature: NORMAL, humidity: NORMAL, luminosity: NORMAL, estabilidade: false },
    abertos: {}, // chave do alerta -> id do alerta aberto
  }
}

function iniciar() {
  const agora = Date.now()
  db.vinherias = [
    { id: 'vin_demo', nome: 'Vinheria Demo', apikey: 'winedemo', vencimento: iso(agora + 30 * DIA), status: 'ativa', suspensaEm: null },
    { id: 'vin_santacruz', nome: 'Adega Santa Cruz', apikey: 'santacruz', vencimento: iso(agora + 12 * DIA), status: 'ativa', suspensaEm: null },
    { id: 'vin_vale', nome: 'Vale Dourado', apikey: 'valedourado', vencimento: iso(agora - 5 * DIA), status: 'suspensa', suspensaEm: agora - 4 * DIA },
  ]
  db.adegas = [
    { id: 'vin_demo/adega1', vinheriaId: 'vin_demo', servicepath: '/adega1', nome: 'Adega 1' },
    { id: 'vin_demo/adega2', vinheriaId: 'vin_demo', servicepath: '/adega2', nome: 'Adega 2' },
    { id: 'vin_santacruz/adega1', vinheriaId: 'vin_santacruz', servicepath: '/adega1', nome: 'Cave principal' },
    { id: 'vin_vale/adega1', vinheriaId: 'vin_vale', servicepath: '/adega1', nome: 'Adega 1' },
  ]
  const antigo = iso(agora - 30 * DIA)
  const lista = [
    { id: 'wgn001', vinheriaId: 'vin_demo', adegaId: 'vin_demo/adega1', nome: 'Adega principal', preset: 'guarda_geral', criadoEm: antigo },
    { id: 'wgn002', vinheriaId: 'vin_demo', adegaId: 'vin_demo/adega2', nome: 'Sala de espumantes', preset: 'espumante', criadoEm: antigo },
    { id: 'wgn003', vinheriaId: 'vin_santacruz', adegaId: 'vin_santacruz/adega1', nome: 'Cave de tintos', preset: 'longa_guarda', criadoEm: antigo },
    { id: 'wgn004', vinheriaId: 'vin_vale', adegaId: 'vin_vale/adega1', nome: 'Adega do vale', preset: 'guarda_geral', criadoEm: antigo },
  ]
  lista.forEach(registrarDispositivo)

  // Alguns alertas antigos, para a tela Alertas já ter histórico
  const atras = (min) => iso(agora - min * MIN)
  const semente = [
    ['wgn001', 'temperature', 'acima', 15.8, 15, 2 * 24 * 60 + 130, 2 * 24 * 60 + 92],
    ['wgn001', 'humidity', 'abaixo', 58.4, 60, 26 * 60, 25 * 60],
    ['wgn001', 'luminosity', 'acima', 34, 10, 9 * 60 + 12, 9 * 60],
    ['wgn001', 'estabilidade', null, 2.7, 2, 5 * 24 * 60, 5 * 24 * 60 - 95],
    ['wgn002', 'temperature', 'acima', 13.6, 13, 3 * 24 * 60 + 50, 3 * 24 * 60 + 20],
    ['wgn003', 'humidity', 'acima', 76.1, 75, 20 * 60, 18 * 60 + 40],
  ]
  for (const [deviceId, variavel, sentido, valor, limite, ini, fim] of semente) {
    const dev = db.dispositivos.find((x) => x.id === deviceId)
    db.alertas.push({
      id: db.proximoAlerta++, vinheriaId: dev.vinheriaId, deviceId, variavel, sentido, valor, limite,
      inicio: atras(ini), fim: atras(fim),
    })
  }
}
iniciar()

// ------------------------------------------------------------------ simulação das leituras
// Ruído repetível: o mesmo (semente, instante) sempre dá o mesmo número.
function ruido(semente, t, escala) {
  const x = Math.sin(semente * 12.9898 + Math.floor(t / 5000) * 78.233) * 43758.5453
  return (x - Math.floor(x) - 0.5) * 2 * escala
}

// Efeito de cada cenário sobre cada variável
function efeito(cenario, variavel, t) {
  switch (cenario) {
    case 'temp_alta': return variavel === 'temperature' ? 5.5 : 0
    case 'temp_baixa': return variavel === 'temperature' ? -5 : 0
    case 'umid_baixa': return variavel === 'humidity' ? -22 : 0
    case 'umid_alta': return variavel === 'humidity' ? 14 : 0
    case 'luz_alta': return variavel === 'luminosity' ? 30 : 0
    case 'instavel': return variavel === 'temperature' ? 2.6 * Math.sin((doisPi * t) / (40 * MIN)) : 0
    default: return 0
  }
}

/** Valor da variável no instante t (milissegundos). */
function valorEm(deviceId, variavel, t) {
  const s = db.sim[deviceId]
  let v = s.base[variavel]
  if (variavel === 'temperature') v += 0.6 * Math.sin((doisPi * t) / (6 * HORA)) + ruido(s.semente + 1, t, 0.12)
  if (variavel === 'humidity') v += 2.5 * Math.sin((doisPi * t) / (8 * HORA) + 1) + ruido(s.semente + 2, t, 0.5)
  if (variavel === 'luminosity') v += 1.2 * Math.abs(Math.sin((doisPi * t) / (3 * HORA))) + ruido(s.semente + 3, t, 0.4)
  if (t >= s.desde) v += efeito(s.cenario, variavel, t)
  if (variavel !== 'temperature') v = Math.min(100, Math.max(0, v))
  return v
}

const arredondar = (variavel, v) => {
  const casas = variavel === 'luminosity' ? 0 : 1
  return Number(v.toFixed(casas))
}

const dispositivo = (id) => db.dispositivos.find((d) => d.id === id)
const vinheria = (id) => db.vinherias.find((v) => v.id === id)
const aguardando = (d) => Date.now() - new Date(d.criadoEm).getTime() < 15000

/** Instante da última leitura que o Node chegou a enviar. */
function instanteUtil(deviceId) {
  const d = dispositivo(deviceId)
  const s = db.sim[deviceId]
  let limite = Date.now()
  const v = vinheria(d.vinheriaId)
  if (v.status === 'suspensa' && v.suspensaEm) limite = Math.min(limite, v.suspensaEm)
  if (s.cenario === 'offline') limite = Math.min(limite, s.desde)
  return limite
}

const estaOffline = (deviceId) => {
  const s = db.sim[deviceId]
  return s.cenario === 'offline' && Date.now() - s.desde > OFFLINE_APOS_MS
}

function serie(deviceId, variavel, ms, pontos, fim = instanteUtil(deviceId)) {
  const d = dispositivo(deviceId)
  const passo = ms / pontos
  const comeco = new Date(d.criadoEm).getTime() + 15000
  const saida = []
  for (let i = pontos - 1; i >= 0; i--) {
    const t = fim - i * passo
    if (t < comeco) continue
    saida.push({ t: iso(Math.round(t)), v: arredondar(variavel, valorEm(deviceId, variavel, t)) })
  }
  return saida
}

// ------------------------------------------------------------------ alertas
function abrirAlerta(deviceId, variavel, dados) {
  const d = dispositivo(deviceId)
  const alerta = {
    id: db.proximoAlerta++, vinheriaId: d.vinheriaId, deviceId, variavel,
    sentido: dados.sentido ?? null, valor: dados.valor ?? null, limite: dados.limite ?? null,
    inicio: iso(Date.now()), fim: null,
  }
  db.alertas.push(alerta)
  db.sim[deviceId].abertos[variavel] = alerta.id
}

function fecharAlerta(deviceId, variavel) {
  const s = db.sim[deviceId]
  const alerta = db.alertas.find((a) => a.id === s.abertos[variavel])
  if (alerta && !alerta.fim) alerta.fim = iso(Date.now())
  delete s.abertos[variavel]
}

/** Avalia o dispositivo agora: abre e fecha alertas (é o que o backend fará a cada 5 s). */
function avaliar(deviceId) {
  const d = dispositivo(deviceId)
  if (!d || aguardando(d)) return
  const s = db.sim[deviceId]
  const v = vinheria(d.vinheriaId)
  const trig = db.triggers[deviceId]

  // Node offline vira alerta (início e fim, como os outros)
  const offline = estaOffline(deviceId)
  if (offline && !s.abertos.offline) abrirAlerta(deviceId, 'offline', {})
  if (!offline && s.abertos.offline) fecharAlerta(deviceId, 'offline')

  // Sem leituras novas (suspenso ou offline): não há o que avaliar
  if (v.status === 'suspensa' || s.cenario === 'offline') return

  const t = Date.now()
  for (const variavel of LISTA_VARIAVEIS) {
    const faixa = trig[VARIAVEIS[variavel].chave]
    const valor = valorEm(deviceId, variavel, t)
    const antes = s.estados[variavel]
    const depois = avaliarVariavel(valor, faixa.min, faixa.max, HISTERESE[variavel], antes)
    if (depois === antes) continue
    if (antes !== NORMAL) fecharAlerta(deviceId, variavel)
    if (depois !== NORMAL) {
      abrirAlerta(deviceId, variavel, {
        sentido: depois === ACIMA ? 'acima' : 'abaixo',
        valor: arredondar(variavel, valor),
        limite: depois === ACIMA ? faixa.max : faixa.min,
      })
    }
    s.estados[variavel] = depois
  }

  // Estabilidade: variação de temperatura nas últimas 24 h (histerese de 20 %)
  const est = calcularEstabilidade(serie(deviceId, 'temperature', DIA, 96), trig.estabilidadeMax)
  const limite = trig.estabilidadeMax
  if (!s.estados.estabilidade && est.variacao > limite) {
    s.estados.estabilidade = true
    abrirAlerta(deviceId, 'estabilidade', { valor: Number(est.variacao.toFixed(1)), limite })
  } else if (s.estados.estabilidade && est.variacao <= limite * 0.8) {
    s.estados.estabilidade = false
    fecharAlerta(deviceId, 'estabilidade')
  }
}

function estadoDe(deviceId) {
  const d = dispositivo(deviceId)
  if (aguardando(d)) return 'aguardando'
  if (vinheria(d.vinheriaId).status === 'suspensa') return 'suspenso'
  if (estaOffline(deviceId)) return 'offline'
  const abertos = Object.keys(db.sim[deviceId].abertos).filter((k) => k !== 'offline')
  return abertos.length > 0 ? 'alerta' : 'ok'
}

/** Suspende automaticamente quem passou do vencimento. */
function verificarVencimentos() {
  for (const v of db.vinherias) {
    if (v.status === 'ativa' && new Date(v.vencimento).getTime() < Date.now()) suspender(v.id)
  }
}

function suspender(vinheriaId) {
  const v = vinheria(vinheriaId)
  v.status = 'suspensa'
  v.suspensaEm = Date.now()
  for (const d of db.dispositivos.filter((x) => x.vinheriaId === vinheriaId)) {
    for (const chave of Object.keys(db.sim[d.id].abertos)) fecharAlerta(d.id, chave) // o Node apaga LED e buzzer
    db.sim[d.id].estados = { temperature: NORMAL, humidity: NORMAL, luminosity: NORMAL, estabilidade: false }
  }
}

// ------------------------------------------------------------------ funções que a API usa
const copia = (x) => structuredClone(x)

export const mock = {
  // ---- vinherias
  listarVinherias() {
    verificarVencimentos()
    return copia(db.vinherias.map((v) => ({ ...v, dispositivos: db.dispositivos.filter((d) => d.vinheriaId === v.id).length })))
  },
  criarVinheria({ nome, vencimento }) {
    let id = idDaVinheria(nome)
    while (vinheria(id)) id += '_2'
    const nova = { id, nome, apikey: apikeyDaVinheria(id), vencimento: iso(vencimento ? new Date(vencimento).getTime() : Date.now() + 90 * 86400000), status: 'ativa', suspensaEm: null }
    db.vinherias.push(nova)
    db.adegas.push({ id: `${id}/adega1`, vinheriaId: id, servicepath: '/adega1', nome: 'Adega 1' })
    return copia(nova)
  },
  suspenderVinheria(id) { suspender(id); return { ok: true } },
  reativarVinheria(id) {
    const v = vinheria(id)
    v.status = 'ativa'
    v.suspensaEm = null
    if (new Date(v.vencimento).getTime() < Date.now()) v.vencimento = iso(Date.now() + 30 * DIA) // pagamento regularizado
    return { ok: true }
  },
  simularInadimplencia(id) {
    vinheria(id).vencimento = iso(Date.now() - DIA)
    suspender(id)
    return { ok: true }
  },

  // ---- adegas
  listarAdegas(vinheriaId) { return copia(db.adegas.filter((a) => a.vinheriaId === vinheriaId)) },

  // ---- dispositivos
  listarDispositivos(vinheriaId) { return copia(db.dispositivos.filter((d) => d.vinheriaId === vinheriaId)) },
  criarDispositivo({ vinheriaId, adegaId, novaAdega, nome, preset }) {
    let adega = db.adegas.find((a) => a.id === adegaId)
    if (novaAdega) {
      const n = db.adegas.filter((a) => a.vinheriaId === vinheriaId).length + 1
      adega = { id: `${vinheriaId}/adega${n}`, vinheriaId, servicepath: `/adega${n}`, nome: novaAdega }
      db.adegas.push(adega)
    }
    const id = proximoIdDispositivo(db.dispositivos)
    registrarDispositivo({ id, vinheriaId, adegaId: adega.id, nome, preset, criadoEm: iso(Date.now()) })
    const v = vinheria(vinheriaId)
    return copia({ dispositivo: dispositivo(id), config: { deviceId: id, apikey: v.apikey, nomeVinheria: v.nome, nomeAdega: adega.nome } })
  },
  atualizarDispositivo(id, { nome, adegaId }) {
    const d = dispositivo(id)
    if (nome) d.nome = nome
    if (adegaId) d.adegaId = adegaId
    return copia(d)
  },
  removerDispositivo(id) {
    db.dispositivos = db.dispositivos.filter((d) => d.id !== id)
    db.alertas = db.alertas.filter((a) => a.deviceId !== id)
    delete db.triggers[id]
    delete db.sim[id]
    return { ok: true }
  },
  obterResumo(vinheriaId) {
    verificarVencimentos()
    return db.dispositivos.filter((d) => d.vinheriaId === vinheriaId).map((d) => {
      avaliar(d.id)
      return copia({
        deviceId: d.id,
        estado: estadoDe(d.id),
        ultimaLeitura: aguardando(d) ? null : iso(instanteUtil(d.id)),
        alertasAtivos: db.alertas.filter((a) => a.deviceId === d.id && !a.fim && a.variavel !== 'offline').length,
      })
    })
  },

  // ---- leituras
  obterAtual(deviceId) {
    const d = dispositivo(deviceId)
    if (!d) throw new Error('Dispositivo não encontrado')
    avaliar(deviceId)
    const s = db.sim[deviceId]
    const base = { deviceId, estado: estadoDe(deviceId), muted: s.mudo ? 1 : 0, firmware: '2.0' }
    if (aguardando(d)) {
      return { ...base, temperature: null, humidity: null, luminosity: null, state: 'aguardando', online: false, rssi: null, ultimaLeitura: null }
    }
    const t = instanteUtil(deviceId)
    const estado = base.estado
    return copia({
      ...base,
      temperature: arredondar('temperature', valorEm(deviceId, 'temperature', t)),
      humidity: arredondar('humidity', valorEm(deviceId, 'humidity', t)),
      luminosity: arredondar('luminosity', valorEm(deviceId, 'luminosity', t)),
      state: estado === 'alerta' ? 'alerta' : estado === 'suspenso' ? 'suspenso' : 'ok',
      online: estado === 'ok' || estado === 'alerta',
      rssi: -62 - Math.round(Math.abs(ruido(s.semente, t, 12))),
      ultimaLeitura: iso(t),
    })
  },
  obterHistorico(deviceId, periodoId) {
    const periodo = PERIODOS.find((p) => p.id === periodoId) ?? PERIODOS[0]
    const fim = instanteUtil(deviceId) // o mesmo instante para as 3 séries
    return copia({
      deviceId,
      temperature: serie(deviceId, 'temperature', periodo.ms, periodo.pontos, fim),
      humidity: serie(deviceId, 'humidity', periodo.ms, periodo.pontos, fim),
      luminosity: serie(deviceId, 'luminosity', periodo.ms, periodo.pontos, fim),
    })
  },
  obterEstabilidade(deviceId) {
    const limite = db.triggers[deviceId].estabilidadeMax
    return copia({ deviceId, ...calcularEstabilidade(serie(deviceId, 'temperature', DIA, 96), limite), limite })
  },

  // ---- triggers
  obterTriggers(deviceId) { return copia(db.triggers[deviceId]) },
  salvarTriggers(deviceId, triggers) {
    db.triggers[deviceId] = copia(triggers)
    return { recebido: true, deviceId, em: iso(Date.now()) } // no sistema real: confirmação do Node (cmdexe)
  },

  // ---- alertas
  listarAlertas({ vinheriaId, deviceId, estado = 'todos' }) {
    db.dispositivos.filter((d) => d.vinheriaId === vinheriaId).forEach((d) => avaliar(d.id))
    return copia(
      db.alertas
        .filter((a) => a.vinheriaId === vinheriaId)
        .filter((a) => !deviceId || a.deviceId === deviceId)
        .filter((a) => estado === 'todos' || (estado === 'ativos' ? !a.fim : !!a.fim))
        .sort((a, b) => new Date(b.inicio) - new Date(a.inicio)),
    )
  },

  // ---- comandos
  enviarComando(deviceId, comando, valor) {
    const s = db.sim[deviceId]
    if (comando === 'mute') s.mudo = valor === '1'
    return { enviado: true, deviceId, comando, valor }
  },

  // ---- só no mock: escolher o cenário da simulação
  definirCenario(deviceId, cenario) {
    const s = db.sim[deviceId]
    s.cenario = cenario
    s.desde = Date.now()
    avaliar(deviceId)
    return { ok: true, cenario }
  },
  obterCenario(deviceId) { return db.sim[deviceId]?.cenario ?? 'normal' },
}

export const CENARIOS = [
  { id: 'normal', rotulo: 'Tudo normal' },
  { id: 'temp_alta', rotulo: 'Temperatura alta' },
  { id: 'temp_baixa', rotulo: 'Temperatura baixa' },
  { id: 'umid_baixa', rotulo: 'Umidade baixa' },
  { id: 'umid_alta', rotulo: 'Umidade alta' },
  { id: 'luz_alta', rotulo: 'Luz acesa' },
  { id: 'instavel', rotulo: 'Temperatura instável' },
  { id: 'offline', rotulo: 'Node offline' },
]

// "PRESETS" é usado só para conferir que o preset do dispositivo existe
export const presetExiste = (id) => id in PRESETS
