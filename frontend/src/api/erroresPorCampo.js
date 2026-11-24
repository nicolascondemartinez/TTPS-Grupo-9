// Problemas por campo de un 400 o 409 del backend: { error: { detalle: { campos: [{ campo, problema }] } } }.
// "especialidades[1]" se agrupa bajo "especialidades". Devuelve { campo: 'Mensaje con mayúscula y punto.' }.
export function erroresPorCampo(e) {
  const campos = e?.data?.error?.detalle?.campos ?? []
  const errores = {}
  for (const { campo, problema } of campos) {
    const clave = campo.split('[')[0]
    errores[clave] ??= `${problema.charAt(0).toUpperCase()}${problema.slice(1)}.`
  }
  return errores
}