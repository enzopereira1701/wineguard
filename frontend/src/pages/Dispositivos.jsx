import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Aviso from '../components/Aviso'
import BlocoCopiar from '../components/BlocoCopiar'
import Cartao from '../components/Cartao'
import Botao from '../components/Botao'
import { Campo, CampoSelecao } from '../components/Campo'
import Confirmar from '../components/Confirmar'
import Distintivo from '../components/Distintivo'
import { Carregando, Erro, Vazio } from '../components/Estado'
import Modal from '../components/Modal'
import StatusDot from '../components/StatusDot'
import { ESTADOS } from '../data/constantes'
import { LISTA_PRESETS, PRESETS, PRESET_PADRAO } from '../data/presets'
import { useAgora } from '../hooks/useAgora'
import { useApp } from '../hooks/useApp'
import * as api from '../services/api'
import { tempoRelativo } from '../utils/formatacao'

// IP do broker MQTT (muda a cada sessão do lab). Sem VITE_MQTT_HOST, tenta o host de VITE_API_URL.
const hostDaApi = () => { try { return new URL(import.meta.env.VITE_API_URL).hostname } catch { return null } }
const HOST = import.meta.env.VITE_MQTT_HOST || hostDaApi() || 'IP_DA_INSTANCIA'

/** Texto pronto para colar no config.h do firmware do Node. */
function montarConfig(c) {
  return [
    '#define SIMULACAO_WOKWI 0',
    '#define WIFI_SSID       "sua_rede_2_4ghz"',
    '#define WIFI_PASSWORD   "sua_senha"',
    `#define MQTT_BROKER     "${HOST}"`,
    '#define MQTT_PORT       1883',
    `#define API_KEY         "${c.apikey}"`,
    `#define DEVICE_ID       "${c.deviceId}"`,
    `#define NOME_VINHERIA   "${c.nomeVinheria}"`,
    `#define NOME_ADEGA      "${c.nomeAdega}"`,
  ].join('\n')
}

const FORM_VAZIO = { nome: '', adegaId: '', novaAdega: '', preset: PRESET_PADRAO }

/** Cadastro, edição e remoção de dispositivos (WineGuard Nodes). */
export default function Dispositivos() {
  const { vinheriaId, adegas, dispositivos, resumo, carregando, erro, recarregarDispositivos, selecionarDispositivo, avisar } = useApp()
  const navegar = useNavigate()
  const [params, setParams] = useSearchParams()
  const agora = useAgora(10000)

  const [form, setForm] = useState(FORM_VAZIO)
  const [criado, setCriado] = useState(null) // resposta do cadastro (mostra o config.h)
  const [enviando, setEnviando] = useState(false)
  const [editando, setEditando] = useState(null)
  const [removendo, setRemovendo] = useState(null)

  const novoAberto = params.get('novo') === '1'
  const adegaEscolhida = form.adegaId || adegas[0]?.id || '__nova__'
  const nomeAdega = (id) => adegas.find((a) => a.id === id)?.nome ?? id

  const abrirNovo = () => {
    setForm(FORM_VAZIO)
    setCriado(null)
    setParams({ novo: '1' })
  }
  const fecharNovo = () => {
    setCriado(null)
    setParams({})
  }

  const cadastrar = async (e) => {
    e.preventDefault()
    const novaAdega = adegaEscolhida === '__nova__'
    setEnviando(true)
    try {
      const r = await api.criarDispositivo({
        vinheriaId,
        adegaId: novaAdega ? null : adegaEscolhida,
        novaAdega: novaAdega ? form.novaAdega.trim() : null,
        nome: form.nome.trim(),
        preset: form.preset,
      })
      setCriado(r)
      await recarregarDispositivos()
      avisar(`Dispositivo ${r.dispositivo.id} cadastrado.`)
    } catch (err) {
      avisar(err.message, 'erro')
    } finally {
      setEnviando(false)
    }
  }

  const salvarEdicao = async (e) => {
    e.preventDefault()
    try {
      await api.atualizarDispositivo(editando.id, { nome: editando.nome.trim(), adegaId: editando.adegaId })
      await recarregarDispositivos()
      setEditando(null)
      avisar('Dispositivo atualizado.')
    } catch (err) {
      avisar(err.message, 'erro')
    }
  }

  const remover = async () => {
    setEnviando(true)
    try {
      await api.removerDispositivo(removendo.id)
      await recarregarDispositivos()
      avisar(`Dispositivo ${removendo.id} removido.`)
      setRemovendo(null)
    } catch (err) {
      avisar(err.message, 'erro')
    } finally {
      setEnviando(false)
    }
  }

  const identificar = async (id) => {
    try {
      await api.enviarComando(id, 'identify')
      avisar('O Node vai piscar por 5 segundos.')
    } catch (err) {
      avisar(err.message, 'erro')
    }
  }

  const abrirNoPainel = (id) => {
    selecionarDispositivo(id)
    navegar('/painel')
  }

  if (carregando) return <Carregando />
  if (erro && dispositivos.length === 0) return <Erro mensagem={erro} />

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl">Dispositivos</h1>
          <p className="text-sm text-suave">Cada WineGuard Node monitora uma adega. Cadastre, edite e acompanhe o estado de todos.</p>
        </div>
        <Botao icone="mais" onClick={abrirNovo}>Novo dispositivo</Botao>
      </div>

      {dispositivos.length === 0 ? (
        <Vazio icone="chip" titulo="Nenhum dispositivo nesta vinheria" texto="Cadastre o primeiro Node e copie o bloco do config.h para o firmware." acao={<Botao onClick={abrirNovo}>Cadastrar dispositivo</Botao>} />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {dispositivos.map((d) => {
            const r = resumo[d.id]
            const estado = r?.estado ?? 'aguardando'
            return (
              <Cartao as="li" key={d.id} tom={ESTADOS[estado].tom} className="p-5 pl-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="flex items-center gap-2 text-xl"><StatusDot estado={estado} />{d.nome}</h2>
                    <p className="numero text-sm text-suave">{d.id}, {nomeAdega(d.adegaId)}</p>
                  </div>
                  <Distintivo tom={ESTADOS[estado].tom}>{ESTADOS[estado].rotulo}</Distintivo>
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div><dt className="text-suave">Preset de guarda</dt><dd className="font-bold">{PRESETS[d.preset]?.nome ?? d.preset}</dd></div>
                  <div><dt className="text-suave">Última leitura</dt><dd className="font-bold">{tempoRelativo(r?.ultimaLeitura, agora)}</dd></div>
                  <div><dt className="text-suave">Alertas ativos</dt><dd className="numero font-bold">{r?.alertasAtivos ?? 0}</dd></div>
                </dl>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Botao tamanho="sm" onClick={() => abrirNoPainel(d.id)}>Abrir no painel</Botao>
                  <Botao tamanho="sm" variante="neutro" icone="busca" onClick={() => identificar(d.id)}>Identificar</Botao>
                  <Botao tamanho="sm" variante="neutro" icone="lapis" onClick={() => setEditando({ ...d })}>Editar</Botao>
                  <Botao tamanho="sm" variante="fantasma" icone="lixeira" onClick={() => setRemovendo(d)}>Remover</Botao>
                </div>
              </Cartao>
            )
          })}
        </ul>
      )}

      {/* ---- novo dispositivo ---- */}
      <Modal
        aberto={novoAberto}
        onFechar={fecharNovo}
        titulo={criado ? 'Dispositivo cadastrado' : 'Novo dispositivo'}
        largura="max-w-xl"
        rodape={
          criado ? (
            <Botao onClick={fecharNovo}>Concluir</Botao>
          ) : (
            <>
              <Botao variante="neutro" onClick={fecharNovo}>Cancelar</Botao>
              <Botao type="submit" form="form-novo" carregando={enviando}>Cadastrar</Botao>
            </>
          )
        }
      >
        {criado ? (
          <div className="space-y-4">
            <p className="text-sm">
              O dispositivo <strong className="numero">{criado.dispositivo.id}</strong> foi cadastrado. Para ligar o Node:
            </p>
            <ol className="list-decimal space-y-1 pl-5 text-sm">
              <li>Abra o firmware na Arduino IDE e copie <strong>config.example.h</strong> para <strong>config.h</strong>.</li>
              <li>Cole o bloco abaixo e troque o nome e a senha do Wi-Fi (rede de 2,4 GHz).</li>
              <li>Grave na placa. Em poucos segundos o estado muda de Aguardando para Normal.</li>
            </ol>
            <BlocoCopiar texto={montarConfig(criado.config)} rotulo="Copiar bloco" />
          </div>
        ) : (
          <form id="form-novo" onSubmit={cadastrar} className="space-y-4">
            <Campo rotulo="Nome do dispositivo" required maxLength={40} placeholder="Ex.: Cave de tintos" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
            <CampoSelecao rotulo="Adega" value={adegaEscolhida} onChange={(e) => setForm({ ...form, adegaId: e.target.value })}>
              {adegas.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
              <option value="__nova__">Criar uma nova adega...</option>
            </CampoSelecao>
            {adegaEscolhida === '__nova__' && (
              <Campo rotulo="Nome da nova adega" required maxLength={40} value={form.novaAdega} onChange={(e) => setForm({ ...form, novaAdega: e.target.value })} />
            )}
            <CampoSelecao rotulo="Preset de guarda" value={form.preset} onChange={(e) => setForm({ ...form, preset: e.target.value })}>
              {LISTA_PRESETS.map((p) => <option key={p.id} value={p.id}>{p.nome} ({p.descricao})</option>)}
            </CampoSelecao>
            <Aviso nivel="info">O número do dispositivo (wgn001, wgn002...) e a chave da vinheria são gerados sozinhos.</Aviso>
          </form>
        )}
      </Modal>

      {/* ---- editar ---- */}
      <Modal
        aberto={!!editando}
        onFechar={() => setEditando(null)}
        titulo="Editar dispositivo"
        rodape={
          <>
            <Botao variante="neutro" onClick={() => setEditando(null)}>Cancelar</Botao>
            <Botao type="submit" form="form-editar">Salvar</Botao>
          </>
        }
      >
        {editando && (
          <form id="form-editar" onSubmit={salvarEdicao} className="space-y-4">
            <Campo rotulo="Nome do dispositivo" required maxLength={40} value={editando.nome} onChange={(e) => setEditando({ ...editando, nome: e.target.value })} />
            <CampoSelecao rotulo="Adega" value={editando.adegaId} onChange={(e) => setEditando({ ...editando, adegaId: e.target.value })}>
              {adegas.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
            </CampoSelecao>
          </form>
        )}
      </Modal>

      {/* ---- remover ---- */}
      <Confirmar
        aberto={!!removendo}
        titulo="Remover dispositivo?"
        mensagem={removendo ? `O cadastro de ${removendo.nome} (${removendo.id}) e os alertas dele serão apagados.` : ''}
        confirmarTexto="Remover"
        perigo
        carregando={enviando}
        onConfirmar={remover}
        onCancelar={() => setRemovendo(null)}
      >
        <Aviso nivel="forte" className="mt-3">
          Se o ESP32 continuar ligado e publicando, a plataforma pode criar o dispositivo de novo sozinha. Desligue o Node antes.
        </Aviso>
      </Confirmar>
    </div>
  )
}
