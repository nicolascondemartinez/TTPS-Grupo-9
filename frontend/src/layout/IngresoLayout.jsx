import AdnHelice from '../components/AdnHelice.jsx'
import Logo from '../components/Logo.jsx'

// Marco de las pantallas de acceso (ingreso, cambio de contraseña, código de verificación):
// fondo oscuro con brillos y ADN a la izquierda, tarjeta blanca a la derecha con `children`.
export default function IngresoLayout({ children }) {
  return (
    <div className="ingreso fondo-oscuro">
      <div className="ingreso__lado">
        <Logo variante="oscuro" />
        <div className="ingreso__hero">
          <div className="ingreso__textos">
            <span className="etiqueta">Acceso al sistema</span>
            <h1 className="ingreso__titulo">
              Estudios de <span className="ingreso__titulo-grad">exoma clínico</span>, de punta a punta.
            </h1>
            <p className="ingreso__bajada">Ingresá con tu cuenta para ver y gestionar tus estudios.</p>
          </div>
          <div className="ingreso__adn"><AdnHelice /></div>
        </div>
        <p className="ingreso__pie">Laboratorio de genética clínica</p>
      </div>
      <div className="ingreso__panel">
        <div className="ingreso__tarjeta">
          <div className="ingreso__tarjeta-cuerpo">{children}</div>
        </div>
      </div>
    </div>
  )
}
