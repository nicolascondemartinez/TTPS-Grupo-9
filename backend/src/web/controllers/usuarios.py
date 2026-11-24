"""Registro de usuarios y catálogos que necesita el formulario de registro."""
from flask import Blueprint, request

from src.core.avisos.mail_service import get_mail_sender
from src.core.common.validation import validar_alta_transportista, validar_registro
from src.core.database import get_db
from src.core.usuarios import service as usuarios_service
from src.web.security import require_permission
from src.web.views.usuarios_view import (
    especialidades_view, provincias_view, registro_view, transportista_view, transportistas_view,
)

bp = Blueprint("usuarios", __name__)


@bp.get("/especialidades")
def listar_especialidades():
    return especialidades_view(usuarios_service.listar_especialidades(get_db()))


@bp.post("/registro")
def registrar():
    """Público: cualquiera puede registrarse como médico, gerente médico, administrativo o bioinformático."""
    datos = validar_registro(request.get_json(silent=True))
    return registro_view(usuarios_service.registrar_usuario(get_db(), datos)), 201


@bp.get("/provincias")
@require_permission("transportista_crear")
def listar_provincias():
    """Para el formulario de alta de transportista: cada provincia indica si ya tiene uno."""
    return provincias_view(usuarios_service.listar_provincias(get_db()))


@bp.get("/transportistas")
@require_permission("transportista_listar")
def listar_transportistas():
    return transportistas_view(usuarios_service.listar_transportistas(get_db()))


@bp.post("/transportistas")
@require_permission("transportista_crear")
def crear_transportista():
    datos = validar_alta_transportista(request.get_json(silent=True))
    transportista = usuarios_service.crear_transportista(get_db(), datos, get_mail_sender())
    return transportista_view(transportista), 201