const COR = {
  ok: 'bg-ok',
  alerta: 'bg-alerta respirar',
  offline: 'bg-suave',
  suspenso: 'bg-atencao',
  aguardando: 'bg-linha',
}

/** Bolinha colorida do estado do dispositivo (decorativa: o texto vem ao lado). */
export default function StatusDot({ estado = 'aguardando', className = '' }) {
  return <span aria-hidden="true" className={`inline-block size-2.5 shrink-0 rounded-full ${COR[estado] ?? COR.aguardando} ${className}`} />
}
