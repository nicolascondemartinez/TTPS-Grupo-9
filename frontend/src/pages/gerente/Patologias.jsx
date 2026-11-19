import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import Icono from '../../components/Icono.jsx'
import Tabla from '../../components/Tabla.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import './patologias.css'

// Gerente médico: listado de patologías (escenarios "Definir la patología" y "Modificar la patología").
// No hay baja: el cliente solo pidió crear y modificar.
export default function Patologias() {
  const navigate = useNavigate()
  const [patologias, setPatologias] = useState([])
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/patologias')
      .then((d) => { setPatologias(d.patologias); setEstado('listo') })
      .catch((e) => { setError(mensajeDeError(e)); setEstado('error') })
  }, [])

  const columnas = [
    { clave: 'nombre', titulo: 'Patología', render: (p) => <strong>{p.nombre}</strong> },
    { clave: 'cardinales', titulo: 'Síntomas cardinales', render: (p) => p.cardinales.map((s) => s.termino).join(' · ') || '—' },
    {
      clave: 'secundarios',
      titulo: 'Síntomas secundarios',
      render: (p) => <span className="patologias__secundarios">{p.secundarios.map((s) => s.termino).join(' · ')}</span>,
    },
    {
      clave: 'acciones',
      titulo: <span className="sr-only">Acciones</span>,
      render: (p) => (
        <Boton variante="ghost" onClick={() => navigate(`/gerente/patologias/${p.id}`)} aria-label={`Modificar ${p.nombre}`}>
          Modificar
        </Boton>
      ),
    },
  ]

  return (
    <>
      <EncabezadoPagina etiqueta="Gerencia médica" titulo="Patologías">
        <Boton icono={<Icono nombre="mas" tamano={18} />} onClick={() => navigate('/gerente/patologias/nueva')}>
          Nueva patología
        </Boton>
      </EncabezadoPagina>

      {estado === 'cargando' && <p role="status">Cargando patologías…</p>}
      {estado === 'error' && <p role="alert" className="patologias__error">{error}</p>}
      {estado === 'listo' && (
        <Tabla titulo="Patologías" columnas={columnas} filas={patologias} vacio="Todavía no hay patologías cargadas." />
      )}
    </>
  )
}
