"""Registro de usuarios y catálogos que necesita el formulario de registro."""
from flask import Blueprint, request

from src.core.common.validation import validar_registro
from src.core.database import get_db
from src.core.usuarios import service as usuarios_service
from src.web.views.usuarios_view import especialidades_view, registro_view

bp = Blueprint("usuarios", __name__)


@bp.get("/especialidades")
def listar_especialidades():
    return especialidades_view(usuarios_service.listar_especialidades(get_db()))


@bp.post("/registro")
def registrar():
    """Público: cualquiera puede registrarse como médico, gerente médico, administrativo o bioinformático."""
    datos = validar_registro(request.get_json(silent=True))
    return registro_view(usuarios_service.registrar_usuario(get_db(), datos)), 201