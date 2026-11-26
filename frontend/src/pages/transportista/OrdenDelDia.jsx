import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import Boton from '../../components/Boton.jsx'
import Chip from '../../components/Chip.jsx'
import EncabezadoPagina from '../../components/EncabezadoPagina.jsx'
import Mapa from '../../components/Mapa.jsx'
import { useNotificar } from '../../components/Notificaciones.jsx'
import Tarjeta from '../../components/Tarjeta.jsx'
import { mensajeDeError } from '../acceso/errores.js'
import './orden_del_dia.css'

/**
 * Vista móvil del transportista: muestra su orden del día, el mapa del recorrido
 * y permite marcar paradas recogidas y registrar la llegada al laboratorio central.
 */
export default function OrdenDelDia() {
  const notificar = useNotificar()
  const [orden, setOrden] = useState(null)
  const [estado, setEstado] = useState('cargando') // cargando | listo | error
  const [error, setError] = useState('')
  const [ocupadoId, setOcupadoId] = useState(null)

  /** Carga o recarga la orden del día actual desde el backend. */
  function cargarOrden() {
    api.get('/transportista/orden-del-dia')
      .then((d) => {
        setOrden(d.orden)
        setEstado('listo')
      })
      .catch((e) => {
        setError(mensajeDeError(e))
        setEstado('error')
      })
  }

  useEffect(() => {
    cargarOrden()
  }, [])

  /** Marca una parada como recogida y refresca la orden del día. */
  async function handleRecoger(parada) {
    setOcupadoId(parada.id)
    try {
      await api.post(`/transportista/paradas/${parada.id}/recoger`)
      notificar(`Parada #${parada.posicion} (${parada.centro.nombre}) recogida`)
      cargarOrden()
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    } finally {
      setOcupadoId(null)
    }
  }

  /** Registra la llegada al laboratorio central cuando todas las paradas fueron recogidas. */
  async function handleEntregar() {
    setOcupadoId('entregar')
    try {
      await api.post(`/transportista/ordenes/${orden.id}/entregar`)
      notificar('Llegada al laboratorio central registrada')
      cargarOrden()
    } catch (e) {
      notificar(mensajeDeError(e), 'error')
    } finally {
      setOcupadoId(null)
    }
  }

  const paradas = orden?.paradas ?? []
  const proximaPendiente = paradas.find((p) => !p.recogido)
  const todasRecogidas = paradas.length > 0 && !proximaPendiente
  const centrosMapa = paradas.map((p) => ({
    id: p.centro.id,
    nombre: `#${p.posicion} · ${p.centro.nombre}`,
    direccion: p.centro.direccion,
    latitud: p.centro.latitud,
    longitud: p.centro.longitud,
    recogido: p.recogido,
  }))

  return (
    <div className="orden-movil">
      <EncabezadoPagina etiqueta="Logística" titulo="Orden del día" />

      {estado === 'cargando' && <p role="status">Cargando orden del día…</p>}
      {estado === 'error' && <p role="alert" className="orden-movil__error">{error}</p>}

      {estado === 'listo' && !orden && (
        <Tarjeta titulo="Sin recorrido asignado" subtitulo="No tenés una orden del día generada para hoy." />
      )}

      {estado === 'listo' && orden && (
        <>
          <Mapa centros={centrosMapa} recorrido={centrosMapa} altura={260} />

          {paradas.map((parada) => {
            const esProxima = proximaPendiente?.id === parada.id
            return (
              <Tarjeta key={parada.id} filo={esProxima}>
                <div className="orden-movil__parada-header">
                  <span className="orden-movil__posicion">Parada #{parada.posicion}</span>
                  <Chip tipo={parada.recogido ? 'listo' : esProxima ? 'curso' : 'neutro'}>
                    {parada.recogido ? 'Recogida' : esProxima ? 'Siguiente' : 'Pendiente'}
                  </Chip>
                </div>

                <h3>{parada.centro.nombre}</h3>
                <p className="orden-movil__direccion">{parada.centro.direccion}</p>
                <p className="orden-movil__muestras">
                  Muestras a retirar: <strong>{parada.cantidad_muestras}</strong>
                </p>

                {!parada.recogido && (
                  <Boton
                    anchoCompleto
                    disabled={!esProxima || ocupadoId !== null}
                    onClick={() => handleRecoger(parada)}
                  >
                    {ocupadoId === parada.id
                      ? 'Registrando…'
                      : esProxima
                        ? 'Marcar centro como recogido'
                        : 'Completá la parada anterior primero'}
                  </Boton>
                )}
              </Tarjeta>
            )
          })}

          {orden.llegada_central_at ? (
            <Chip tipo="listo">Entrega en laboratorio central registrada</Chip>
          ) : (
            <Boton
              anchoCompleto
              disabled={!todasRecogidas || ocupadoId !== null}
              onClick={handleEntregar}
            >
              {ocupadoId === 'entregar' ? 'Registrando llegada…' : 'Registrar llegada al laboratorio central'}
            </Boton>
          )}
        </>
      )}
    </div>
  )
}