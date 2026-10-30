import { useEffect, useRef } from 'react'
import Boton from './Boton.jsx'

// Pide confirmación antes de una acción importante (cancelar un turno, registrar una inasistencia,etc)
// Usa <dialog>: se cierra con Esc y el foco queda adentro mientras está abierto
// peligro: el botón de confirmar se muestra en rojo (acciones que no se pueden deshacer)
export default function ModalConfirmacion({
  abierto, titulo, children, textoConfirmar = 'Confirmar', textoCancelar = 'Volver',
  peligro = false, onConfirmar, onCancelar,
}) {
  const dialogo = useRef(null)

  useEffect(() => {
    const d = dialogo.current
    if (abierto && !d.open) d.showModal()
    if (!abierto && d.open) d.close()
  }, [abierto])

  return (
    <dialog
      ref={dialogo} className="modal" aria-labelledby="modal-titulo"
      onCancel={(e) => { e.preventDefault(); onCancelar() }}
    >
      <div className="modal__cuerpo">
        <h2 id="modal-titulo" className="modal__titulo">{titulo}</h2>
        <div className="modal__texto">{children}</div>
        <div className="modal__acciones">
          <Boton variante="secundario" onClick={onCancelar}>{textoCancelar}</Boton>
          <Boton className={peligro ? 'btn-peligro' : undefined} onClick={onConfirmar}>{textoConfirmar}</Boton>
        </div>
      </div>
    </dialog>
  )
}
