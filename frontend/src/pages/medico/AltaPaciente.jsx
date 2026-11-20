import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import GrabadorHistoriaClinica from '../../components/GrabadorHistoriaClinica.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import SeccionFamiliares from '../../components/SeccionFamiliares.jsx'
import SelectorSintomas from '../../components/SelectorSintomas.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { codigoDeError, mensajeDeError } from '../acceso/errores.js'
import './pacientes.css'

const LISTADO = '/medico/pacientes'
const VACIO = {
  nombre: '', apellido: '', dni: '', fecha_nacimiento: '', telefono: '', email: '',
  tipo_sospecha: '', patologia_ids: [], sintomas: [], historia_clinica: '', familiares: [],
}

// Menor de 18 años: el mail de contacto es el del padre, la madre o el tutor.
function esMenor(fechaIso) {
  if (!fechaIso) return false
  const nacimiento = new Date(`${fechaIso}T00:00:00`)
  const mayoria = new Date(nacimiento)
  mayoria.setFullYear(nacimiento.getFullYear() + 18)
  return new Date() < mayoria
}

// Errores del backend por campo: "familiares[1].nombre" va a la sección de familiares, en la posición 1.
function repartirErrores(e) {
  const errores = {}
  const familiares = {}
  for (const { campo, problema } of e?.data?.error?.detalle?.campos ?? []) {
    const texto = `${problema.charAt(0).toUpperCase()}${problema.slice(1)}.`
    const familiar = campo.match(/^familiares\[(\d+)\]/)
    if (familiar) familiares[familiar[1]] ??= texto
    else errores[campo.split('[')[0]] ??= texto
  }
  return { errores, familiares }
}

function validar(d) {
  const p = {}
  for (const [campo, texto] of [['nombre', 'el nombre'], ['apellido', 'el apellido'], ['dni', 'el DNI'],
    ['fecha_nacimiento', 'la fecha de nacimiento'], ['telefono', 'el teléfono'], ['email', 'el mail']]) {
    if (!d[campo].trim()) p[campo] = `Ingresá ${texto}.`
  }
  if (d.dni.trim() && !/^\d{7,8}$/.test(d.dni.replace(/[.\s-]/g, ''))) p.dni = 'El DNI tiene que tener 7 u 8 números.'
  if (!d.tipo_sospecha) p.tipo_sospecha = 'Elegí el tipo de sospecha.'
  if (d.patologia_ids.length === 0) p.patologia_ids = 'Elegí al menos una patología sospechada.'
  if (d.tipo_sospecha === 'clinica' && d.sintomas.length === 0) p.sintomas = 'Con sospecha clínica, elegí al menos un síntoma.'
  if (!d.historia_clinica.trim()) p.historia_clinica = 'Grabá o escribí el resumen de la historia clínica.'
  return p
}

// Médico tratante: alta del paciente (escenario "Dar de alta el paciente"). Junta datos personales, sospecha,
// diagnóstico presuntivo, síntomas (SNOMED), historia clínica (grabada o escrita) y familiares (opcional).
// El backend valida el diagnóstico y guarda todo junto: si algo falla, no se crea nada.
export default function AltaPaciente() {
  const navigate = useNavigate()
  const notificar = useNotificar()
  const [datos, setDatos] = useState(VACIO)
  const [patologias, setPatologias] = useState([])
  const [errores, setErrores] = useState({})
  const [erroresFamiliares, setErroresFamiliares] = useState({})
  const [diagnostico, setDiagnostico] = useState(null) // { mensaje, resultados } si no es consistente
  const [errorGeneral, setErrorGeneral] = useState('')
  const [familiogramaCaido, setFamiliogramaCaido] = useState(false)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    api.get('/patologias').then((d) => setPatologias(d.patologias)).catch((e) => setErrorGeneral(mensajeDeError(e)))
  }, [])

  const cambiar = (campo) => (valor) => setDatos((d) => ({ ...d, [campo]: valor }))
  const alEscribir = (campo) => (e) => cambiar(campo)(e.target.value)
  const menor = esMenor(datos.fecha_nacimiento)

  function alternarPatologia(id) {
    setDatos((d) => ({
      ...d,
      patologia_ids: d.patologia_ids.includes(id) ? d.patologia_ids.filter((x) => x !== id) : [...d.patologia_ids, id],
    }))
  }

  async function enviar(sinFamiliograma = false) {
    setEnviando(true)
    setFamiliogramaCaido(false)
    try {
      const paciente = await api.post('/pacientes', { ...datos, sin_familiograma: sinFamiliograma })
      notificar(`${paciente.nombre} ${paciente.apellido} quedó dado de alta`)
      navigate(LISTADO)
    } catch (e) {
      const codigo = codigoDeError(e)
      if (codigo === 'VALIDACION') {
        const { errores: porCampo, familiares } = repartirErrores(e)
        setErrores(porCampo)
        setErroresFamiliares(familiares)
        setErrorGeneral('Revisá los datos marcados.')
      } else if (codigo === 'DNI_DUPLICADO') setErrores({ dni: 'Ya hay un paciente con ese DNI.' })
      else if (codigo === 'MAIL_EN_USO') setErrores({ email: 'Ya hay un usuario con ese mail.' })
      else if (codigo === 'DIAGNOSTICO_INCONSISTENTE') {
        setDiagnostico({ mensaje: e.data.error.mensaje, resultados: e.data.error.detalle.resultados })
        document.getElementById('seccion-diagnostico')?.scrollIntoView({ behavior: 'smooth' })
      } else if (codigo === 'FAMILIOGRAMA_NO_DISPONIBLE') setFamiliogramaCaido(true)
      else setErrorGeneral(mensajeDeError(e))
    } finally {
      setEnviando(false)
    }
  }

  function guardar(e) {
    e.preventDefault()
    if (enviando) return
    const problemas = validar(datos)
    setErrores(problemas)
    setErroresFamiliares({})
    setDiagnostico(null)
    setErrorGeneral(Object.keys(problemas).length ? 'Revisá los datos marcados.' : '')
    if (Object.keys(problemas).length === 0) enviar()
  }

  return (
    <>
      <EncabezadoPagina etiqueta="Médico tratante" titulo="Nuevo paciente" />
      <form className="alta-paciente" onSubmit={guardar} noValidate>
        <Tarjeta titulo="Datos personales">
          <div className="alta-paciente__grilla">
            <Campo etiqueta="Nombre" value={datos.nombre} maxLength={100} onChange={alEscribir('nombre')} error={errores.nombre} autoComplete="off" />
            <Campo etiqueta="Apellido" value={datos.apellido} maxLength={100} onChange={alEscribir('apellido')} error={errores.apellido} autoComplete="off" />
            <Campo etiqueta="DNI" value={datos.dni} inputMode="numeric" maxLength={12} onChange={alEscribir('dni')} error={errores.dni} ayuda="Sin puntos o con puntos, como prefieras." />
            <Campo etiqueta="Fecha de nacimiento" type="date" value={datos.fecha_nacimiento} onChange={alEscribir('fecha_nacimiento')} error={errores.fecha_nacimiento} />
            <Campo etiqueta="Teléfono" type="tel" value={datos.telefono} maxLength={30} onChange={alEscribir('telefono')} error={errores.telefono} />
            <Campo
              etiqueta={menor ? 'Mail del padre, madre o tutor' : 'Mail'} type="email" value={datos.email} maxLength={254}
              onChange={alEscribir('email')} error={errores.email}
              ayuda={menor ? 'Es menor de edad: el usuario y la contraseña le llegan al padre, la madre o el tutor.' : 'Ahí le llegan el usuario y la contraseña.'}
            />
          </div>
        </Tarjeta>

        <Tarjeta titulo="Sospecha y diagnóstico presuntivo">
          <fieldset className="alta-paciente__opciones" aria-describedby="sospecha-error">
            <legend className="campo-grupo__label">Tipo de sospecha</legend>
            {[['clinica', 'Clínica', 'Por los síntomas del paciente'], ['familiar', 'Familiar', 'Un familiar tiene la enfermedad diagnosticada']].map(([valor, texto, ayuda]) => (
              <label key={valor} className="alta-paciente__opcion">
                <input type="radio" name="tipo_sospecha" value={valor} checked={datos.tipo_sospecha === valor} onChange={() => cambiar('tipo_sospecha')(valor)} />
                <span><strong>{texto}</strong><span className="alta-paciente__ayuda">{ayuda}</span></span>
              </label>
            ))}
            <span id="sospecha-error">{errores.tipo_sospecha && <span className="campo-grupo__error">{errores.tipo_sospecha}</span>}</span>
          </fieldset>

          <fieldset id="seccion-diagnostico" className="alta-paciente__opciones" aria-describedby="diagnostico-error">
            <legend className="campo-grupo__label">Patologías sospechadas</legend>
            {patologias.map((p) => (
              <label key={p.id} className="alta-paciente__opcion alta-paciente__opcion--chica">
                <input type="checkbox" checked={datos.patologia_ids.includes(p.id)} onChange={() => alternarPatologia(p.id)} />
                <span>{p.nombre}</span>
              </label>
            ))}
            <span id="diagnostico-error">
              {errores.patologia_ids && <span className="campo-grupo__error">{errores.patologia_ids}</span>}
              {!errores.patologia_ids && datos.tipo_sospecha === 'familiar' && (
                <span className="campo-grupo__ayuda">Cargá en Familiares a quien tiene la patología diagnosticada.</span>
              )}
            </span>
          </fieldset>

          {diagnostico && (
            <div className="alta-paciente__diagnostico" role="alert">
              <strong>{diagnostico.mensaje}</strong>
              <ul>{diagnostico.resultados.map((r) => <li key={r.patologia} className={r.valido ? '' : 'alta-paciente__invalido'}>{r.motivo}</li>)}</ul>
            </div>
          )}

          <SelectorSintomas
            etiqueta="Síntomas del paciente" valor={datos.sintomas} onChange={cambiar('sintomas')} error={errores.sintomas}
            ayuda={datos.tipo_sospecha === 'familiar' ? 'Opcional con sospecha familiar: puede no tener síntomas todavía.' : undefined}
          />
        </Tarjeta>

        <Tarjeta titulo="Historia clínica">
          <GrabadorHistoriaClinica valor={datos.historia_clinica} onChange={cambiar('historia_clinica')} error={errores.historia_clinica} deshabilitado={enviando} />
        </Tarjeta>

        <Tarjeta titulo="Familiares" subtitulo="Opcional">
          <SeccionFamiliares valor={datos.familiares} onChange={cambiar('familiares')} errores={erroresFamiliares} deshabilitado={enviando} />
        </Tarjeta>

        {familiogramaCaido && (
          <div className="alta-paciente__familiograma" role="alert">
            <strong>No pudimos generar el familiograma</strong>
            <p>
              El servicio de familiograma no respondió y todavía no se guardó nada. Podés reintentar o dar de alta al
              paciente sin familiograma (los familiares se guardan igual).
            </p>
            <div className="alta-paciente__acciones">
              <Boton variante="secundario" onClick={() => enviar(true)} disabled={enviando}>Dar de alta sin familiograma</Boton>
              <Boton onClick={() => enviar(false)} disabled={enviando}>{enviando ? 'Reintentando…' : 'Reintentar'}</Boton>
            </div>
          </div>
        )}
        {errorGeneral && <p role="alert" className="pacientes__error">{errorGeneral}</p>}
        {!familiogramaCaido && <div className="alta-paciente__acciones">
          <Boton variante="ghost" onClick={() => navigate(LISTADO)} disabled={enviando}>Cancelar</Boton>
          <Boton type="submit" disabled={enviando}>{enviando ? 'Guardando…' : 'Dar de alta'}</Boton>
        </div>}
      </form>

    </>
  )
}
