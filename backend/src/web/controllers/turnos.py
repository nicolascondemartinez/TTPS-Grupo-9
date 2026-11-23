"""Centros de extracción y turnos: el paciente ve los centros, elige un horario libre, reserva y cancela."""
from flask import Blueprint, Response, g, request
import hmac
import os

from src.core.database import get_db
from src.core.turnos import service as turnos_service
from src.core.turnos.validation import validar_fecha_opcional, validar_reserva
from src.web.security import require_permission
from src.web.views.turno_view import centros_view, inasistencias_procesadas_view, turno_view, turnos_libres_view
from src.core.avisos.mail_service import get_mail_sender
from src.core.common.errors import ApiError

bp = Blueprint("turnos", __name__)


@bp.get("/centros")
@require_permission("centro_listar")
def centros():
    return centros_view(turnos_service.listar_centros(get_db(), request.args.get("provincia_id")))


@bp.get("/centros/<centro_id>/turnos-libres")
@require_permission("centro_listar")
def libres(centro_id):
    desde = validar_fecha_opcional(request.args.get("desde"), "desde")
    hasta = validar_fecha_opcional(request.args.get("hasta"), "hasta")
    return turnos_libres_view(centro_id, turnos_service.turnos_libres(get_db(), centro_id, desde, hasta))


@bp.post("/estudios/<estudio_id>/turno")
@require_permission("turno_crear")
def reservar(estudio_id):
    centro_id, fecha_hora = validar_reserva(request.get_json(silent=True))
    turno, centro, estudio = turnos_service.reservar_turno(get_db(), estudio_id, g.usuario, centro_id, fecha_hora)
    return turno_view(turno, centro, estudio), 201


@bp.get("/estudios/<estudio_id>/turno")
@require_permission("turno_ver")
def ver(estudio_id):
    return turno_view(*turnos_service.turno_vigente(get_db(), estudio_id, g.usuario))


@bp.post("/turnos/<turno_id>/cancelar")
@require_permission("turno_cancelar")
def cancelar(turno_id):
    return turno_view(*turnos_service.cancelar_turno(get_db(), turno_id, g.usuario))

@bp.get("/turnos/<turno_id>/orden.pdf")
@require_permission("turno_ver")
def orden(turno_id):
    return _pdf(*turnos_service.documento_del_turno(get_db(), turno_id, g.usuario, "orden"))


@bp.get("/turnos/<turno_id>/consentimiento.pdf")
@require_permission("turno_ver")
def consentimiento(turno_id):
    return _pdf(*turnos_service.documento_del_turno(get_db(), turno_id, g.usuario, "consentimiento"))

#funcion auxiliar que usan las 2 rutas de arriba
def _pdf(contenido: bytes, nombre: str) -> Response:
    """Respuesta con el PDF para descargar."""
    return Response(contenido, mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})

@bp.post("/turnos/<turno_id>/extraccion")
@require_permission("extraccion_registrar")
def registrar_extraccion(turno_id):
    return turno_view(*turnos_service.registrar_extraccion(get_db(), turno_id, g.usuario))

def _autorizar_job_interno() -> None:
    """Exige cabecera X-Internal-Token igual a INTERNAL_JOBS_TOKEN."""
    token_esperado = os.environ.get("INTERNAL_JOBS_TOKEN", "").strip()
    token_recibido = request.headers.get("X-Internal-Token", "").strip()
    if not token_esperado or not token_recibido or not hmac.compare_digest(token_esperado, token_recibido):
        raise ApiError(401, "TOKEN_INTERNO_INVALIDO", "Token interno inválido o faltante")
    
@bp.post("/turnos/procesar-inasistencias")
def procesar_inasistencias():
    """Job automático (CRON) que registra las inasistencias de turnos reservados vencidos"""
    _autorizar_job_interno()
    datos = request.get_json(silent=True) or {}
    fecha_corte = validar_fecha_opcional(datos.get("fecha_corte"), "fecha_corte")
    resumen = turnos_service.procesar_inasistencias(
        get_db(),
        fecha_corte=fecha_corte,
        mail=get_mail_sender(),
    )
    return inasistencias_procesadas_view(resumen)
