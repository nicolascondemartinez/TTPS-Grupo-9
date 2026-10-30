import { ESTADOS_ESTUDIO } from '../constants/estados.js'
import Chip from './Chip.jsx'

// Chip del estado de un estudio a partir del valor que devuelve el backend (ej. "turno_sacado").
export default function EstadoChip({ estado }) {
  const info = ESTADOS_ESTUDIO[estado] ?? { texto: estado, tipo: 'neutro' }
  return <Chip tipo={info.tipo}>{info.texto}</Chip>
}
