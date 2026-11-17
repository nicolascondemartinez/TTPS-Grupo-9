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
  const [estudio, setEstudio] = useState(null)        // el estudio del paciente, arranca vacío hasta que llega del back
  const [estado, setEstado] = useState('cargando')    // cargando | listo | error
  const [error, setError] = useState('')              // el texto del error, si algo sale mal

  const cargar = useCallback(() => {
    //useCallback sirve para que la función no se vuelva a crear en cada renderizado, 
    // evitando así que el useEffect se ejecute de nuevo innecesariamente.
    setEstado('cargando')
    setError('')                     // limpio el error anterior por si quedó alguno
    api.get('/presupuestos/mios')    // trae los estudios del paciente logueado
      .then((d) => {
        // Se trabaja con el estudio más reciente (el backend los manda del más nuevo al más viejo).
        setEstudio(d.estudios[0] ?? null)             // si no tiene ninguno, queda en null
        setEstado('listo')
      })
      .catch((e) => { setError(mensajeDeError(e)); setEstado('error') })   // mensajeDeError lo pasa a un texto entendible
  }, [])

  useEffect(cargar, [cargar])   // se ejecuta una sola vez, cuando aparece la pantalla

  return (
    <>
      <EncabezadoPagina etiqueta="Extracción" titulo="Turno" />
      {/* según el estado muestro una cosa u otra; el && es "si esto es verdad, mostrá lo de la derecha" */}
      {estado === 'cargando' && <p role="status">Cargando…</p>}
      {estado === 'error' && <p role="alert" className="turnos__error">{error}</p>}
      {/* le paso cargar a Contenido para que, después de reservar o cancelar, se vuelva a pedir el estudio */}
      {estado === 'listo' && <Contenido estudio={estudio} alCambiar={cargar} />}
    </>
  )
}

// Decide qué mostrar según en qué estado está el estudio.
function Contenido({ estudio, alCambiar }) {
  const navigate = useNavigate()                      // para mandar al paciente a otra pantalla

  // no tiene estudios: no hay nada que hacer todavía
  if (!estudio) {
    return <Tarjeta><p>Todavía no tenés estudios. Cuando tu médico te dé de alta uno, vas a poder sacar turno acá.</p></Tarjeta>
  }

  // ya pagó: puede elegir centro, día y horario
  if (estudio.estado === 'pagado') return <SacarTurno estudioId={estudio.estudio_id} alReservar={alCambiar} />

  // ya tiene turno: le muestro cuál es y puede cancelarlo
  if (estudio.estado === 'turno_sacado') return <MiTurno estudioId={estudio.estudio_id} alCancelar={alCambiar} />

  // todavía no pagó: sin pago no hay turno, lo mando a pagar
  if (estudio.estado === 'creado') {
    return (
      <Tarjeta titulo="Primero, el pago">
        <p className="turnos__texto">Para sacar turno, el estudio tiene que estar pagado.</p>
        <div><Boton onClick={() => navigate('/paciente/pagos')}>Ir a presupuesto y pago</Boton></div>
      </Tarjeta>
    )
  }

  // cualquier otro estado (listo para retirar, en viaje a Corea, etc.): la extracción ya pasó, no necesita turno
  return (
    <Tarjeta titulo="No necesitás sacar turno">
      <div><EstadoChip estado={estudio.estado} /></div>
      <p className="turnos__texto">Tu estudio ya pasó la etapa de extracción. Te avisamos por mail cuando haya novedades.</p>
    </Tarjeta>
  )
}
