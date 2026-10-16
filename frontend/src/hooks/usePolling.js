import { useEffect, useRef } from 'react'

/**
 * Repete uma função assíncrona a cada `intervaloMs` (e roda uma vez já na entrada).
 * Usado para atualizar o painel "ao vivo".
 *
 * @param {(aindaVale: () => boolean) => Promise<void>} funcao
 *        recebe `aindaVale()`: devolve false se a tela já saiu ou a chave mudou.
 *        Use antes de gravar no estado, para não gravar um resultado "velho".
 * @param {number} intervaloMs
 * @param {string|number|null} chave  quando muda, a repetição recomeça (ex.: id do dispositivo)
 * @param {boolean} [ativo=true]  false pausa a repetição
 */
export function usePolling(funcao, intervaloMs, chave, ativo = true) {
  const ultimaFuncao = useRef(funcao)

  // guarda sempre a versão mais nova da função, sem reiniciar o intervalo
  useEffect(() => {
    ultimaFuncao.current = funcao
  })

  useEffect(() => {
    if (!ativo || chave === null || chave === undefined) return undefined
    let vivo = true
    const rodar = async () => {
      try {
        await ultimaFuncao.current(() => vivo)
      } catch {
        // cada tela trata seus erros dentro da própria função
      }
    }
    rodar()
    const id = setInterval(rodar, intervaloMs)
    return () => {
      vivo = false
      clearInterval(id)
    }
  }, [intervaloMs, chave, ativo])
}
