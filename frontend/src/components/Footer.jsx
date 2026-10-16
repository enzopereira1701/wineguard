import { Link } from 'react-router-dom'
import { ROTAS } from '../data/constantes'
import { EQUIPE, GRUPO } from '../data/equipe'
import { usandoMock } from '../services/api'

const REPO = 'https://github.com/enzopereira1701/wineguard'
const LINK = 'rounded text-creme underline-offset-4 hover:underline'
const TITULO = 'text-sm text-creme/70'

/**
 * Rodapé compacto: faixa vinho de ponta a ponta, na mesma coluna do resto do site.
 * Linha 1: quem fez. Linha 2: sobre, telas e projeto. Linha 3: avisos.
 */
export default function Footer() {
  return (
    <footer className="bg-bordo-escuro text-creme">
      <div className="mx-auto max-w-7xl px-4">
        <section aria-labelledby="titulo-quem-fez" className="flex flex-col gap-3 border-b border-creme/15 py-7 md:flex-row md:items-baseline md:gap-10">
          <h2 id="titulo-quem-fez" className="shrink-0 text-2xl">Quem fez</h2>
          <ul className="flex flex-wrap gap-x-8 gap-y-1 font-titulo text-lg">
            {EQUIPE.map((nome) => <li key={nome}>{nome}</li>)}
          </ul>
        </section>

        <div className="grid gap-8 py-8 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <p className="font-titulo text-xl font-semibold">wineguard</p>
            <p className="mt-2 max-w-xs text-sm text-creme/80">
              Monitoramento de temperatura, umidade e luz para adegas, com alerta na hora no aparelho e no painel.
            </p>
          </div>

          <nav aria-label="Rodapé">
            <p className={TITULO}>Telas</p>
            <ul className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <li><Link to="/" className={LINK}>Início</Link></li>
              {ROTAS.map((r) => <li key={r.caminho}><Link to={r.caminho} className={LINK}>{r.rotulo}</Link></li>)}
            </ul>
          </nav>

          <div>
            <p className={TITULO}>Projeto</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li><a className={LINK} href={REPO} target="_blank" rel="noreferrer">Código no GitHub</a></li>
              <li><a className={LINK} href={`${REPO}/tree/main/docs`} target="_blank" rel="noreferrer">Documentação</a></li>
            </ul>
          </div>
        </div>

        <div className="space-y-1 border-t border-creme/15 py-5 pb-24 text-xs text-creme/70 md:pb-5">
          <p>
            Projeto do grupo <strong className="text-creme">{GRUPO}</strong>, CP5 Vinheria Full. Plataforma FIWARE de código aberto, base do
            professor Fábio Henrique Cabrini. As referências de guarda são recomendações de especialistas, não uma norma oficial.
            Esta demonstração não tem login: qualquer pessoa com o link vê e altera as vinherias. As fotos do site foram geradas com IA.
          </p>
          {usandoMock && <p className="font-bold text-creme">Você está vendo dados de demonstração, gerados no navegador.</p>}
          <p>© 2026 {GRUPO}. Todos os direitos reservados.</p>
        </div>
      </div>
    </footer>
  )
}
