// Único punto de contacto con el backend: todas las pantallas llaman a la API por acá.
import { avisarNoAutorizado, getDeviceId, getToken } from '../sesion/almacen.js'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5001/api'

async function request(method, path, body) {
  const token = getToken()
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      'X-Device-Id': getDeviceId(),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    // 401 con una sesión abierta = token vencido o revocado: se cierra la sesión local
    // (el 401 del login, sin token, es "credenciales incorrectas" y lo maneja la pantalla).
    if (response.status === 401 && token) avisarNoAutorizado()
    throw { status: response.status, data }
  }
  return data
}

// Descarga un archivo (por ejemplo un PDF) que necesita sesión: no alcanza con un <a href>, porque el link
// no manda el token. Se pide con fetch, se arma un link temporal y se "hace clic" para que el navegador lo baje.
async function descargar(path, nombreArchivo) {
  const token = getToken()                                   // el token de la sesión, para que el back sepa quién pide
  const response = await fetch(`${BASE_URL}${path}`, {
    // mismos headers que en request(), pero sin Content-Type porque no mandamos nada en el cuerpo
    headers: { 'X-Device-Id': getDeviceId(), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    credentials: 'include',
  })
  if (!response.ok) {
    // si falla, el back manda el error en JSON (no un PDF), así que lo leo como en request()
    const data = await response.json().catch(() => null)
    if (response.status === 401 && token) avisarNoAutorizado()   // sesión vencida: se cierra la sesión
    throw { status: response.status, data }                      // la pantalla lo agarra con el catch
  }
  const url = URL.createObjectURL(await response.blob()) // blob = el archivo en memoria; le creo una dirección temporal
  const link = document.createElement('a')  // armo un link invisible...
  link.href = url
  link.download = nombreArchivo      // ...que descarga con este nombre en vez de abrirlo
  link.click()                       // lo "clickeo" por código y el navegador baja el archivo
  URL.revokeObjectURL(url)           // libero la dirección temporal, ya no hace falta
}

export const api = {
  get: (path) => request('GET', path),   // pedir datos
  post: (path, body) => request('POST', path, body),  // crear algo
  put: (path, body) => request('PUT', path, body), // modificar algo
  delete: (path) => request('DELETE', path),   // borrar algo
  descargar,   // bajar un archivo (es lo mismo que descargar: descargar)
}

