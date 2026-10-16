import { Link, NavLink } from 'react-router-dom'
import { ROTAS } from '../data/constantes'
import { useApp } from '../hooks/useApp'
import { CampoSelecao } from './Campo'
import Distintivo from './Distintivo'
import Icone from './Icone'

/**
 * Selo vermelho com o número de alertas ativos (só aparece se houver).
 * `emLinha`: fica AO LADO do texto (menu do computador). Sem ele, fica sobre o canto do ícone (barra do celular).
 */
function SeloAlertas({ quantidade, emLinha = false }) {
  if (!quantidade) return null
  const posicao = emLinha ? '' : 'absolute -right-3 -top-1'
  return (
    <span className={`${posicao} grid min-w-5 place-items-center rounded-full bg-alerta px-1 text-[11px] font-bold leading-5 text-papel ring-2 ring-papel/80`}>
      <span className="sr-only">Alertas ativos: </span>
      {quantidade}
    </span>
  )
}

/** Marca: círculo branco com o símbolo + nome (leva para o Início). */
function Marca() {
  return (
    <Link to="/" aria-label="WineGuard, página inicial" className="flex items-center gap-3">
      <span className="grid size-10 shrink-0 place-items-center rounded-full bg-creme md:size-12">
        <img src="/wineguard-simbolo-compacto.svg" alt="" className="h-6 w-auto md:h-7" />
      </span>
      <span className="font-titulo text-2xl font-semibold leading-none tracking-tight text-creme md:hidden md:text-3xl lg:inline">wineguard</span>
    </Link>
  )
}

/**
 * Navegação em barra de ponta a ponta, vinho e meio translúcida.
 * Ao passar o mouse, o item vira uma pílula branca. No celular, os atalhos ficam
 * numa barra embaixo (mais fácil de alcançar com o polegar).
 */
export default function Header() {
  const { vinherias, vinheria, vinheriaId, selecionarVinheria, alertasAtivos } = useApp()

  const classeTopo = ({ isActive }) =>
    `inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-base font-bold transition-colors duration-200 hover:bg-creme hover:text-bordo focus-visible:bg-creme focus-visible:text-bordo ${
      isActive ? 'bg-creme/20 text-creme' : 'text-creme'
    }`
  const classeBase = ({ isActive }) =>
    `relative flex flex-1 flex-col items-center gap-0.5 rounded-full py-2 text-[11px] font-bold transition-colors ${isActive ? 'bg-creme text-bordo' : 'text-creme'}`

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 border-b border-creme/10 bg-bordo/85 shadow-[0_8px_24px_-12px_rgb(74_18_32/0.6)] backdrop-blur-md">
        <div className="mx-auto flex h-16 w-full max-w-7xl md:h-20 items-center justify-between gap-6 px-4">
          <Marca />

          <div className="flex items-center gap-2">
            <nav aria-label="Principal" className="hidden items-center gap-1 md:flex">
              {ROTAS.map((rota) => (
                <NavLink key={rota.caminho} to={rota.caminho} className={classeTopo}>
                  {rota.rotulo}
                  {rota.caminho === '/alertas' && <SeloAlertas quantidade={alertasAtivos} emLinha />}
                </NavLink>
              ))}
            </nav>

            <div className="hidden items-center gap-2 pl-4 lg:flex">
              {vinheria?.status === 'suspensa' && <Distintivo tom="atencao">Suspensa</Distintivo>}
              <CampoSelecao
                rotulo="Vinheria"
                semRotulo
                value={vinheriaId ?? ''}
                onChange={(e) => selecionarVinheria(e.target.value)}
                className="w-52 [&_select]:rounded-full [&_select]:border-0 [&_select]:bg-creme [&_select]:py-2.5 [&_select]:text-base [&_select]:font-bold [&_select]:text-bordo"
              >
                {vinherias.map((v) => <option key={v.id} value={v.id}>{v.nome}</option>)}
              </CampoSelecao>
            </div>
          </div>
        </div>
      </header>

      <nav aria-label="Atalhos" className="fixed inset-x-0 bottom-0 z-40 flex gap-1 border-t border-creme/10 bg-bordo/90 p-1.5 backdrop-blur-md md:hidden">
        {ROTAS.map((rota) => (
          <NavLink key={rota.caminho} to={rota.caminho} className={classeBase}>
            <span className="relative">
              <Icone nome={rota.icone} />
              {rota.caminho === '/alertas' && <SeloAlertas quantidade={alertasAtivos} />}
            </span>
            {rota.rotulo}
          </NavLink>
        ))}
      </nav>
    </>
  )
}
