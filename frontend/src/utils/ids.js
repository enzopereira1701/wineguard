// Geração de identificadores no padrão do projeto.

/** Próximo device_id livre: wgn001, wgn002, ... */
export function proximoIdDispositivo(dispositivos) {
  const maior = dispositivos.reduce((acc, d) => {
    const n = Number(String(d.id).replace(/\D/g, ''))
    return Number.isFinite(n) && n > acc ? n : acc
  }, 0)
  return `wgn${String(maior + 1).padStart(3, '0')}`
}

/** "Adega Santa Cruz" -> "vin_adega_santa_cruz" (minúsculas, sem acento, com _). */
export function idDaVinheria(nome) {
  const limpo = nome
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return `vin_${limpo || 'nova'}`
}

/** apikey de uma vinheria: o nome sem "vin_" e sem "_" ("vin_santa_cruz" -> "santacruz"). */
export const apikeyDaVinheria = (id) => id.replace(/^vin_/, '').replace(/_/g, '')
