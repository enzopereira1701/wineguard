import Icone from './Icone'

const ESTILOS = {
  bloqueia: { caixa: 'border-alerta/40 bg-alerta/10 text-alerta', icone: 'fechar' },
  alerta: { caixa: 'border-alerta/40 bg-alerta/10 text-alerta', icone: 'alerta' },
  forte: { caixa: 'border-atencao/50 bg-atencao/10 text-tinta', icone: 'alerta' },
  leve: { caixa: 'border-linha bg-papel text-tinta', icone: 'info' },
  info: { caixa: 'border-linha bg-papel text-tinta', icone: 'info' },
  ok: { caixa: 'border-ok/40 bg-ok/10 text-ok', icone: 'check' },
}

/** Caixa de aviso com ícone. `nivel` escolhe a cor e o ícone. */
export default function Aviso({ nivel = 'info', titulo, children, className = '' }) {
  const e = ESTILOS[nivel] ?? ESTILOS.info
  return (
    <div role={nivel === 'bloqueia' || nivel === 'alerta' ? 'alert' : 'status'} className={`flex gap-2.5 rounded-md border px-3 py-2.5 text-sm ${e.caixa} ${className}`}>
      <Icone nome={e.icone} className="mt-0.5 size-4" />
      <div>
        {titulo && <p className="font-bold">{titulo}</p>}
        <div>{children}</div>
      </div>
    </div>
  )
}
