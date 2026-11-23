import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import Mapa from '../../components/Mapa.jsx'
import ModalConfirmacion from '../../components/ModalConfirmacion.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { codigoDeError, mensajeDeError } from '../acceso/errores.js'
import { conMayuscula, diaCorto, diaLargo, hora } from './fechas.js'

// Sacar turno en 3 pasos: 1) centro (en el mapa o en la lista), 2) día, 3) horario. Después, confirmar.
export default function SacarTurno({ estudioId, alReservar }) {
  const notificar = useNotificar()
  const [centros, setCentros] = useState([])
  const [provincia, setProvincia] = useState('')
  const [centro, setCentro] = useState(null)
  const [dias, setDias] = useState(null) // null = todavía no se eligió centro
  const [dia, setDia] = useState(null)
  const [franja, setFranja] = useState(null)
  const [confirmando, setConfirmando] = useState(false)
  const [reservando, setReservando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/centros').then((d) => setCentros(d.centros)).catch((e) => setError(mensajeDeError(e)))
  }, [])

  const provincias = useMemo(() => [...new Set(centros.map((c) => c.provincia))].sort(), [centros])
  const visibles = useMemo(() => (provincia ? centros.filter((c) => c.provincia === provincia) : centros), [centros, provincia])

  const cargarDias = (c) => {
    setDias(null)
    setDia(null)
    setFranja(null)
    api.get(`/centros/${c.id}/turnos-libres`)
      .then((d) => { setDias(d.dias); setDia(d.dias[0] ?? null) })
      .catch((e) => setError(mensajeDeError(e)))
  }

  const elegirCentro = (c) => {
    setCentro(c)
    setError('')
    cargarDias(c)
  }

  const reservar = async () => {
    setConfirmando(false)
    setReservando(true)
    try {
      await api.post(`/estudios/${estudioId}/turno`, { centro_id: centro.id, fecha_hora: franja })
      notificar('Turno reservado')
      alReservar()
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
      // Si otra persona lo tomó recién, se vuelven a pedir los horarios para no ofrecer el ocupado.
      if (codigoDeError(e) === 'TURNO_OCUPADO') cargarDias(centro)
    } finally {
      setReservando(false)
    }
  }

  return (
    <div className="turnos">
      {error && <p role="alert" className="turnos__error">{error}</p>}

      <Tarjeta titulo="1. Elegí el centro de extracción" subtitulo="Tocá un punto del mapa o elegilo de la lista.">
        <Campo
          etiqueta="Provincia" value={provincia} onChange={(e) => setProvincia(e.target.value)}
          opciones={[{ valor: '', texto: 'Todas las provincias' }, ...provincias.map((p) => ({ valor: p, texto: p }))]}
        />
        <Mapa centros={visibles} centroSeleccionadoId={centro?.id} onSeleccionarCentro={elegirCentro} altura={320} />
        <ul className="turnos__centros" aria-label="Centros de extracción">
          {visibles.map((c) => (
            <li key={c.id}>
              <button
                type="button" className="turnos__centro" aria-pressed={c.id === centro?.id} onClick={() => elegirCentro(c)}
              >
                <strong>{c.nombre}</strong>
                <span>{c.direccion} · {c.provincia}</span>
              </button>
            </li>
          ))}
        </ul>
      </Tarjeta>

      {centro && (
        <Tarjeta titulo="2. Elegí el día y el horario" subtitulo={`${centro.nombre} · ${centro.direccion}`}>
          {dias === null && <p role="status">Buscando turnos libres…</p>}
          {dias?.length === 0 && <p className="turnos__texto">Este centro no tiene turnos libres en los próximos 30 días.</p>}
          {dias?.length > 0 && (
            <>
              <div className="turnos__dias" role="group" aria-label="Días con turnos libres">
                {dias.map((d) => (
                  <button
                    key={d.fecha} type="button" className="turnos__opcion" aria-pressed={d.fecha === dia?.fecha}
                    onClick={() => { setDia(d); setFranja(null) }}
                  >
                    {diaCorto(d.fecha)}
                  </button>
                ))}
              </div>
              {dia && (
                <>
                  <p className="turnos__subtitulo">Horarios libres del {diaLargo(dia.fecha)}</p>
                  <div className="turnos__franjas" role="group" aria-label="Horarios libres">
                    {dia.franjas.map((f) => (
                      <button
                        key={f} type="button" className="turnos__opcion" aria-pressed={f === franja}
                        onClick={() => setFranja(f)}
                      >
                        {hora(f)}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </Tarjeta>
      )}

      {franja && (
        <Tarjeta titulo="3. Confirmá tu turno" filo>
          <p>
            <strong>{conMayuscula(diaLargo(dia.fecha))}, a las {hora(franja)} hs</strong><br />
            {centro.nombre} · {centro.direccion}
          </p>
          <p className="turnos__texto">No necesitás ninguna preparación especial (no hace falta ayuno).</p>
          <div className="turnos__acciones">
            <Boton onClick={() => setConfirmando(true)} disabled={reservando}>
              {reservando ? 'Reservando…' : 'Reservar turno'}
            </Boton>
          </div>
        </Tarjeta>
      )}

      {franja && (
        <ModalConfirmacion
          abierto={confirmando} titulo="¿Reservás este turno?" textoConfirmar="Reservar"
          onConfirmar={reservar} onCancelar={() => setConfirmando(false)}
        >
          {conMayuscula(diaLargo(dia.fecha))}, a las {hora(franja)} hs, en {centro.nombre}.
        </ModalConfirmacion>
      )}
    </div>
  )
}
