"""Permisos por rol (patrón modulo_accion). Idempotente: se puede correr todas las veces que haga falta.

    poetry run python -m seeds.seed_permisos

Esta es la MATRIZ INICIAL, armada a partir de los escenarios. Cada responsable de un área agrega
acá los permisos de sus pantallas y endpoints (una línea por permiso, bajo el rol que corresponda) y los
usa con @require_permission("modulo_accion"). El seed solo agrega: para quitar un permiso hay que
borrarlo también de la tabla rol_permiso.
"""
from sqlalchemy.dialects.postgresql import insert

from src.core.enums import RolUsuario
from src.core.models import Permiso, RolPermiso
from src.core.database import nueva_sesion

PERMISOS_POR_ROL: dict[RolUsuario, list[str]] = {
    RolUsuario.paciente: [
        "aviso_listar",
        "centro_listar",
        "chatbot_consultar",
        "cobertura_elegir",
        "cupon_aplicar",
        "demanda_presentar",
        "estudio_listar",
        "estudio_ver",
        "informe_descargar",
        "pago_realizar",
        "presupuesto_ver",
        "turno_cancelar",
        "turno_crear",
        "turno_ver",
    ],
    RolUsuario.medico: [
        "aviso_listar",
        "cupon_asignar",
        "cupon_listar",
        "estudio_agregar_genes",
        "estudio_crear",
        "estudio_listar",
        "estudio_reanalizar",
        "estudio_ver",
        "familiar_crear",
        "historia_clinica_grabar",
        "informe_descargar",
        "paciente_crear",
        "paciente_listar",
        "paciente_ver",
        "patologia_listar",
        "sintoma_buscar",
    ],
    RolUsuario.gerente_medico: [
        "aviso_listar",
        "cupon_asignar",
        "cupon_crear",
        "cupon_emitir",
        "cupon_listar",
        "patologia_crear",
        "patologia_editar",
        "patologia_listar",
        "sintoma_buscar",
    ],
    RolUsuario.administrativo: [
        "aviso_listar",
        "centro_listar",
        "cobertura_autorizar",
        "cobertura_rechazar",
        "estudio_listar",
        "estudio_ubicacion_ver",
        "estudio_ver",
        "inasistencia_registrar",
        "lote_listar",
        "lote_programar_retiro",
        "movimiento_listar",
        "obra_social_listar",
        "presupuesto_emitir",
        "presupuesto_ver",
        "remuestreo_notificar",
        "resultado_cargar",
        "transportista_crear",
        "transportista_listar",
        "turno_listar",
    ],
    RolUsuario.bioinformatico: [
        "analisis_cargar",
        "analisis_listar",
        "analisis_tomar",
        "aviso_listar",
        "estudio_ver",
    ],
    RolUsuario.transportista: [
        "aviso_listar",
        "orden_dia_entregar",
        "orden_dia_recoger",
        "orden_dia_ver",
    ],
}


def cargar_permisos(session, matriz: dict[RolUsuario, list[str]] = PERMISOS_POR_ROL) -> None:
    nombres = sorted({p for permisos in matriz.values() for p in permisos})
    session.execute(insert(Permiso).values([{"nombre": n} for n in nombres]).on_conflict_do_nothing(index_elements=["nombre"]))
    ids = {p.nombre: p.id for p in session.query(Permiso).filter(Permiso.nombre.in_(nombres))}
    pares = [{"rol": rol, "permiso_id": ids[n]} for rol, permisos in matriz.items() for n in permisos]
    session.execute(insert(RolPermiso).values(pares).on_conflict_do_nothing())
    session.commit()


def run() -> None:
    with nueva_sesion() as session:
        cargar_permisos(session)
        total = sum(len(v) for v in PERMISOS_POR_ROL.values())
        print(f"{len({p for v in PERMISOS_POR_ROL.values() for p in v})} permisos, {total} asignaciones a roles")