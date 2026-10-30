import { createContext, useCallback, useContext, useState } from 'react'
import Icono from './Icono.jsx'

// Avisos cortos que aparecen abajo a la derecha y se van solos (ej "Pago registrado")
// Uso en cualquier pantalla:
//   const notificar = useNotificar()
//   notificar('Pago registrado')                      // éxito
//   notificar('No se pudo guardar', 'error')          // tipos: exito | error | info
const NotificacionesContext = createContext(null)
const DURACION_MS = 4000

export function NotificacionesProvider({ children }) {
  const [avisos, setAvisos] = useState([])

  const cerrar = useCallback((id) => setAvisos((lista) => lista.filter((a) => a.id !== id)), [])

  const notificar = useCallback((texto, tipo = 'exito') => {
    const id = crypto.randomUUID()
    setAvisos((lista) => [...lista, { id, texto, tipo }])
    setTimeout(() => cerrar(id), DURACION_MS)
  }, [cerrar])

  return (
    <NotificacionesContext.Provider value={notificar}>
      {children}
      <div className="notificaciones" role="status" aria-live="polite">
        {avisos.map((a) => (
          <div key={a.id} className={`notificacion notificacion--${a.tipo}`}>
            <span className="notificacion__texto">{a.texto}</span>
            <button type="button" className="notificacion__cerrar" onClick={() => cerrar(a.id)}>
              <Icono nombre="cerrar" tamano={16} titulo="Cerrar aviso" />
            </button>
          </div>
        ))}
      </div>
    </NotificacionesContext.Provider>
  )
}

export function useNotificar() {
  return useContext(NotificacionesContext)
}
