// Dónde se guardan los datos de la sesión en el navegador.
//
// - token de acceso -> sessionStorage: sobrevive a recargar la página pero se borra al cerrar la pestaña,
//   así el token no queda guardado indefinidamente en el equipo. Riesgo: si hubiera una vulnerabilidad XSS,
//   un script de la página podría leerlo (igual que con localStorage); por eso la app no usa
//   dangerouslySetInnerHTML, el token nunca va en la URL ni se muestra en pantalla o consola, vence a las
//   8 horas y se revoca en el servidor al cerrar sesión. Alternativas descartadas: memoria (se pierde al
//   recargar) y localStorage (queda guardado aunque se cierre el navegador).
// - id de dispositivo -> localStorage: tiene que persistir entre sesiones para que el backend reconozca
//   el dispositivo y no pida el código por mail cada vez. No es una credencial: sin la contraseña no sirve.
const CLAVE_TOKEN = 'exoma:token'
const CLAVE_DISPOSITIVO = 'exoma:dispositivo'

export function getToken() {
  return sessionStorage.getItem(CLAVE_TOKEN)
}

export function setToken(token) {
  sessionStorage.setItem(CLAVE_TOKEN, token)
}

export function clearToken() {
  sessionStorage.removeItem(CLAVE_TOKEN)
}

// Identificador aleatorio del dispositivo: se genera una sola vez y se manda en cada pedido (X-Device-Id).
export function getDeviceId() {
  let id = localStorage.getItem(CLAVE_DISPOSITIVO)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(CLAVE_DISPOSITIVO, id)
  }
  return id
}

// Aviso de "sesión no válida": el cliente HTTP lo dispara ante un 401 y el SesionProvider lo escucha.
let alNoAutorizado = () => {}

export function onNoAutorizado(fn) {
  alNoAutorizado = fn
  return () => {
    alNoAutorizado = () => {}
  }
}

export function avisarNoAutorizado() {
  alNoAutorizado()
}
