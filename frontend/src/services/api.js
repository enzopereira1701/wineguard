// ÚNICO lugar do site que "busca dados". Nenhuma tela chama fetch direto.
//
//   VITE_USE_MOCK=true  (padrão)  -> responde com os dados de mentira (services/mock.js)
//   VITE_USE_MOCK=false           -> chama o backend FastAPI em VITE_API_URL
//
// Para ligar o backend: troque o .env e confira, na tabela abaixo, se os caminhos
// batem com os do backend. Os formatos de resposta estão em docs/api-contrato.md.
import { mock } from './mock'

const USAR_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

/** Espera `ms` milissegundos (para o mock parecer uma chamada de rede). */
const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/** Chamada HTTP de verdade. Lança Error com mensagem clara quando algo dá errado. */
async function http(metodo, caminho, corpo) {
  let resposta
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method: metodo,
      headers: corpo ? { 'Content-Type': 'application/json' } : undefined,
      body: corpo ? JSON.stringify(corpo) : undefined,
    })
  } catch {
    throw new Error('Não foi possível falar com o servidor. Confira a internet e o endereço da API.')
  }
  if (!resposta.ok) {
    const detalhe = await resposta.json().catch(() => ({}))
    throw new Error(detalhe.detail ?? `O servidor respondeu com erro ${resposta.status}.`)
  }
  return resposta.json()
}

/**
 * Decide entre mock e backend.
 * @param {() => any} funcaoMock  roda no modo mock
 * @param {[string, string, any?]} requisicao  [método, caminho, corpo] no modo real
 * @param {number} [latencia]  atraso simulado do mock (ms)
 */
async function rota(funcaoMock, requisicao, latencia = 120) {
  if (USAR_MOCK) {
    await esperar(latencia)
    return funcaoMock()
  }
  return http(...requisicao)
}

export const usandoMock = USAR_MOCK

// ----------------------------------------------------- vinheria escolhida (modo real)
// As rotas por dispositivo precisam saber de qual vinheria ele é (cada vinheria é um service do FIWARE):
// o AppProvider chama definirVinheriaAtual() sempre que a escolha muda e o ?vinheriaId= é acrescentado aqui.
let vinheriaAtual = null
export const definirVinheriaAtual = (id) => {
  vinheriaAtual = id
}
const comVinheria = (caminho) =>
  vinheriaAtual ? `${caminho}${caminho.includes('?') ? '&' : '?'}vinheriaId=${encodeURIComponent(vinheriaAtual)}` : caminho

// ----------------------------------------------------------------- vinherias
export const listarVinherias = () => rota(() => mock.listarVinherias(), ['GET', '/api/vinherias'])
export const criarVinheria = (dados) => rota(() => mock.criarVinheria(dados), ['POST', '/api/vinherias', dados])
export const suspenderVinheria = (id) => rota(() => mock.suspenderVinheria(id), ['POST', `/api/vinherias/${id}/suspender`])
export const reativarVinheria = (id) => rota(() => mock.reativarVinheria(id), ['POST', `/api/vinherias/${id}/reativar`])
export const simularInadimplencia = (id) =>
  rota(() => mock.simularInadimplencia(id), ['POST', `/api/vinherias/${id}/simular-inadimplencia`])

// -------------------------------------------------------------------- adegas
export const listarAdegas = (vinheriaId) =>
  rota(() => mock.listarAdegas(vinheriaId), ['GET', `/api/vinherias/${vinheriaId}/adegas`])

// ------------------------------------------------------------- dispositivos
export const listarDispositivos = (vinheriaId) =>
  rota(() => mock.listarDispositivos(vinheriaId), ['GET', `/api/vinherias/${vinheriaId}/dispositivos`])
export const criarDispositivo = (dados) =>
  rota(() => mock.criarDispositivo(dados), ['POST', `/api/vinherias/${dados.vinheriaId}/dispositivos`, dados], 400)
export const atualizarDispositivo = (id, dados) =>
  rota(() => mock.atualizarDispositivo(id, dados), ['PATCH', comVinheria(`/api/dispositivos/${id}`), dados])
export const removerDispositivo = (id) =>
  rota(() => mock.removerDispositivo(id), ['DELETE', comVinheria(`/api/dispositivos/${id}`)], 300)
/** Estado de todos os dispositivos da vinheria (chips, cartões e selo do menu). */
export const obterResumo = (vinheriaId) =>
  rota(() => mock.obterResumo(vinheriaId), ['GET', `/api/vinherias/${vinheriaId}/resumo`], 60)

// ------------------------------------------------------------------ leituras
export const obterAtual = (deviceId) => rota(() => mock.obterAtual(deviceId), ['GET', comVinheria(`/api/dispositivos/${deviceId}/atual`)], 60)
export const obterHistorico = (deviceId, periodo) =>
  rota(() => mock.obterHistorico(deviceId, periodo), ['GET', comVinheria(`/api/dispositivos/${deviceId}/historico?periodo=${periodo}`)], 80)
export const obterEstabilidade = (deviceId) =>
  rota(() => mock.obterEstabilidade(deviceId), ['GET', comVinheria(`/api/dispositivos/${deviceId}/estabilidade`)], 40)

// ------------------------------------------------------------------ triggers
export const obterTriggers = (deviceId) => rota(() => mock.obterTriggers(deviceId), ['GET', comVinheria(`/api/dispositivos/${deviceId}/triggers`)])
/** Salva e envia ao Node. A resposta confirma o recebimento ({ recebido: true, em }). */
export const salvarTriggers = (deviceId, triggers) =>
  rota(() => mock.salvarTriggers(deviceId, triggers), ['PUT', comVinheria(`/api/dispositivos/${deviceId}/triggers`), triggers], 700)

// ------------------------------------------------------------------- alertas
export const listarAlertas = (filtros) =>
  rota(
    () => mock.listarAlertas(filtros),
    ['GET', `/api/vinherias/${filtros.vinheriaId}/alertas?${new URLSearchParams({ ...(filtros.deviceId && { deviceId: filtros.deviceId }), estado: filtros.estado ?? 'todos' })}`],
    80,
  )

// ------------------------------------------------------------------ comandos
/** Comandos do Node: mute ("1"/"0"), identify, suspend, resume... */
export const enviarComando = (deviceId, comando, valor = '') =>
  rota(() => mock.enviarComando(deviceId, comando, valor), ['POST', comVinheria(`/api/dispositivos/${deviceId}/comando`), { comando, valor }], 250)

// ---------------------------------------------------- só existem no modo mock
export const definirCenario = (deviceId, cenario) => mock.definirCenario(deviceId, cenario)
export const obterCenario = (deviceId) => mock.obterCenario(deviceId)
