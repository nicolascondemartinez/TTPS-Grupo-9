import { useEffect } from 'react'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

function crearIconoPin(variante = '', contenido = '') {
  return L.divIcon({
    className: 'mapa-pin-wrapper',
    html: `<div class="mapa-pin ${variante}">${contenido}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -16],
  })
}
function AjustarVista({ puntos }) {
  const map = useMap()
  useEffect(() => {
    if (puntos.length === 1) {
      map.setView(puntos[0], 14)
    } else if (puntos.length > 1) {
      map.fitBounds(puntos, { padding: [36, 36] })
    }
  }, [map, puntos])
  return null
}

export default function Mapa({
  centros = [],
  centroSeleccionadoId = null,
  onSeleccionarCentro = null,
  transportista = null,
  recorrido = [],
  altura = 380,
}) {// 1) Juntamos todas las coordenadas para centrar el mapa automáticamente
  const puntos = [
    ...centros.map((c) => [Number(c.latitud), Number(c.longitud)]),
    ...recorrido.map((p) => [Number(p.latitud), Number(p.longitud)]),
    ...(transportista?.latitud != null && transportista?.longitud != null
      ? [[Number(transportista.latitud), Number(transportista.longitud)]]
      : []),
  ]
  // 2) Elegimos la clase CSS del pin según el estado del centro
  function iconoDeCentro(centro) {
    if (centro.id === centroSeleccionadoId) return crearIconoPin('mapa-pin--seleccionado')
    if (centro.recogido) return crearIconoPin('mapa-pin--recogido', '✓')
    return crearIconoPin()
  }
  return (
    <div className="mapa-contenedor" style={{ height: altura }}>
      <MapContainer center={[-34.6037, -58.3816]} zoom={5} style={{ width: '100%', height: '100%' }}>
        <TileLayer
          attribution="&copy; OpenStreetMap"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <AjustarVista puntos={puntos} />
        {/* Marcadores de centros de extracción */}
        {centros.map((centro) => (
          <Marker
            key={centro.id}
            position={[Number(centro.latitud), Number(centro.longitud)]}
            icon={iconoDeCentro(centro)}
            eventHandlers={{
              click: () => onSeleccionarCentro?.(centro),
            }}
          >
            <Popup>
              <p className="mapa-popup__titulo">{centro.nombre}</p>
              <p className="mapa-popup__texto">{centro.direccion}</p>
            </Popup>
          </Marker>
        ))}
        {/* Línea del recorrido (solo si hay al menos 2 paradas) */}
        {recorrido.length > 1 && (
          <Polyline
            positions={recorrido.map((p) => [Number(p.latitud), Number(p.longitud)])}
            pathOptions={{ color: '#6d28d9', weight: 4 }}
          />
        )}
        {/* Marcador del transportista (solo si se pasó la prop transportista) */}
        {transportista?.latitud != null && transportista?.longitud != null && (
          <Marker
            position={[Number(transportista.latitud), Number(transportista.longitud)]}
            icon={crearIconoPin('mapa-pin--transportista', '🚚')}
          >
            <Popup>
              <p className="mapa-popup__titulo">{transportista.nombre}</p>
              {transportista.provincia && (
                <p className="mapa-popup__texto">{transportista.provincia}</p>
              )}
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  )}