import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import Boton from './Boton.jsx'
import Campo from './Campo.jsx'
import Icono from './Icono.jsx'
import SelectorSintomas from './SelectorSintomas.jsx'
import './seccion-familiares.css'

// Familiares del paciente en el alta (escenario "Cargar un familiar del paciente"). Es opcional: puede quedar vacía.
// Componente controlado: `valor` es la lista de familiares y `onChange` recibe la lista nueva.
//
//   const [familiares, setFamiliares] = useState([])
//   <SeccionFamiliares valor={familiares} onChange={setFamiliares} errores={erroresFamiliares} />
//
// Cada familiar: { parentesco, nombre, sexo, edad (años o null), fallecido, sintomas: [{ snomed_code, termino }],
// patologia_id (null = ninguna) }. Un progenitor desconocido se carga igual ("Padre Desconocido"): el familiograma
// lo necesita como nexo para ubicar a los abuelos y tíos de ese lado.
// El sexo (hombre | mujer | no_identificado) lo usa el familiograma para ubicar a los abuelos, tíos y medio
// hermanos de cada lado: por eso hay que cargar a los progenitores con su sexo.
// `errores` (opcional): { 0: 'Ingresá nombre y apellido', ... } por posición, para los errores del backend.
// El parentesco sale del catálogo del módulo de familiograma (GET /api/parentescos); si no responde, se escribe a mano.
// No usa <form>: va adentro del formulario del alta, así que Enter no confirma nada acá.

const VACIO = { parentesco: '', nombre: '', sexo: '', edad: null, fallecido: false, desconocido: false, sintomas: [], patologia_id: null }
const SEXOS = { hombre: 'Hombre', mujer: 'Mujer', no_identificado: 'No sé' }
const OPCIONES_SEXO = [{ valor: '', texto: 'Elegí el sexo' }, ...Object.entries(SEXOS).map(([valor, texto]) => ({ valor, texto }))]

function problemasDe(f) {
  const problemas = {}
  if (!f.parentesco.trim()) problemas.parentesco = 'Elegí el parentesco.'
  if (f.nombre.trim().split(/\s+/).filter(Boolean).length < 2) problemas.nombre = 'Ingresá nombre y apellido.'
  if (!f.sexo) problemas.sexo = 'Elegí el sexo (o "No sé").'
  if (f.desconocido && !['hombre', 'mujer'].includes(f.sexo)) problemas.sexo = 'Indicá si es el padre o la madre.'
  if (f.edad !== null && (!Number.isInteger(f.edad) || f.edad < 0 || f.edad > 120)) problemas.edad = 'Ingresá la edad en años (0 a 120).'
  return problemas
}

const sinEnter = (e) => { if (e.key === 'Enter') e.preventDefault() }

export default function SeccionFamiliares({ valor, onChange, errores = {}, deshabilitado = false }) {
  const [parentescos, setParentescos] = useState(null) // null: cargando | [] y error: escribir a mano
  const [errorCatalogo, setErrorCatalogo] = useState(false)
  const [patologias, setPatologias] = useState([])
  const [edicion, setEdicion] = useState(null) // null: cerrado | { indice (null = nuevo), datos }
  const [problemas, setProblemas] = useState({})

  useEffect(() => {
    api.get('/parentescos')
      .then((d) => setParentescos(d.parentescos))
      .catch(() => { setParentescos([]); setErrorCatalogo(true) })
    api.get('/patologias').then((d) => setPatologias(d.patologias)).catch(() => setPatologias([]))
  }, [])

  const nombrePatologia = (id) => patologias.find((p) => p.id === id)?.nombre ?? 'diagnóstico cargado'

  function abrir(indice) {
    setProblemas({})
    const datos = indice === null ? VACIO : { ...VACIO, ...valor[indice] }
    setEdicion({ indice, datos: { ...datos, desconocido: /^(Padre Desconocido|Madre Desconocida)$/.test(datos.nombre) } })
  }

  function cambiar(campo, dato) {
    setEdicion((e) => {
      const datos = { ...e.datos, [campo]: dato }
      if (campo === 'parentesco' && dato !== 'progenitor') datos.desconocido = false
      // Progenitor desconocido: nombre fijo según el sexo (el familiograma pide nombre y apellido).
      if (datos.desconocido) datos.nombre = datos.sexo === 'mujer' ? 'Madre Desconocida' : 'Padre Desconocido'
      return { ...e, datos }
    })
  }

  function guardar() {
    const { desconocido, ...resto } = edicion.datos
    const datos = { ...resto, nombre: resto.nombre.trim().replace(/\s+/g, ' ') }
    const encontrados = problemasDe(datos)
    setProblemas(encontrados)
    if (Object.keys(encontrados).length) return
    onChange(edicion.indice === null ? [...valor, datos] : valor.map((f, i) => (i === edicion.indice ? datos : f)))
    setEdicion(null)
  }

  function quitar(indice) {
    onChange(valor.filter((_, i) => i !== indice))
    if (edicion?.indice === indice) setEdicion(null)
  }

  const opcionesParentesco = [
    { valor: '', texto: 'Elegí el parentesco' },
    ...(parentescos ?? []).map((p) => ({ valor: p.nombre, texto: p.nombre })),
  ]
  const opcionesPatologia = [
    { valor: '', texto: 'Ninguno' },
    ...patologias.map((p) => ({ valor: p.id, texto: p.nombre })),
  ]

  return (
    <div className="familiares">
      {valor.length === 0 && !edicion && (
        <p className="familiares__vacio">No hay familiares cargados. Es opcional: si cargás alguno, se genera el familiograma.</p>
      )}
      <p className="familiares__vacio">
        Para ubicar a abuelos, tíos y medio hermanos de un lado, cargá al progenitor de ese lado con su sexo. Los primos
        necesitan a su tío, los sobrinos a un hermano, los nietos a un hijo y los suegros a la pareja.
      </p>

      {valor.length > 0 && (
        <ul className="familiares__lista" aria-label="Familiares cargados">
          {valor.map((f, i) => (
            <li key={i} className="familiares__item">
              <div className="familiares__datos">
                <strong>{f.nombre}</strong>
                <span className="familiares__parentesco">
                  {f.parentesco} · {SEXOS[f.sexo] ?? 'Sexo no informado'}
                  {f.edad !== null && f.edad !== undefined ? ` · ${f.edad} años` : ''}{f.fallecido ? ' · Fallecido/a' : ''}
                </span>
                <span className="familiares__detalle">
                  Diagnóstico previo: {f.patologia_id ? nombrePatologia(f.patologia_id) : 'ninguno'}
                  {' · '}Síntomas: {f.sintomas.length ? f.sintomas.map((s) => s.termino).join(', ') : 'ninguno'}
                </span>
                {errores[i] && <span className="campo-grupo__error" role="alert">{errores[i]}</span>}
              </div>
              <div className="familiares__acciones">
                <Boton variante="ghost" onClick={() => abrir(i)} disabled={deshabilitado} aria-label={`Editar a ${f.nombre}`}>Editar</Boton>
                <Boton variante="ghost" onClick={() => quitar(i)} disabled={deshabilitado} aria-label={`Quitar a ${f.nombre}`}>Quitar</Boton>
              </div>
            </li>
          ))}
        </ul>
      )}

      {edicion ? (
        <div className="familiares__editor" role="group" aria-label={edicion.indice === null ? 'Nuevo familiar' : 'Editar familiar'}>
          {parentescos === null ? (
            <p role="status" className="familiares__vacio">Cargando parentescos…</p>
          ) : errorCatalogo ? (
            <Campo
              etiqueta="Parentesco" value={edicion.datos.parentesco} maxLength={50} onKeyDown={sinEnter}
              onChange={(e) => cambiar('parentesco', e.target.value)} error={problemas.parentesco}
              ayuda="No pudimos traer la lista de parentescos: escribilo (por ejemplo, progenitor o hermano/a)."
            />
          ) : (
            <Campo
              etiqueta="Parentesco" opciones={opcionesParentesco} value={edicion.datos.parentesco}
              onChange={(e) => cambiar('parentesco', e.target.value)} error={problemas.parentesco}
            />
          )}
          {edicion.datos.parentesco === 'progenitor' && (
            <label className="familiares__check">
              <input type="checkbox" checked={edicion.datos.desconocido} onChange={(e) => cambiar('desconocido', e.target.checked)} />
              No lo conozco (se carga igual para ubicar a sus padres y hermanos)
            </label>
          )}
          <Campo
            etiqueta="Nombre y apellido" value={edicion.datos.nombre} maxLength={150} onKeyDown={sinEnter}
            onChange={(e) => cambiar('nombre', e.target.value)} error={problemas.nombre} disabled={edicion.datos.desconocido}
            ayuda={edicion.datos.desconocido ? 'Se completa solo según el sexo.' : 'El apellido va al final (lo usa el familiograma).'}
          />
          <Campo
            etiqueta="Sexo" opciones={OPCIONES_SEXO} value={edicion.datos.sexo}
            onChange={(e) => cambiar('sexo', e.target.value)} error={problemas.sexo}
          />
          <div className="familiares__fila">
            <Campo
              etiqueta="Edad (opcional)" type="number" inputMode="numeric" min={0} max={120} onKeyDown={sinEnter}
              value={edicion.datos.edad ?? ''} error={problemas.edad}
              onChange={(e) => cambiar('edad', e.target.value === '' ? null : Number(e.target.value))}
            />
            <label className="familiares__check">
              <input type="checkbox" checked={edicion.datos.fallecido} onChange={(e) => cambiar('fallecido', e.target.checked)} />
              Fallecido/a
            </label>
          </div>
          <SelectorSintomas
            etiqueta="Síntomas del familiar" valor={edicion.datos.sintomas} onChange={(s) => cambiar('sintomas', s)}
            ayuda="Opcional."
          />
          <Campo
            etiqueta="Diagnóstico previo" opciones={opcionesPatologia} value={edicion.datos.patologia_id ?? ''}
            onChange={(e) => cambiar('patologia_id', e.target.value || null)}
          />
          <div className="familiares__botones">
            <Boton variante="ghost" onClick={() => setEdicion(null)}>Cancelar</Boton>
            <Boton variante="secundario" onClick={guardar}>
              {edicion.indice === null ? 'Agregar familiar' : 'Guardar cambios'}
            </Boton>
          </div>
        </div>
      ) : (
        <div>
          <Boton variante="secundario" icono={<Icono nombre="mas" tamano={18} />} onClick={() => abrir(null)} disabled={deshabilitado}>
            Agregar familiar
          </Boton>
        </div>
      )}
    </div>
  )
}
