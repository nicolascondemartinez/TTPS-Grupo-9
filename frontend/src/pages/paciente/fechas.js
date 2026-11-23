// Formato de fechas y horas en hora argentina, para las pantallas de turnos.
// El backend manda los horarios con zona horaria ("2026-11-24T09:15:00-03:00") y los días como "2026-11-24".
const ZONA = 'America/Argentina/Buenos_Aires'

const DIA_LARGO = new Intl.DateTimeFormat('es-AR', { weekday: 'long', day: 'numeric', month: 'long', timeZone: ZONA })
const DIA_CORTO = new Intl.DateTimeFormat('es-AR', { weekday: 'short', day: 'numeric', month: 'numeric', timeZone: ZONA })
const HORA = new Intl.DateTimeFormat('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: ZONA })

// Un día "2026-11-24" se interpreta al mediodía argentino para que ninguna zona horaria lo corra al día anterior.
const aFecha = (dia) => new Date(`${dia}T12:00:00-03:00`)

export const diaLargo = (dia) => DIA_LARGO.format(aFecha(dia))          // "lunes, 24 de noviembre"
export const diaCorto = (dia) => DIA_CORTO.format(aFecha(dia))          // "lun, 24/11"
export const hora = (momento) => HORA.format(new Date(momento))         // "09:15"
export const diaDeHorario = (momento) => DIA_LARGO.format(new Date(momento))   // "martes, 24 de noviembre"
export const conMayuscula = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1)
