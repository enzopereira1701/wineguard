import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { VARIAVEIS } from '../data/constantes'
import { formatarDataHora, formatarEixoTempo, formatarValor } from '../utils/formatacao'
import { mesclarSeries } from '../utils/series'

/**
 * As 3 variáveis juntas. Escalas muito diferentes, então são DOIS eixos:
 * temperatura em °C (esquerda) e umidade e luz em % (direita, de 0 a 100).
 */
export default function GraficoCombinado({ historico, periodo }) {
  const dados = mesclarSeries(historico, 2000, periodo)
  const { temperature: t, humidity: h, luminosity: l } = VARIAVEIS

  return (
    <figure className="rounded-md border border-linha bg-papel p-4">
      <figcaption className="mb-3 font-titulo text-lg">As três variáveis juntas</figcaption>
      {dados.length === 0 ? (
        <p className="grid h-72 place-items-center text-sm text-suave">Sem leituras neste período.</p>
      ) : (
        <div className="h-72 w-full" role="img" aria-label="Gráfico combinado de temperatura, umidade e luminosidade">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dados} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
              <CartesianGrid stroke="#d9cfc1" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="t" tickFormatter={(x) => formatarEixoTempo(x, periodo)} tick={{ fontSize: 11, fill: '#6e5f55' }} minTickGap={40} stroke="#d9cfc1" padding={{ left: 12, right: 12 }} />
              <YAxis yAxisId="c" orientation="left" domain={[(min) => Math.floor(min - 1), (max) => Math.ceil(max + 1)]} tickFormatter={(v) => `${v}°`} tick={{ fontSize: 11, fill: t.cor }} stroke="#d9cfc1" width={44} />
              <YAxis yAxisId="p" orientation="right" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: '#6e5f55' }} stroke="#d9cfc1" width={44} />
              <Tooltip
                labelFormatter={(x) => formatarDataHora(x)}
                formatter={(v, nome) => [v == null ? 'sem leitura' : formatarValor(nome, v), VARIAVEIS[nome]?.rotulo ?? nome]}
                contentStyle={{ background: '#fbf8f3', border: '1px solid #d9cfc1', borderRadius: 6, fontSize: 12 }}
              />
              <Legend formatter={(nome) => VARIAVEIS[nome]?.rotulo ?? nome} />
              <Line yAxisId="c" type="monotone" dataKey="temperature" stroke={t.cor} strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line yAxisId="c" dataKey="temperaturePonto" stroke="none" dot={{ r: 3, fill: t.cor, stroke: t.cor }} activeDot={false} isAnimationActive={false} tooltipType="none" legendType="none" />
              <Line yAxisId="p" dataKey="humidityPonto" stroke="none" dot={{ r: 3, fill: h.cor, stroke: h.cor }} activeDot={false} isAnimationActive={false} tooltipType="none" legendType="none" />
              <Line yAxisId="p" dataKey="luminosityPonto" stroke="none" dot={{ r: 3, fill: l.cor, stroke: l.cor }} activeDot={false} isAnimationActive={false} tooltipType="none" legendType="none" />
              <Line yAxisId="p" type="monotone" dataKey="humidity" stroke={h.cor} strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line yAxisId="p" type="monotone" dataKey="luminosity" stroke={l.cor} strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  )
}
