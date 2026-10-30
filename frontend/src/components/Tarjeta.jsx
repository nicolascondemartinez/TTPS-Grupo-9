// Tarjeta blanca. `filo` agrega la franja superior de degradé (para destacar).
export default function Tarjeta({ titulo, subtitulo, filo = false, children }) {
  return (
    <section className={`tarjeta${filo ? ' tarjeta-filo' : ''}`}>
      <div className="tarjeta__cuerpo">
        {(titulo || subtitulo) && (
          <div>
            {titulo && <h2 className="tarjeta__titulo">{titulo}</h2>}
            {subtitulo && <p className="tarjeta__subtitulo">{subtitulo}</p>}
          </div>
        )}
        {children}
      </div>
    </section>
  )
}
