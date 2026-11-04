"""Decoradores de seguridad para los controladores.

    @bp.get("/pacientes")
    @require_permission("paciente_listar")      # exige sesión completa y el permiso
    def listar(): ...

    @require_auth                                # solo exige sesión completa
    @require_auth(allow_limited=True)            # acepta también la sesión de primer ingreso

El 401 (sin token, inválido o vencido) se resuelve antes que cualquier regla de negocio o permiso.
Usuario y sesión quedan en `flask.g` (g.usuario, g.sesion).
"""
from functools import wraps

from flask import g, request

from src.core.enums import AlcanceSesion
from src.core.database import get_db
from src.core.common.errors import ApiError
from src.core.auth import service as auth_service


def _token_del_request() -> str | None:
    cabecera = request.headers.get("Authorization", "")
    esquema, _, token = cabecera.partition(" ")
    return token.strip() if esquema.lower() == "bearer" and token.strip() else None


def require_auth(func=None, *, allow_limited: bool = False):
    def decorador(f):
        @wraps(f)
        def envoltura(*args, **kwargs):
            usuario, sesion = auth_service.autenticar_token(get_db(), _token_del_request())
            if sesion.alcance != AlcanceSesion.completo and not allow_limited:
                raise ApiError(403, "CAMBIO_CONTRASENA_REQUERIDO", "Tenés que cambiar la contraseña antes de continuar")
            g.usuario, g.sesion = usuario, sesion
            return f(*args, **kwargs)

        return envoltura

    return decorador(func) if func is not None else decorador


def require_permission(nombre: str):
    """Exige sesión completa y que el rol del usuario tenga el permiso `nombre` (modulo_accion)."""

    def decorador(f):
        @wraps(f)
        @require_auth
        def envoltura(*args, **kwargs):
            if not auth_service.tiene_permiso(get_db(), g.usuario.rol, nombre):
                raise ApiError(403, "PERMISO_DENEGADO", "No tenés permiso para realizar esta acción", {"permiso": nombre})
            return f(*args, **kwargs)

        return envoltura

    return decorador
