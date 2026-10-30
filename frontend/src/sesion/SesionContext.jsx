import { createContext, useContext, useState } from 'react'
import { ROLES } from '../constants/roles.js'

// Usuario logueado, disponible en toda la app con useSesion().
// PROVISORIO: hasta que esté el login (Persona 1), el usuario es de prueba y su rol se elige
// con el selector que aparece en la barra lateral solo en desarrollo. Cuando el login exista,
// este provider pasa a obtener el usuario real del backend; el resto de la app no cambia.
const SesionContext = createContext(null)
const CLAVE_ROL = 'exoma:rol-dev'

export function SesionProvider({ children }) {
  const [rol, setRol] = useState(() => {
    const guardado = localStorage.getItem(CLAVE_ROL)
    return guardado in ROLES ? guardado : 'administrativo'
  })

  const cambiarRol = (nuevo) => {
    localStorage.setItem(CLAVE_ROL, nuevo)
    setRol(nuevo)
  }

  const usuario = { nombre: 'Usuario de prueba', rol }
  return <SesionContext.Provider value={{ usuario, cambiarRol }}>{children}</SesionContext.Provider>
}

export function useSesion() {
  return useContext(SesionContext)
}
