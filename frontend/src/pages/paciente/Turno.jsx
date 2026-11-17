import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import EstadoChip from '../../components/EstadoChip.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import MiTurno from './MiTurno.jsx'
import SacarTurno from './SacarTurno.jsx'
import './turnos.css'

// Paciente: sacar el turno de extracción o ver el que ya tiene (escenarios "Sacar el turno" y "Cancelar el turno").
// Según el estado del estudio muestra una cosa u otra:
//   pagado        -> elegir centro, día y horario
//   turno_sacado  -> el turno reservado, con la opción de cancelarlo
//   creado        -> primero tiene que pagar
export default function Turno() {
  const [estudio, setEstudio] = useState(null)
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [error, setError] = useState('')

  const cargar = useCallback(() => {
    api.get('/presupuestos/mios')
      .then((d) => {
        // Se trabaja con el estudio más reciente (el backend los manda del más nuevo al más viejo).
        setEstudio(d.estudios[0] ?? null)
        setEstado('listo')
      })
      .catch((e) => { setError(mensajeDeError(e)); setEstado('error') })
  }, [])

  useEffect(cargar, [cargar])

  return (
    <>
      <EncabezadoPagina etiqueta="Extracción" titulo="Turno" />
      {estado === 'cargando' && <p role="status">Cargando…</p>}
      {estado === 'error' && <p role="alert" className="turnos__error">{error}</p>}
      {estado === 'listo' && <Contenido estudio={estudio} alCambiar={cargar} />}
    </>
  )
}

function Contenido({ estudio, alCambiar }) {
  const navigate = useNavigate()
  if (!estudio) {
    return <Tarjeta><p>Todavía no tenés estudios. Cuando tu médico te dé de alta uno, vas a poder sacar turno acá.</p></Tarjeta>
  }
  if (estudio.estado === 'pagado') return <SacarTurno estudioId={estudio.estudio_id} alReservar={alCambiar} />
  if (estudio.estado === 'turno_sacado') return <MiTurno estudioId={estudio.estudio_id} alCancelar={alCambiar} />
  if (estudio.estado === 'creado') {
    return (
      <Tarjeta titulo="Primero, el pago">
        <p className="turnos__texto">Para sacar turno, el estudio tiene que estar pagado.</p>
        <div><Boton onClick={() => navigate('/paciente/pagos')}>Ir a presupuesto y pago</Boton></div>
      </Tarjeta>
    )
  }
  return (
    <Tarjeta titulo="No necesitás sacar turno">
      <div><EstadoChip estado={estudio.estado} /></div>
      <p className="turnos__texto">Tu estudio ya pasó la etapa de extracción. Te avisamos por mail cuando haya novedades.</p>
    </Tarjeta>
  )
}
