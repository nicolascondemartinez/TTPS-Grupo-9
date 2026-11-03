"""JSON que devuelven los endpoints de autenticación."""
from app.services.auth_service import Autenticacion


def usuario_view(usuario) -> dict:
    return {
        "id": str(usuario.id),
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "correo": usuario.email,
        "rol": usuario.rol.value,
        "debe_cambiar_contrasena": usuario.debe_cambiar_password,
    }


def _enmascarar_correo(correo: str) -> str:
    local, _, dominio = correo.partition("@")
    return f"{local[:2]}{'*' * max(len(local) - 2, 1)}@{dominio}"


def autenticacion_view(resultado: Autenticacion, permisos: list[str]) -> dict:
    if resultado.estado == "verificacion_requerida":
        return {
            "estado": resultado.estado,
            "desafio_id": resultado.desafio_id,
            "correo": _enmascarar_correo(resultado.usuario.email),
        }
    return {
        "estado": resultado.estado,
        "token": resultado.token,
        "expira_at": resultado.expira_at.isoformat(),
        "usuario": usuario_view(resultado.usuario),
        "permisos": permisos,
    }


def me_view(usuario, sesion, permisos: list[str]) -> dict:
    return {
        "estado": "cambio_contrasena_requerido" if sesion.alcance.value == "cambio_contrasena" else "autenticado",
        "usuario": usuario_view(usuario),
        "permisos": permisos,
    }
