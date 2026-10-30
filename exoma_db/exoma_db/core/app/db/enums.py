"""Enums de dominio. Cada uno se mapea a un ENUM nativo de Postgres (ver pg_enum)."""
from enum import Enum


class RolUsuario(str, Enum):
    paciente = "paciente"
    medico = "medico"
    gerente_medico = "gerente_medico"
    administrativo = "administrativo"
    bioinformatico = "bioinformatico"
    transportista = "transportista"


class TipoSospecha(str, Enum):
    clinica = "clinica"
    familiar = "familiar"


class EstadoEstudio(str, Enum):
    creado = "creado"
    esperando_autorizacion = "esperando_autorizacion"  # obra social
    rechazado = "rechazado"  # rechazo de obra social
    pagado = "pagado"
    turno_sacado = "turno_sacado"
    listo_para_retirar = "listo_para_retirar"
    en_camino_laboratorio_central = "en_camino_laboratorio_central"
    esperando_armado_lote = "esperando_armado_lote"
    en_viaje_a_corea = "en_viaje_a_corea"
    en_analisis_bioinformatica = "en_analisis_bioinformatica"
    en_analisis_de_un_bioinformatico = "en_analisis_de_un_bioinformatico"
    finalizado = "finalizado"


class EstadoLote(str, Enum):
    esperando_autorizacion_ministerio = "esperando_autorizacion_ministerio"
    esperando_retiro = "esperando_retiro"
    en_viaje_a_corea = "en_viaje_a_corea"


class ResultadoAnalisis(str, Enum):
    positivo = "positivo"
    negativo = "negativo"


class OrigenGen(str, Enum):
    patologia = "patologia"
    hallazgo_secundario = "hallazgo_secundario"
    manual = "manual"


class ClasificacionVariante(str, Enum):
    patogenica = "patogenica"
    benigna = "benigna"
    inocua = "inocua"
    vus = "vus"  # variante de significado incierto


class EstadoTurno(str, Enum):
    reservado = "reservado"
    cancelado = "cancelado"
    asistido = "asistido"
    ausente = "ausente"


class OrigenPago(str, Enum):
    paciente = "paciente"
    obra_social = "obra_social"


class ConceptoPago(str, Enum):
    estudio = "estudio"  # pago particular completo (con o sin cupón)
    diferencia_cobertura = "diferencia_cobertura"  # parte no cubierta por la obra social
    cobertura_obra_social = "cobertura_obra_social"  # parte que paga la obra social


class TipoAviso(str, Enum):
    presupuesto_emitido = "presupuesto_emitido"
    autorizacion_obra_social = "autorizacion_obra_social"
    rechazo_obra_social = "rechazo_obra_social"
    reautorizacion_solicitada = "reautorizacion_solicitada"
    diferencia_a_abonar = "diferencia_a_abonar"
    puede_sacar_turno = "puede_sacar_turno"
    recordatorio_turno = "recordatorio_turno"
    remuestreo = "remuestreo"
    pago_perdido = "pago_perdido"
    resultado_para_analizar = "resultado_para_analizar"
    resultado_disponible = "resultado_disponible"


class EstrategiaCdss(str, Enum):
    """Estrategias del módulo 4 (CDSS). Se guardan como valor en `configuracion`."""

    mayor_cantidad_sintomas = "mayor_cantidad_sintomas"
    mayor_cantidad_cardinales = "mayor_cantidad_cardinales"
    menor_diferencia_sintomas = "menor_diferencia_sintomas"


# (nombre del tipo en Postgres, clase) — usado por la migración y por el generador de DER
PG_ENUMS: list[tuple[str, type[Enum]]] = [
    ("rol_usuario", RolUsuario),
    ("tipo_sospecha", TipoSospecha),
    ("estado_estudio", EstadoEstudio),
    ("estado_lote", EstadoLote),
    ("resultado_analisis", ResultadoAnalisis),
    ("origen_gen", OrigenGen),
    ("clasificacion_variante", ClasificacionVariante),
    ("estado_turno", EstadoTurno),
    ("origen_pago", OrigenPago),
    ("concepto_pago", ConceptoPago),
    ("tipo_aviso", TipoAviso),
]
