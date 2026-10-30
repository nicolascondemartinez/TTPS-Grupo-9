// Roles: mismos valores que el enum RolUsuario del backend (backend/app/db/enums.py).
// MENU es la navegación lateral de cada rol. Es una propuesta: cada responsable ajusta
// los ítems de su área (texto, ruta e ícono). Mientras una ruta no tenga pantalla,
// se muestra "En construcción".
export const ROLES = {
  paciente: 'Paciente',
  medico: 'Médico tratante',
  gerente_medico: 'Gerente médico',
  administrativo: 'Administrativo',
  bioinformatico: 'Bioinformático',
  transportista: 'Transportista',
}

export const MENU = {
  paciente: [
    { texto: 'Mis estudios', ruta: '/paciente/estudios', icono: 'lista' },
    { texto: 'Presupuesto y pago', ruta: '/paciente/pagos', icono: 'tarjeta' },
    { texto: 'Turno', ruta: '/paciente/turno', icono: 'calendario' },
    { texto: 'Resultados', ruta: '/paciente/resultados', icono: 'documento' },
    { texto: 'Consultas', ruta: '/paciente/consultas', icono: 'chat' },
    { texto: 'Avisos', ruta: '/avisos', icono: 'campana' },
  ],
  medico: [
    { texto: 'Pacientes', ruta: '/medico/pacientes', icono: 'persona' },
    { texto: 'Estudios', ruta: '/medico/estudios', icono: 'lista' },
    { texto: 'Cupones', ruta: '/medico/cupones', icono: 'cupon' },
    { texto: 'Avisos', ruta: '/avisos', icono: 'campana' },
  ],
  gerente_medico: [
    { texto: 'Patologías', ruta: '/gerente/patologias', icono: 'adn' },
    { texto: 'Cupones', ruta: '/gerente/cupones', icono: 'cupon' },
    { texto: 'Avisos', ruta: '/avisos', icono: 'campana' },
  ],
  administrativo: [
    { texto: 'Estudios', ruta: '/administrativo/estudios', icono: 'lista' },
    { texto: 'Obras sociales', ruta: '/administrativo/obras-sociales', icono: 'escudo' },
    { texto: 'Turnos', ruta: '/administrativo/turnos', icono: 'calendario' },
    { texto: 'Lotes', ruta: '/administrativo/lotes', icono: 'caja' },
    { texto: 'Transportistas', ruta: '/administrativo/transportistas', icono: 'camion' },
    { texto: 'Movimientos', ruta: '/administrativo/movimientos', icono: 'tarjeta' },
    { texto: 'Avisos', ruta: '/avisos', icono: 'campana' },
  ],
  bioinformatico: [
    { texto: 'Estudios a analizar', ruta: '/bioinformatico/estudios', icono: 'lista' },
    { texto: 'Avisos', ruta: '/avisos', icono: 'campana' },
  ],
  transportista: [
    { texto: 'Orden del día', ruta: '/transportista/orden-del-dia', icono: 'camion' },
    { texto: 'Avisos', ruta: '/avisos', icono: 'campana' },
  ],
}
