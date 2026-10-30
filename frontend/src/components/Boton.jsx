// Botón. variante: primario | secundario | ghost. Acepta cualquier prop de <button>.
export default function Boton({ variante = 'primario', anchoCompleto = false, icono, children, type = 'button', ...props }) {
  const clases = ['btn', `btn-${variante}`, anchoCompleto && 'btn--ancho', props.className].filter(Boolean).join(' ')
  return (
    <button type={type} {...props} className={clases}>
      {icono}
      {children}
    </button>
  )
}
