"""Centros de extracción y turnos: el paciente ve los centros, elige un horario libre, reserva y cancela."""
from flask import Blueprint, g, request

from src.core.database import get_db
from src.core.turnos import service as turnos_service
from src.core.turnos.validation import validar_fecha_opcional, validar_reserva
from src.web.security import require_permission
from src.web.views.turno_view import centros_view, turno_view, turnos_libres_view

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
