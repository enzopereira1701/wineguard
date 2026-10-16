import { useId } from 'react'

const ESTILO_CAMPO =
  'w-full rounded-md border border-linha bg-papel px-3 py-2 text-sm text-tinta placeholder:text-suave/70 focus:border-bordo disabled:bg-creme disabled:text-suave'

/** Campo de texto/número com rótulo, ajuda e mensagem de erro ligados pelo id (acessibilidade). */
export function Campo({ rotulo, ajuda, erro, className = '', ...input }) {
  const id = useId()
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-sm font-bold">{rotulo}</label>
      <input id={id} aria-invalid={!!erro} aria-describedby={ajuda || erro ? `${id}-d` : undefined} className={`${ESTILO_CAMPO} numero ${erro ? 'border-alerta' : ''}`} {...input} />
      {(ajuda || erro) && <p id={`${id}-d`} className={`mt-1 text-xs ${erro ? 'text-alerta' : 'text-suave'}`}>{erro ?? ajuda}</p>}
    </div>
  )
}

/** Lista de escolha (select) com rótulo. As <option> vão como filhos. */
export function CampoSelecao({ rotulo, className = '', children, semRotulo = false, ...select }) {
  const id = useId()
  return (
    <div className={className}>
      <label htmlFor={id} className={semRotulo ? 'sr-only' : 'mb-1 block text-sm font-bold'}>{rotulo}</label>
      <select id={id} className={ESTILO_CAMPO} {...select}>{children}</select>
    </div>
  )
}
