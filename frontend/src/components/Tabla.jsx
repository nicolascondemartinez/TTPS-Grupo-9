// Tabla con scroll horizontal en pantallas angostas.
// columnas: [{ clave, titulo, render?(fila) }]   filas: array de objetos con `id`.
// Con onSeleccionar, las filas se pueden elegir (clic o Enter) y la elegida se resalta.
export default function Tabla({ columnas, filas, titulo, seleccionadaId, onSeleccionar, vacio = 'No hay datos para mostrar.' }) {
  return (
    <div className="tarjeta">
      <div className="tabla-contenedor">
        <table className="tabla">
          {titulo && <caption className="sr-only">{titulo}</caption>}
          <thead>
            <tr>{columnas.map((c) => <th key={c.clave} scope="col">{c.titulo}</th>)}</tr>
          </thead>
          <tbody>
            {filas.length === 0 && (
              <tr><td className="tabla__vacio" colSpan={columnas.length}>{vacio}</td></tr>
            )}
            {filas.map((fila) => (
              <tr
                key={fila.id}
                className={onSeleccionar ? 'tabla__fila--clic' : undefined}
                aria-selected={onSeleccionar ? fila.id === seleccionadaId : undefined}
                tabIndex={onSeleccionar ? 0 : undefined}
                onClick={onSeleccionar ? () => onSeleccionar(fila) : undefined}
                onKeyDown={onSeleccionar ? (e) => e.key === 'Enter' && onSeleccionar(fila) : undefined}
              >
                {columnas.map((c) => <td key={c.clave}>{c.render ? c.render(fila) : fila[c.clave]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
