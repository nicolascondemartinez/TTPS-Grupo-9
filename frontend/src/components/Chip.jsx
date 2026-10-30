// Chip con punto + texto (el estado no se distingue solo por color).
// tipo: neutro | curso | atencion | error | listo
export default function Chip({ tipo = 'neutro', children }) {
  return <span className={`chip chip-${tipo}`}>{children}</span>
}
