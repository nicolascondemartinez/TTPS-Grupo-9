import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import Chip from '../../components/Chip.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import SubirArchivo from '../../components/SubirArchivo.jsx'
import { mensajeDeError } from '../acceso/errores.js'

// Carga del consentimiento informado firmado (uno por estudio). Sin él, el administrativo no puede
// registrar la extracción el día del turno.
export default function ConsentimientoFirmado({ estudioId }) {
  const notificar = useNotificar()
  const [info, setInfo] = useState(null) // { cargado, subido_at } que manda el back
  const [error, setError] = useState('')
  const [archivo, setArchivo] = useState(null) // el PDF que eligió para subir
  const [subiendo, setSubiendo] = useState(false)
  const [reemplazando, setReemplazando] = useState(false) // ya tenía uno cargado y quiere subir otro

  useEffect(() => {
    api.get(`/estudios/${estudioId}/consentimiento`).then(setInfo).catch((e) => setError(mensajeDeError(e)))
  }, [estudioId])

  const subir = async () => {
    const datos = new FormData()
    datos.append('archivo', archivo) // el back lo lee del campo "archivo"
    setSubiendo(true)
    try {
      setInfo(await api.enviarArchivos(`/estudios/${estudioId}/consentimiento`, datos))
      setArchivo(null)
      setReemplazando(false)
      notificar('Consentimiento cargado')
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    } finally {
      setSubiendo(false)
    }
  }

  const ver = async () => {
    try {
      await api.descargar(`/estudios/${estudioId}/consentimiento.pdf`, 'consentimiento-firmado.pdf')
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    }
  }

  if (error) return <p role="alert" className="turnos__error">{error}</p>
  if (!info) return <p role="status">Buscando tu consentimiento…</p>

  // ya está cargado: lo puede ver o reemplazar
  if (info.cargado && !reemplazando) {
    return (
      <div className="turnos__consentimiento">
        <p className="turnos__subtitulo">Consentimiento firmado</p>
        <div className="turnos__inasistencias">
          <Chip tipo="listo">Cargado el {new Date(info.subido_at).toLocaleDateString('es-AR')}</Chip>
        </div>
        <div className="turnos__acciones">
          <Boton variante="secundario" onClick={ver}>Ver el que subí</Boton>
          <Boton variante="ghost" onClick={() => setReemplazando(true)}>Reemplazar</Boton>
        </div>
      </div>
    )
  }

  // todavía no lo cargó (o lo quiere reemplazar)
  return (
    <div className="turnos__consentimiento">
      <p className="turnos__subtitulo">Consentimiento firmado</p>
      {!info.cargado && (
        <div className="turnos__inasistencias">
          <Chip tipo="atencion">Falta cargarlo</Chip>
          <span className="turnos__texto">Sin el consentimiento firmado no te pueden hacer la extracción.</span>
        </div>
      )}
      <SubirArchivo
        etiqueta="Consentimiento firmado (PDF)"
        ayuda="Imprimilo, firmalo y subilo escaneado en PDF, hasta 5 MB."
        onChange={setArchivo}
      />
      <div className="turnos__acciones">
        <Boton onClick={subir} disabled={!archivo || subiendo}>
          {subiendo ? 'Subiendo…' : 'Subir consentimiento'}
        </Boton>
        {reemplazando && <Boton variante="ghost" onClick={() => setReemplazando(false)}>Cancelar</Boton>}
      </div>
    </div>
  )
}