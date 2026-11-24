import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import { erroresPorCampo } from '../../api/erroresPorCampo.js'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import './transportistas.css'

const LISTADO = '/administrativo/transportistas'
const FORMATO_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const FORMATO_TELEFONO = /^\+?[0-9][0-9 ()-]{5,29}$/
const DATOS_VACIOS = { nombre: '', apellido: '', telefono: '', correo: '', provincia_id: '' }

// Alta de un transportista (lo hace el administrativo). El sistema le manda por mail el usuario y una
// contraseña temporal; en su primer ingreso tiene que cambiarla.
export default function FormularioTransportista() {
  const navigate = useNavigate()
  const notificar = useNotificar()
  const [datos, setDatos] = useState(DATOS_VACIOS)
  const [provincias, setProvincias] = useState([])
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    api.get('/provincias')
      .then((d) => { setProvincias(d.provincias); setEstado('listo') })
      .catch((e) => { setErrorGeneral(mensajeDeError(e)); setEstado('error') })
  }, [])

  const cambiar = (campo) => (e) => setDatos((d) => ({ ...d, [campo]: e.target.value }))
  const libres = provincias.filter((p) => !p.tiene_transportista)

  function validar() {
    const p = {}
    if (!datos.nombre.trim()) p.nombre = 'Ingresá el nombre.'
    if (!datos.apellido.trim()) p.apellido = 'Ingresá el apellido.'
    if (!datos.telefono.trim()) p.telefono = 'Ingresá un teléfono de contacto.'
    else if (!FORMATO_TELEFONO.test(datos.telefono.trim())) p.telefono = 'El teléfono no tiene un formato válido.'
    if (!datos.correo.trim()) p.correo = 'Ingresá el correo electrónico.'
    else if (!FORMATO_CORREO.test(datos.correo.trim())) p.correo = 'El correo electrónico no tiene un formato válido.'
    if (!datos.provincia_id) p.provincia_id = 'Elegí la provincia que cubre.'
    return p
  }

  async function guardar(e) {
    e.preventDefault()
    if (enviando) return
    const problemas = validar()
    setErrores(problemas)
    setErrorGeneral('')
    if (Object.keys(problemas).length) return

    setEnviando(true)
    try {
      await api.post('/transportistas', {
        nombre: datos.nombre.trim(),
        apellido: datos.apellido.trim(),
        telefono: datos.telefono.trim(),
        correo: datos.correo.trim(),
        provincia_id: datos.provincia_id,
      })
      notificar('Transportista creado: le enviamos sus credenciales por mail')
      navigate(LISTADO)
    } catch (err) {
      const porCampo = erroresPorCampo(err) // 400 de validación y 409 de correo o provincia repetidos
      if (Object.keys(porCampo).length) setErrores(porCampo)
      else setErrorGeneral(mensajeDeError(err)) // por ejemplo, el 503 si no se pudo enviar el mail
    } finally {
      setEnviando(false)
    }
  }

  if (estado !== 'listo') {
    return (
      <>
        <EncabezadoPagina etiqueta="Logística" titulo="Nuevo transportista" />
        {estado === 'cargando' && <p role="status">Cargando provincias…</p>}
        {estado === 'error' && (
          <div className="transportista-form__aviso">
            <p role="alert" className="transportistas__error">{errorGeneral}</p>
            <Link to={LISTADO}>Volver a transportistas</Link>
          </div>
        )}
      </>
    )
  }

  return (
    <>
      <EncabezadoPagina etiqueta="Logística" titulo="Nuevo transportista" />
      <form className="transportista-form" onSubmit={guardar} noValidate>
        <Tarjeta>
          <div className="transportista-form__campos">
            <Campo etiqueta="Nombre" maxLength={100} value={datos.nombre} onChange={cambiar('nombre')} error={errores.nombre} />
            <Campo etiqueta="Apellido" maxLength={100} value={datos.apellido} onChange={cambiar('apellido')} error={errores.apellido} />
            <Campo etiqueta="Teléfono de contacto" type="tel" maxLength={30} value={datos.telefono} onChange={cambiar('telefono')} error={errores.telefono} />
            <Campo etiqueta="Correo electrónico" type="email" placeholder="nombre@dominio.com" value={datos.correo} onChange={cambiar('correo')} error={errores.correo}
              ayuda="Ahí le llegan el usuario y la contraseña temporal." />
            {libres.length === 0 ? (
              <p role="status" className="transportistas__ayuda">Todas las provincias ya tienen un transportista asignado.</p>
            ) : (
              <Campo
                etiqueta="Provincia que cubre"
                value={datos.provincia_id}
                onChange={cambiar('provincia_id')}
                opciones={[{ valor: '', texto: 'Elegí una provincia…' }, ...libres.map((p) => ({ valor: p.id, texto: p.nombre }))]}
                error={errores.provincia_id}
                ayuda="Solo aparecen las provincias que todavía no tienen transportista."
              />
            )}
            {errorGeneral && <p role="alert" className="transportistas__error">{errorGeneral}</p>}
          </div>
        </Tarjeta>

        <div className="transportista-form__acciones">
          <Boton variante="ghost" onClick={() => navigate(LISTADO)} disabled={enviando}>Cancelar</Boton>
          <Boton type="submit" disabled={enviando || libres.length === 0}>
            {enviando ? 'Creando…' : 'Crear transportista'}
          </Boton>
        </div>
      </form>
    </>
  )
}