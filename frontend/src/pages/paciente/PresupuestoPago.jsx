import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import EstadoChip from '../../components/EstadoChip.jsx'
import ModalConfirmacion from '../../components/ModalConfirmacion.jsx'
import Monto, { formatearUSD } from '../../components/Monto.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import './pagos.css'

// Paciente: ve el presupuesto de su estudio y lo paga (escenario "Abonar el estudio").
// El pago es simulado y en un solo pago. Cupón y obra social se suman en las etapas siguientes.
export default function PresupuestoPago() {
  const [estudios, setEstudios] = useState([])
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [error, setError] = useState('')

  const cargar = useCallback(() => {
    api.get('/presupuestos/mios')
      .then((d) => { setEstudios(d.estudios); setEstado('listo') })
      .catch((e) => { setError(mensajeDeError(e)); setEstado('error') })
  }, [])

  useEffect(cargar, [cargar])

  return (
    <>
      <EncabezadoPagina etiqueta="Pagos" titulo="Presupuesto y pago" />

      {estado === 'cargando' && <p role="status">Cargando tu presupuesto…</p>}
      {estado === 'error' && <p role="alert" className="pagos__error">{error}</p>}
      {estado === 'listo' && estudios.length === 0 && (
        <Tarjeta><p>Todavía no tenés estudios. Cuando tu médico te dé de alta uno, vas a ver acá el presupuesto.</p></Tarjeta>
      )}
      {estado === 'listo' && (
        <div className="pagos__lista">
          {estudios.map((e) => <EstudioAPagar key={e.estudio_id} estudio={e} alPagar={cargar} />)}
        </div>
      )}
    </>
  )
}

function EstudioAPagar({ estudio, alPagar }) {
  const navigate = useNavigate()
  const notificar = useNotificar()
  const [confirmando, setConfirmando] = useState(false)
  const [pagando, setPagando] = useState(false)
  const [error, setError] = useState('')
  const { presupuesto } = estudio
  const fecha = new Date(estudio.creado_at).toLocaleDateString('es-AR')

  const pagar = async () => {
    setConfirmando(false)
    setPagando(true)
    setError('')
    try {
      await api.post(`/estudios/${estudio.estudio_id}/pagos`)
      notificar('Pago registrado. Ya podés sacar tu turno.')
      alPagar()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setPagando(false)
    }
  }

  return (
    <Tarjeta titulo="Exoma clínico" subtitulo={`Estudio pedido el ${fecha}`} filo={estudio.estado === 'creado' && !!presupuesto}>
      <div><EstadoChip estado={estudio.estado} /></div>

      {!presupuesto && (
        <p className="pagos__texto">Tu presupuesto todavía no está listo. Te avisamos por mail cuando lo esté.</p>
      )}

      {presupuesto && <Desglose presupuesto={presupuesto} />}

      {presupuesto && estudio.estado === 'creado' && (
        <>
          <p className="pagos__texto">El pago es en un solo pago e incluye la extracción de sangre.</p>
          <div className="pagos__acciones">
            <Boton onClick={() => setConfirmando(true)} disabled={pagando}>
              {pagando ? 'Procesando…' : `Pagar ${formatearUSD(presupuesto.monto_total)}`}
            </Boton>
          </div>
        </>
      )}

      {estudio.estado === 'pagado' && (
        <div className="pagos__acciones">
          <p className="pagos__texto">Tu estudio está pago. El siguiente paso es sacar el turno para la extracción.</p>
          <Boton variante="secundario" onClick={() => navigate('/paciente/turno')}>Sacar turno</Boton>
        </div>
      )}

      {error && <p role="alert" className="pagos__error">{error}</p>}

      {presupuesto && (
        <ModalConfirmacion
          abierto={confirmando} titulo="¿Confirmás el pago?" textoConfirmar="Pagar"
          onConfirmar={pagar} onCancelar={() => setConfirmando(false)}
        >
          Vas a pagar <Monto valor={presupuesto.monto_total} /> por tu exoma clínico. Por ahora el pago es simulado.
        </ModalConfirmacion>
      )}
    </Tarjeta>
  )
}

function Desglose({ presupuesto }) {
  const adicionales = presupuesto.genes_adicionales
  const subtotalAdicionales = Number(presupuesto.precio_gen_adicional) * adicionales
  return (
    <dl className="pagos__desglose">
      <div>
        <dt>Estudio (hasta {presupuesto.genes_incluidos} genes)</dt>
        <dd><Monto valor={presupuesto.precio_base} /></dd>
      </div>
      {adicionales > 0 && (
        <div>
          <dt>{adicionales} {adicionales === 1 ? 'gen adicional' : 'genes adicionales'} × <Monto valor={presupuesto.precio_gen_adicional} /></dt>
          <dd><Monto valor={subtotalAdicionales} /></dd>
        </div>
      )}
      <div className="pagos__total">
        <dt>Total ({presupuesto.cantidad_genes} genes)</dt>
        <dd><Monto valor={presupuesto.monto_total} /></dd>
      </div>
    </dl>
  )
}
