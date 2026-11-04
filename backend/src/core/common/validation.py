"""Validación de las entradas de autenticación (módulo aparte: recibe los datos y devuelve el
resultado limpio o lanza un error 400 con el detalle de cada campo)."""
import re

from src.core.common.errors import ApiError, validation_error

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_CODIGO_RE = re.compile(r"^\d{6}$")

CONTRASENA_MIN = 8
CONTRASENA_MAX = 128


def _cuerpo(datos) -> dict:
    if not isinstance(datos, dict):
        raise validation_error([{"campo": "(cuerpo)", "problema": "se esperaba un JSON en el cuerpo de la petición"}])
    return datos


def validar_login(datos) -> tuple[str, str]:
    datos = _cuerpo(datos)
    problemas = []
    correo, contrasena = datos.get("correo"), datos.get("contrasena")
    if not isinstance(correo, str) or not correo.strip():
        problemas.append({"campo": "correo", "problema": "es obligatorio"})
    elif len(correo.strip()) > 254 or not _EMAIL_RE.match(correo.strip()):
        problemas.append({"campo": "correo", "problema": "no tiene un formato de correo válido"})
    if not isinstance(contrasena, str) or contrasena == "":
        problemas.append({"campo": "contrasena", "problema": "es obligatoria"})
    elif len(contrasena) > CONTRASENA_MAX:
        problemas.append({"campo": "contrasena", "problema": f"admite como máximo {CONTRASENA_MAX} caracteres"})
    if problemas:
        raise validation_error(problemas)
    return correo.strip().lower(), contrasena


def validar_device_id(valor) -> str:
    """Identificador del dispositivo (header X-Device-Id): lo genera el navegador una sola vez."""
    if not isinstance(valor, str) or not _DEVICE_RE.match(valor):
        raise validation_error([{"campo": "X-Device-Id", "problema": "falta el identificador del dispositivo o no es válido"}])
    return valor


def validar_verificacion(datos) -> tuple[str, str]:
    datos = _cuerpo(datos)
    problemas = []
    desafio_id, codigo = datos.get("desafio_id"), datos.get("codigo")
    if not isinstance(desafio_id, str) or not desafio_id.strip():
        problemas.append({"campo": "desafio_id", "problema": "es obligatorio"})
    if not isinstance(codigo, str) or not _CODIGO_RE.match(codigo.strip()):
        problemas.append({"campo": "codigo", "problema": "debe tener 6 dígitos"})
    if problemas:
        raise validation_error(problemas)
    return desafio_id.strip(), codigo.strip()


def validar_cambio_contrasena(datos, correo: str) -> tuple[str, str]:
    datos = _cuerpo(datos)
    problemas = []
    actual, nueva = datos.get("contrasena_actual"), datos.get("contrasena_nueva")
    if not isinstance(actual, str) or actual == "":
        problemas.append({"campo": "contrasena_actual", "problema": "es obligatoria"})
    if not isinstance(nueva, str) or nueva == "":
        problemas.append({"campo": "contrasena_nueva", "problema": "es obligatoria"})
    elif len(nueva) < CONTRASENA_MIN or len(nueva) > CONTRASENA_MAX:
        problemas.append({"campo": "contrasena_nueva", "problema": f"debe tener entre {CONTRASENA_MIN} y {CONTRASENA_MAX} caracteres"})
    elif nueva == actual:
        problemas.append({"campo": "contrasena_nueva", "problema": "debe ser distinta de la actual"})
    elif nueva.strip().lower() == correo.strip().lower():
        problemas.append({"campo": "contrasena_nueva", "problema": "no puede ser igual al correo"})
    if problemas:
        raise validation_error(problemas)
    return actual, nueva


def validar_uuid(valor: str) -> bool:
    return bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", valor or ""))


__all__ = ["ApiError"]
