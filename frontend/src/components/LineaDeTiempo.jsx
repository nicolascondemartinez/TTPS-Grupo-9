// Historial de cambios (auditoría). items: [{ id, titulo, fecha, usuario }], del más reciente al más viejo.
export default function LineaDeTiempo({ items }) {
  return (
    <ol className="linea-tiempo">
      {items.map((item) => (
        <li key={item.id} className="linea-tiempo__item">
          <span className="linea-tiempo__eje" aria-hidden="true">
            <span className="linea-tiempo__punto" />
            <span className="linea-tiempo__linea" />
          </span>
          <span className="linea-tiempo__texto">
            <span className="linea-tiempo__titulo">{item.titulo}</span>
            <span className="linea-tiempo__detalle">{item.fecha} · {item.usuario ?? 'Sistema'}</span>
          </span>
        </li>
      ))}
    </ol>
  )
}
