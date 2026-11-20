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
// Cada familiar: { parentesco, nombre, sintomas: [{ snomed_code, termino }], patologia_id (null = ninguna) }.
// `errores` (opcional): { 0: 'Ingresá nombre y apellido', ... } por posición, para los errores del backend.
// El parentesco sale del catálogo del módulo de familiograma (GET /api/parentescos); si no responde, se escribe a mano.
// No usa <form>: va adentro del formulario del alta, así que Enter no confirma nada acá.

const VACIO = { parentesco: '', nombre: '', sintomas: [], patologia_id: null }

function problemasDe(f) {
  const problemas = {}
  if (!f.parentesco.trim()) problemas.parentesco = 'Elegí el parentesco.'
  if (f.nombre.trim().split(/\s+/).filter(Boolean).length < 2) problemas.nombre = 'Ingresá nombre y apellido.'
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
    setEdicion({ indice, datos: indice === null ? VACIO : valor[indice] })
  }

  function cambiar(campo, dato) {
    setEdicion((e) => ({ ...e, datos: { ...e.datos, [campo]: dato } }))
  }

  function guardar() {
    const datos = { ...edicion.datos, nombre: edicion.datos.nombre.trim().replace(/\s+/g, ' ') }
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

      {valor.length > 0 && (
        <ul className="familiares__lista" aria-label="Familiares cargados">
          {valor.map((f, i) => (
            <li key={i} className="familiares__item">
              <div className="familiares__datos">
                <strong>{f.nombre}</strong>
                <span className="familiares__parentesco">{f.parentesco}</span>
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
          <Campo
            etiqueta="Nombre y apellido" value={edicion.datos.nombre} maxLength={150} onKeyDown={sinEnter}
            onChange={(e) => cambiar('nombre', e.target.value)} error={problemas.nombre}
            ayuda="El apellido va al final (lo usa el familiograma)."
          />
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
