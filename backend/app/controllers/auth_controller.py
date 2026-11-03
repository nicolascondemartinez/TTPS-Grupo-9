"""Autenticación: login, verificación de dispositivo nuevo, cambio de contraseña, logout y /me."""
from flask import Blueprint, current_app, g, request

from app.controllers.security import require_auth
from app.db.enums import AlcanceSesion
from app.db.flask_db import get_db
from app.services import auth_service
from app.services.mail_service import get_mail_sender
from app.services.validation import (
    validar_cambio_contrasena,
    validar_device_id,
    validar_login,
    validar_verificacion,
)
from app.views.auth_view import autenticacion_view, me_view

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
