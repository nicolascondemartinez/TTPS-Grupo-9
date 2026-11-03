import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import IngresoLayout from '../../layout/IngresoLayout.jsx'
import { destinoTrasIngresar } from '../../sesion/acceso.js'
import { useSesion } from '../../sesion/SesionContext.jsx'
import './acceso.css'
import { mensajeDeError } from './errores.js'

const FORMATO_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

// Pantalla de ingreso (visual: docs/diseno/referencia/ingreso.html).
// Según la respuesta de la API:
//   autenticado                 -> vuelve a la ruta que se intentaba abrir (o al inicio de su rol)
//   cambio_contrasena_requerido -> /acceso/cambiar-contrasena (primer ingreso)
//   verificacion_requerida      -> /acceso/verificar (dispositivo nuevo: el código llega por mail)
export default function Ingreso() {
  const { estado, usuario, ingresar } = useSesion()
  const navigate = useNavigate()
  const { state } = useLocation()
  const desde = state?.desde
  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [errores, setErrores] = useState([])
  const [enviando, setEnviando] = useState(false)

  if (estado === 'autenticado') return <Navigate to={destinoTrasIngresar(usuario, desde)} replace />
  if (estado === 'cambio_contrasena_requerido') return <Navigate to="/acceso/cambiar-contrasena" replace state={{ desde }} />

  const enviar = async (e) => {
    e.preventDefault()
    if (enviando) return
    const problemas = []
    if (!correo.trim()) problemas.push('Ingresá tu correo electrónico.')
    else if (!FORMATO_CORREO.test(correo.trim())) problemas.push('El correo electrónico no tiene un formato válido.')
    if (!contrasena) problemas.push('Ingresá tu contraseña.')
    setErrores(problemas)
    if (problemas.length) return

    setEnviando(true)
    try {
      const r = await ingresar(correo.trim(), contrasena)
      if (r.estado === 'verificacion_requerida') {
        navigate('/acceso/verificar', { state: { desafioId: r.desafio_id, correo: r.correo, desde } })
      }
    } catch (err) {
      setErrores([mensajeDeError(err)])
      setContrasena('')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <IngresoLayout>
      <div className="ingreso__encabezado">
        <h2 className="ingreso__form-titulo">Ingresar</h2>
        <p className="ingreso__form-bajada">Si es tu primer ingreso, vas a tener que cambiar la contraseña.</p>
      </div>
      <form className="ingreso__form" onSubmit={enviar} noValidate>
        <Campo
          etiqueta="Correo electrónico" type="email" placeholder="nombre@dominio.com" autoComplete="username"
          value={correo} onChange={(e) => setCorreo(e.target.value)} required
        />
        <Campo
          etiqueta="Contraseña" type="password" autoComplete="current-password"
          value={contrasena} onChange={(e) => setContrasena(e.target.value)} required
        />
        {errores.map((m) => <p key={m} role="alert" className="acceso__error">{m}</p>)}
        <Boton type="submit" anchoCompleto className="btn--grande" disabled={enviando}>
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </Boton>
      </form>
      {/* TODO: flujo de recuperación de contraseña (todavía no está en los escenarios) */}
      <button type="button" className="enlace ingreso__olvido">¿Olvidaste tu contraseña?</button>
    </IngresoLayout>
  )
}
