import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { AppContext } from './AppContext'
import { INTERVALO_ATUALIZACAO_MS } from '../data/constantes'
import { usePolling } from '../hooks/usePolling'
import * as api from '../services/api'

/**
 * Estado que várias telas usam ao mesmo tempo:
 * vinherias, vinheria/adega/dispositivo escolhidos, estado de cada dispositivo
 * (para os chips e o selo de alertas) e os avisos (toasts).
 */
export function AppProvider({ children }) {
  const [vinherias, setVinherias] = useState([])
  const [adegas, setAdegas] = useState([])
  const [dispositivos, setDispositivos] = useState([])
  const [resumo, setResumo] = useState({}) // deviceId -> { estado, ultimaLeitura, alertasAtivos }
  const [vinheriaId, setVinheriaId] = useState(null)
  const [adegaId, setAdegaId] = useState('todas')
  const [deviceId, setDeviceId] = useState(null)
  const [carregandoVinherias, setCarregandoVinherias] = useState(true)
  const [dispositivosDe, setDispositivosDe] = useState(null) // vinheria cujos dispositivos já chegaram
  const [erro, setErro] = useState(null)
  const [toasts, setToasts] = useState([])

  // Diz à camada de dados qual vinheria está escolhida: as rotas por dispositivo
  // (/api/dispositivos/wgn004/...) levam ?vinheriaId=. Layout effect: roda antes de qualquer busca das telas.
  useLayoutEffect(() => {
    api.definirVinheriaAtual(vinheriaId)
  }, [vinheriaId])

  // ---- avisos (toasts)
  const removerToast = useCallback((id) => setToasts((lista) => lista.filter((t) => t.id !== id)), [])
  const avisar = useCallback(
    (mensagem, tipo = 'ok') => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      setToasts((lista) => [...lista, { id, mensagem, tipo }])
      setTimeout(() => removerToast(id), 4500)
    },
    [removerToast],
  )

  // ---- carregamento
  const recarregarVinherias = useCallback(async () => {
    try {
      const lista = await api.listarVinherias()
      setVinherias(lista)
      setVinheriaId((atual) => atual ?? lista[0]?.id ?? null)
      setErro(null)
      return lista
    } catch (e) {
      setErro(e.message)
      return []
    } finally {
      setCarregandoVinherias(false)
    }
  }, [])

  const recarregarDispositivos = useCallback(async () => {
    if (!vinheriaId) return
    try {
      const [listaAdegas, listaDisp] = await Promise.all([api.listarAdegas(vinheriaId), api.listarDispositivos(vinheriaId)])
      setAdegas(listaAdegas)
      setDispositivos(listaDisp)
      // mantém o dispositivo escolhido se ele ainda existe; senão escolhe o primeiro
      setDeviceId((atual) => (listaDisp.some((d) => d.id === atual) ? atual : (listaDisp[0]?.id ?? null)))
    } catch (e) {
      setErro(e.message)
    } finally {
      setDispositivosDe(vinheriaId) // evita piscar "nenhum dispositivo" enquanto a lista ainda chega
    }
  }, [vinheriaId])

  useEffect(() => {
    recarregarVinherias()
  }, [recarregarVinherias])

  useEffect(() => {
    recarregarDispositivos()
  }, [recarregarDispositivos])

  // estado de todos os dispositivos, a cada 5 s
  usePolling(
    async (aindaVale) => {
      const lista = await api.obterResumo(vinheriaId)
      if (!aindaVale()) return
      setResumo(Object.fromEntries(lista.map((r) => [r.deviceId, r])))
    },
    INTERVALO_ATUALIZACAO_MS,
    vinheriaId,
  )

  // ---- escolhas do usuário
  const selecionarVinheria = useCallback((id) => {
    setVinheriaId(id)
    setAdegaId('todas')
    setDeviceId(null)
    setDispositivos([])
    setResumo({})
  }, [])

  const selecionarAdega = useCallback(
    (id) => {
      setAdegaId(id)
      // se o dispositivo atual não é dessa adega, troca para o primeiro dela
      const daAdega = dispositivos.filter((d) => id === 'todas' || d.adegaId === id)
      setDeviceId((atual) => (daAdega.some((d) => d.id === atual) ? atual : (daAdega[0]?.id ?? atual)))
    },
    [dispositivos],
  )

  const vinheria = vinherias.find((v) => v.id === vinheriaId) ?? null
  const dispositivo = dispositivos.find((d) => d.id === deviceId) ?? null
  const adegaDoDispositivo = adegas.find((a) => a.id === dispositivo?.adegaId) ?? null
  const alertasAtivos = Object.values(resumo).reduce((soma, r) => soma + (r.alertasAtivos ?? 0), 0)
  // "carregando" vale para as vinherias E para os dispositivos da vinheria escolhida
  const carregando = carregandoVinherias || (vinheriaId !== null && dispositivosDe !== vinheriaId)

  const valor = useMemo(
    () => ({
      vinherias, vinheria, vinheriaId, adegas, adegaId, dispositivos, dispositivo, adegaDoDispositivo,
      deviceId, resumo, alertasAtivos, carregando, carregandoVinherias, erro, toasts,
      selecionarVinheria, selecionarAdega, selecionarDispositivo: setDeviceId,
      recarregarVinherias, recarregarDispositivos, avisar, removerToast,
    }),
    [
      vinherias, vinheria, vinheriaId, adegas, adegaId, dispositivos, dispositivo, adegaDoDispositivo,
      deviceId, resumo, alertasAtivos, carregando, carregandoVinherias, erro, toasts,
      selecionarVinheria, selecionarAdega, recarregarVinherias, recarregarDispositivos, avisar, removerToast,
    ],
  )

  return <AppContext.Provider value={valor}>{children}</AppContext.Provider>
}
