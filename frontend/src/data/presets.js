// Presets de GUARDA (não de servir). Os números de "alerta" são a adaptação do
// grupo a partir das fontes em data/fontes.js; "alvo" é onde a maioria concorda.
// A luz é em % RELATIVA (o LDR não mede em lux).

/**
 * @typedef {{ min: number, max: number }} Faixa
 * @typedef {{ id: string, nome: string, descricao: string,
 *             temp: Faixa, umid: Faixa, luz: Faixa,
 *             alvo: { temp: Faixa, umid: Faixa, luz: Faixa } }} Preset
 */

/** @type {Record<string, Preset>} */
export const PRESETS = {
  guarda_geral: {
    id: 'guarda_geral',
    nome: 'Guarda geral',
    descricao: 'Tinto, branco e rosé',
    temp: { min: 10, max: 15 },
    umid: { min: 60, max: 75 },
    luz: { min: 0, max: 10 },
    alvo: { temp: { min: 12, max: 14 }, umid: { min: 65, max: 70 }, luz: { min: 0, max: 10 } },
  },
  longa_guarda: {
    id: 'longa_guarda',
    nome: 'Longa guarda',
    descricao: 'Vinhos para envelhecer',
    temp: { min: 11, max: 14 },
    umid: { min: 65, max: 75 },
    luz: { min: 0, max: 5 },
    alvo: { temp: { min: 12, max: 13 }, umid: { min: 65, max: 70 }, luz: { min: 0, max: 5 } },
  },
  espumante: {
    id: 'espumante',
    nome: 'Espumante',
    descricao: 'Espumantes e champagne',
    temp: { min: 9, max: 13 },
    umid: { min: 65, max: 80 },
    luz: { min: 0, max: 5 },
    alvo: { temp: { min: 10, max: 12 }, umid: { min: 70, max: 80 }, luz: { min: 0, max: 5 } },
  },
}

export const LISTA_PRESETS = Object.values(PRESETS)
export const PRESET_PADRAO = 'guarda_geral'

/**
 * Monta os triggers iniciais de um preset (modo "referencia").
 * @param {string} presetId
 */
export function triggersDoPreset(presetId) {
  const p = PRESETS[presetId] ?? PRESETS[PRESET_PADRAO]
  return {
    preset: p.id,
    modo: 'referencia', // 'referencia' (valores do preset) ou 'personalizado'
    temp: { ...p.temp },
    umid: { ...p.umid },
    luz: { ...p.luz },
    estabilidadeMax: 2,
    luzEscuro: null, // valor medido ao calibrar a luz (ou null)
  }
}
