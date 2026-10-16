import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Aviso from '../components/Aviso'
import Botao from '../components/Botao'
import { Carregando, Erro, Vazio } from '../components/Estado'
import FaixaChips from '../components/FaixaChips'
import GraficoCombinado from '../components/GraficoCombinado'
import GraficoVariavel from '../components/GraficoVariavel'
import Icone from '../components/Icone'
import Metrica from '../components/Metrica'
import SeletoresPainel from '../components/SeletoresPainel'
import Simulador from '../components/Simulador'
import Distintivo from '../components/Distintivo'
import { ESTADOS, INTERVALO_ATUALIZACAO_MS, LISTA_VARIAVEIS, PERIODOS, TIPOS_ALERTA, VARIAVEIS } from '../data/constantes'
import { PRESETS } from '../data/presets'
import { useAgora } from '../hooks/useAgora'
import { useApp } from '../hooks/useApp'
import { usePolling } from '../hooks/usePolling'
import * as api from '../services/api'
import { descreverAlerta, tituloAlerta } from '../utils/alertas'
import { statusSimples } from '../utils/avaliacao'
import { formatarNumero, tempoRelativo } from '../utils/formatacao'

/** Tela principal: valores de agora, 4 gráficos e controles do Node. */
export default function Painel() {
  const { vinheriaId, deviceId, dispositivo, adegaDoDispositivo, dispositivos, carregando, erro: erroApp, avisar } = useApp()
  const [periodo, setPeriodo] = useState('1h')
  const [aoVivo, setAoVivo] = useState(true)
  const [leitura, setLeitura] = useState(null) // { id, atual, historico, estabilidade, alertas }
  const [limites, setLimites] = useState(null) // { id, triggers }
  const [erro, setErro] = useState(null)
  const agora = useAgora(10000)

  // limites (triggers) do dispositivo: para as linhas dos gráficos e a cor dos cartões
  useEffect(() => {
    if (!deviceId) return undefined
    let vivo = true
    api.obterTriggers(deviceId)
      .then((t) => vivo && setLimites({ id: deviceId, triggers: t }))
      .catch((e) => vivo && setErro(e.message))
    return () => {
      vivo = false
    }
  }, [deviceId])

  // atualização "ao vivo": leituras, histórico, estabilidade e alertas ativos, a cada 5 s
  usePolling(
    async (aindaVale) => {
      try {
        const [atual, historico, estabilidade, alertas] = await Promise.all([
          api.obterAtual(deviceId),
          api.obterHistorico(deviceId, periodo),
          api.obterEstabilidade(deviceId),
          api.listarAlertas({ vinheriaId, deviceId, estado: 'ativos' }),
        ])
        if (!aindaVale()) return
        setLeitura({ id: deviceId, atual, historico, estabilidade, alertas })
        setErro(null)
      } catch (e) {
        if (aindaVale()) setErro(e.message)
      }
    },
    INTERVALO_ATUALIZACAO_MS,
    deviceId ? `${deviceId}|${periodo}` : null,
    aoVivo,
  )

  // só usa os dados se forem do dispositivo que está escolhido agora
  const dados = leitura?.id === deviceId ? leitura : null
  const triggers = limites?.id === deviceId ? limites.triggers : null

  const trocarPeriodo = (id) => {
    setPeriodo(id)
    setAoVivo(true)
  }

  const alternarMudo = async () => {
    const novo = dados.atual.muted === 1 ? '0' : '1'
    try {
      await api.enviarComando(deviceId, 'mute', novo)
      setLeitura((l) => (l ? { ...l, atual: { ...l.atual, muted: Number(novo) } } : l))
      avisar(novo === '1' ? 'Buzzer silenciado. O LED continua ligado.' : 'Som reativado.')
    } catch (e) {
      avisar(e.message, 'erro')
    }
  }

  const identificar = async () => {
    try {
      await api.enviarComando(deviceId, 'identify')
      avisar('O Node vai piscar por 5 segundos.')
    } catch (e) {
      avisar(e.message, 'erro')
    }
  }

  // ---------------------------------------------------------------- estados da tela
  if (carregando) return <Carregando texto="Carregando o painel..." />
  if (erroApp && dispositivos.length === 0) return <Erro mensagem={erroApp} />
  if (!dispositivo) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <Vazio
          icone="chip"
          titulo="Esta vinheria ainda não tem dispositivos"
          texto="Cadastre o primeiro WineGuard Node para começar a ver temperatura, umidade e luz."
          acao={<Link to="/dispositivos?novo=1" className="rounded-md bg-bordo px-4 py-2 text-sm font-bold text-papel hover:bg-bordo-escuro">Cadastrar dispositivo</Link>}
        />
      </div>
    )
  }

  const atual = dados?.atual
  const aguardando = atual?.estado === 'aguardando'
  const estadoInfo = ESTADOS[atual?.estado ?? 'aguardando']
  const faixaDe = (chave) => triggers?.[chave]
  const alvoDe = (chave) => (triggers?.modo === 'referencia' ? PRESETS[triggers.preset]?.alvo[chave] : null)

  return (
    <div className="mx-auto max-w-7xl space-y-5 px-4 py-6">
      <div>
        <h1 className="text-3xl">Painel</h1>
        <p className="text-sm text-suave">
          {adegaDoDispositivo?.nome}, {dispositivo.nome}. Dispositivo {dispositivos.findIndex((d) => d.id === deviceId) + 1} de {dispositivos.length}.
        </p>
      </div>

      <SeletoresPainel />
      <FaixaChips />

      {/* status e controles */}
      <div className="flex flex-wrap items-center gap-3 border-y border-linha py-3">
        <Distintivo tom={estadoInfo.tom}>{estadoInfo.rotulo}</Distintivo>
        <span className="text-sm text-suave">
          Última leitura: <span className="numero font-bold text-tinta">{tempoRelativo(atual?.ultimaLeitura, agora)}</span>
        </span>
        {aoVivo ? (
          <span className="inline-flex items-center gap-1.5 text-sm text-ok">
            <span className="ao-vivo size-2 rounded-full bg-ok" aria-hidden="true" />
            Ao vivo, atualiza a cada 5 s
          </span>
        ) : (
          <span className="text-sm text-suave">Atualização em pausa</span>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="flex overflow-hidden rounded-md border border-linha" role="group" aria-label="Período dos gráficos">
            {PERIODOS.map((p) => (
              <button
                key={p.id}
                type="button"
                aria-pressed={periodo === p.id}
                onClick={() => trocarPeriodo(p.id)}
                className={`px-3 py-1.5 text-sm font-bold ${periodo === p.id ? 'bg-bordo text-papel' : 'bg-papel text-suave hover:text-bordo'}`}
              >
                {p.rotulo}
              </button>
            ))}
          </div>
          <Botao variante="neutro" tamanho="sm" icone={aoVivo ? 'pausa' : 'play'} onClick={() => setAoVivo((v) => !v)}>
            {aoVivo ? 'Pausar' : 'Retomar'}
          </Botao>
          <Botao variante="neutro" tamanho="sm" icone={atual?.muted === 1 ? 'som' : 'mudo'} onClick={alternarMudo} disabled={!atual || aguardando}>
            {atual?.muted === 1 ? 'Reativar som' : 'Silenciar'}
          </Botao>
          <Botao variante="neutro" tamanho="sm" icone="busca" onClick={identificar} disabled={!atual || aguardando}>
            Identificar Node
          </Botao>
        </div>
      </div>

      {erro && <Aviso nivel="alerta" titulo="Falha ao atualizar">{erro}</Aviso>}
      {!dados && !erro && <Carregando texto="Lendo o dispositivo..." />}

      {aguardando && (
        <Aviso nivel="info" titulo="Aguardando a primeira leitura">
          Ligue o Node com o bloco do <strong>config.h</strong> mostrado ao cadastrar. Assim que ele publicar, os valores aparecem aqui.
        </Aviso>
      )}

      {dados && !aguardando && (
        <>
          {/* alertas ativos */}
          {dados.alertas.length > 0 && (
            <ul className="space-y-2" aria-label="Alertas ativos">
              {dados.alertas.map((a) => (
                <li key={a.id} className="respirar flex items-start gap-3 rounded-md border border-alerta/40 bg-alerta/10 px-4 py-3 text-alerta">
                  <Icone nome={TIPOS_ALERTA[a.variavel].icone} className="mt-0.5 size-5" />
                  <div>
                    <p className="font-bold">{tituloAlerta(a)}</p>
                    <p className="text-sm text-tinta">{descreverAlerta(a)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* valores de agora */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {LISTA_VARIAVEIS.map((v) => {
              const info = VARIAVEIS[v]
              const faixa = faixaDe(info.chave)
              const alvo = alvoDe(info.chave)
              return (
                <Metrica
                  key={v}
                  icone={info.icone}
                  cor={info.cor}
                  rotulo={info.rotulo}
                  valor={formatarNumero(atual[v], info.decimais)}
                  unidade={info.unidade}
                  status={faixa ? statusSimples(atual[v], faixa.min, faixa.max) : 'sem-dado'}
                  detalhe={faixa ? `Limites ${faixa.min} a ${faixa.max} ${info.unidade}${alvo ? `, alvo ${alvo.min} a ${alvo.max}` : ''}` : undefined}
                />
              )
            })}
            <Metrica
              icone="onda"
              cor={TIPOS_ALERTA.estabilidade.cor}
              rotulo="Estabilidade (24 h)"
              valor={formatarNumero(dados.estabilidade.variacao, 1)}
              unidade="°C de variação"
              status={dados.estabilidade.variacao > dados.estabilidade.limite ? 'instavel' : 'estavel'}
              detalhe={`Limite de ${formatarNumero(dados.estabilidade.limite, 1)} °C. Mín ${formatarNumero(dados.estabilidade.min, 1)}, máx ${formatarNumero(dados.estabilidade.max, 1)} °C.`}
            />
          </div>

          {/* gráficos */}
          <GraficoCombinado historico={dados.historico} periodo={periodo} />
          <div className="grid gap-4 lg:grid-cols-3">
            {LISTA_VARIAVEIS.map((v) => (
              <GraficoVariavel key={v} variavel={v} dados={dados.historico[v]} faixa={faixaDe(VARIAVEIS[v].chave)} alvo={alvoDe(VARIAVEIS[v].chave)} periodo={periodo} />
            ))}
          </div>
        </>
      )}

      <Simulador key={deviceId} deviceId={deviceId} />
    </div>
  )
}
