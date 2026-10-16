import { useState } from 'react'
import { Link } from 'react-router-dom'
import Distintivo from '../components/Distintivo'
import { Carregando, Erro, Vazio } from '../components/Estado'
import { CampoSelecao } from '../components/Campo'
import Icone from '../components/Icone'
import { INTERVALO_ATUALIZACAO_MS, TIPOS_ALERTA } from '../data/constantes'
import { useAgora } from '../hooks/useAgora'
import { useApp } from '../hooks/useApp'
import { usePolling } from '../hooks/usePolling'
import * as api from '../services/api'
import { descreverAlerta, tituloAlerta } from '../utils/alertas'
import { formatarDataHora, formatarDuracao } from '../utils/formatacao'

/** Histórico de alertas, do mais novo para o mais antigo, com filtros. */
export default function Alertas() {
  const { vinheriaId, dispositivos, carregando } = useApp()
  const [lista, setLista] = useState(null) // { id: vinheriaId, itens }
  const [erro, setErro] = useState(null)
  const [tipo, setTipo] = useState('todos')
  const [estado, setEstado] = useState('todos')
  const [disp, setDisp] = useState('todos')
  const agora = useAgora(10000)

  usePolling(
    async (aindaVale) => {
      try {
        const itens = await api.listarAlertas({ vinheriaId, estado: 'todos' })
        if (!aindaVale()) return
        setLista({ id: vinheriaId, itens })
        setErro(null)
      } catch (e) {
        if (aindaVale()) setErro(e.message)
      }
    },
    INTERVALO_ATUALIZACAO_MS,
    vinheriaId,
  )

  const itens = lista?.id === vinheriaId ? lista.itens : null
  const nomeDo = (id) => dispositivos.find((d) => d.id === id)?.nome ?? id
  const filtrados = (itens ?? []).filter(
    (a) =>
      (tipo === 'todos' || a.variavel === tipo) &&
      (disp === 'todos' || a.deviceId === disp) &&
      (estado === 'todos' || (estado === 'ativos' ? !a.fim : !!a.fim)),
  )
  const ativos = (itens ?? []).filter((a) => !a.fim).length

  if (carregando) return <Carregando />
  if (erro && !itens) return <Erro mensagem={erro} />

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
      <div>
        <h1 className="text-3xl">Alertas</h1>
        <p className="text-sm text-suave">
          Cada alerta tem início e fim. {ativos > 0 ? <strong className="text-alerta">{ativos} em andamento agora.</strong> : 'Nenhum em andamento agora.'}
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <CampoSelecao rotulo="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="todos">Todos os tipos</option>
          {Object.entries(TIPOS_ALERTA).map(([id, t]) => <option key={id} value={id}>{t.rotulo}</option>)}
        </CampoSelecao>
        <CampoSelecao rotulo="Situação" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="todos">Todas</option>
          <option value="ativos">Em andamento</option>
          <option value="encerrados">Encerrados</option>
        </CampoSelecao>
        <CampoSelecao rotulo="Dispositivo" value={disp} onChange={(e) => setDisp(e.target.value)}>
          <option value="todos">Todos os dispositivos</option>
          {dispositivos.map((d) => <option key={d.id} value={d.id}>{d.nome}</option>)}
        </CampoSelecao>
      </div>

      {!itens ? (
        <Carregando texto="Carregando alertas..." />
      ) : filtrados.length === 0 ? (
        <Vazio
          icone="sino"
          titulo="Nenhum alerta com esses filtros"
          texto="Quando uma leitura sair dos limites, o alerta aparece aqui com início e fim."
          acao={<Link to="/triggers" className="text-sm font-bold text-bordo underline underline-offset-2">Ver os limites configurados</Link>}
        />
      ) : (
        <ul className="divide-y divide-linha rounded-md border border-linha bg-papel">
          {filtrados.map((a) => {
            const info = TIPOS_ALERTA[a.variavel]
            const fim = a.fim ? new Date(a.fim).getTime() : agora
            return (
              <li key={a.id} className="grid gap-2 px-4 py-4 md:grid-cols-[1fr_auto] md:items-center">
                <div className="flex items-start gap-3">
                  <Icone nome={info.icone} className="mt-0.5 size-5" style={{ color: info.cor }} />
                  <div>
                    <p className="flex flex-wrap items-center gap-2 font-bold">
                      {tituloAlerta(a)}
                      {!a.fim && <Distintivo tom="alerta">Em andamento</Distintivo>}
                    </p>
                    <p className="text-sm text-tinta">{descreverAlerta(a)}</p>
                    <p className="text-xs text-suave">{nomeDo(a.deviceId)} ({a.deviceId})</p>
                  </div>
                </div>
                <dl className="numero grid grid-cols-3 gap-4 text-sm md:text-right">
                  <div><dt className="text-xs text-suave">Início</dt><dd>{formatarDataHora(a.inicio)}</dd></div>
                  <div><dt className="text-xs text-suave">Fim</dt><dd>{a.fim ? formatarDataHora(a.fim) : 'em andamento'}</dd></div>
                  <div><dt className="text-xs text-suave">Duração</dt><dd>{formatarDuracao(fim - new Date(a.inicio).getTime())}</dd></div>
                </dl>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
