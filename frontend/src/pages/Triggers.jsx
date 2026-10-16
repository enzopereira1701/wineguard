import { useEffect, useMemo, useState } from 'react'
import Aviso from '../components/Aviso'
import BarraFaixa from '../components/BarraFaixa'
import Botao from '../components/Botao'
import { Campo } from '../components/Campo'
import Confirmar from '../components/Confirmar'
import Distintivo from '../components/Distintivo'
import { Carregando, Erro, Vazio } from '../components/Estado'
import Icone from '../components/Icone'
import Modal from '../components/Modal'
import { VARIAVEIS } from '../data/constantes'
import { AVISO_FONTES, FONTES } from '../data/fontes'
import { LISTA_PRESETS, PRESETS, triggersDoPreset } from '../data/presets'
import { useApp } from '../hooks/useApp'
import * as api from '../services/api'
import { formatarHora } from '../utils/formatacao'
import { NIVEL, temAvisoForte, temBloqueio, validarTriggers } from '../utils/validacao'

// Cada variável: nome, unidade, cor e a "régua" (domínio) da barra de referência
const CAMPOS = [
  { chave: 'temp', info: VARIAVEIS.temperature, dominio: [0, 30], passo: 0.5 },
  { chave: 'umid', info: VARIAVEIS.humidity, dominio: [30, 100], passo: 1 },
  { chave: 'luz', info: VARIAVEIS.luminosity, dominio: [0, 50], passo: 1 },
]

const COR_NIVEL = { bloqueia: 'text-alerta', forte: 'text-atencao', leve: 'text-suave' }

/** Limites de alerta: preset de referência ou valores próprios, com avisos antes de salvar. */
export default function Triggers() {
  const { deviceId, dispositivo, carregando, avisar } = useApp()
  const [carga, setCarga] = useState(null) // { id, salvo, rascunho }
  const [erro, setErro] = useState(null)
  const [trocaPendente, setTrocaPendente] = useState(null) // id do preset esperando confirmação
  const [confirmaForte, setConfirmaForte] = useState(false)
  const [mostrarFontes, setMostrarFontes] = useState(false)
  const [envio, setEnvio] = useState({ estado: 'parado' }) // parado | enviando | recebido | erro
  const [calibrando, setCalibrando] = useState(false)

  // carrega os triggers sempre que troca o dispositivo
  useEffect(() => {
    if (!deviceId) return undefined
    let vivo = true
    api.obterTriggers(deviceId)
      .then((t) => {
        if (!vivo) return
        setCarga({ id: deviceId, salvo: t, rascunho: structuredClone(t) })
        setEnvio({ estado: 'parado' })
        setErro(null)
      })
      .catch((e) => vivo && setErro(e.message))
    return () => {
      vivo = false
    }
  }, [deviceId])

  const pronto = carga?.id === deviceId
  const t = pronto ? carga.rascunho : null
  const salvo = pronto ? carga.salvo : null
  const avisos = useMemo(() => (t ? validarTriggers(t) : []), [t])
  const alterado = !!t && JSON.stringify(t) !== JSON.stringify(salvo)

  // altera o rascunho (nunca o que está salvo)
  const atualizar = (funcao) => setCarga((c) => (c ? { ...c, rascunho: funcao(c.rascunho) } : c))

  const alterarCampo = (chave, campo, texto) =>
    atualizar((r) => ({ ...r, [chave]: { ...r[chave], [campo]: texto === '' ? NaN : Number(texto) } }))
  const alterarEstabilidade = (texto) => atualizar((r) => ({ ...r, estabilidadeMax: texto === '' ? NaN : Number(texto) }))

  const usarReferencia = () => atualizar((r) => ({ ...triggersDoPreset(r.preset), estabilidadeMax: r.estabilidadeMax }))
  const personalizar = () => atualizar((r) => ({ ...r, modo: 'personalizado' }))

  const escolherPreset = (id) => {
    if (t.preset === id && t.modo === 'referencia') return
    setTrocaPendente(id) // pede confirmação mostrando os valores de antes e depois
  }
  const confirmarTroca = () => {
    atualizar((r) => ({ ...triggersDoPreset(trocaPendente), estabilidadeMax: r.estabilidadeMax }))
    setTrocaPendente(null)
  }

  // Calibração da luz: lê a luz de agora (adega fechada e apagada) e põe o limite um pouco acima
  const calibrarLuz = async () => {
    setCalibrando(true)
    try {
      const atual = await api.obterAtual(deviceId)
      if (atual.luminosity === null || atual.luminosity === undefined) throw new Error('Ainda não há leitura de luz neste dispositivo.')
      const escuro = atual.luminosity
      const limite = Math.min(100, Math.ceil(escuro) + 4)
      atualizar((r) => ({ ...r, modo: 'personalizado', luzEscuro: escuro, luz: { min: 0, max: limite } }))
      avisar(`Escuro normal registrado: ${escuro} %. Limite de luz em ${limite} %.`)
    } catch (e) {
      avisar(e.message, 'erro')
    } finally {
      setCalibrando(false)
    }
  }

  const salvar = async (forcar = false) => {
    if (temAvisoForte(avisos) && !forcar) {
      setConfirmaForte(true)
      return
    }
    setConfirmaForte(false)
    setEnvio({ estado: 'enviando' })
    try {
      const r = await api.salvarTriggers(deviceId, t)
      setCarga((c) => (c ? { ...c, salvo: structuredClone(c.rascunho) } : c))
      setEnvio({ estado: 'recebido', em: r.em })
      avisar('Limites enviados e recebidos pelo Node.')
    } catch (e) {
      setEnvio({ estado: 'erro', mensagem: e.message })
      avisar('Não foi possível enviar os limites ao Node.', 'erro')
    }
  }

  // ---------------------------------------------------------------- estados da tela
  if (carregando) return <Carregando />
  if (!dispositivo) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <Vazio icone="ajustes" titulo="Escolha um dispositivo" texto="Os limites são definidos para cada Node. Cadastre ou selecione um dispositivo primeiro." />
      </div>
    )
  }
  if (erro) return <Erro mensagem={erro} />
  if (!t) return <Carregando texto="Carregando os limites..." />

  const referencia = PRESETS[t.preset]
  const referenciaAtiva = t.modo === 'referencia'

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-6">
      <div>
        <h1 className="text-3xl">Triggers</h1>
        <p className="text-sm text-suave">
          Limites de <strong className="text-tinta">{dispositivo.nome}</strong> ({dispositivo.id}). Fora deles, o Node acende o LED, toca o buzzer e mostra o alerta na tela.
        </p>
      </div>

      {/* preset e modo */}
      <section aria-labelledby="titulo-preset" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="titulo-preset" className="text-xl">Referência de guarda</h2>
          <div className="flex overflow-hidden rounded-md border border-linha" role="group" aria-label="Origem dos limites">
            <button type="button" aria-pressed={referenciaAtiva} onClick={usarReferencia} className={`px-3 py-1.5 text-sm font-bold ${referenciaAtiva ? 'bg-bordo text-papel' : 'bg-papel text-suave hover:text-bordo'}`}>
              Usar referência
            </button>
            <button type="button" aria-pressed={!referenciaAtiva} onClick={personalizar} className={`px-3 py-1.5 text-sm font-bold ${!referenciaAtiva ? 'bg-bordo text-papel' : 'bg-papel text-suave hover:text-bordo'}`}>
              Personalizar
            </button>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {LISTA_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              aria-pressed={t.preset === p.id}
              onClick={() => escolherPreset(p.id)}
              className={`rounded-md border p-4 text-left transition-colors ${t.preset === p.id ? 'border-bordo bg-papel ring-1 ring-bordo' : 'border-linha bg-papel hover:border-bordo/50'}`}
            >
              <span className="block font-titulo text-lg">{p.nome}</span>
              <span className="block text-sm text-suave">{p.descricao}</span>
              <span className="numero mt-2 block text-xs text-suave">
                {p.temp.min} a {p.temp.max} °C, {p.umid.min} a {p.umid.max} %, luz até {p.luz.max} %
              </span>
            </button>
          ))}
        </div>
        <p className="text-sm text-suave">
          São presets de <strong>guarda</strong>, não de servir: a temperatura de guarda é quase a mesma para tinto, branco e rosé.{' '}
          {referenciaAtiva ? 'Os campos abaixo seguem o preset.' : 'Você está usando valores próprios; a referência continua aparecendo para comparação.'}
        </p>
      </section>

      {/* uma seção por variável */}
      {CAMPOS.map(({ chave, info, dominio, passo }) => {
        const faixa = t[chave]
        const ref = referencia[chave]
        const doCampo = avisos.filter((a) => a.variavel === chave)
        const fora = !referenciaAtiva && Number.isFinite(faixa.min) && Number.isFinite(faixa.max) && (faixa.min < ref.min || faixa.max > ref.max)
        return (
          <section key={chave} aria-labelledby={`titulo-${chave}`} className="rounded-md border border-linha bg-papel p-5">
            <div className="flex flex-wrap items-center gap-2">
              <Icone nome={info.icone} className="size-5" style={{ color: info.cor }} />
              <h2 id={`titulo-${chave}`} className="text-xl" style={{ color: info.cor }}>{info.rotulo}</h2>
              <span className="text-xs text-suave">LED {info.corLed}</span>
              {fora && <Distintivo tom="atencao" icone="alerta" className="ml-auto">Fora da referência</Distintivo>}
            </div>

            <div className="mt-4 grid gap-6 md:grid-cols-2">
              <BarraFaixa dominio={dominio} alerta={ref} alvo={referencia.alvo[chave]} usuario={faixa} unidade={info.unidade} cor={info.cor} />
              <div className="grid grid-cols-2 gap-3">
                <Campo rotulo={`Mínimo (${info.unidade})`} type="number" inputMode="decimal" step={passo} disabled={referenciaAtiva} value={Number.isNaN(faixa.min) ? '' : faixa.min} onChange={(e) => alterarCampo(chave, 'min', e.target.value)} />
                <Campo rotulo={`Máximo (${info.unidade})`} type="number" inputMode="decimal" step={passo} disabled={referenciaAtiva} value={Number.isNaN(faixa.max) ? '' : faixa.max} onChange={(e) => alterarCampo(chave, 'max', e.target.value)} />
              </div>
            </div>

            {chave === 'luz' && (
              <div className="mt-4 rounded-md border border-dashed border-linha p-3">
                <p className="text-sm">
                  O sensor de luz mede em porcentagem <strong>relativa</strong>, e o valor muda de um módulo para outro. Com a adega <strong>fechada e apagada</strong>, calibre para ajustar o limite ao seu sensor.
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <Botao variante="secundario" tamanho="sm" icone="sol" carregando={calibrando} onClick={calibrarLuz}>Marcar o valor atual como escuro normal</Botao>
                  {t.luzEscuro !== null && <span className="numero text-sm text-suave">Escuro normal registrado: {t.luzEscuro} %</span>}
                </div>
              </div>
            )}

            {doCampo.length > 0 && (
              <ul className="mt-3 space-y-1.5" aria-label={`Avisos de ${info.rotulo}`}>
                {doCampo.map((a, i) => (
                  <li key={i} className={`flex items-start gap-2 text-sm ${COR_NIVEL[a.nivel]}`}>
                    <Icone nome={a.nivel === NIVEL.BLOQUEIA ? 'fechar' : 'alerta'} className="mt-0.5 size-4" />
                    <span className="text-tinta">{a.mensagem}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )
      })}

      {/* estabilidade */}
      <section aria-labelledby="titulo-estab" className="rounded-md border border-linha bg-papel p-5">
        <div className="flex items-center gap-2">
          <Icone nome="onda" className="size-5 text-ouro-escuro" />
          <h2 id="titulo-estab" className="text-xl text-ouro-escuro">Estabilidade da temperatura</h2>
        </div>
        <p className="mt-2 text-sm text-suave">
          Segundo os especialistas, a variação faz mais mal ao vinho do que um valor fixo um pouco fora do ideal. Se a temperatura variar mais que o limite em 24 horas, o sistema avisa.
        </p>
        <div className="mt-3 max-w-xs">
          <Campo rotulo="Variação máxima em 24 h (°C)" type="number" inputMode="decimal" step="0.5" value={Number.isNaN(t.estabilidadeMax) ? '' : t.estabilidadeMax} onChange={(e) => alterarEstabilidade(e.target.value)} />
        </div>
        {avisos.filter((a) => a.variavel === 'estabilidade').map((a, i) => (
          <p key={i} className="mt-2 text-sm text-tinta">{a.mensagem}</p>
        ))}
      </section>

      {/* salvar */}
      <div className="sticky bottom-20 z-30 space-y-3 rounded-md border border-linha bg-creme/95 p-4 backdrop-blur md:bottom-4">
        {envio.estado === 'recebido' && !alterado && <Aviso nivel="ok">Recebido pelo Node às {formatarHora(envio.em)}. Os novos limites já estão valendo.</Aviso>}
        {envio.estado === 'erro' && <Aviso nivel="alerta" titulo="Falha ao enviar">{envio.mensagem}</Aviso>}
        <div className="flex flex-wrap items-center gap-3">
          <Botao variante="fantasma" icone="livro" onClick={() => setMostrarFontes(true)}>Fontes</Botao>
          <Botao variante="neutro" onClick={usarReferencia} disabled={referenciaAtiva}>Restaurar referência</Botao>
          <span className="ml-auto text-sm text-suave">{alterado ? 'Há alterações não salvas.' : 'Nada para salvar.'}</span>
          <Botao carregando={envio.estado === 'enviando'} disabled={temBloqueio(avisos) || (!alterado && envio.estado !== 'erro')} onClick={() => salvar(false)}>
            Salvar e enviar ao Node
          </Botao>
        </div>
        {temBloqueio(avisos) && <p className="text-sm text-alerta">Corrija os campos com erro para poder salvar.</p>}
      </div>

      {/* troca de preset com confirmação */}
      <Modal
        aberto={!!trocaPendente}
        onFechar={() => setTrocaPendente(null)}
        titulo={trocaPendente ? `Trocar para ${PRESETS[trocaPendente].nome}?` : ''}
        rodape={
          <>
            <Botao variante="neutro" onClick={() => setTrocaPendente(null)}>Cancelar</Botao>
            <Botao onClick={confirmarTroca}>Aplicar</Botao>
          </>
        }
      >
        {trocaPendente && (
          <div className="space-y-3 text-sm">
            <p>Os limites abaixo vão mudar. Você ainda precisa salvar para enviar ao Node.</p>
            <table className="w-full">
              <thead className="text-left text-suave">
                <tr><th className="py-1 font-bold">Variável</th><th className="font-bold">Antes</th><th className="font-bold">Depois</th></tr>
              </thead>
              <tbody className="numero">
                {CAMPOS.map(({ chave, info }) => (
                  <tr key={chave} className="border-t border-linha">
                    <td className="py-1.5 font-bold">{info.rotulo}</td>
                    <td>{t[chave].min} a {t[chave].max} {info.unidade}</td>
                    <td>{PRESETS[trocaPendente][chave].min} a {PRESETS[trocaPendente][chave].max} {info.unidade}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Modal>

      {/* aviso forte antes de salvar */}
      <Confirmar
        aberto={confirmaForte}
        titulo="Esse limite pode permitir danos ao vinho"
        confirmarTexto="Salvar mesmo assim"
        perigo
        onConfirmar={() => salvar(true)}
        onCancelar={() => setConfirmaForte(false)}
      >
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {avisos.filter((a) => a.nivel === NIVEL.FORTE).map((a, i) => <li key={i}>{a.mensagem}</li>)}
        </ul>
      </Confirmar>

      {/* fontes */}
      <Modal aberto={mostrarFontes} onFechar={() => setMostrarFontes(false)} titulo="De onde vêm as referências" largura="max-w-2xl">
        <div className="space-y-3 text-sm">
          <Aviso nivel="forte">{AVISO_FONTES}</Aviso>
          <ul className="space-y-3">
            {FONTES.map((f) => (
              <li key={f.url}>
                <a href={f.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-bold text-bordo underline underline-offset-2">
                  {f.nome}
                  <Icone nome="externo" className="size-3.5" />
                </a>
                <p className="text-suave">{f.resumo}</p>
              </li>
            ))}
          </ul>
        </div>
      </Modal>
    </div>
  )
}
