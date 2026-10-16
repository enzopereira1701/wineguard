import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { VARIAVEIS } from '../data/constantes'
import { formatarDataHora, formatarEixoTempo, formatarNumero, formatarValor } from '../utils/formatacao'
import { paraGrafico } from '../utils/series'

const COR_LIMITE = '#8a6a2f'

/**
 * Gráfico de linha de UMA variável, com:
 *  - faixa de referência (alvo) sombreada
 *  - limites (triggers) em linhas tracejadas
 *
 * @param {{ variavel: import('../data/constantes').Variavel, dados: {t:string,v:number}[],
 *           faixa?: {min:number,max:number}, alvo?: {min:number,max:number}, periodo: string }} props
 */
export default function GraficoVariavel({ variavel, dados, faixa, alvo, periodo }) {
  const info = VARIAVEIS[variavel]
  const serie = paraGrafico(dados, periodo)

  // eixo Y: cobre os dados E os limites, com uma folga
  const valores = serie.map((p) => p.valor).filter((v) => v !== null) // ignora os vazios das lacunas
  const limites = faixa ? [faixa.min, faixa.max] : []
  const baixo = Math.min(...valores, ...limites)
  const alto = Math.max(...valores, ...limites)
  const folga = Math.max((alto - baixo) * 0.12, 1)
  const dominio = [Math.floor(baixo - folga), Math.ceil(alto + folga)]

  return (
    <figure className="rounded-md border border-linha bg-papel p-4">
      <figcaption className="mb-3 flex items-baseline justify-between gap-2">
        <span className="font-titulo text-lg" style={{ color: info.cor }}>{info.rotulo}</span>
        {faixa && <span className="numero text-xs text-suave">limites {formatarNumero(faixa.min, 0)} a {formatarNumero(faixa.max, 0)} {info.unidade}</span>}
      </figcaption>
      {valores.length === 0 ? (
        <p className="grid h-56 place-items-center text-sm text-suave">Sem leituras neste período.</p>
      ) : (
        <div className="h-56 w-full" role="img" aria-label={`Gráfico de ${info.rotulo}`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={serie} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
              <CartesianGrid stroke="#d9cfc1" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="t" tickFormatter={(t) => formatarEixoTempo(t, periodo)} tick={{ fontSize: 11, fill: '#6e5f55' }} minTickGap={40} stroke="#d9cfc1" padding={{ left: 12, right: 12 }} />
              <YAxis domain={dominio} tick={{ fontSize: 11, fill: '#6e5f55' }} stroke="#d9cfc1" width={44} />
              <Tooltip
                labelFormatter={(t) => formatarDataHora(t)}
                formatter={(v) => [v == null ? 'sem leitura' : formatarValor(variavel, v), info.rotulo]}
                contentStyle={{ background: '#fbf8f3', border: '1px solid #d9cfc1', borderRadius: 6, fontSize: 12 }}
              />
              {alvo && <ReferenceArea y1={alvo.min} y2={alvo.max} fill={info.cor} fillOpacity={0.12} />}
              {faixa && <ReferenceLine y={faixa.min} stroke={COR_LIMITE} strokeDasharray="5 4" />}
              {faixa && <ReferenceLine y={faixa.max} stroke={COR_LIMITE} strokeDasharray="5 4" />}
              <Line type="monotone" dataKey="valor" stroke={info.cor} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
              {/* leituras isoladas (com buraco dos dois lados) não formam linha: aparecem como bolinha */}
              <Line dataKey="ponto" stroke="none" dot={{ r: 3, fill: info.cor, stroke: info.cor }} activeDot={false} isAnimationActive={false} tooltipType="none" legendType="none" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  )
}
