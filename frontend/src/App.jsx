import { Navigate, Route, Routes } from 'react-router-dom'
import EnConstruccion from './components/EnConstruccion.jsx'
import Design from './design/Design.jsx'
import AppLayout from './layout/AppLayout.jsx'
import { MENU } from './constants/roles.js'
import Ingreso from './pages/acceso/Ingreso.jsx'
import { useSesion } from './sesion/SesionContext.jsx'

// Rutas de la aplicación.
// Para sumar una pantalla interna: agregar <Route path="/rol/algo" element={<MiPantalla />} />
// dentro de <AppLayout> (y su ítem en constants/roles.js si va en el menú).
export default function App() {
  const { usuario } = useSesion()
  const inicio = MENU[usuario.rol][0].ruta
  const rutasDelMenu = [...new Set(Object.values(MENU).flat().map((i) => i.ruta))]

  return (
    <Routes>
      <Route path="/design" element={<Design />} />
      <Route path="/ingreso" element={<Ingreso />} />

      <Route element={<AppLayout />}>
        <Route index element={<Navigate to={inicio} replace />} />
        {/* Pantallas reales: van acá, antes de las rutas provisorias */}

        {rutasDelMenu.map((ruta) => <Route key={ruta} path={ruta} element={<EnConstruccion />} />)}
        <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
      </Route>
    </Routes>
  )
}
