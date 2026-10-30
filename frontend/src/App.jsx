import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { api } from './api/client.js'

// Pantalla provisoria: confirma que el frontend llega al backend.
// Las rutas por rol se agregan cuando esté la base (layout, auth y navegación).
function Inicio() {
  const [estado, setEstado] = useState('consultando…')

  useEffect(() => {
    api.get('/health')
      .then((data) => setEstado(data.status))
      .catch(() => setEstado('sin conexión con la API'))
  }, [])

  return (
    <main>
      <h1>Sistema de Exoma Clínico</h1>
      <p>API: {estado}</p>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
    </Routes>
  )
}
