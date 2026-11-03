// Texto para mostrar al usuario según el error que devolvió la API (formato {error: {codigo, mensaje, detalle}}).
const MENSAJES = {
  CREDENCIALES_INVALIDAS: 'Correo o contraseña incorrectos.',
  CUENTA_INACTIVA: 'Tu cuenta está inactiva. Consultá con el laboratorio.',
  MAIL_NO_DISPONIBLE: 'No pudimos enviar el código por mail. Probá de nuevo en unos minutos.',
  CONTRASENA_ACTUAL_INCORRECTA: 'La contraseña actual es incorrecta.',
  CODIGO_VENCIDO: 'El código venció. Volvé a ingresar para recibir uno nuevo.',
  DESAFIO_AGOTADO: 'Superaste el máximo de intentos. Volvé a ingresar para recibir un código nuevo.',
  DESAFIO_INVALIDO: 'La verificación ya no es válida. Volvé a ingresar para recibir un código nuevo.',
}

// Errores que terminan el intento de verificación: no tiene sentido seguir escribiendo códigos.
export const ERRORES_TERMINALES = ['CODIGO_VENCIDO', 'DESAFIO_AGOTADO', 'DESAFIO_INVALIDO']

export const codigoDeError = (e) => e?.data?.error?.codigo

export function mensajeDeError(e) {
  if (!e || e.status === undefined) {
    return 'No pudimos conectarnos con el servidor. Revisá tu conexión e intentá de nuevo.'
  }
  const error = e.data?.error
  if (error?.codigo === 'CODIGO_INCORRECTO') {
    const n = error.detalle?.intentos_restantes
    return n === 1 ? 'Código incorrecto. Te queda 1 intento.' : `Código incorrecto. Te quedan ${n} intentos.`
  }
  if (error?.codigo === 'VALIDACION' && error.detalle?.campos?.length) {
    return error.detalle.campos.map((c) => c.problema).join('. ') + '.'
  }
  return MENSAJES[error?.codigo] ?? error?.mensaje ?? 'Ocurrió un error inesperado. Intentá de nuevo.'
}
