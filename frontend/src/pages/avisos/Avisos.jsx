import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import { useAvisos } from '../../avisos/AvisosContext.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import './avisos.css'

export default function Avisos() {
  const { refrescar } = useAvisos()
  const [avisos, setAvisos] = useState(null)
  const [error, setError] = useState(false)

  const cargar = useCallback(async () => {
    try {
      const respuesta = await api.get('/avisos')
      setAvisos(respuesta.avisos)
      setError(false)
    } catch {
      setError(true)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  async function marcarLeido(aviso) {
    if (aviso.leido) return
    try {
      await api.post(`/avisos/${aviso.id}/leido`)
      setAvisos((lista) => lista.map((a) => (a.id === aviso.id ? { ...a, leido: true } : a)))
      refrescar()
    } catch {
      cargar()
    }
  }

  async function leerTodos() {
    try {
      await api.post('/avisos/leer-todos')
      setAvisos((lista) => lista.map((a) => ({ ...a, leido: true })))
      refrescar()
    } catch {
      cargar()
    }
  }

  const hayPendientes = avisos?.some((a) => !a.leido)

  return (
    <>
      <EncabezadoPagina etiqueta="Novedades" titulo="Avisos">
        {hayPendientes && <button type="button" className="enlace" onClick={leerTodos}>Marcar todos como leídos</button>}
      </EncabezadoPagina>

      {error && <Tarjeta titulo="No se pudieron cargar los avisos" subtitulo="Probá de nuevo en unos segundos." />}
      {!error && avisos === null && <p>Cargando…</p>}
      {avisos?.length === 0 && <Tarjeta titulo="No tenés avisos" subtitulo="Cuando haya novedades van a aparecer acá." />}

      {avisos?.length > 0 && (
        <ul className="avisos">
          {avisos.map((aviso) => (
            <li key={aviso.id}>
              <button
                type="button"
                className={`aviso${aviso.leido ? '' : ' aviso--pendiente'}`}
                onClick={() => marcarLeido(aviso)}
              >
                <span className="aviso__titulo">{aviso.titulo}</span>
                <span className="aviso__mensaje">{aviso.mensaje}</span>
                <span className="aviso__fecha">
                  {new Date(aviso.creado_en).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}