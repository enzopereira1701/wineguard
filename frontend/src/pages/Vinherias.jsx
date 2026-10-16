import { useState } from 'react'
import Aviso from '../components/Aviso'
import Botao from '../components/Botao'
import Cartao from '../components/Cartao'
import { Campo } from '../components/Campo'
import Confirmar from '../components/Confirmar'
import Distintivo from '../components/Distintivo'
import { Carregando, Erro } from '../components/Estado'
import Modal from '../components/Modal'
import { useAgora } from '../hooks/useAgora'
import { useApp } from '../hooks/useApp'
import * as api from '../services/api'
import { diasAte, formatarData } from '../utils/formatacao'

/** Texto do vencimento: "vence em 12 dias", "venceu há 5 dias". */
function textoVencimento(vencimento, agora) {
  const dias = diasAte(vencimento, agora)
  if (dias > 1) return `vence em ${dias} dias`
  if (dias === 1) return 'vence amanhã'
  if (dias === 0) return 'vence hoje'
  return `venceu há ${Math.abs(dias)} ${Math.abs(dias) === 1 ? 'dia' : 'dias'}`
}


/** Cadastro de vinherias e suspensão por inadimplência (demonstração, sem login). */
export default function Vinherias() {
  const { vinherias, vinheriaId, selecionarVinheria, recarregarVinherias, carregandoVinherias, erro, avisar } = useApp()
  const agora = useAgora(60000)
  const [novaAberta, setNovaAberta] = useState(false)
  const [form, setForm] = useState({ nome: '', vencimento: '' })
  const [acao, setAcao] = useState(null) // { tipo: 'suspender'|'reativar'|'inadimplencia', vinheria }
  const [ocupado, setOcupado] = useState(false)

  const abrirNova = () => {
    setForm({ nome: '', vencimento: '' })
    setNovaAberta(true)
  }

  const criar = async (e) => {
    e.preventDefault()
    setOcupado(true)
    try {
      const v = await api.criarVinheria({ nome: form.nome.trim(), ...(form.vencimento ? { vencimento: form.vencimento } : {}) })
      await recarregarVinherias()
      setNovaAberta(false)
      avisar(`Vinheria ${v.nome} cadastrada.`)
    } catch (err) {
      avisar(err.message, 'erro')
    } finally {
      setOcupado(false)
    }
  }

  const TEXTOS = {
    suspender: { titulo: 'Suspender vinheria?', botao: 'Suspender', perigo: true, ok: 'foi suspensa.', fn: api.suspenderVinheria },
    reativar: { titulo: 'Reativar vinheria?', botao: 'Reativar', perigo: false, ok: 'foi reativada.', fn: api.reativarVinheria },
    inadimplencia: { titulo: 'Simular inadimplência?', botao: 'Simular', perigo: true, ok: 'ficou inadimplente e foi suspensa.', fn: api.simularInadimplencia },
  }

  const executar = async () => {
    const { tipo, vinheria } = acao
    setOcupado(true)
    try {
      await TEXTOS[tipo].fn(vinheria.id)
      await recarregarVinherias()
      avisar(`${vinheria.nome} ${TEXTOS[tipo].ok}`)
      setAcao(null)
    } catch (err) {
      avisar(err.message, 'erro')
    } finally {
      setOcupado(false)
    }
  }

  if (carregandoVinherias) return <Carregando />
  if (erro && vinherias.length === 0) return <Erro mensagem={erro} aoTentar={recarregarVinherias} />

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl">Vinherias</h1>
          <p className="text-sm text-suave">Cada vinheria tem suas adegas e dispositivos, com os dados separados dos das outras.</p>
        </div>
        <Botao icone="mais" onClick={abrirNova}>Nova vinheria</Botao>
      </div>

      <Aviso nivel="forte" titulo="Demonstração sem autenticação">
        Qualquer pessoa com o link pode suspender e reativar vinherias. Em um sistema real, só o administrador da plataforma faria isso. Veja &quot;Limitações e evolução&quot; no README.
      </Aviso>

      <ul className="space-y-3">
        {vinherias.map((v) => {
          const suspensa = v.status === 'suspensa'
          return (
            <Cartao as="li" key={v.id} tom={suspensa ? 'atencao' : 'ok'} className="p-5 pl-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="flex flex-wrap items-center gap-2 text-xl">
                    {v.nome}
                    <Distintivo tom={suspensa ? 'atencao' : 'ok'} icone={suspensa ? 'alerta' : 'check'}>{suspensa ? 'Suspensa' : 'Ativa'}</Distintivo>
                    {v.id === vinheriaId && <Distintivo tom="marca">Em uso</Distintivo>}
                  </h2>
                  <p className="numero text-sm text-suave">{v.id}</p>
                </div>
                <dl className="numero flex gap-6 text-sm">
                  <div><dt className="text-xs text-suave">Vencimento</dt><dd className="font-bold">{formatarData(v.vencimento)}</dd><dd className={diasAte(v.vencimento, agora) < 0 ? 'text-alerta' : 'text-suave'}>{textoVencimento(v.vencimento, agora)}</dd></div>
                  <div><dt className="text-xs text-suave">Dispositivos</dt><dd className="font-bold">{v.dispositivos}</dd></div>
                </dl>
              </div>
              {suspensa && (
                <p className="mt-3 text-sm text-suave">Os Nodes estão em espera: sem LED, sem som e sem novas leituras. O histórico foi preservado.</p>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                {v.id !== vinheriaId && <Botao tamanho="sm" variante="neutro" onClick={() => selecionarVinheria(v.id)}>Usar esta vinheria</Botao>}
                {suspensa ? (
                  <Botao tamanho="sm" onClick={() => setAcao({ tipo: 'reativar', vinheria: v })}>Reativar</Botao>
                ) : (
                  <>
                    <Botao tamanho="sm" variante="secundario" onClick={() => setAcao({ tipo: 'suspender', vinheria: v })}>Suspender</Botao>
                    <Botao tamanho="sm" variante="fantasma" onClick={() => setAcao({ tipo: 'inadimplencia', vinheria: v })}>Simular inadimplência</Botao>
                  </>
                )}
              </div>
            </Cartao>
          )
        })}
      </ul>

      <Modal
        aberto={novaAberta}
        onFechar={() => setNovaAberta(false)}
        titulo="Nova vinheria"
        rodape={
          <>
            <Botao variante="neutro" onClick={() => setNovaAberta(false)}>Cancelar</Botao>
            <Botao type="submit" form="form-vinheria" carregando={ocupado}>Cadastrar</Botao>
          </>
        }
      >
        <form id="form-vinheria" onSubmit={criar} className="space-y-4">
          <Campo rotulo="Nome da vinheria" required maxLength={50} placeholder="Ex.: Adega Santa Cruz" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          <Campo rotulo="Vencimento da mensalidade (opcional, padrão 90 dias)" type="date" value={form.vencimento} onChange={(e) => setForm({ ...form, vencimento: e.target.value })} />
          <Aviso nivel="info">O identificador técnico e a chave dos dispositivos são gerados sozinhos a partir do nome.</Aviso>
        </form>
      </Modal>

      <Confirmar
        aberto={!!acao}
        titulo={acao ? TEXTOS[acao.tipo].titulo : ''}
        confirmarTexto={acao ? TEXTOS[acao.tipo].botao : ''}
        perigo={acao ? TEXTOS[acao.tipo].perigo : false}
        carregando={ocupado}
        onConfirmar={executar}
        onCancelar={() => setAcao(null)}
      >
        {acao?.tipo === 'reativar' ? (
          <p className="text-sm">Os Nodes de <strong>{acao.vinheria.nome}</strong> voltam a publicar e a alertar. Se o vencimento já passou, ele é renovado por 30 dias.</p>
        ) : (
          acao && (
            <p className="text-sm">
              Os Nodes de <strong>{acao.vinheria.nome}</strong> param de publicar e apagam LED e buzzer, e o painel da vinheria mostra o aviso de serviço suspenso. O histórico é preservado e dá para reativar depois.
            </p>
          )
        )}
      </Confirmar>
    </div>
  )
}
