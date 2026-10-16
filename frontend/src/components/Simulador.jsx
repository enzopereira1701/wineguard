import { useState } from 'react'
import { CENARIOS } from '../services/mock'
import { definirCenario, obterCenario, usandoMock } from '../services/api'

/**
 * Só aparece com dados de mentira. Escolhe o que o "sensor" simulado faz,
 * para testar alertas, estabilidade e Node offline durante o desenvolvimento e a demonstração.
 * Use <Simulador key={deviceId} .../> para reiniciar o estado ao trocar de dispositivo.
 */
export default function Simulador({ deviceId, aoMudar }) {
  const [cenario, setCenario] = useState(() => obterCenario(deviceId))
  if (!usandoMock) return null

  const escolher = (id) => {
    definirCenario(deviceId, id)
    setCenario(id)
    aoMudar?.(id)
  }

  return (
    <section className="rounded-md border border-dashed border-ouro p-4" aria-labelledby="titulo-simulador">
      <h2 id="titulo-simulador" className="text-lg">Simulador de sensor</h2>
      <p className="mb-3 text-sm text-suave">Os dados são de demonstração. Escolha um cenário e veja os alertas, o selo do menu e o histórico reagirem.</p>
      <div className="flex flex-wrap gap-2">
        {CENARIOS.map((c) => (
          <button
            key={c.id}
            type="button"
            aria-pressed={cenario === c.id}
            onClick={() => escolher(c.id)}
            className={`rounded-md border px-3 py-1.5 text-sm font-bold ${cenario === c.id ? 'border-bordo bg-bordo text-papel' : 'border-linha bg-papel text-tinta hover:border-bordo/60'}`}
          >
            {c.rotulo}
          </button>
        ))}
      </div>
    </section>
  )
}
