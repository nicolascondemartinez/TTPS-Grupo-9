"""Síntomas: búsqueda en SNOMED para el autocompletado (patologías, pacientes y familiares)."""
from flask import Blueprint, request

from src.web.security import require_permission
from src.core.clinico import service as clinico_service
from src.web.views.sintoma_view import sintomas_view

bp = Blueprint("sintomas", __name__)


@bp.get("/sintomas")
@require_permission("sintoma_buscar")
def buscar():
    return sintomas_view(clinico_service.buscar_sintomas(request.args.get("q", "")))
