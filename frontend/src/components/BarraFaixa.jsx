/**
 * Mostra, na mesma régua, a faixa de REFERÊNCIA (clara = alerta, escura = alvo)
 * e a faixa que o usuário escolheu (barra bordô). Assim ele vê na hora se está longe do recomendado.
 *
 * @param {{ dominio: [number, number], alerta: {min:number,max:number}, alvo: {min:number,max:number},
 *           usuario: {min:number,max:number}, unidade: string, cor: string }} props
 */
export default function BarraFaixa({ dominio, alerta, alvo, usuario, unidade, cor }) {
  const [a, b] = dominio
  const limitar = (n) => Math.min(100, Math.max(0, n))
  const esquerda = (v) => limitar(((v - a) / (b - a)) * 100)
  const largura = (x, y) => limitar(((Math.min(y, b) - Math.max(x, a)) / (b - a)) * 100)
  const usuarioValido = Number.isFinite(usuario.min) && Number.isFinite(usuario.max) && usuario.min < usuario.max

  return (
    <div className="space-y-2">
      <div>
        <p className="mb-1 text-xs text-suave">
          Referência: {alerta.min} a {alerta.max} {unidade} (alvo {alvo.min} a {alvo.max})
        </p>
        <div className="relative h-3 rounded-full bg-linha/60" role="img" aria-label={`Referência de ${alerta.min} a ${alerta.max} ${unidade}`}>
          <div className="absolute inset-y-0 rounded-full" style={{ left: `${esquerda(alerta.min)}%`, width: `${largura(alerta.min, alerta.max)}%`, background: cor, opacity: 0.28 }} />
          <div className="absolute inset-y-0 rounded-full" style={{ left: `${esquerda(alvo.min)}%`, width: `${largura(alvo.min, alvo.max)}%`, background: cor, opacity: 0.7 }} />
        </div>
      </div>
      <div>
        <p className="mb-1 text-xs text-suave">
          Seus limites: {usuarioValido ? `${usuario.min} a ${usuario.max} ${unidade}` : 'incompletos'}
        </p>
        <div className="relative h-3 rounded-full bg-linha/60" role="img" aria-label="Seus limites">
          {usuarioValido && (
            <div className="absolute inset-y-0 rounded-full bg-bordo" style={{ left: `${esquerda(usuario.min)}%`, width: `${largura(usuario.min, usuario.max)}%` }} />
          )}
        </div>
      </div>
      <div className="numero flex justify-between text-[11px] text-suave"><span>{a}</span><span>{b} {unidade}</span></div>
    </div>
  )
}
