// Validação dos triggers digitados pelo usuário.
// Níveis (do mais grave ao mais leve):
//   bloqueia - não deixa salvar
//   forte    - pede confirmação ("Esse limite pode permitir danos ao vinho")
//   leve     - mostra a referência ao lado, mas permite salvar
import { PRESETS, PRESET_PADRAO } from '../data/presets'
import { formatarNumero } from './formatacao'

export const NIVEL = { BLOQUEIA: 'bloqueia', FORTE: 'forte', LEVE: 'leve' }

const ROTULO = { temp: 'Temperatura', umid: 'Umidade', luz: 'Luminosidade' }
const UNIDADE = { temp: '°C', umid: '%', luz: '%' }
// Valores fisicamente impossíveis (ou fora do que o sensor mede)
const LIMITE_FISICO = { temp: [-20, 60], umid: [0, 100], luz: [0, 100] }

/**
 * @typedef {{ nivel: 'bloqueia'|'forte'|'leve', variavel: string, mensagem: string }} Aviso
 */

/**
 * Valida os triggers e devolve uma lista de avisos (lista vazia = tudo certo).
 * @param {ReturnType<import('../data/presets').triggersDoPreset>} triggers
 * @returns {Aviso[]}
 */
export function validarTriggers(triggers) {
  /** @type {Aviso[]} */
  const avisos = []
  const add = (nivel, variavel, mensagem) => avisos.push({ nivel, variavel, mensagem })
  const referencia = PRESETS[triggers.preset] ?? PRESETS[PRESET_PADRAO]

  for (const chave of ['temp', 'umid', 'luz']) {
    const { min, max } = triggers[chave]
    const un = UNIDADE[chave]
    const nome = ROTULO[chave]

    // 1) Bloqueia
    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      add(NIVEL.BLOQUEIA, chave, `${nome}: preencha o mínimo e o máximo.`)
      continue
    }
    const [lo, hi] = LIMITE_FISICO[chave]
    if (min < lo || max > hi) {
      add(NIVEL.BLOQUEIA, chave, `${nome}: use valores entre ${lo} e ${hi} ${un}.`)
      continue
    }
    if (min >= max) {
      add(NIVEL.BLOQUEIA, chave, `${nome}: o mínimo precisa ser menor que o máximo.`)
      continue
    }

    // 2) Forte (pode causar dano ao vinho)
    if (chave === 'temp' && max > 24) {
      add(NIVEL.FORTE, chave, 'Acima de 24 °C o vinho envelhece cedo demais.')
    }
    if (chave === 'temp' && min < 4) {
      add(NIVEL.FORTE, chave, 'Abaixo de 4 °C a evolução do vinho fica prejudicada.')
    }
    if (chave === 'umid' && max > 85) {
      add(NIVEL.FORTE, chave, 'Acima de 85 % de umidade os rótulos e as caixas podem se danificar.')
    }
    if (chave === 'umid' && min < 40) {
      add(NIVEL.FORTE, chave, 'Abaixo de 40 % de umidade as rolhas podem ressecar.')
    }

    // 3) Leve (só no modo personalizado: comparado à referência do preset)
    if (triggers.modo === 'personalizado') {
      const ref = referencia[chave]
      if (min < ref.min || max > ref.max) {
        add(
          NIVEL.LEVE,
          chave,
          `${nome}: sua faixa (${formatarNumero(min, 0)} a ${formatarNumero(max, 0)} ${un}) passa da referência ` +
            `(${ref.min} a ${ref.max} ${un}).`,
        )
      }
      if (max - min > 2 * (ref.max - ref.min)) {
        add(NIVEL.LEVE, chave, `${nome}: faixa muito larga, o alerta pode demorar a disparar.`)
      }
    }

    // 4) Faixa de temperatura estreita demais para a precisão do sensor
    if (chave === 'temp' && max - min < 1) {
      add(NIVEL.LEVE, chave, 'Faixa menor que 1 °C: o DHT22 tem margem de ±0,5 °C e pode gerar alertas falsos.')
    }
  }

  const est = triggers.estabilidadeMax
  if (!Number.isFinite(est) || est <= 0) {
    add(NIVEL.BLOQUEIA, 'estabilidade', 'Estabilidade: informe uma variação máxima maior que zero.')
  } else if (est > 5) {
    add(NIVEL.LEVE, 'estabilidade', 'Estabilidade: acima de 5 °C de variação o alerta quase nunca dispara.')
  }
  return avisos
}

/** true se algum aviso impede de salvar. */
export const temBloqueio = (avisos) => avisos.some((a) => a.nivel === NIVEL.BLOQUEIA)
/** true se algum aviso pede confirmação antes de salvar. */
export const temAvisoForte = (avisos) => avisos.some((a) => a.nivel === NIVEL.FORTE)
