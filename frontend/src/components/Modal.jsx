import { useEffect, useId, useRef } from 'react'
import Icone from './Icone'

/**
 * Janela por cima da página. Fecha com Esc ou clicando fora.
 * @param {{ aberto: boolean, titulo: string, onFechar: () => void, rodape?: React.ReactNode,
 *           largura?: string, children: React.ReactNode }} props
 */
export default function Modal({ aberto, titulo, onFechar, rodape, largura = 'max-w-lg', children }) {
  const idTitulo = useId()
  const caixa = useRef(null)
  // onFechar costuma ser uma função nova a cada render; guardar na ref evita refazer o efeito
  // (e devolver o foco ao primeiro campo) a cada letra digitada
  const fechar = useRef(onFechar)
  fechar.current = onFechar

  useEffect(() => {
    if (!aberto) return undefined
    const aoTeclar = (e) => e.key === 'Escape' && fechar.current()
    document.addEventListener('keydown', aoTeclar)
    // leva o foco para dentro da janela (primeiro campo ou botão), só ao abrir
    caixa.current?.querySelector('input, select, textarea, button:not([data-fechar])')?.focus()
    return () => document.removeEventListener('keydown', aoTeclar)
  }, [aberto])

  if (!aberto) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/50 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onFechar()}>
      <div ref={caixa} role="dialog" aria-modal="true" aria-labelledby={idTitulo} className={`entrar flex max-h-[90vh] w-full flex-col rounded-t-xl border border-linha bg-papel sm:rounded-lg ${largura}`}>
        <div className="flex items-start justify-between gap-4 border-b border-linha px-5 py-4">
          <h2 id={idTitulo} className="text-xl">{titulo}</h2>
          <button type="button" data-fechar onClick={onFechar} aria-label="Fechar janela" className="rounded p-1 text-suave hover:bg-bordo/10 hover:text-bordo">
            <Icone nome="fechar" />
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {rodape && <div className="flex flex-wrap justify-end gap-2 border-t border-linha px-5 py-3">{rodape}</div>}
      </div>
    </div>
  )
}
