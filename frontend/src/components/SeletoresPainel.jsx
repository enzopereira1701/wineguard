import { useApp } from '../hooks/useApp'
import { CampoSelecao } from './Campo'

/** Três listas: vinheria, adega e dispositivo. A adega só filtra a lista de dispositivos. */
export default function SeletoresPainel() {
  const { vinherias, vinheriaId, selecionarVinheria, adegas, adegaId, selecionarAdega, dispositivos, deviceId, selecionarDispositivo } = useApp()
  const doFiltro = dispositivos.filter((d) => adegaId === 'todas' || d.adegaId === adegaId)

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <CampoSelecao rotulo="Vinheria" value={vinheriaId ?? ''} onChange={(e) => selecionarVinheria(e.target.value)}>
        {vinherias.map((v) => <option key={v.id} value={v.id}>{v.nome}</option>)}
      </CampoSelecao>
      <CampoSelecao rotulo="Adega" value={adegaId} onChange={(e) => selecionarAdega(e.target.value)}>
        <option value="todas">Todas as adegas</option>
        {adegas.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
      </CampoSelecao>
      <CampoSelecao rotulo="Dispositivo" value={deviceId ?? ''} onChange={(e) => selecionarDispositivo(e.target.value)} disabled={doFiltro.length === 0}>
        {doFiltro.map((d) => <option key={d.id} value={d.id}>{d.nome} ({d.id})</option>)}
      </CampoSelecao>
    </div>
  )
}
