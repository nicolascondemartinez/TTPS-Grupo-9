// Único punto de contacto con el backend: todas las pantallas llaman a la API por acá.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5001/api'

async function request(method, path, body) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
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
