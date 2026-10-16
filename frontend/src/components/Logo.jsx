// Marca do WineGuard. Os arquivos .svg ficam em /public (copiados do repositório).
//   variante "navbar"  : símbolo compacto + palavra (para o topo do site)
//   variante "emblema" : emblema grande, colorido (para o Início)
export default function Logo({ variante = 'navbar', className = '' }) {
  if (variante === 'emblema') {
    return <img src="/wineguard-emblema.svg" alt="Emblema do WineGuard" className={`h-auto ${className}`} />
  }
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <img src="/wineguard-simbolo-compacto.svg" alt="" className="h-9 w-auto" />
      <span className="font-titulo text-2xl font-semibold leading-none tracking-tight text-bordo">wineguard</span>
    </span>
  )
}
