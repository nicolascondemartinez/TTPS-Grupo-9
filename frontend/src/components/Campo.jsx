import { useId } from 'react'
import Icono from './Icono.jsx'

// Campo de formulario con etiqueta siempre presente (visible u oculta con etiquetaOculta).
// Acepta cualquier prop de <input>. Con `opciones` se dibuja un <select>.
export default function Campo({ etiqueta, etiquetaOculta = false, ayuda, error, icono, opciones, id, ...props }) {
  const autoId = useId()
  const campoId = id ?? autoId
  const ayudaId = `${campoId}-ayuda`
  const describedBy = error || ayuda ? ayudaId : undefined

  const control = opciones ? (
    <select id={campoId} className="campo" aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...props}>
      {opciones.map((o) => <option key={o.valor} value={o.valor}>{o.texto}</option>)}
    </select>
  ) : (
    <input id={campoId} className="campo" aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...props} />
  )

  return (
    <div className="campo-grupo">
      <label htmlFor={campoId} className={etiquetaOculta ? 'sr-only' : 'campo-grupo__label'}>{etiqueta}</label>
      {icono ? (
        <div className="campo-con-icono">
          <span className="campo-con-icono__icono"><Icono nombre={icono} tamano={18} /></span>
          {control}
        </div>
      ) : control}
      {error && <span id={ayudaId} className="campo-grupo__error">{error}</span>}
      {!error && ayuda && <span id={ayudaId} className="campo-grupo__ayuda">{ayuda}</span>}
    </div>
  )
}
