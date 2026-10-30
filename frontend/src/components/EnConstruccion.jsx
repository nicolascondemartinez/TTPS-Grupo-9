import { useLocation } from 'react-router-dom'
import EncabezadoPagina from './EncabezadoPagina.jsx'
import Tarjeta from './Tarjeta.jsx'

// Se muestra en las rutas del menú que todavía no tienen pantalla.
export default function EnConstruccion({ titulo = 'En construcción' }) {
  const { pathname } = useLocation()
  return (
    <>
      <EncabezadoPagina etiqueta="Próximamente" titulo={titulo} />
      <div className="en-construccion">
        <Tarjeta>
          <p>Esta pantalla todavía no está hecha.</p>
          <p className="tarjeta__subtitulo">Ruta: {pathname}</p>
        </Tarjeta>
      </div>
    </>
  )
}
