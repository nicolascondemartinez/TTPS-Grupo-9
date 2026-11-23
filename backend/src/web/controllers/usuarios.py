"""Registro de usuarios y catálogos que necesita el formulario de registro."""
from flask import Blueprint

from src.core.database import get_db
from src.core.usuarios import service as usuarios_service
from src.web.views.usuarios_view import especialidades_view

bp = Blueprint("usuarios", __name__)


@bp.get("/especialidades")
def listar_especialidades():
    return especialidades_view(usuarios_service.listar_especialidades(get_db()))