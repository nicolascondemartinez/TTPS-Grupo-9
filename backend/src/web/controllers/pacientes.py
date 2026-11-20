"""Pacientes: catálogo de parentescos para cargar familiares y descarga del familiograma.
El alta del paciente (#14) se suma acá."""
from flask import Blueprint, Response, g

from src.core.clinico import familiares as familiares_service
from src.core.database import get_db
from src.web.security import require_auth, require_permission

bp = Blueprint("pacientes", __name__)


@bp.get("/parentescos")
@require_permission("familiar_crear")
def parentescos():
    """Catálogo del módulo 1 (Familiograma) para el selector de parentesco."""
    return {"parentescos": [{"id": p.id, "nombre": p.nombre} for p in familiares_service.parentescos()]}


@bp.get("/pacientes/<paciente_id>/familiograma")
@require_auth
def familiograma(paciente_id):
    """Lo descargan el médico que dio de alta al paciente y el propio paciente (si no, 404)."""
    archivo = familiares_service.familiograma_del_paciente(get_db(), paciente_id, g.usuario)
    # Siempre como descarga: un SVG puede traer scripts y este viene de un módulo externo.
    return Response(archivo.contenido, mimetype=archivo.tipo, headers={
        "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
        "X-Content-Type-Options": "nosniff",
    })
