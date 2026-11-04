"""Autenticación: login, verificación de dispositivo nuevo, cambio de contraseña, logout y /me."""
from flask import Blueprint, current_app, g, request

from src.web.security import require_auth
from src.core.enums import AlcanceSesion
from src.core.database import get_db
from src.core.auth import service as auth_service
from src.core.avisos.mail_service import get_mail_sender
from src.core.common.validation import (
    validar_cambio_contrasena,
    validar_device_id,
    validar_login,
    validar_verificacion,
)
from src.web.views.auth_view import autenticacion_view, me_view

bp = Blueprint("auth", __name__)


def _settings() -> auth_service.AuthSettings:
    return auth_service.AuthSettings.from_config(current_app.config)


def _device_id() -> str:
    return validar_device_id(request.headers.get("X-Device-Id"))


def _responder(resultado: auth_service.Autenticacion):
    permisos = []
    if resultado.estado == "autenticado":
        permisos = auth_service.permisos_del_rol(get_db(), resultado.usuario.rol)
    return autenticacion_view(resultado, permisos)


@bp.post("/auth/login")
def login():
    correo, contrasena = validar_login(request.get_json(silent=True))
    resultado = auth_service.iniciar_sesion(get_db(), correo, contrasena, _device_id(), _settings(), get_mail_sender())
    return _responder(resultado)


@bp.post("/auth/verify-device")
def verify_device():
    desafio_id, codigo = validar_verificacion(request.get_json(silent=True))
    resultado = auth_service.verificar_dispositivo(get_db(), desafio_id, codigo, _device_id(), _settings())
    return _responder(resultado)


@bp.post("/auth/change-password")
@require_auth(allow_limited=True)
def change_password():
    actual, nueva = validar_cambio_contrasena(request.get_json(silent=True), g.usuario.email)
    resultado = auth_service.cambiar_contrasena(get_db(), g.usuario, actual, nueva, _device_id(), _settings())
    return _responder(resultado)


@bp.post("/auth/logout")
@require_auth(allow_limited=True)
def logout():
    auth_service.cerrar_sesion(get_db(), g.sesion)
    return "", 204


@bp.get("/auth/me")
@require_auth(allow_limited=True)
def me():
    permisos = []
    if g.sesion.alcance == AlcanceSesion.completo:
        permisos = auth_service.permisos_del_rol(get_db(), g.usuario.rol)
    return me_view(g.usuario, g.sesion, permisos)
