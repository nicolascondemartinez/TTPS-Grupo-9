"""Avisos del usuario logueado: lista, contador y marcar como leídos."""
from flask import Blueprint, g, request

from src.core.avisos import service as avisos_service
from src.core.database import get_db
from src.web.security import require_auth
from src.web.views.avisos_view import aviso_view

bp = Blueprint("avisos", __name__)


@bp.get("/avisos")
@require_auth
def listar():
    solo_pendientes = request.args.get("pendientes") == "true"
    avisos = avisos_service.listar_avisos(get_db(), g.usuario.id, solo_pendientes)
    return {"avisos": [aviso_view(a) for a in avisos]}


@bp.get("/avisos/pendientes/cantidad")
@require_auth
def cantidad_pendientes():
    return {"cantidad": avisos_service.contar_pendientes(get_db(), g.usuario.id)}


@bp.post("/avisos/<aviso_id>/leido")
@require_auth
def marcar_leido(aviso_id):
    return aviso_view(avisos_service.marcar_leido(get_db(), g.usuario.id, aviso_id))


@bp.post("/avisos/leer-todos")
@require_auth
def leer_todos():
    return {"marcados": avisos_service.marcar_todos_leidos(get_db(), g.usuario.id)}