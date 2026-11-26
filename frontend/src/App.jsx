import { Navigate, Route, Routes } from 'react-router-dom'
import EnConstruccion from './components/EnConstruccion.jsx'
import Design from './design/Design.jsx'
import AppLayout from './layout/AppLayout.jsx'
import { MENU } from './constants/roles.js'
import CambioContrasena from './pages/acceso/CambioContrasena.jsx'
import FormularioPatologia from './pages/gerente/FormularioPatologia.jsx'
import Patologias from './pages/gerente/Patologias.jsx'
import AltaPaciente from './pages/medico/AltaPaciente.jsx'
import PacientesMedico from './pages/medico/Pacientes.jsx'
import Ingreso from './pages/acceso/Ingreso.jsx'
import Registro from './pages/acceso/Registro.jsx'
import Presupuestos from './pages/administrativo/Presupuestos.jsx'
import Turno from './pages/paciente/Turno.jsx'
import PresupuestoPago from './pages/paciente/PresupuestoPago.jsx'
import VerificarCodigo from './pages/acceso/VerificarCodigo.jsx'
import RutaProtegida from './sesion/RutaProtegida.jsx'
import { useSesion } from './sesion/SesionContext.jsx'
import { AvisosProvider } from './avisos/AvisosContext.jsx'
import Avisos from './pages/avisos/Avisos.jsx'
import OrdenDelDia from './pages/transportista/OrdenDelDia.jsx'
import Transportistas from './pages/administrativo/Transportistas.jsx'
import FormularioTransportista from './pages/administrativo/FormularioTransportista.jsx'

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
      <Route path="/registro" element={<Registro />} />
      <Route path="/acceso/verificar" element={<VerificarCodigo />} />
      <Route path="/acceso/cambiar-contrasena" element={<CambioContrasena />} />

      <Route element={<RutaProtegida />}>
        <Route element={<AvisosProvider><AppLayout /></AvisosProvider>}>
          <Route index element={<Inicio />} />
          <Route path="/transportista/orden-del-dia" element={<OrdenDelDia />} />
          {/* Pantallas reales: van acá, antes de las rutas provisorias */}
          <Route path="/avisos" element={<Avisos />} />
          <Route path="/gerente/patologias" element={<Patologias />} />
          <Route path="/paciente/pagos" element={<PresupuestoPago />} />
          <Route path="/paciente/turno" element={<Turno />} />
          <Route path="/administrativo/presupuestos" element={<Presupuestos />} />
          <Route path="/administrativo/transportistas" element={<Transportistas />} />
          <Route path="/administrativo/transportistas/nuevo" element={<FormularioTransportista />} />
          <Route path="/gerente/patologias/nueva" element={<FormularioPatologia />} />
          <Route path="/gerente/patologias/:id" element={<FormularioPatologia />} />
          <Route path="/medico/pacientes" element={<PacientesMedico />} />
          <Route path="/medico/pacientes/nuevo" element={<AltaPaciente />} />

          {rutasDelMenu.map((ruta) => <Route key={ruta} path={ruta} element={<EnConstruccion />} />)}
          <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
        </Route>
      </Route>
    </Routes>
  )
}
