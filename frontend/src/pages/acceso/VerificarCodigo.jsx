import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import IngresoLayout from '../../layout/IngresoLayout.jsx'
import { destinoTrasIngresar } from '../../sesion/acceso.js'
import { useSesion } from '../../sesion/SesionContext.jsx'
import './acceso.css'
import { codigoDeError, ERRORES_TERMINALES, mensajeDeError } from './errores.js'

// Dispositivo nuevo: el backend mandó un código de 6 dígitos por mail. Se llega desde Ingreso con
// { desafioId, correo (enmascarado), desde } en el state de la navegación.
export default function VerificarCodigo() {
  const { estado, usuario, verificarCodigo } = useSesion()
  const navigate = useNavigate()
  const { state } = useLocation()
  const [codigo, setCodigo] = useState('')
  const [error, setError] = useState('')
  const [terminal, setTerminal] = useState(false)
  const [enviando, setEnviando] = useState(false)

  const desde = state?.desde
  if (estado === 'autenticado') return <Navigate to={destinoTrasIngresar(usuario, desde)} replace />
  if (!state?.desafioId) return <Navigate to="/ingreso" replace />

  const enviar = async (e) => {
    e.preventDefault()
    if (enviando || terminal) return
    if (!/^\d{6}$/.test(codigo)) {
      setError('Ingresá los 6 dígitos del código.')
      return
    }
    setError('')
    setEnviando(true)
    try {
      await verificarCodigo(state.desafioId, codigo)
    } catch (err) {
      setError(mensajeDeError(err))
      setCodigo('')
      if (ERRORES_TERMINALES.includes(codigoDeError(err))) setTerminal(true)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <IngresoLayout>
      <div className="ingreso__encabezado">
        <h2 className="ingreso__form-titulo">Verificá tu dispositivo</h2>
        <p className="ingreso__form-bajada">
          Ingresaste desde un dispositivo nuevo. Te enviamos un código de 6 dígitos a {state.correo}.
        </p>
      </div>
      <form className="ingreso__form" onSubmit={enviar} noValidate>
        <Campo
          etiqueta="Código de verificación" type="text" inputMode="numeric" autoComplete="one-time-code"
          maxLength={6} placeholder="000000" value={codigo} disabled={terminal}
          onChange={(e) => setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))} required
        />
        {error && <p role="alert" className="acceso__error">{error}</p>}
        <Boton type="submit" anchoCompleto className="btn--grande" disabled={enviando || terminal}>
          {enviando ? 'Verificando…' : 'Verificar'}
        </Boton>
      </form>
      <div className="acceso__acciones">
        <p className="acceso__ayuda">El código vence a los 10 minutos.</p>
        <button type="button" className="enlace" onClick={() => navigate('/ingreso', { replace: true, state: { desde } })}>
          Volver a ingresar
        </button>
      </div>
    </IngresoLayout>
  )
}
