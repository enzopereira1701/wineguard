import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import Footer from './components/Footer'
import Header from './components/Header'
import Toasts from './components/Toasts'
import { useApp } from './hooks/useApp'
import Alertas from './pages/Alertas'
import Dispositivos from './pages/Dispositivos'
import Error from './pages/Error'
import Home from './pages/Home'
import Painel from './pages/Painel'
import Suspenso from './pages/Suspenso'
import Triggers from './pages/Triggers'
import Vinherias from './pages/Vinherias'

// Telas que continuam abertas mesmo com a vinheria suspensa (para poder reativar)
const ROTAS_LIVRES = ['/', '/vinherias']

/** Volta para o topo a cada troca de página. */
function RolarParaOTopo() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

/** Estrutura do site: menu no topo, a página da rota, rodapé e avisos. */
function App() {
  const { vinheria } = useApp()
  const { pathname } = useLocation()
  const bloqueada = vinheria?.status === 'suspensa' && !ROTAS_LIVRES.includes(pathname)

  return (
    <div className="flex min-h-screen flex-col bg-creme text-tinta">
      <RolarParaOTopo />
      <Header />
      <main className={`flex-1 ${pathname === '/' ? '' : 'pt-16 md:pt-20'}`}>
        {bloqueada ? (
          <Suspenso />
        ) : (
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/painel" element={<Painel />} />
            <Route path="/dispositivos" element={<Dispositivos />} />
            <Route path="/triggers" element={<Triggers />} />
            <Route path="/alertas" element={<Alertas />} />
            <Route path="/vinherias" element={<Vinherias />} />
            <Route path="*" element={<Error />} />
          </Routes>
        )}
      </main>
      <Footer />
      <Toasts />
    </div>
  )
}

export default App
