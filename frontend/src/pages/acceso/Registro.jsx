import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import { ROLES } from '../../constants/roles.js'
import IngresoLayout from '../../layout/IngresoLayout.jsx'
import { useSesion } from '../../sesion/SesionContext.jsx'
import './acceso.css'
import { mensajeDeError } from './errores.js'

const FORMATO_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const FORMATO_TELEFONO = /^\+?[0-9][0-9 ()-]{5,29}$/
const CONTRASENA_MIN = 8
const CONTRASENA_MAX = 128
const MAX_ESPECIALIDADES = 10

// Los cuatro roles que se registran solos. El paciente no: lo da de alta su médico y recibe sus datos por mail.
const ROLES_REGISTRO = [
  { rol: 'medico', descripcion: 'Derivo pacientes y solicito estudios de exoma.' },
  { rol: 'gerente_medico', descripcion: 'Defino las patologías y administro los cupones de descuento.' },
  { rol: 'administrativo', descripcion: 'Gestiono presupuestos, autorizaciones, lotes y resultados.' },
  { rol: 'bioinformatico', descripcion: 'Analizo las variantes genéticas de los estudios.' },
]
const CON_MATRICULA = ['medico', 'gerente_medico'] // estos dos piden matrícula y especialidades

const DATOS_VACIOS = { nombre: '', apellido: '', telefono: '', correo: '', matricula: '', contrasena: '', repetir: '' }

// Problemas por campo del 400/409 del backend: "especialidades[1]" se muestra en el campo "especialidades".
function erroresPorCampo(e) {
  const campos = e?.data?.error?.detalle?.campos ?? []
  const errores = {}
  for (const { campo, problema } of campos) {
    const clave = campo.split('[')[0]
    errores[clave] ??= `${problema.charAt(0).toUpperCase()}${problema.slice(1)}.`
  }
  return errores
}

// Registro en dos pasos: 1) se elige el rol, 2) se completa el formulario de ese rol.
// Médico y gerente médico piden además matrícula y especialidades (lista desplegable).
export default function Registro() {
  const { estado } = useSesion()
  const navigate = useNavigate()
  const [rol, setRol] = useState(null)
  const [datos, setDatos] = useState(DATOS_VACIOS)
  const [elegidas, setElegidas] = useState([]) // ids de las especialidades elegidas
  const [catalogo, setCatalogo] = useState({ estado: 'idle', lista: [], mensaje: '' }) // idle | cargando | listo | error
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  const esProfesional = CON_MATRICULA.includes(rol)

  // Las especialidades se piden una sola vez, recién cuando se elige un rol que las necesita.
  useEffect(() => {
    if (!esProfesional || catalogo.estado !== 'idle') return
    setCatalogo({ estado: 'cargando', lista: [], mensaje: '' })
    api.get('/especialidades')
      .then((d) => setCatalogo({ estado: 'listo', lista: d.especialidades, mensaje: '' }))
      .catch((e) => setCatalogo({ estado: 'error', lista: [], mensaje: mensajeDeError(e) }))
  }, [esProfesional, catalogo.estado])

  if (estado === 'autenticado') return <Navigate to="/" replace />
  if (estado === 'cambio_contrasena_requerido') return <Navigate to="/acceso/cambiar-contrasena" replace />

  const cambiar = (campo) => (e) => setDatos((d) => ({ ...d, [campo]: e.target.value }))

  const elegirRol = (r) => {
    setRol(r)
    setErrores({})
    setErrorGeneral('')
  }

  const agregarEspecialidad = (e) => {
    const id = e.target.value
    if (id && !elegidas.includes(id) && elegidas.length < MAX_ESPECIALIDADES) setElegidas([...elegidas, id])
  }

  const nombreDe = (id) => catalogo.lista.find((x) => x.id === id)?.nombre ?? id
  const disponibles = catalogo.lista.filter((x) => !elegidas.includes(x.id))

  function validar() {
    const p = {}
    if (!datos.nombre.trim()) p.nombre = 'Ingresá tu nombre.'
    if (!datos.apellido.trim()) p.apellido = 'Ingresá tu apellido.'
    if (!datos.telefono.trim()) p.telefono = 'Ingresá un teléfono de contacto.'
    else if (!FORMATO_TELEFONO.test(datos.telefono.trim())) p.telefono = 'El teléfono no tiene un formato válido.'
    if (!datos.correo.trim()) p.correo = 'Ingresá tu correo electrónico.'
    else if (!FORMATO_CORREO.test(datos.correo.trim())) p.correo = 'El correo electrónico no tiene un formato válido.'
    if (esProfesional) {
      if (!datos.matricula.trim()) p.matricula = 'Ingresá tu matrícula.'
      if (elegidas.length === 0) p.especialidades = 'Elegí al menos una especialidad.'
    }
    if (!datos.contrasena) p.contrasena = 'Definí una contraseña.'
    else if (datos.contrasena.length < CONTRASENA_MIN || datos.contrasena.length > CONTRASENA_MAX) {
      p.contrasena = `La contraseña debe tener entre ${CONTRASENA_MIN} y ${CONTRASENA_MAX} caracteres.`
    }
    if (datos.contrasena && datos.repetir !== datos.contrasena) p.repetir = 'Las contraseñas no coinciden.'
    return p
  }

  async function enviar(e) {
    e.preventDefault()
    if (enviando) return
    const problemas = validar()
    setErrores(problemas)
    setErrorGeneral('')
    if (Object.keys(problemas).length) return

    const cuerpo = {
      rol,
      nombre: datos.nombre.trim(),
      apellido: datos.apellido.trim(),
      telefono: datos.telefono.trim(),
      correo: datos.correo.trim(),
      contrasena: datos.contrasena,
      ...(esProfesional ? { matricula: datos.matricula.trim(), especialidades: elegidas } : {}),
    }
    setEnviando(true)
    try {
      await api.post('/registro', cuerpo)
      // No se abre sesión: se vuelve al ingreso, donde el primer login desde este navegador pide el código por mail.
      navigate('/ingreso', { replace: true, state: { registrado: true } })
    } catch (err) {
      const porCampo = erroresPorCampo(err) // 400 de validación y 409 de correo o matrícula repetidos
      if (Object.keys(porCampo).length) setErrores(porCampo)
      else setErrorGeneral(mensajeDeError(err))
      setDatos((d) => ({ ...d, contrasena: '', repetir: '' }))
    } finally {
      setEnviando(false)
    }
  }

  // ----------------------------------------------------------------- paso 1: elegir el rol
  if (!rol) {
    return (
      <IngresoLayout>
        <div className="ingreso__encabezado">
          <h2 className="ingreso__form-titulo">Crear cuenta</h2>
          <p className="ingreso__form-bajada">Elegí tu rol en el laboratorio.</p>
        </div>
        <div className="registro__roles" role="group" aria-label="Rol">
          {ROLES_REGISTRO.map(({ rol: r, descripcion }) => (
            <button key={r} type="button" className="registro__rol" onClick={() => elegirRol(r)}>
              <strong>{ROLES[r]}</strong>
              <span>{descripcion}</span>
            </button>
          ))}
        </div>
        <p className="acceso__ayuda">Si sos paciente, tu médico te da de alta y te llegan tus datos de acceso por mail.</p>
        <Link to="/ingreso" className="enlace">¿Ya tenés cuenta? Ingresá</Link>
      </IngresoLayout>
    )
  }

  // ----------------------------------------------------------------- paso 2: formulario del rol
  return (
    <IngresoLayout>
      <div className="ingreso__encabezado">
        <h2 className="ingreso__form-titulo">Registro: {ROLES[rol]}</h2>
        <button type="button" className="enlace" onClick={() => setRol(null)} disabled={enviando}>
          Cambiar rol
        </button>
      </div>
      <form className="ingreso__form" onSubmit={enviar} noValidate>
        <Campo etiqueta="Nombre" autoComplete="given-name" maxLength={100}
          value={datos.nombre} onChange={cambiar('nombre')} error={errores.nombre} />
        <Campo etiqueta="Apellido" autoComplete="family-name" maxLength={100}
          value={datos.apellido} onChange={cambiar('apellido')} error={errores.apellido} />
        <Campo etiqueta="Teléfono de contacto" type="tel" autoComplete="tel" maxLength={30}
          value={datos.telefono} onChange={cambiar('telefono')} error={errores.telefono} />
        <Campo etiqueta="Correo electrónico" type="email" autoComplete="username" placeholder="nombre@dominio.com"
          value={datos.correo} onChange={cambiar('correo')} error={errores.correo} />

        {esProfesional && (
          <>
            <Campo etiqueta="Matrícula" maxLength={30}
              value={datos.matricula} onChange={cambiar('matricula')} error={errores.matricula} />

            {catalogo.estado === 'cargando' && <p role="status" className="acceso__ayuda">Cargando especialidades…</p>}
            {catalogo.estado === 'error' && (
              <div>
                <p role="alert" className="acceso__error">{catalogo.mensaje}</p>
                <button type="button" className="enlace"
                  onClick={() => setCatalogo({ estado: 'idle', lista: [], mensaje: '' })}>
                  Reintentar
                </button>
              </div>
            )}
            {catalogo.estado === 'listo' && (
              <div>
                <Campo
                  etiqueta="Especialidades"
                  value=""
                  onChange={agregarEspecialidad}
                  disabled={elegidas.length >= MAX_ESPECIALIDADES}
                  opciones={[{ valor: '', texto: 'Elegí una especialidad…' }, ...disponibles.map((x) => ({ valor: x.id, texto: x.nombre }))]}
                  error={errores.especialidades}
                  ayuda={`Podés elegir hasta ${MAX_ESPECIALIDADES}.`}
                />
                {elegidas.length > 0 && (
                  <ul className="registro__elegidas" aria-label="Especialidades elegidas">
                    {elegidas.map((id) => (
                      <li key={id}>
                        <span>{nombreDe(id)}</span>
                        <Boton variante="ghost" aria-label={`Quitar ${nombreDe(id)}`}
                          onClick={() => setElegidas(elegidas.filter((x) => x !== id))}>
                          Quitar
                        </Boton>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </>
        )}

        <Campo etiqueta="Contraseña" type="password" autoComplete="new-password"
          value={datos.contrasena} onChange={cambiar('contrasena')} error={errores.contrasena}
          ayuda={`Entre ${CONTRASENA_MIN} y ${CONTRASENA_MAX} caracteres.`} />
        <Campo etiqueta="Repetir contraseña" type="password" autoComplete="new-password"
          value={datos.repetir} onChange={cambiar('repetir')} error={errores.repetir} />

        {errorGeneral && <p role="alert" className="acceso__error">{errorGeneral}</p>}
        <Boton type="submit" anchoCompleto className="btn--grande" disabled={enviando}>
          {enviando ? 'Creando cuenta…' : 'Crear cuenta'}
        </Boton>
      </form>
      <Link to="/ingreso" className="enlace">¿Ya tenés cuenta? Ingresá</Link>
    </IngresoLayout>
  )
}