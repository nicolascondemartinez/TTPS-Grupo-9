import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../api/client.js'
import Chip from './Chip.jsx'
import Icono from './Icono.jsx'

// Autocompletado de síntomas SNOMED (escenario "Seleccionar los síntomas"). Lo usan patologías,
// pacientes y familiares. Componente controlado: `valor` es la lista elegida [{ snomed_code, termino }]
// y `onChange` recibe la lista nueva. No hay texto libre: lo escrito solo sirve para buscar.
//
//   const [sintomas, setSintomas] = useState([])
//   <SelectorSintomas etiqueta="Síntomas del paciente" valor={sintomas} onChange={setSintomas} />
//
// Opcionales:
//   maximo   tope de síntomas (ej. maximo={1} si solo se puede elegir uno)
//   excluir  síntomas que no se ofrecen aunque coincidan (ej. los cardinales en la lista de secundarios)
//   buscar   reemplaza la consulta a la API: (texto) => Promise<[{ snomed_code, termino }]>
const MINIMO_LETRAS = 3
const ESPERA_MS = 300
const MENSAJE_ERROR = 'No pudimos consultar los síntomas. Intentá de nuevo en unos minutos.'

const buscarEnApi = (texto) => api.get(`/sintomas?q=${encodeURIComponent(texto)}`).then((d) => d.sintomas)

export default function SelectorSintomas({
  etiqueta = 'Síntomas',
  valor = [],
  onChange,
  ayuda,
  error,
  disabled = false,
  maximo,
  excluir = [],
  buscar = buscarEnApi,
}) {
  const id = useId()
  const listaId = `${id}-lista`
  const avisoId = `${id}-aviso`
  const inputRef = useRef(null)
  const buscarRef = useRef(buscar)
  const [texto, setTexto] = useState('')
  const [resultados, setResultados] = useState([])
  const [estado, setEstado] = useState('inactivo') // inactivo | buscando | listo | error
  const [errorApi, setErrorApi] = useState('')
  const [abierto, setAbierto] = useState(false)
  const [activo, setActivo] = useState(-1)

  useEffect(() => { buscarRef.current = buscar }, [buscar])

  const buscable = texto.trim()
  const elegidos = new Set(valor.map((s) => s.snomed_code))
  const excluidos = new Set(excluir.map((s) => s.snomed_code))
  const opciones = resultados.filter((s) => !elegidos.has(s.snomed_code) && !excluidos.has(s.snomed_code))
  const completo = maximo != null && valor.length >= maximo

  // Debounce: consulta cuando se deja de escribir; una respuesta vieja no pisa a una nueva.
  useEffect(() => {
    if (buscable.length < MINIMO_LETRAS) {
      setResultados([])
      setEstado('inactivo')
      return
    }
    let vigente = true
    setEstado('buscando')
    const espera = setTimeout(() => {
      buscarRef.current(buscable)
        .then((lista) => {
          if (!vigente) return
          setResultados(lista ?? [])
          setEstado('listo')
          setErrorApi('')
          setActivo(-1)
        })
        .catch((e) => {
          if (!vigente) return
          setResultados([])
          setEstado('error')
          setErrorApi(e?.data?.error?.mensaje || MENSAJE_ERROR)
        })
    }, ESPERA_MS)
    return () => {
      vigente = false
      clearTimeout(espera)
    }
  }, [buscable])

  function elegir(sintoma) {
    if (!elegidos.has(sintoma.snomed_code) && !completo) {
      onChange?.([...valor, { snomed_code: sintoma.snomed_code, termino: sintoma.termino }])
    }
    setTexto('')
    setAbierto(false)
    setActivo(-1)
    inputRef.current?.focus()
  }

  function quitar(sintoma) {
    onChange?.(valor.filter((s) => s.snomed_code !== sintoma.snomed_code))
    setTimeout(() => inputRef.current?.focus()) // después del render: con `maximo` el campo recién se habilita
  }

  function alPresionarTecla(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setAbierto(true)
      setActivo((i) => Math.min(i + 1, opciones.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActivo((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      // Nunca envía el formulario ni agrega lo escrito: solo elige la opción marcada.
      e.preventDefault()
      if (abierto && opciones[activo]) elegir(opciones[activo])
    } else if (e.key === 'Escape') {
      setAbierto(false)
    }
  }

  // Al salir del campo se descarta lo escrito (no queda texto que parezca elegido).
  function alSalir() {
    setTexto('')
    setAbierto(false)
    setActivo(-1)
  }

  const mostrarPanel = abierto && !completo && buscable.length >= MINIMO_LETRAS && estado !== 'error'
  let aviso = ayuda
  if (buscable.length > 0 && buscable.length < MINIMO_LETRAS) aviso = `Escribí al menos ${MINIMO_LETRAS} letras para buscar`
  if (completo && !disabled) aviso = maximo === 1 ? 'Para cambiarlo, quitá el síntoma elegido.' : `Llegaste al máximo de ${maximo} síntomas.`

  return (
    <div className="campo-grupo selector-sintomas">
      <label htmlFor={id} className="campo-grupo__label">{etiqueta}</label>

      {valor.length > 0 && (
        <ul className="selector-sintomas__elegidos" aria-label={`${etiqueta} elegidos`}>
          {valor.map((s) => (
            <li key={s.snomed_code}>
              <Chip tipo="curso">
                <span className="selector-sintomas__termino">{s.termino}</span>
                {!disabled && (
                  <button type="button" className="selector-sintomas__quitar" onClick={() => quitar(s)} aria-label={`Quitar ${s.termino}`}>
                    <Icono nombre="cerrar" tamano={16} />
                  </button>
                )}
              </Chip>
            </li>
          ))}
        </ul>
      )}

      <div className="campo-con-icono">
        <span className="campo-con-icono__icono"><Icono nombre="buscar" tamano={18} /></span>
        <input
          ref={inputRef}
          id={id}
          className="campo"
          type="text"
          role="combobox"
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={mostrarPanel}
          aria-controls={listaId}
          aria-activedescendant={mostrarPanel && opciones[activo] ? `${listaId}-${activo}` : undefined}
          aria-invalid={error || errorApi ? true : undefined}
          aria-describedby={avisoId}
          placeholder={completo ? 'Síntoma elegido' : 'Escribí un síntoma (ej. hepatomegalia)'}
          value={texto}
          disabled={disabled || completo}
          onChange={(e) => { setTexto(e.target.value); setAbierto(true) }}
          onFocus={() => setAbierto(true)}
          onBlur={alSalir}
          onKeyDown={alPresionarTecla}
        />
        {mostrarPanel && (
          // mousedown sin foco: elegir una opción no dispara el blur del input antes del click.
          <div className="selector-sintomas__panel" onMouseDown={(e) => e.preventDefault()}>
            {estado === 'buscando' && <p className="selector-sintomas__mensaje">Buscando…</p>}
            {estado === 'listo' && opciones.length === 0 && (
              <p className="selector-sintomas__mensaje">
                {resultados.length > 0 ? 'Los resultados de esta búsqueda ya están elegidos' : 'No encontramos síntomas con ese texto'}
              </p>
            )}
            {estado === 'listo' && opciones.length > 0 && (
              <ul id={listaId} role="listbox" aria-label={etiqueta} className="selector-sintomas__lista">
                {opciones.map((s, i) => (
                  <li
                    key={s.snomed_code}
                    id={`${listaId}-${i}`}
                    role="option"
                    aria-selected={i === activo}
                    className="selector-sintomas__opcion"
                    onMouseEnter={() => setActivo(i)}
                    onClick={() => elegir(s)}
                  >
                    {s.termino}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div id={avisoId} aria-live="polite">
        {errorApi && estado === 'error' && <span className="campo-grupo__error" role="alert">{errorApi}</span>}
        {error && <span className="campo-grupo__error">{error}</span>}
        {!error && !(errorApi && estado === 'error') && aviso && <span className="campo-grupo__ayuda">{aviso}</span>}
      </div>
    </div>
  )
}
