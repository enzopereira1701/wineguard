// Funções de formatação (texto para a tela). Todas são "puras": mesma entrada, mesma saída.
import { VARIAVEIS } from '../data/constantes'

/**
 * Formata um número no padrão brasileiro (vírgula decimal).
 * @param {number|null|undefined} valor
 * @param {number} [decimais=1]
 * @returns {string} Ex.: 14,3  ou  "--" quando não há valor
 */
export const formatarNumero = (valor, decimais = 1) =>
  valor === null || valor === undefined || Number.isNaN(Number(valor))
    ? '--'
    : Number(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: decimais,
        maximumFractionDigits: decimais,
      })

/**
 * Número + unidade da variável.  formatarValor('temperature', 14.26) -> "14,3 °C"
 * @param {import('../data/constantes').Variavel} variavel
 * @param {number|null|undefined} valor
 */
export const formatarValor = (variavel, valor) => {
  const info = VARIAVEIS[variavel]
  return `${formatarNumero(valor, info.decimais)} ${info.unidade}`
}

/** "14:35" a partir de uma data ISO. */
export const formatarHora = (iso) =>
  new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })

/** "04/10 14:35" a partir de uma data ISO. */
export const formatarDataHora = (iso) => {
  const d = new Date(iso)
  const dia = d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  return `${dia} ${formatarHora(iso)}`
}

/** "04/10/2026" a partir de uma data ISO (só a data). */
export const formatarData = (iso) => new Date(iso).toLocaleDateString('pt-BR')

/** Texto do eixo X do gráfico: só a hora (1 h e 24 h) ou dia + hora (7 dias). */
export const formatarEixoTempo = (iso, periodoId) =>
  periodoId === '7d' ? formatarDataHora(iso) : formatarHora(iso)

/**
 * Duração legível.  formatarDuracao(125000) -> "2 min" ;  7_800_000 -> "2 h 10 min"
 * @param {number} ms
 */
export const formatarDuracao = (ms) => {
  const seg = Math.max(0, Math.round(ms / 1000))
  if (seg < 60) return `${seg} s`
  const min = Math.floor(seg / 60)
  if (min < 60) return `${min} min`
  const horas = Math.floor(min / 60)
  if (horas < 24) return `${horas} h ${String(min % 60).padStart(2, '0')} min`
  return `${Math.floor(horas / 24)} d ${horas % 24} h`
}

/**
 * "agora", "há 40 s", "há 5 min", "há 3 h" ...
 * @param {string|null|undefined} iso
 * @param {number} agora  Date.now() vindo de fora (assim a função continua pura)
 */
export const tempoRelativo = (iso, agora) => {
  if (!iso) return 'sem leituras'
  const dif = agora - new Date(iso).getTime()
  if (dif < 5000) return 'agora'
  if (dif < 60000) return `há ${Math.round(dif / 1000)} s`
  if (dif < 3600000) return `há ${Math.round(dif / 60000)} min`
  if (dif < 86400000) return `há ${Math.round(dif / 3600000)} h`
  return `há ${Math.round(dif / 86400000)} d`
}

/**
 * Dias de calendário entre hoje e uma data (negativo = já passou; -1 = ontem).
 * Compara o DIA, não as horas: assim "venceu ontem" não vira "vence hoje" por alguns minutos de diferença.
 */
export const diasAte = (iso, agora) => {
  const dia = (ms) => {
    const d = new Date(ms)
    return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())
  }
  return Math.round((dia(new Date(iso).getTime()) - dia(agora)) / 86400000)
}
