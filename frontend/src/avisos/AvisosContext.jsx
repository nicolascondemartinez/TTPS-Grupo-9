import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../api/client.js'

// Cantidad de avisos sin leer del usuario, para la insignia del menú. Se actualiza sola cada minuto.
const AvisosContext = createContext({ pendientes: 0, refrescar: () => {} })
const CADA_MS = 60000

export function AvisosProvider({ children }) {
  const [pendientes, setPendientes] = useState(0)

  const refrescar = useCallback(async () => {
    try {
      const { cantidad } = await api.get('/avisos/pendientes/cantidad')
      setPendientes(cantidad)
    } catch {
      // si falla, se queda con el último valor
    }
  }, [])

  useEffect(() => {
    refrescar()
    const id = setInterval(refrescar, CADA_MS)
    return () => clearInterval(id)
  }, [refrescar])

  return <AvisosContext.Provider value={{ pendientes, refrescar }}>{children}</AvisosContext.Provider>
}

export function useAvisos() {
  return useContext(AvisosContext)
}