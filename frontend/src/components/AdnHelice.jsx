import adn from '../assets/dna.svg'

// Hélice grande de ADN. Solo para ingreso y portadas, nunca en pantallas de trabajo (DESIGN.md §5).
export default function AdnHelice({ alto = 352 }) {
  return <img className="adn" src={adn} alt="" height={alto} width={alto * 0.3} />
}
