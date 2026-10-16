// Junta as 3 séries do histórico (uma por variável) em uma lista só,
// no formato que o gráfico combinado precisa: [{ t, temperature, humidity, luminosity }].
//
// As 3 leituras de uma mesma mensagem do Node podem chegar com alguns milissegundos de
// diferença. Por isso a junção é por PROXIMIDADE de tempo (tolerância), e não por igualdade exata:
// sem isso o gráfico ganharia linhas duplicadas e a curva ficaria cheia de buracos.

const VARIAVEIS_SERIE = ['temperature', 'humidity', 'luminosity']

/**
 * @param {{ temperature?: {t:string,v:number}[], humidity?: {t:string,v:number}[], luminosity?: {t:string,v:number}[] }} historico
 * @param {number} [toleranciaMs=2000]  pontos mais próximos que isso entram na mesma linha
 */
export function mesclarSeries(historico, toleranciaMs = 2000, periodo) {
  // 1) todos os pontos, de todas as variáveis, em ordem de tempo
  const pontos = []
  for (const variavel of VARIAVEIS_SERIE) {
    for (const p of historico?.[variavel] ?? []) pontos.push({ variavel, t: p.t, ms: new Date(p.t).getTime(), v: p.v })
  }
  pontos.sort((a, b) => a.ms - b.ms)

  // 2) cada ponto entra na linha anterior se estiver perto e se aquela variável ainda não estiver nela
  const linhas = []
  let ultima = null
  for (const p of pontos) {
    if (ultima && p.ms - ultima.ms <= toleranciaMs && ultima.linha[p.variavel] === undefined) {
      ultima.linha[p.variavel] = p.v
    } else {
      ultima = { ms: p.ms, linha: { t: p.t, [p.variavel]: p.v } }
      linhas.push(ultima)
    }
  }
  const preenchidas = preencherBuracos(linhas.map((l) => l.linha), periodo)
  // leituras isoladas (sem vizinho dos dois lados) não formam linha: ganham um campo "<variavel>Ponto" para a bolinha
  return preenchidas.map((linha, i) => {
    const extra = {}
    for (const variavel of VARIAVEIS_SERIE) {
      if (linha[variavel] != null && preenchidas[i - 1]?.[variavel] == null && preenchidas[i + 1]?.[variavel] == null) {
        extra[`${variavel}Ponto`] = linha[variavel]
      }
    }
    return { ...linha, ...extra }
  })
}

// ---------------------------------------------------------------- lacunas do histórico
// A API devolve só os pontos que existem. Quando o Node ficou offline (ou a vinheria suspensa) há
// um buraco, e o gráfico ligaria os dois lados com uma reta, como se houvesse leitura. Aqui entram
// linhas VAZIAS (sem valor) nos horários que faltam: o Recharts quebra a linha nelas.
// Passo do histórico: 1 min na janela de 1 h; 1 h em 24 h e 7 d (igual ao agrupamento do backend).
const PASSO_MS = { '1h': 60_000, '24h': 3_600_000, '7d': 3_600_000 }

/**
 * @param {{ t: string }[]} linhas  em ordem de tempo
 * @param {string} [periodo]  '1h' | '24h' | '7d' (sem período, não preenche nada)
 * @param {(t: string) => object} criarVazia  cria a linha vazia de um horário
 */
function preencherBuracos(linhas, periodo, criarVazia = (t) => ({ t })) {
  const passo = PASSO_MS[periodo]
  if (!passo) return linhas
  const saida = []
  linhas.forEach((linha, i) => {
    saida.push(linha)
    const proxima = linhas[i + 1]
    if (!proxima) return
    const de = new Date(linha.t).getTime()
    const ate = new Date(proxima.t).getTime()
    if (ate - de <= passo * 1.5) return // intervalo normal
    for (let ms = de + passo; ms < ate - passo / 2; ms += passo) saida.push(criarVazia(new Date(ms).toISOString()))
  })
  return saida
}

/** Converte [{t, v}] em [{ t, valor }] para um gráfico de uma variável. */
export function paraGrafico(serie = [], periodo) {
  const cheia = preencherBuracos(
    serie.map((p) => ({ t: p.t, valor: p.v })),
    periodo,
    (t) => ({ t, valor: null }),
  )
  // leitura isolada (sem vizinho dos dois lados) não forma linha: ganha "ponto" para o gráfico desenhar uma bolinha
  return cheia.map((p, i) =>
    p.valor !== null && cheia[i - 1]?.valor == null && cheia[i + 1]?.valor == null ? { ...p, ponto: p.valor } : p,
  )
}
