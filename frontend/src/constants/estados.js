// Estados del estudio: mismos valores que el enum EstadoEstudio del backend
// (backend/app/db/enums.py). Cada uno tiene su texto y el tipo de chip (ver DESIGN.md §2).
// Tipos: neutro | curso | atencion | error | listo
export const ESTADOS_ESTUDIO = {
  creado: { texto: 'Creado', tipo: 'neutro' },
  esperando_autorizacion: { texto: 'Esperando autorización', tipo: 'atencion' },
  rechazado: { texto: 'Rechazado', tipo: 'error' },
  pagado: { texto: 'Pagado', tipo: 'curso' },
  turno_sacado: { texto: 'Turno sacado', tipo: 'curso' },
  listo_para_retirar: { texto: 'Listo para retirar', tipo: 'atencion' },
  en_camino_laboratorio_central: { texto: 'En camino al laboratorio central', tipo: 'curso' },
  esperando_armado_lote: { texto: 'Esperando armado de lote', tipo: 'curso' },
  en_viaje_a_corea: { texto: 'En viaje a Corea', tipo: 'curso' },
  en_analisis_bioinformatica: { texto: 'En análisis por bioinformática', tipo: 'curso' },
  en_analisis_de_un_bioinformatico: { texto: 'En análisis de un bioinformático', tipo: 'curso' },
  finalizado: { texto: 'Finalizado', tipo: 'listo' },
}
