import { useApp } from '../hooks/useApp'
import Icone from './Icone'

const COR = { ok: 'border-ok/40 text-ok', erro: 'border-alerta/50 text-alerta', info: 'border-linha text-tinta' }
const ICONE = { ok: 'check', erro: 'alerta', info: 'info' }

/** Avisos rápidos no canto da tela ("Dispositivo cadastrado", "Erro ao salvar"...). */
export default function Toasts() {
  const { toasts, removerToast } = useApp()
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} role="status" className={`entrar pointer-events-auto flex max-w-md items-center gap-2 rounded-md border bg-papel px-4 py-2.5 text-sm font-bold ${COR[t.tipo] ?? COR.info}`}>
          <Icone nome={ICONE[t.tipo] ?? 'info'} className="size-4" />
          <span className="text-tinta">{t.mensagem}</span>
          <button type="button" onClick={() => removerToast(t.id)} aria-label="Dispensar aviso" className="ml-1 text-suave hover:text-bordo">
            <Icone nome="fechar" className="size-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
