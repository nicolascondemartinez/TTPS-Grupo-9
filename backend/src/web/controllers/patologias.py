"""Patologías: las define y modifica el gerente médico (no hay baja); el médico las lista."""
from flask import Blueprint, request

from src.web.security import require_permission
from src.core.database import get_db
from src.core.clinico import service as clinico_service
from src.core.clinico.validation import validar_alta_patologia, validar_modificacion_patologia
from src.web.views.patologia_view import patologia_view, patologias_view

bp = Blueprint("patologias", __name__)


@bp.get("/patologias")
@require_permission("patologia_listar")
def listar():
    return patologias_view(clinico_service.listar_patologias(get_db()))


@bp.get("/patologias/<patologia_id>")
@require_permission("patologia_listar")
def ver(patologia_id):
    return patologia_view(clinico_service.obtener_patologia(get_db(), patologia_id))


@bp.post("/patologias")
@require_permission("patologia_crear")
def crear():
    nombre, cardinal, secundarios = validar_alta_patologia(request.get_json(silent=True))
    return patologia_view(clinico_service.crear_patologia(get_db(), nombre, cardinal, secundarios)), 201


@bp.put("/patologias/<patologia_id>")
@require_permission("patologia_editar")
def modificar(patologia_id):
    cardinal, secundarios = validar_modificacion_patologia(request.get_json(silent=True))
    return patologia_view(clinico_service.modificar_patologia(get_db(), patologia_id, cardinal, secundarios))
