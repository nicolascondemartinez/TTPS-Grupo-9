import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import Icono from '../../components/Icono.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import Tabla from '../../components/Tabla.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import './pacientes.css'

const SOSPECHA = { clinica: 'Clínica', familiar: 'Familiar' }
const fecha = (iso) => (iso ? new Date(iso).toLocaleDateString('es-AR') : '—')

// Médico tratante: sus pacientes (los que dio de alta) y el acceso al alta de uno nuevo.
export default function Pacientes() {
  const navigate = useNavigate()
  const notificar = useNotificar()
  const [pacientes, setPacientes] = useState([])
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/pacientes')
      .then((d) => { setPacientes(d.pacientes); setEstado('listo') })
      .catch((e) => { setError(mensajeDeError(e)); setEstado('error') })
  }, [])

  async function reenviarCredenciales(p) {
    try {
      const { credenciales_enviadas: enviado } = await api.post(`/pacientes/${p.id}/credenciales`)
      if (enviado) notificar(`Le reenviamos el usuario y una contraseña nueva a ${p.nombre} ${p.apellido}.`)
      else notificar('No pudimos enviar el mail. Intentá de nuevo en unos minutos.', 'error')
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    }
  }

  async function descargarFamiliograma(p) {
    try {
      await api.descargar(`/pacientes/${p.id}/familiograma`, `familiograma-${p.apellido}-${p.dni}.svg`)
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    }
  }

  const columnas = [
    { clave: 'nombre', titulo: 'Paciente', render: (p) => <strong>{p.apellido}, {p.nombre}</strong> },
    { clave: 'dni', titulo: 'DNI' },
    { clave: 'patologias', titulo: 'Diagnóstico presuntivo', render: (p) => p.patologias.join(', ') },
    { clave: 'tipo_sospecha', titulo: 'Sospecha', render: (p) => SOSPECHA[p.tipo_sospecha] },
    { clave: 'fecha_alta', titulo: 'Alta', render: (p) => fecha(p.fecha_alta) },
    {
      clave: 'acceso',
      titulo: 'Acceso',
      render: (p) => (p.primer_ingreso_pendiente ? (
        <div className="pacientes__acceso">
          <span className="pacientes__suave">Pendiente de primer ingreso</span>
          <Boton variante="ghost" onClick={() => reenviarCredenciales(p)} aria-label={`Reenviar el usuario y la contraseña a ${p.nombre} ${p.apellido}`}>
            Reenviar credenciales
          </Boton>
        </div>
      ) : <span className="pacientes__suave">Ya ingresó</span>),
    },
    {
      clave: 'familiograma',
      titulo: 'Familiograma',
      render: (p) => (p.tiene_familiograma ? (
        <Boton variante="ghost" onClick={() => descargarFamiliograma(p)} aria-label={`Descargar el familiograma de ${p.nombre} ${p.apellido}`}>
          Descargar
        </Boton>
      ) : <span className="pacientes__suave">Sin familiograma</span>),
    },
  ]

  return (
    <>
      <EncabezadoPagina etiqueta="Médico tratante" titulo="Pacientes">
        <Boton icono={<Icono nombre="mas" tamano={18} />} onClick={() => navigate('/medico/pacientes/nuevo')}>
          Nuevo paciente
        </Boton>
      </EncabezadoPagina>

      {estado === 'cargando' && <p role="status">Cargando pacientes…</p>}
      {estado === 'error' && <p role="alert" className="pacientes__error">{error}</p>}
      {estado === 'listo' && (
        <Tabla titulo="Pacientes" columnas={columnas} filas={pacientes} vacio="Todavía no diste de alta pacientes." />
      )}
    </>
  )
}
