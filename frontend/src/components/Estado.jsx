import Aviso from './Aviso'
import Botao from './Botao'
import Icone from './Icone'

/** Tela/área enquanto os dados chegam. */
export function Carregando({ texto = 'Carregando...' }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 py-16 text-suave">
      <span className="size-4 animate-spin rounded-full border-2 border-linha border-t-bordo" aria-hidden="true" />
      {texto}
    </div>
  )
}

/** Quando não há nada para mostrar: explica e convida a agir. */
export function Vazio({ icone = 'info', titulo, texto, acao }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-linha px-6 py-12 text-center">
      <Icone nome={icone} className="size-8 text-ouro-escuro" />
      <h3 className="text-lg">{titulo}</h3>
      {texto && <p className="max-w-md text-sm text-suave">{texto}</p>}
      {acao && <div className="mt-2">{acao}</div>}
    </div>
  )
}

/** Erro de carregamento, com botão para tentar de novo. */
export function Erro({ mensagem, aoTentar }) {
  return (
    <div className="mx-auto max-w-xl py-10">
      <Aviso nivel="alerta" titulo="Não foi possível carregar os dados">
        {mensagem}
      </Aviso>
      {aoTentar && (
        <div className="mt-3">
          <Botao variante="secundario" onClick={aoTentar}>Tentar de novo</Botao>
        </div>
      )}
    </div>
  )
}
