import { Navigate, Route, Routes } from 'react-router-dom'
import EnConstruccion from './components/EnConstruccion.jsx'
import Design from './design/Design.jsx'
import AppLayout from './layout/AppLayout.jsx'
import { MENU } from './constants/roles.js'
import CambioContrasena from './pages/acceso/CambioContrasena.jsx'
import Ingreso from './pages/acceso/Ingreso.jsx'
import VerificarCodigo from './pages/acceso/VerificarCodigo.jsx'
import RutaProtegida from './sesion/RutaProtegida.jsx'
import { useSesion } from './sesion/SesionContext.jsx'

// Lleva a cada usuario a la primera pantalla de su rol (solo se renderiza con sesión: lo garantiza RutaProtegida).
function Inicio() {
  const { usuario } = useSesion()
  return <Navigate to={MENU[usuario.rol][0].ruta} replace />
}

// Rutas de la aplicación.
// Para sumar una pantalla interna: agregar <Route path="/rol/algo" element={<MiPantalla />} />
// dentro de <AppLayout> (y su ítem en constants/roles.js si va en el menú).
export default function App() {
  const rutasDelMenu = [...new Set(Object.values(MENU).flat().map((i) => i.ruta))]

  return (
    <Routes>
      <Route path="/design" element={<Design />} />
      <Route path="/ingreso" element={<Ingreso />} />
      <Route path="/acceso/verificar" element={<VerificarCodigo />} />
      <Route path="/acceso/cambiar-contrasena" element={<CambioContrasena />} />

      <Route element={<RutaProtegida />}>
        <Route element={<AppLayout />}>
          <Route index element={<Inicio />} />
          {/* Pantallas reales: van acá, antes de las rutas provisorias */}

          {rutasDelMenu.map((ruta) => <Route key={ruta} path={ruta} element={<EnConstruccion />} />)}
          <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
        </Route>
      </Route>
    </Routes>
  )
}
