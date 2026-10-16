import { Link } from 'react-router-dom'
import Icone from '../components/Icone'
import { useApp } from '../hooks/useApp'
import { formatarData } from '../utils/formatacao'

/** Aviso que substitui o painel quando a vinheria escolhida está suspensa. */
export default function Suspenso() {
  const { vinheria } = useApp()
  // só diz "vencida" se o vencimento já passou (a suspensão também pode ser manual)
  const vencida = Boolean(vinheria?.vencimento) && new Date(vinheria.vencimento) <= new Date()
  return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center">
      <Icone nome="escudo" className="mx-auto size-14 text-atencao" />
      <h1 className="mt-4 text-3xl">Serviço WineGuard suspenso</h1>
      <p className="mt-3 text-tinta">
        {vencida ? (
          <>
            A vinheria <strong>{vinheria?.nome}</strong> está com a mensalidade vencida desde{' '}
            <span className="numero">{formatarData(vinheria.vencimento)}</span>.
          </>
        ) : (
          <>
            A vinheria <strong>{vinheria?.nome}</strong> foi suspensa
            {vinheria?.suspensaEm ? <> em <span className="numero">{formatarData(vinheria.suspensaEm)}</span></> : null}.
          </>
        )}{' '}
        Os Nodes estão em espera e não enviam leituras nem alertas.
      </p>
      <p className="mt-2 text-sm text-suave">O histórico está preservado. Quando o pagamento for regularizado, o serviço volta ao normal.</p>
      <Link to="/vinherias" className="mt-6 inline-block rounded-md bg-bordo px-5 py-2.5 text-sm font-bold text-papel hover:bg-bordo-escuro">
        Ir para Vinherias
      </Link>
    </div>
  )
}
