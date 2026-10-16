import { createContext } from 'react'

// O objeto de contexto fica em arquivo próprio (sem componentes) para o
// "react-refresh" do Vite continuar atualizando a tela sem recarregar.
export const AppContext = createContext(null)
