import { Link } from 'react-router-dom'
import bannerVinhedo from '../assets/img/banner-vinhedo.webp'
import ameacaLuz from '../assets/img/ameaca-luz.webp'
import ameacaTemperatura from '../assets/img/ameaca-temperatura.webp'
import ameacaUmidade from '../assets/img/ameaca-umidade.webp'
import heroAdega from '../assets/img/hero-adega.webp'
import Cartao from '../components/Cartao'
import Icone from '../components/Icone'
import { LISTA_VARIAVEIS, VARIAVEIS } from '../data/constantes'

const AMEACAS = [
  { variavel: 'temperature', imagem: ameacaTemperatura, texto: 'O calor acelera o envelhecimento. E mais do que o valor, o que prejudica é a temperatura que sobe e desce.' },
  { variavel: 'humidity', imagem: ameacaUmidade, texto: 'Umidade baixa resseca as rolhas e prejudica o vinho com o tempo. Umidade muito alta danifica rótulos e caixas.' },
  { variavel: 'luminosity', imagem: ameacaLuz, texto: 'Luz forte altera a cor e o sabor, sobretudo em espumantes e em garrafas de vidro claro.' },
]

const CAMADAS = [
  { nome: 'Percepção', icone: 'chip', texto: 'O WineGuard Node, um ESP32 com sensor de temperatura e umidade, sensor de luz, LED RGB, buzzer e tela OLED.' },
  { nome: 'Comunicação', icone: 'sinal', texto: 'O Node envia as leituras por Wi-Fi, com o protocolo MQTT, e recebe comandos pelo mesmo caminho.' },
  { nome: 'Plataforma', icone: 'servidor', texto: 'FIWARE: o IoT Agent traduz as mensagens, o Orion guarda o último valor e o STH-Comet guarda o histórico.' },
  { nome: 'Aplicação', icone: 'ajustes', texto: 'O backend confere os limites de cada adega a cada 5 segundos e manda ao Node o comando de alerta.' },
  { nome: 'Apresentação', icone: 'painel', texto: 'Este painel, que funciona no computador e no celular.' },
]

/** Duração do som do buzzer em milissegundos: liga, desliga, liga... (igual ao firmware). */
const PADROES_SOM = { alta: [600, 600], baixa: [300, 250, 300, 1000] }

/** Desenho do ritmo do buzzer: barra cheia = som, espaço = silêncio. */
function RitmoSom({ padrao, rotulo }) {
  return (
    <span className="flex h-3 items-center" role="img" aria-label={rotulo}>
      {padrao.map((ms, i) => (
        <span key={i} style={{ width: ms / 12 }} className={`h-full ${i % 2 === 0 ? 'rounded-sm bg-bordo' : ''}`} />
      ))}
    </span>
  )
}

const TH = 'py-2 pr-4 font-bold'

/** Página inicial: explica o produto, como funciona e quem fez. */
export default function Home() {
  return (
    <div>
      {/* abertura: a foto da adega é o momento principal da página */}
      <section className="relative isolate flex min-h-[100svh] items-center overflow-hidden bg-tinta text-papel">
        <img src={heroAdega} alt="" className="absolute inset-0 -z-20 size-full object-cover object-center" fetchPriority="high" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-tinta/90 via-tinta/60 to-tinta/10" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-t from-tinta/60 via-transparent to-tinta/30" />
        <div className="mx-auto w-full max-w-7xl px-4 pb-16 pt-32">
          <h1 className="max-w-3xl text-5xl leading-[1.05] md:text-7xl">Cada garrafa no ponto certo.</h1>
          <p className="mt-5 max-w-xl text-lg text-papel/90">
            O WineGuard vigia a temperatura, a umidade e a luz de cada adega e avisa na hora, com luz, som e tela, quando algo sai do lugar.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/painel" className="rounded-md bg-papel px-5 py-2.5 text-sm font-bold text-bordo hover:bg-creme">Abrir o painel</Link>
            <Link to="/dispositivos?novo=1" className="rounded-md border border-papel/70 px-5 py-2.5 text-sm font-bold text-papel hover:bg-papel/15">Cadastrar um dispositivo</Link>
          </div>
        </div>
      </section>

      {/* o que ameaça o vinho */}
      <section className="mx-auto max-w-7xl px-4 py-14" aria-labelledby="titulo-ameacas">
        <h2 id="titulo-ameacas" className="text-3xl">O que ameaça o vinho na adega</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {AMEACAS.map(({ variavel, imagem, texto }) => {
            const info = VARIAVEIS[variavel]
            return (
              <article key={variavel} className="overflow-hidden rounded-lg border border-linha bg-papel">
                <img src={imagem} alt="" loading="lazy" className="aspect-[4/3] w-full object-cover" />
                <div className="p-5">
                  <p className="flex items-center gap-2 font-titulo text-xl" style={{ color: info.cor }}>
                    <Icone nome={info.icone} className="size-6" />
                    {info.rotulo}
                  </p>
                  <p className="mt-2 text-tinta">{texto}</p>
                </div>
              </article>
            )
          })}
        </div>
        <p className="mt-4 text-sm text-suave">Resumo de recomendações de especialistas. As fontes estão na tela Triggers.</p>
      </section>

      {/* como funciona (uma sequência de verdade: numerada) */}
      <section className="border-y border-linha bg-papel" aria-labelledby="titulo-camadas">
        <div className="mx-auto max-w-7xl px-4 py-14">
          <h2 id="titulo-camadas" className="text-3xl">Como funciona, em cinco camadas</h2>
          <ol className="mt-10 grid gap-0 md:grid-cols-5 md:gap-6">
            {CAMADAS.map((c, i) => (
              <li key={c.nome} className="relative flex gap-4 pb-8 last:pb-0 md:block md:pb-0">
                <span className="relative inline-grid size-14 shrink-0 place-items-center rounded-xl bg-bordo text-creme">
                  <Icone nome={c.icone} className="size-7" />
                  <span className="numero absolute -right-2 -top-2 grid size-6 place-items-center rounded-full bg-papel text-xs font-bold text-bordo ring-2 ring-bordo">{i + 1}</span>
                </span>
                {i < CAMADAS.length - 1 && (
                  <>
                    <span aria-hidden="true" className="absolute left-16 top-7 -right-6 hidden h-0.5 bg-bordo/25 md:block" />
                    <span aria-hidden="true" className="absolute bottom-0 left-7 top-16 -ml-px w-0.5 bg-bordo/25 md:hidden" />
                  </>
                )}
                <div className="md:mt-5">
                  <h3 className="font-titulo text-xl">{c.nome}</h3>
                  <p className="mt-1 text-sm text-tinta">{c.texto}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* vinheria > adega > node */}
      <section className="mx-auto max-w-7xl px-4 py-14" aria-labelledby="titulo-modelo">
        <h2 id="titulo-modelo" className="text-3xl">Uma plataforma, várias vinherias</h2>
        <p className="mt-2 max-w-2xl text-suave">Cada vinheria vê só os seus dados. Dentro dela, cada adega tem um ou mais Nodes, e cada Node tem os seus limites.</p>
        <div className="mt-6 rounded-lg border border-bordo/40 p-4">
          <p className="font-bold text-bordo">Vinheria</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {['Adega 1', 'Adega 2'].map((adega, i) => (
              <Cartao key={adega} tom="marca" className="p-4 pl-5">
                <p className="font-bold">{adega}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(i === 0 ? ['Node wgn001'] : ['Node wgn002', 'Node wgn003']).map((n) => (
                    <span key={n} className="numero inline-flex items-center gap-1.5 rounded-full border border-linha px-3 py-1 text-sm">
                      <Icone nome="chip" className="size-4 text-bordo" />
                      {n}
                    </span>
                  ))}
                </div>
              </Cartao>
            ))}
          </div>
        </div>
      </section>

      {/* alertas que se entendem sem ler */}
      <section className="border-y border-linha bg-papel" aria-labelledby="titulo-alertas">
        <div className="mx-auto max-w-7xl px-4 py-14">
          <h2 id="titulo-alertas" className="text-3xl">Alertas que se entendem sem ler</h2>
          <p className="mt-2 max-w-2xl text-suave">
            A cor do LED e a tela dizem qual variável saiu do ponto. O LED e o som dizem se o valor ficou acima ou abaixo do limite.
          </p>

          <div className="mt-8 grid gap-5 lg:grid-cols-2">
            <Cartao tom="marca" className="p-5 pl-6">
              <h3 className="text-xl">Qual variável</h3>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[20rem] text-left text-sm">
                  <thead className="border-b border-linha text-suave">
                    <tr><th className={TH}>Variável</th><th className={TH}>Cor do LED</th><th className="font-bold">Tela do Node</th></tr>
                  </thead>
                  <tbody>
                    {LISTA_VARIAVEIS.map((v) => {
                      const info = VARIAVEIS[v]
                      return (
                        <tr key={v} className="border-b border-linha/60 last:border-0">
                          <td className="py-3 pr-4 font-bold" style={{ color: info.cor }}>{info.rotulo}</td>
                          <td className="pr-4">{info.corLed}</td>
                          <td>o nome, o valor e o limite</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Cartao>

            <Cartao tom="alerta" className="p-5 pl-6">
              <h3 className="text-xl">Acima ou abaixo do limite</h3>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[28rem] text-left text-sm">
                  <thead className="border-b border-linha text-suave">
                    <tr><th className={TH}>Situação</th><th className={TH}>LED</th><th className={TH}>Buzzer</th><th className="font-bold">Tela do Node</th></tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-linha/60">
                      <td className="py-3 pr-4 font-bold">Alta (acima do limite)</td>
                      <td className="pr-4">Fixo</td>
                      <td className="pr-4">
                        Bipe longo, repetido
                        <RitmoSom padrao={PADROES_SOM.alta} rotulo="Ritmo: um som longo, uma pausa" />
                      </td>
                      <td>&quot;ALTA&quot;, o valor e o limite máximo</td>
                    </tr>
                    <tr>
                      <td className="py-3 pr-4 font-bold">Baixa (abaixo do limite)</td>
                      <td className="pr-4">Pisca junto com o som</td>
                      <td className="pr-4">
                        2 bipes e uma pausa
                        <RitmoSom padrao={PADROES_SOM.baixa} rotulo="Ritmo: dois sons curtos, uma pausa longa" />
                      </td>
                      <td>&quot;BAIXA&quot;, o valor e o limite mínimo</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Cartao>
          </div>

          <p className="mt-5 max-w-2xl text-sm text-tinta">
            Com mais de uma variável em alerta, o Node alterna entre elas, com uma pausa de silêncio no meio. O botão do aparelho silencia só o buzzer: o LED continua.
          </p>
        </div>
      </section>

      {/* faixa final: a foto do vinhedo escurece até a cor do rodapé */}
      <section className="relative isolate overflow-hidden bg-bordo-escuro text-creme" aria-labelledby="titulo-final">
        <img src={bannerVinhedo} alt="" loading="lazy" className="absolute inset-0 -z-20 size-full object-cover" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-bordo-escuro/40 via-bordo-escuro/55 to-bordo-escuro" />
        <div className="mx-auto max-w-7xl px-4 pb-20 pt-28 md:pb-24 md:pt-40">
          <h2 id="titulo-final" className="max-w-2xl text-3xl md:text-5xl">Sua adega no ponto certo, a qualquer hora.</h2>
          <p className="mt-4 max-w-xl text-lg text-creme/90">Cadastre um Node e acompanhe as leituras em tempo real.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/painel" className="rounded-md bg-creme px-5 py-2.5 text-sm font-bold text-bordo hover:bg-papel">Abrir o painel</Link>
            <Link to="/dispositivos?novo=1" className="rounded-md border border-creme/70 px-5 py-2.5 text-sm font-bold text-creme hover:bg-creme/15">Cadastrar um dispositivo</Link>
          </div>
        </div>
      </section>
    </div>
  )
}
