const TONS = {
  ok: 'before:bg-ok',
  alerta: 'before:bg-alerta',
  atencao: 'before:bg-atencao',
  neutro: 'before:bg-suave/40',
  marca: 'before:bg-bordo',
}

/**
 * Cartão padrão do site: superfície clara, borda fina e uma faixa colorida na esquerda
 * que indica o estado (a cor nunca é a única pista: o texto do cartão diz o mesmo).
 * `as` troca a tag (ex.: "li").
 */
export default function Cartao({ as: Tag = 'div', tom = 'neutro', className = '', children, ...resto }) {
  return (
    <Tag
      className={`relative overflow-hidden rounded-lg border border-linha bg-papel before:absolute before:inset-y-0 before:left-0 before:w-1 ${TONS[tom] ?? TONS.neutro} ${className}`}
      {...resto}
    >
      {children}
    </Tag>
  )
}
