import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import ModalConfirmacion from '../../components/ModalConfirmacion.jsx'
import Monto from '../../components/Monto.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import Tabla from '../../components/Tabla.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import '../paciente/pagos.css'

// Administrativo: estudios en estado Creado que todavía no tienen presupuesto (escenario "Emitir el presupuesto").
// Al emitirlo, el paciente recibe un aviso y un mail.
export default function Presupuestos() {
  const notificar = useNotificar()
  const [pendientes, setPendientes] = useState([])
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [error, setError] = useState('')
  const [aEmitir, setAEmitir] = useState(null) // estudio elegido para confirmar
  const [emitiendo, setEmitiendo] = useState(false)

  useEffect(() => {
    api.get('/presupuestos/pendientes')
      .then((d) => { setPendientes(d.estudios.map((e) => ({ ...e, id: e.estudio_id }))); setEstado('listo') })
      .catch((e) => { setError(mensajeDeError(e)); setEstado('error') })
  }, [])

  const emitir = async () => {
    const estudio = aEmitir
    setAEmitir(null)
    setEmitiendo(true)
    try {
      await api.post(`/estudios/${estudio.estudio_id}/presupuesto`)
      setPendientes((lista) => lista.filter((e) => e.id !== estudio.id))
      notificar(`Presupuesto emitido para ${estudio.paciente}`)
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    } finally {
      setEmitiendo(false)
    }
  }

  const columnas = [
    { clave: 'paciente', titulo: 'Paciente', render: (e) => <strong>{e.paciente}</strong> },
    { clave: 'dni', titulo: 'DNI' },
    { clave: 'cantidad_genes', titulo: 'Genes' },
    {
      clave: 'monto_estimado',
      titulo: 'Monto',
      render: (e) => (e.monto_estimado ? <Monto valor={e.monto_estimado} /> : <span className="pagos__error">Sin genes</span>),
    },
    { clave: 'creado_at', titulo: 'Alta del estudio', render: (e) => new Date(e.creado_at).toLocaleDateString('es-AR') },
    {
      clave: 'acciones',
      titulo: <span className="sr-only">Acciones</span>,
      render: (e) => (
        <Boton variante="secundario" disabled={!e.monto_estimado || emitiendo} onClick={() => setAEmitir(e)}>
          Emitir presupuesto
        </Boton>
      ),
    },
  ]

  return (
    <>
      <EncabezadoPagina etiqueta="Pagos" titulo="Presupuestos por emitir" />

      {estado === 'cargando' && <p role="status">Cargando estudios…</p>}
      {estado === 'error' && <p role="alert" className="pagos__error">{error}</p>}
      {estado === 'listo' && (
        <Tabla titulo="Estudios sin presupuesto" columnas={columnas} filas={pendientes} vacio="No hay estudios esperando presupuesto." />
      )}

      <ModalConfirmacion
        abierto={aEmitir !== null} titulo="¿Emitir el presupuesto?" textoConfirmar="Emitir"
        onConfirmar={emitir} onCancelar={() => setAEmitir(null)}
      >
        {aEmitir && (
          <>
            {aEmitir.paciente} va a recibir un presupuesto de <Monto valor={aEmitir.monto_estimado} /> por{' '}
            {aEmitir.cantidad_genes} genes, con un aviso y un mail.
          </>
        )}
      </ModalConfirmacion>
    </>
  )
}