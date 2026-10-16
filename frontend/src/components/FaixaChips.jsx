import { Link } from 'react-router-dom'
import { ESTADOS } from '../data/constantes'
import { useApp } from '../hooks/useApp'
import Icone from './Icone'
import StatusDot from './StatusDot'

/**
 * Faixa fina com TODOS os dispositivos da vinheria. O painel mostra um por vez;
 * aqui o usuário vê que existem outros (e se algum está em alerta) e troca com um clique.
 */
export default function FaixaChips() {
  const { dispositivos, deviceId, selecionarDispositivo, resumo } = useApp()

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1" aria-label="Dispositivos da vinheria">
      {dispositivos.map((d) => {
        const estado = resumo[d.id]?.estado ?? 'aguardando'
        const escolhido = d.id === deviceId
        return (
          <button
            key={d.id}
            type="button"
            aria-pressed={escolhido}
            onClick={() => selecionarDispositivo(d.id)}
            className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-bold transition-colors ${
              escolhido ? 'border-bordo bg-papel text-bordo' : 'border-linha text-suave hover:border-bordo/60 hover:text-bordo'
            }`}
          >
            <StatusDot estado={estado} />
            {d.nome}
            <span className="sr-only">: {ESTADOS[estado].rotulo}</span>
          </button>
        )
      })}
      <Link
        to="/dispositivos?novo=1"
        className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-dashed border-linha px-3 py-1.5 text-sm font-bold text-suave hover:border-bordo hover:text-bordo"
      >
        <Icone nome="mais" className="size-4" />
        Adicionar dispositivo
      </Link>
    </div>
  )
}
