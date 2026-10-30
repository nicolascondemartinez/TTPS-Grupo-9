// Montos en dólares con el formato argentino: USD 590 · USD 1.250 · USD 552,50
// El backend manda los montos como texto ("590.00"), acá se aceptan texto o número.
const SIN_DECIMALES = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })
const CON_DECIMALES = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function formatearUSD(valor) {
  const numero = Number(valor)
  const formato = Number.isInteger(numero) ? SIN_DECIMALES : CON_DECIMALES
  return `USD ${formato.format(numero)}`
}

export default function Monto({ valor }) {
  return <span className="monto">{formatearUSD(valor)}</span>
}