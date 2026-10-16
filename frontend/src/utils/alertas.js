// Textos dos alertas (usados no Painel e na tela Alertas).
import { TIPOS_ALERTA, VARIAVEIS } from '../data/constantes'
import { formatarNumero, formatarValor } from './formatacao'

/** "Temperatura acima do limite", "Node offline"... */
export function tituloAlerta(alerta) {
  const tipo = TIPOS_ALERTA[alerta.variavel]
  if (alerta.variavel === 'offline') return 'Node offline'
  if (alerta.variavel === 'estabilidade') return 'Temperatura instável'
  return `${tipo.rotulo} ${alerta.sentido === 'acima' ? 'acima' : 'abaixo'} do limite`
}

/** Frase com o valor e o limite. */
export function descreverAlerta(alerta) {
  if (alerta.variavel === 'offline') return 'O Node parou de enviar leituras.'
  if (alerta.variavel === 'estabilidade') {
    return `A temperatura variou ${formatarNumero(alerta.valor, 1)} °C em 24 h (limite ${formatarNumero(alerta.limite, 1)} °C).`
  }
  const limite = alerta.sentido === 'acima' ? 'máximo' : 'mínimo'
  return `Leitura de ${formatarValor(alerta.variavel, alerta.valor)}, ${limite} de ${formatarValor(alerta.variavel, alerta.limite)}.`
}

/** true se for um alerta de uma das 3 variáveis medidas. */
export const ehDeVariavel = (alerta) => alerta.variavel in VARIAVEIS
