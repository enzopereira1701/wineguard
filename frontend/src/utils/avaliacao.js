// Avaliação de uma leitura contra os triggers.
// É a MESMA regra do firmware do Node (e do backend FastAPI): serve de referência
// para portar para Python depois.

/** Estado de uma variável: 0 = normal, 1 = acima, 2 = abaixo. */
export const NORMAL = 0
export const ACIMA = 1
export const ABAIXO = 2

/**
 * Avalia uma leitura com histerese (evita o alerta ligar e desligar em cima do limite).
 * - Normal: passa a "acima" se valor > max, ou "abaixo" se valor < min.
 * - Acima: só volta ao normal quando valor <= max - histerese.
 * - Abaixo: só volta ao normal quando valor >= min + histerese.
 *
 * @param {number} valor
 * @param {number} min
 * @param {number} max
 * @param {number} histerese
 * @param {0|1|2} [estadoAtual=0]
 * @returns {0|1|2}
 */
export function avaliarVariavel(valor, min, max, histerese, estadoAtual = NORMAL) {
  if (estadoAtual === NORMAL) {
    if (valor > max) return ACIMA
    if (valor < min) return ABAIXO
    return NORMAL
  }
  if (estadoAtual === ACIMA) return valor <= max - histerese ? NORMAL : ACIMA
  return valor >= min + histerese ? NORMAL : ABAIXO
}

/**
 * Versão simples (sem histerese) para só PINTAR o cartão na tela.
 * @returns {'normal'|'acima'|'abaixo'|'sem-dado'}
 */
export function statusSimples(valor, min, max) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return 'sem-dado'
  if (valor > max) return 'acima'
  if (valor < min) return 'abaixo'
  return 'normal'
}
