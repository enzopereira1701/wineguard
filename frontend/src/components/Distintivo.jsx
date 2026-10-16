import Icone from './Icone'

const TONS = {
  ok: 'bg-ok/10 text-ok',
  alerta: 'bg-alerta/10 text-alerta',
  atencao: 'bg-atencao/15 text-atencao',
  neutro: 'bg-suave/10 text-suave',
  marca: 'bg-bordo/10 text-bordo',
}

/** Selo pequeno com texto (e ícone opcional). Nunca depende só da cor: sempre tem texto. */
export default function Distintivo({ tom = 'neutro', icone, children, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${TONS[tom]} ${className}`}>
      {icone && <Icone nome={icone} className="size-3.5" />}
      {children}
    </span>
  )
}
