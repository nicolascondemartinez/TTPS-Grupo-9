import { MENU } from '../constants/roles.js'

// Área de cada rol = primer tramo de sus rutas del menú (/medico/..., /paciente/..., /gerente/...).
const AREAS = Object.fromEntries(
  Object.entries(MENU).map(([rol, items]) => [
    rol,
    new Set(items.map((i) => i.ruta.split('/')[1]).filter((area) => area !== 'avisos')),
  ]),
)
const TODAS_LAS_AREAS = new Set(Object.values(AREAS).flatMap((a) => [...a]))

/** ¿Puede este rol abrir esta ruta? Cada rol solo entra a su área, y /avisos es de todos. */
export function puedeAcceder(rol, pathname) {
  const area = pathname.split('/')[1]
  if (!area || area === 'avisos') return true
  if (!TODAS_LAS_AREAS.has(area)) return true // ruta que no es de ningún rol: la resuelve "Página no encontrada"
  return AREAS[rol]?.has(area) ?? false
}

/**
 * A dónde ir después de ingresar: a la ruta que se intentaba abrir (`desde`) si este usuario puede verla;
 * si no (por ejemplo, entró otra persona con otro rol que la que cerró sesión), al inicio de su rol.
 */
export function destinoTrasIngresar(usuario, desde) {
  if (desde && usuario && puedeAcceder(usuario.rol, desde.pathname)) return `${desde.pathname}${desde.search ?? ''}`
  return '/'
}
