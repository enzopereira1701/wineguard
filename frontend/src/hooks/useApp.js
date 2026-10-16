import { useContext } from 'react'
import { AppContext } from '../context/AppContext'

/** Acesso ao estado global (vinheria, dispositivo selecionado, avisos...). */
export function useApp() {
  const contexto = useContext(AppContext)
  if (!contexto) throw new Error('useApp precisa estar dentro de <AppProvider>.')
  return contexto
}
