import { useEffect, useState } from 'react'

/**
 * Devolve "agora" (em ms) e atualiza a cada `intervaloMs`.
 * Serve para textos como "há 5 min" se atualizarem sozinhos.
 */
export function useAgora(intervaloMs = 10000) {
  const [agora, setAgora] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setAgora(Date.now()), intervaloMs)
    return () => clearInterval(id)
  }, [intervaloMs])
  return agora
}
