"""Errores tipados de los adaptadores.

Heredan de ApiError, así que si nadie los atrapa el handler general responde un JSON con el formato
de siempre en lugar de un 500. Ninguno usa 401: el frontend cierra la sesión ante un 401, y una
credencial mal configurada contra un módulo externo no es culpa del usuario logueado.
"""
from src.core.common.errors import ApiError


class AdaptadorError(ApiError):
    def __init__(self, modulo: str, status: int, codigo: str, mensaje: str, detalle: dict | None = None):
        super().__init__(status, codigo, mensaje, {"modulo": modulo, **(detalle or {})})
        self.modulo = modulo


class AdaptadorNoDisponible(AdaptadorError):
    """Timeout, conexión rechazada o error 5xx/429 del módulo externo. Con respuesta HTTP, `status_externo`,
    `cuerpo` y `reintentar_en` (segundos del header Retry-After, si vino) quedan disponibles para el adaptador."""

    def __init__(self, modulo: str, detalle: dict | None = None, status_externo: int | None = None,
                 cuerpo=None, reintentar_en: int | None = None):
        super().__init__(modulo, 503, "MODULO_NO_DISPONIBLE",
                         "El servicio externo no está disponible. Intentá de nuevo en unos minutos.", detalle)
        self.status_externo = status_externo
        self.cuerpo = cuerpo
        self.reintentar_en = reintentar_en


class AdaptadorNoAutorizado(AdaptadorError):
    """El módulo externo rechazó nuestra API key (401/403). `status_externo` y `cuerpo` sirven para los
    módulos que usan el 403 como regla de negocio."""

    def __init__(self, modulo: str, detalle: dict | None = None, status_externo: int | None = None, cuerpo=None):
        super().__init__(modulo, 502, "MODULO_NO_AUTORIZADO",
                         "No pudimos autenticarnos con el servicio externo.", detalle)
        self.status_externo = status_externo
        self.cuerpo = cuerpo


class RespuestaInvalida(AdaptadorError):
    """La respuesta no es JSON o no tiene la forma esperada."""

    def __init__(self, modulo: str, detalle: dict | None = None):
        super().__init__(modulo, 502, "MODULO_RESPUESTA_INVALIDA",
                         "El servicio externo devolvió una respuesta inválida.", detalle)


class SolicitudRechazada(AdaptadorError):
    """Otro 4xx del módulo externo (400, 404, 409, 422...). El adaptador real puede atraparlo y
    traducirlo a un error de negocio (por ejemplo, "afiliado no encontrado")."""

    def __init__(self, modulo: str, status_externo: int, cuerpo=None):
        super().__init__(modulo, 502, "MODULO_SOLICITUD_RECHAZADA",
                         "El servicio externo rechazó la solicitud.", {"status_externo": status_externo})
        self.status_externo = status_externo
        self.cuerpo = cuerpo
