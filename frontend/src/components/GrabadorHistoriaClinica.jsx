import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { mensajeDeError } from '../pages/acceso/errores.js'
import Boton from './Boton.jsx'
import Icono from './Icono.jsx'
import ModalConfirmacion from './ModalConfirmacion.jsx'
import './grabador-historia-clinica.css'

// Resumen de la historia clínica (escenario "Grabar el resumen de la historia clínica"). El médico graba con
// el micrófono, el audio se transcribe en POST /api/historia-clinica/transcribir y el texto queda en el cuadro,
// siempre editable, para que lo corrija. Lo que se confirma es el texto: el audio no se guarda.
// Componente controlado, como SelectorSintomas: `valor` es el texto y `onChange` recibe el texto nuevo.
//
//   const [historia, setHistoria] = useState('')
//   <GrabadorHistoriaClinica valor={historia} onChange={setHistoria} error={errores.historia_clinica} />
//
// Botones: Grabar / Detener; con texto, Reanudar (agrega otro tramo al final) y Volver a grabar (borra todo y
// empieza de cero, con confirmación). Si no hay micrófono o se niega el permiso, se escribe a mano.
// El navegador solo permite el micrófono en https o en localhost.

// En orden de preferencia: webm (Chrome, Android, Firefox), ogg (Firefox) y mp4 (Safari en iPhone y Mac).
const FORMATOS = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
const MAXIMO_SEGUNDOS = 10 * 60 // tope del backend: 10 MB, que alcanza de sobra para 10 minutos

function puedeGrabar() {
  return Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia && window.MediaRecorder)
}

function formatoElegido() {
  return FORMATOS.find((f) => MediaRecorder.isTypeSupported?.(f)) ?? ''
}

function extension(tipo) {
  if (tipo.includes('mp4')) return 'mp4'
  if (tipo.includes('ogg')) return 'ogg'
  return 'webm'
}

function mensajeDeMicrofono(e) {
  if (e?.name === 'NotAllowedError' || e?.name === 'SecurityError') {
    return 'No diste permiso para usar el micrófono. Podés escribir el resumen a mano.'
  }
  if (e?.name === 'NotFoundError') return 'No encontramos un micrófono. Podés escribir el resumen a mano.'
  return 'No pudimos usar el micrófono. Podés escribir el resumen a mano.'
}

const duracion = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

export default function GrabadorHistoriaClinica({ valor, onChange, etiqueta = 'Resumen de la historia clínica', error, deshabilitado = false }) {
  const id = useId()
  const avisoId = `${id}-aviso`
  const [estado, setEstado] = useState('listo') // listo | pidiendo_permiso | grabando | transcribiendo
  const [segundos, setSegundos] = useState(0)
  const [aviso, setAviso] = useState('') // por qué no se puede grabar o por qué falló la transcripción
  const [sinMicrofono, setSinMicrofono] = useState(() => !puedeGrabar())
  const [confirmarBorrado, setConfirmarBorrado] = useState(false)
  const grabador = useRef(null)
  const valorActual = useRef(valor) // el texto al terminar la transcripción (puede haber cambiado mientras)
  valorActual.current = valor

  // Al salir de la pantalla se corta la grabación y se libera el micrófono.
  useEffect(() => () => {
    const g = grabador.current
    if (g) {
      g.onstop = null
      if (g.state !== 'inactive') g.stop()
      g.stream.getTracks().forEach((t) => t.stop())
    }
  }, [])

  // Contador de la grabación; a los 10 minutos se detiene sola.
  useEffect(() => {
    if (estado !== 'grabando') return undefined
    const intervalo = setInterval(() => setSegundos((s) => s + 1), 1000)
    return () => clearInterval(intervalo)
  }, [estado])
  useEffect(() => {
    if (estado === 'grabando' && segundos >= MAXIMO_SEGUNDOS) detener()
  }, [estado, segundos])

  async function grabar() {
    setAviso('')
    setEstado('pidiendo_permiso')
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      setSinMicrofono(true)
      setAviso(mensajeDeMicrofono(e))
      setEstado('listo')
      return
    }
    const formato = formatoElegido()
    const g = new MediaRecorder(stream, formato ? { mimeType: formato } : undefined)
    const partes = []
    g.ondataavailable = (e) => { if (e.data.size) partes.push(e.data) }
    g.onstop = () => {
      stream.getTracks().forEach((t) => t.stop()) // apaga el indicador de micrófono del navegador
      grabador.current = null
      transcribir(new Blob(partes, { type: g.mimeType || formato || 'audio/webm' }))
    }
    grabador.current = g
    setSegundos(0)
    g.start()
    setEstado('grabando')
  }

  function detener() {
    if (grabador.current?.state === 'recording') grabador.current.stop()
  }

  async function transcribir(audio) {
    if (!audio.size) {
      setAviso('La grabación quedó vacía. Probá de nuevo.')
      setEstado('listo')
      return
    }
    setEstado('transcribiendo')
    const datos = new FormData()
    datos.append('audio', audio, `historia-clinica.${extension(audio.type)}`)
    try {
      const { texto } = await api.enviarArchivos('/historia-clinica/transcribir', datos)
      const anterior = valorActual.current.trim()
      onChange(anterior ? `${anterior}\n\n${texto}` : texto) // Reanudar: el tramo nuevo va al final
    } catch (e) {
      setAviso(`No pudimos transcribir la grabación: ${mensajeDeError(e)} Podés grabar de nuevo o escribir a mano.`)
    } finally {
      setEstado('listo')
    }
  }

  function volverAGrabar() {
    setConfirmarBorrado(false)
    onChange('')
    grabar()
  }

  const ocupado = estado !== 'listo'
  const hayTexto = valor.trim() !== ''
  const ayuda = sinMicrofono
    ? 'Escribí el resumen de la historia clínica.'
    : 'Grabá el resumen o escribilo. Revisá y corregí el texto antes de guardar.'

  return (
    <div className="campo-grupo grabador-hc">
      <label htmlFor={id} className="campo-grupo__label">{etiqueta}</label>

      {!sinMicrofono && (
        <div className="grabador-hc__controles">
          {estado === 'grabando' ? (
            <>
              <Boton variante="secundario" onClick={detener}>Detener</Boton>
              <span className="grabador-hc__grabando" role="status">
                <span className="grabador-hc__punto" aria-hidden="true" /> Grabando {duracion(segundos)}
              </span>
            </>
          ) : hayTexto ? (
            <>
              <Boton variante="secundario" icono={<Icono nombre="microfono" tamano={18} />} onClick={grabar} disabled={ocupado || deshabilitado}>
                Reanudar
              </Boton>
              <Boton variante="ghost" onClick={() => setConfirmarBorrado(true)} disabled={ocupado || deshabilitado}>
                Volver a grabar
              </Boton>
            </>
          ) : (
            <Boton variante="secundario" icono={<Icono nombre="microfono" tamano={18} />} onClick={grabar} disabled={ocupado || deshabilitado}>
              Grabar
            </Boton>
          )}
          {estado === 'pidiendo_permiso' && <span className="grabador-hc__estado" role="status">Esperando el permiso del micrófono…</span>}
          {estado === 'transcribiendo' && <span className="grabador-hc__estado" role="status">Transcribiendo…</span>}
        </div>
      )}

      <textarea
        id={id}
        className="campo grabador-hc__texto"
        rows={8}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        disabled={deshabilitado || estado === 'transcribiendo'}
        aria-invalid={error ? true : undefined}
        aria-describedby={avisoId}
        placeholder={sinMicrofono ? 'Escribí acá el resumen…' : 'El texto transcripto aparece acá y lo podés corregir.'}
      />

      <span id={avisoId}>
        {aviso && <span className="campo-grupo__error" role="alert">{aviso} </span>}
        {error && <span className="campo-grupo__error">{error}</span>}
        {!error && !aviso && <span className="campo-grupo__ayuda">{ayuda}</span>}
      </span>

      <ModalConfirmacion
        abierto={confirmarBorrado}
        titulo="¿Volver a grabar?"
        textoConfirmar="Borrar y grabar"
        peligro
        onConfirmar={volverAGrabar}
        onCancelar={() => setConfirmarBorrado(false)}
      >
        Se borra el texto actual, incluidas tus correcciones. Si querés sumar algo a lo que ya está, usá Reanudar.
      </ModalConfirmacion>
    </div>
  )
}
