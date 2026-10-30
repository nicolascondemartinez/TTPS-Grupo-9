// Encabezado de cada pantalla: etiqueta de sección, título y acciones a la derecha.
export default function EncabezadoPagina({ etiqueta, titulo, children }) {
  return (
    <header className="encabezado">
      <div className="encabezado__textos">
        {etiqueta && <span className="etiqueta">{etiqueta}</span>}
        <h1 className="encabezado__titulo">{titulo}</h1>
      </div>
      {children && <div className="encabezado__acciones">{children}</div>}
    </header>
  )
}
