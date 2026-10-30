import { useState } from 'react'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import IngresoLayout from '../../layout/IngresoLayout.jsx'

// Pantalla de ingreso: base visual, igual a docs/diseno/referencia/ingreso.html.
// PENDIENTE (Persona 1): enviar el formulario al backend, mostrar el error de credenciales,
// y redirigir al cambio de contraseña (primer ingreso) o al código de verificación (dispositivo nuevo).
export default function Ingreso() {
  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')

  const ingresar = (e) => {
    e.preventDefault()
    // TODO Persona 1: llamar a la API de autenticación con { correo, contrasena }.
  }

  return (
    <IngresoLayout>
      <div className="ingreso__encabezado">
        <h2 className="ingreso__form-titulo">Ingresar</h2>
        <p className="ingreso__form-bajada">Si es tu primer ingreso, vas a tener que cambiar la contraseña.</p>
      </div>
      <form className="ingreso__form" onSubmit={ingresar} noValidate>
        <Campo
          etiqueta="Correo electrónico" type="email" placeholder="nombre@dominio.com" autoComplete="username"
          value={correo} onChange={(e) => setCorreo(e.target.value)} required
        />
        <Campo
          etiqueta="Contraseña" type="password" autoComplete="current-password"
          value={contrasena} onChange={(e) => setContrasena(e.target.value)} required
        />
        <Boton type="submit" anchoCompleto className="btn--grande">Ingresar</Boton>
      </form>
      {/* TODO Persona 1: flujo de recuperación de contraseña (todavía no está en los escenarios) */}
      <button type="button" className="enlace ingreso__olvido">¿Olvidaste tu contraseña?</button>
    </IngresoLayout>
  )
}
