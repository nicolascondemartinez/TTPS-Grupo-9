import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import Avatar from '../components/Avatar.jsx'
import Icono from '../components/Icono.jsx'
import Logo from '../components/Logo.jsx'
import { MENU, ROLES } from '../constants/roles.js'
import { useSesion } from '../sesion/SesionContext.jsx'

// Marco de las pantallas internas: barra lateral con el menú del rol + contenido.
// En el celular la barra se convierte en una barra superior con menú desplegable.
export default function AppLayout() {
  const { usuario, cambiarRol } = useSesion()
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <div className={`app${menuAbierto ? ' app--menu-abierto' : ''}`}>
      <aside className="app__lateral">
        <div className="app__marca">
          <Logo variante="oscuro" />
          <button
            type="button" className="app__menu-boton"
            aria-expanded={menuAbierto} aria-controls="menu-principal"
            onClick={() => setMenuAbierto(!menuAbierto)}
          >
            <Icono nombre={menuAbierto ? 'cerrar' : 'menu'} titulo={menuAbierto ? 'Cerrar menú' : 'Abrir menú'} />
          </button>
        </div>

        <nav id="menu-principal" className="app__nav" aria-label="Principal">
          {MENU[usuario.rol].map((item) => (
            <NavLink key={item.ruta} to={item.ruta} className="app__nav-item" onClick={() => setMenuAbierto(false)}>
              <Icono nombre={item.icono} />
              {item.texto}
            </NavLink>
          ))}
        </nav>

        <div className="app__usuario">
          <div className="app__usuario-fila">
            <Avatar />
            <div>
              <div className="app__usuario-nombre">{usuario.nombre}</div>
              <div className="app__usuario-rol">{ROLES[usuario.rol]}</div>
            </div>
          </div>
          {import.meta.env.DEV && (
            <label className="app__selector-rol">
              Rol (solo en desarrollo)
              <select className="campo" value={usuario.rol} onChange={(e) => cambiarRol(e.target.value)}>
                {Object.entries(ROLES).map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
              </select>
            </label>
          )}
        </div>
      </aside>

      <main className="app__contenido">
        <Outlet />
      </main>
    </div>
  )
}
