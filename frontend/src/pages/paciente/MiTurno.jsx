import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import Chip from '../../components/Chip.jsx'
import Icono from '../../components/Icono.jsx'
import ModalConfirmacion from '../../components/ModalConfirmacion.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import ConsentimientoFirmado from './ConsentimientoFirmado.jsx'
import { conMayuscula, diaDeHorario, hora } from './fechas.js'

// El turno reservado: centro, día y hora, inasistencias acumuladas y la opción de cancelar.
export default function MiTurno({ estudioId, alCancelar }) {
  const notificar = useNotificar()
  const [turno, setTurno] = useState(null)
  const [error, setError] = useState('')
  const [confirmando, setConfirmando] = useState(false)
  const [cancelando, setCancelando] = useState(false)

  useEffect(() => {
    api
      .get(`/estudios/${estudioId}/turno`)
      .then(setTurno)
      .catch((e) => setError(mensajeDeError(e)))
  }, [estudioId])

  const cancelar = async () => {
    setConfirmando(false)
    setCancelando(true)
    try {
      await api.post(`/turnos/${turno.id}/cancelar`)
      notificar('Turno cancelado. Podés sacar otro cuando quieras.')
      alCancelar()
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
      setCancelando(false)
    }
  }
  const descargar = async (documento, nombre) => {
    try {
      await api.descargar(`/turnos/${turno.id}/${documento}.pdf`, nombre)
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    }
  }

  if (error)
    return (
      <p role="alert" className="turnos__error">
        {error}
      </p>
    )
  if (!turno) return <p role="status">Cargando tu turno…</p>

  const restantes = turno.inasistencias_maximas - turno.inasistencias
  return (
    <div className="turnos">
      <Tarjeta titulo="Tu turno de extracción" filo>
        <p className="turnos__fecha">
          <span className="turnos__dia">{conMayuscula(diaDeHorario(turno.fecha_hora))}</span>
          <span className="turnos__hora">{hora(turno.fecha_hora)} hs</span>
        </p>
        <p>
          <strong>{turno.centro.nombre}</strong>
          <br />
          <span className="turnos__texto">{turno.centro.direccion}</span>
        </p>
        <p className="turnos__texto">No necesitás ninguna preparación especial (no hace falta ayuno).</p>
        <div className="turnos__documentos">
          <p className="turnos__texto">
            Descargá el consentimiento, firmalo y subilo acá abajo. El día del turno llevá la orden de extracción.
          </p>
          <div className="turnos__acciones">
            <Boton
              variante="secundario"
              icono={<Icono nombre="documento" tamano={18} />}
              onClick={() => descargar('orden', 'orden-de-extraccion.pdf')}
            >
              Orden de extracción
            </Boton>
            <Boton
              variante="secundario"
              icono={<Icono nombre="documento" tamano={18} />}
              onClick={() => descargar('consentimiento', 'consentimiento-informado.pdf')}
            >
              Consentimiento informado
            </Boton>
          </div>
        </div>
        <ConsentimientoFirmado estudioId={estudioId} />
        <div className="turnos__inasistencias">
          <Chip tipo={turno.inasistencias > 0 ? 'atencion' : 'neutro'}>
            Inasistencias: {turno.inasistencias} de {turno.inasistencias_maximas}
          </Chip>
          <span className="turnos__texto">
            {restantes === 1
              ? 'Si faltás a este turno, perdés el pago del estudio.'
              : `Si faltás ${restantes} veces, perdés el pago del estudio.`}
          </span>
        </div>

        <div className="turnos__acciones">
          <Boton
            variante="secundario"
            className="btn-peligro-borde"
            onClick={() => setConfirmando(true)}
            disabled={cancelando}
          >
            {cancelando ? 'Cancelando…' : 'Cancelar turno'}
          </Boton>
        </div>
      </Tarjeta>

      <ModalConfirmacion
        abierto={confirmando}
        titulo="¿Cancelar el turno?"
        peligro
        textoConfirmar="Cancelar turno"
        textoCancelar="Volver"
        onConfirmar={cancelar}
        onCancelar={() => setConfirmando(false)}
      >
        El turno del {diaDeHorario(turno.fecha_hora)} a las {hora(turno.fecha_hora)} hs queda libre para otra persona.
        Cancelar no cuenta como inasistencia y vas a poder sacar otro.
      </ModalConfirmacion>
    </div>
  )
}
