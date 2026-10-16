import { useState } from 'react'
import Botao from './Botao'

/** Caixa de código com botão "Copiar". Usada para o bloco do config.h do Node. */
export default function BlocoCopiar({ texto, rotulo = 'Copiar' }) {
  const [copiado, setCopiado] = useState(false)

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto)
    } catch {
      // alguns navegadores bloqueiam o clipboard: seleciona o texto para copiar à mão
      const area = document.createElement('textarea')
      area.value = texto
      document.body.appendChild(area)
      area.select()
      document.execCommand('copy')
      area.remove()
    }
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  return (
    <div className="rounded-md border border-linha bg-tinta text-papel">
      <pre className="overflow-x-auto p-4 text-xs leading-relaxed"><code>{texto}</code></pre>
      <div className="flex justify-end border-t border-papel/15 p-2">
        <Botao variante="neutro" tamanho="sm" icone={copiado ? 'check' : 'copiar'} onClick={copiar}>
          {copiado ? 'Copiado' : rotulo}
        </Botao>
      </div>
    </div>
  )
}
