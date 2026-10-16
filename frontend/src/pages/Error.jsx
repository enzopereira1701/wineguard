import { Link } from 'react-router-dom'

/** Página não encontrada (rota "*"). */
export default function Error() {
  return (
    <div className="mx-auto max-w-xl px-4 py-20 text-center">
      <p className="numero text-6xl font-bold text-ouro-escuro">404</p>
      <h1 className="mt-2 text-3xl">Esta página não existe</h1>
      <p className="mt-2 text-suave">O endereço pode ter mudado ou estar escrito errado.</p>
      <Link to="/" className="mt-6 inline-block rounded-md bg-bordo px-5 py-2.5 text-sm font-bold text-papel hover:bg-bordo-escuro">
        Voltar ao início
      </Link>
    </div>
  )
}
