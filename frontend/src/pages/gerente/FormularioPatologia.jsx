import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import Campo from '../../components/Campo.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import SelectorSintomas from '../../components/SelectorSintomas.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { codigoDeError, mensajeDeError } from '../acceso/errores.js'
import './patologias.css'

const LISTADO = '/gerente/patologias'

// Problemas por campo del 400 del backend: "secundarios[1]" se muestra en el campo "secundarios".
function erroresPorCampo(e) {
  const campos = e?.data?.error?.detalle?.campos ?? []
  const errores = {}
  for (const { campo, problema } of campos) {
    const clave = campo.split('[')[0]
    errores[clave] ??= `${problema.charAt(0).toUpperCase()}${problema.slice(1)}.`
  }
  return errores
}

// Alta (/gerente/patologias/nueva) y modificación (/gerente/patologias/:id) de una patología.
// Una patología tiene al menos un síntoma cardinal y al menos un secundario, todos de SNOMED.
// El nombre se elige al crearla y después queda fijo (Bioinformática busca los genes por nombre).
export default function FormularioPatologia() {
  const { id } = useParams()
  const esAlta = !id
  const navigate = useNavigate()
  const notificar = useNotificar()
  const [nombre, setNombre] = useState('')
  const [cardinales, setCardinales] = useState([])
  const [secundarios, setSecundarios] = useState([])
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [estado, setEstado] = useState(esAlta ? 'listo' : 'cargando') // cargando | listo | no_encontrada | error
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (esAlta) return
    api.get(`/patologias/${id}`)
      .then((p) => {
        setNombre(p.nombre)
        setCardinales(p.cardinales)
        setSecundarios(p.secundarios)
        setEstado('listo')
      })
      .catch((e) => {
        setErrorGeneral(mensajeDeError(e))
        setEstado(e?.status === 404 ? 'no_encontrada' : 'error')
      })
  }, [esAlta, id])

  function validar() {
    const problemas = {}
    if (esAlta && !nombre.trim()) problemas.nombre = 'Ingresá el nombre de la patología.'
    if (cardinales.length === 0) problemas.cardinales = 'Elegí al menos un síntoma cardinal.'
    if (secundarios.length === 0) problemas.secundarios = 'Elegí al menos un síntoma secundario.'
    return problemas
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
      const datos = { cardinales, secundarios }
      if (esAlta) await api.post('/patologias', { nombre: nombre.trim(), ...datos })
      else await api.put(`/patologias/${id}`, datos)
      notificar(esAlta ? 'Patología creada' : 'Patología modificada')
      navigate(LISTADO)
    } catch (err) {
      if (codigoDeError(err) === 'PATOLOGIA_DUPLICADA') setErrores({ nombre: 'Ya existe una patología con ese nombre.' })
      else if (codigoDeError(err) === 'VALIDACION') setErrores(erroresPorCampo(err))
      else setErrorGeneral(mensajeDeError(err))
    } finally {
      setEnviando(false)
    }
  }

  const titulo = esAlta ? 'Nueva patología' : 'Modificar patología'

  if (estado !== 'listo') {
    return (
      <>
        <EncabezadoPagina etiqueta="Gerencia médica" titulo={titulo} />
        {estado === 'cargando' && <p role="status">Cargando patología…</p>}
        {estado !== 'cargando' && (
          <div className="patologia-form__aviso">
            <p role="alert" className="patologias__error">
              {estado === 'no_encontrada' ? 'La patología no existe.' : errorGeneral}
            </p>
            <Link to={LISTADO}>Volver a patologías</Link>
          </div>
        )}
      </>
    )
  }

  return (
    <>
      <EncabezadoPagina etiqueta="Gerencia médica" titulo={titulo} />
      <form className="patologia-form" onSubmit={guardar} noValidate>
        <Tarjeta>
          <Campo
            etiqueta="Nombre"
            value={nombre}
            maxLength={100}
            onChange={(e) => setNombre(e.target.value)}
            disabled={!esAlta}
            error={errores.nombre}
            ayuda={esAlta ? 'Después de crearla, el nombre no se puede cambiar.' : 'El nombre no se puede modificar.'}
          />
          <SelectorSintomas
            etiqueta="Síntomas cardinales"
            valor={cardinales}
            onChange={setCardinales}
            excluir={secundarios}
            error={errores.cardinales}
            ayuda="Los síntomas principales de la patología. Al menos uno."
          />
          <SelectorSintomas
            etiqueta="Síntomas secundarios"
            valor={secundarios}
            onChange={setSecundarios}
            excluir={cardinales}
            error={errores.secundarios}
            ayuda="Al menos uno. Los cardinales no pueden repetirse acá."
          />
          {errorGeneral && <p role="alert" className="patologias__error">{errorGeneral}</p>}
        </Tarjeta>

        <div className="patologia-form__acciones">
          <Boton variante="ghost" onClick={() => navigate(LISTADO)} disabled={enviando}>Cancelar</Boton>
          <Boton type="submit" disabled={enviando}>
            {enviando ? 'Guardando…' : esAlta ? 'Crear patología' : 'Guardar cambios'}
          </Boton>
        </div>
      </form>
    </>
  )
}
