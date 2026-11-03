import { Navigate, Outlet, useLocation } from 'react-router-dom'
import AccesoDenegado from '../pages/acceso/AccesoDenegado.jsx'
import { puedeAcceder } from './acceso.js'
import { useSesion } from './SesionContext.jsx'

/**
 * Guard de rutas internas:
 *  - sin sesión -> /ingreso (guardando la ruta para volver después de ingresar)
 *  - primer ingreso -> /acceso/cambiar-contrasena
 *  - ruta de otro rol -> Acceso denegado
 * Ocultar ítems del menú no reemplaza esto, y esto no reemplaza los permisos del backend.
 */
export default function RutaProtegida() {
  const { estado, usuario } = useSesion()
  const location = useLocation()

  if (estado === 'cargando') return <p role="status" className="acceso__cargando">Cargando…</p>
  if (estado === 'anonimo') return <Navigate to="/ingreso" replace state={{ desde: location }} />
  if (estado === 'cambio_contrasena_requerido') {
    return <Navigate to="/acceso/cambiar-contrasena" replace state={{ desde: location }} />
  }
  if (!puedeAcceder(usuario.rol, location.pathname)) return <AccesoDenegado />
  return <Outlet />
}
