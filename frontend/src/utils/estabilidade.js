// Estabilidade da temperatura: o quanto ela variou num período (normalmente 24 h).
// As fontes apontam a variação como mais prejudicial do que um valor fixo um pouco fora do ideal.

/**
 * @param {{ t: string, v: number }[]} pontos  leituras de temperatura
 * @param {number} limite  variação máxima aceita (°C)
 * @returns {{ min: number|null, max: number|null, variacao: number, instavel: boolean }}
 */
export function calcularEstabilidade(pontos, limite) {
  if (!pontos || pontos.length === 0) {
    return { min: null, max: null, variacao: 0, instavel: false }
  }
  const valores = pontos.map((p) => p.v)
  const min = Math.min(...valores)
  const max = Math.max(...valores)
  const variacao = max - min
  return { min, max, variacao, instavel: variacao > limite }
}
