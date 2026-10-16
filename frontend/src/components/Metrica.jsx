import Cartao from './Cartao'
import Distintivo from './Distintivo'
import Icone from './Icone'

const STATUS = {
  normal: { tom: 'ok', icone: 'check', texto: 'Normal' },
  acima: { tom: 'alerta', icone: 'alerta', texto: 'Acima do limite' },
  abaixo: { tom: 'alerta', icone: 'alerta', texto: 'Abaixo do limite' },
  estavel: { tom: 'ok', icone: 'check', texto: 'Estável' },
  instavel: { tom: 'atencao', icone: 'alerta', texto: 'Instável' },
  'sem-dado': { tom: 'neutro', icone: 'info', texto: 'Sem leitura' },
}

const TOM_CARTAO = { ok: 'ok', alerta: 'alerta', atencao: 'atencao', neutro: 'neutro' }

/**
 * Um cartão da faixa de valores do Painel: ícone, rótulo, número grande,
 * selo de status (sempre com texto) e uma linha de detalhe.
 */
export default function Metrica({ icone, cor, rotulo, valor, unidade, status = 'sem-dado', detalhe }) {
  const s = STATUS[status] ?? STATUS['sem-dado']
  return (
    <Cartao tom={TOM_CARTAO[s.tom]} className="p-4 pl-5 md:p-5 md:pl-6">
      <div className="flex items-center gap-2 text-sm font-bold" style={{ color: cor }}>
        <Icone nome={icone} className="size-5" />
        {rotulo}
      </div>
      <p className="mt-2 flex items-baseline gap-1">
        <span className="numero text-4xl font-bold text-tinta md:text-5xl">{valor}</span>
        <span className="text-base text-suave">{unidade}</span>
      </p>
      <div className="mt-2"><Distintivo tom={s.tom} icone={s.icone}>{s.texto}</Distintivo></div>
      {detalhe && <p className="mt-2 text-xs text-suave">{detalhe}</p>}
    </Cartao>
  )
}
