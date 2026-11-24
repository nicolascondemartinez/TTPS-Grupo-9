import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import Icono from '../../components/Icono.jsx'
import Tabla from '../../components/Tabla.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import './transportistas.css'

// Administrativo: transportistas del laboratorio, uno por provincia (escenario "Registrar el transportista").
export default function Transportistas() {
  const navigate = useNavigate()
  const [transportistas, setTransportistas] = useState([])
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/transportistas')
      .then((d) => { setTransportistas(d.transportistas); setEstado('listo') })
      .catch((e) => { setError(mensajeDeError(e)); setEstado('error') })
  }, [])

  const columnas = [
    { clave: 'provincia', titulo: 'Provincia', render: (t) => <strong>{t.provincia.nombre}</strong> },
    { clave: 'nombre', titulo: 'Transportista', render: (t) => `${t.nombre} ${t.apellido}` },
    { clave: 'correo', titulo: 'Correo' },
    { clave: 'telefono', titulo: 'Teléfono' },
  ]

  return (
    <>
      <EncabezadoPagina etiqueta="Logística" titulo="Transportistas">
        <Boton icono={<Icono nombre="mas" tamano={18} />} onClick={() => navigate('/administrativo/transportistas/nuevo')}>
          Nuevo transportista
        </Boton>
      </EncabezadoPagina>

      {estado === 'cargando' && <p role="status">Cargando transportistas…</p>}
      {estado === 'error' && <p role="alert" className="transportistas__error">{error}</p>}
      {estado === 'listo' && (
        <Tabla titulo="Transportistas" columnas={columnas} filas={transportistas} vacio="Todavía no hay transportistas registrados." />
      )}
    </>
  )
}