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

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  delete: (path) => request('DELETE', path),
}
