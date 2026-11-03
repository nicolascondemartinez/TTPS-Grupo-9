import { Link } from 'react-router-dom'
import IngresoLayout from '../../layout/IngresoLayout.jsx'
import { useSesion } from '../../sesion/SesionContext.jsx'
import './acceso.css'

// Se muestra cuando el usuario abre una ruta de otro rol (por ejemplo, un paciente en /administrativo/...).
// El backend igual valida los permisos de cada endpoint: esto solo evita mostrar pantallas que no le corresponden.
export default function AccesoDenegado() {
  const { cerrarSesion } = useSesion()
  return (
    <IngresoLayout>
      <div className="ingreso__encabezado">
        <h2 className="ingreso__form-titulo">Acceso denegado</h2>
        <p className="ingreso__form-bajada">No tenés permiso para ver esta pantalla.</p>
      </div>
      <div className="acceso__acciones">
        <Link className="enlace" to="/">Volver al inicio</Link>
        <button type="button" className="enlace" onClick={cerrarSesion}>Cerrar sesión</button>
      </div>
    </IngresoLayout>
  )
}
