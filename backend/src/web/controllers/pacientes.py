"""Pacientes: alta y listado del médico, catálogo de parentescos y descarga del familiograma."""
from datetime import date

from flask import Blueprint, Response, current_app, g, request

from src.core.avisos.mail_service import get_mail_sender
from src.core.clinico import credenciales as credenciales_service
from src.core.clinico import familiares as familiares_service
from src.core.clinico import pacientes as pacientes_service
from src.core.clinico.validation import validar_alta_paciente
from src.core.database import get_db
from src.web.security import require_auth, require_permission
from src.web.views.paciente_view import paciente_resumen_view, pacientes_view

bp = Blueprint("pacientes", __name__)


@bp.post("/pacientes")
@require_permission("paciente_crear")
def alta():
    """Alta del paciente por su médico tratante. Errores: 400 por campo, 409 DNI_DUPLICADO, MAIL_EN_USO o
    DIAGNOSTICO_INCONSISTENTE (con el motivo), 503 FAMILIOGRAMA_NO_DISPONIBLE (reenviar con "sin_familiograma": true).
    "credenciales_enviadas": false si no salió el mail (el alta queda igual; se reenvía con /credenciales)."""
    datos = validar_alta_paciente(request.get_json(silent=True), date.today())
    paciente, enviado = pacientes_service.dar_de_alta(get_db(), datos, g.usuario, get_mail_sender(), _url_ingreso())
    return {**paciente_resumen_view(paciente), "credenciales_enviadas": enviado}, 201


@bp.post("/pacientes/<paciente_id>/credenciales")
@require_permission("paciente_crear")
def reenviar_credenciales(paciente_id):
    """Contraseña temporal nueva y mail de nuevo, mientras el paciente no haya ingresado (si ya ingresó, 409)."""
    enviado = credenciales_service.reenviar_credenciales(get_db(), paciente_id, g.usuario, get_mail_sender(), _url_ingreso())
    return {"credenciales_enviadas": enviado}


def _url_ingreso() -> str:
    return f"{current_app.config['FRONTEND_URL'].rstrip('/')}/ingreso"


@bp.get("/pacientes")
@require_permission("paciente_listar")
def listar():
    """Los pacientes que dio de alta el médico logueado."""
    return pacientes_view(pacientes_service.listar_pacientes(get_db(), g.usuario))


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
