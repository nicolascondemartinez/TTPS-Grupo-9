import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import IngresoLayout from '../../layout/IngresoLayout.jsx'
import { destinoTrasIngresar } from '../../sesion/acceso.js'
import { useSesion } from '../../sesion/SesionContext.jsx'
import './acceso.css'
import { mensajeDeError } from './errores.js'

const LARGO_MINIMO = 8

// Primer ingreso: con el usuario y la contraseña que llegaron por mail solo se puede cambiar la contraseña.
export default function CambioContrasena() {
  const { estado, usuario, cambiarContrasena, cerrarSesion } = useSesion()
  const navigate = useNavigate()
  const { state } = useLocation()
  const desde = state?.desde
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [errores, setErrores] = useState([])
  const [enviando, setEnviando] = useState(false)

  if (estado === 'cargando') return <p role="status" className="acceso__cargando">Cargando…</p>
  if (estado === 'anonimo') return <Navigate to="/ingreso" replace />
  if (estado === 'autenticado') return <Navigate to={destinoTrasIngresar(usuario, desde)} replace />

  const enviar = async (e) => {
    e.preventDefault()
    if (enviando) return
    const problemas = []
    if (!actual) problemas.push('Ingresá la contraseña actual.')
    if (nueva.length < LARGO_MINIMO) problemas.push(`La contraseña nueva debe tener al menos ${LARGO_MINIMO} caracteres.`)
    else if (nueva === actual) problemas.push('La contraseña nueva debe ser distinta de la actual.')
    if (nueva !== confirmacion) problemas.push('La confirmación no coincide con la contraseña nueva.')
    setErrores(problemas)
    if (problemas.length) return

    setEnviando(true)
    try {
      await cambiarContrasena(actual, nueva) // al terminar la sesión pasa a 'autenticado' y se redirige
    } catch (err) {
      setErrores([mensajeDeError(err)])
    } finally {
      setEnviando(false)
    }
  }

  const cancelar = async () => {
    await cerrarSesion()
    navigate('/ingreso', { replace: true })
  }

  return (
    <IngresoLayout>
      <div className="ingreso__encabezado">
        <h2 className="ingreso__form-titulo">Cambiá tu contraseña</h2>
        <p className="ingreso__form-bajada">
          Es tu primer ingreso. Elegí una contraseña nueva para continuar.
        </p>
      </div>
      <form className="ingreso__form" onSubmit={enviar} noValidate>
        <Campo
          etiqueta="Contraseña actual (la que te enviamos por mail)" type="password" autoComplete="current-password"
          value={actual} onChange={(e) => setActual(e.target.value)} required
        />
        <Campo
          etiqueta="Contraseña nueva" type="password" autoComplete="new-password"
          value={nueva} onChange={(e) => setNueva(e.target.value)} required
        />
        <Campo
          etiqueta="Repetí la contraseña nueva" type="password" autoComplete="new-password"
          value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} required
        />
        <p className="acceso__ayuda">Mínimo {LARGO_MINIMO} caracteres, distinta de la actual.</p>
        {errores.map((m) => <p key={m} role="alert" className="acceso__error">{m}</p>)}
        <Boton type="submit" anchoCompleto className="btn--grande" disabled={enviando}>
          {enviando ? 'Guardando…' : 'Cambiar contraseña'}
        </Boton>
      </form>
      <div className="acceso__acciones">
        <button type="button" className="enlace" onClick={cancelar}>Cancelar y salir</button>
      </div>
    </IngresoLayout>
  )
}
