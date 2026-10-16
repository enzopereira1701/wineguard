import Botao from './Botao'
import Modal from './Modal'

/**
 * Pergunta "Tem certeza?" antes de uma ação difícil de desfazer.
 * Usada ao suspender vinheria, remover dispositivo e salvar limites perigosos.
 */
export default function Confirmar({ aberto, titulo, mensagem, confirmarTexto = 'Confirmar', perigo = false, carregando = false, onConfirmar, onCancelar, children }) {
  return (
    <Modal
      aberto={aberto}
      titulo={titulo}
      onFechar={onCancelar}
      largura="max-w-md"
      rodape={
        <>
          <Botao variante="neutro" onClick={onCancelar}>Cancelar</Botao>
          <Botao variante={perigo ? 'perigo' : 'primario'} carregando={carregando} onClick={onConfirmar}>{confirmarTexto}</Botao>
        </>
      }
    >
      {mensagem && <p className="text-sm">{mensagem}</p>}
      {children}
    </Modal>
  )
}
