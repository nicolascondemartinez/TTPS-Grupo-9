"""Errores de la API con un formato único: {"error": {"codigo", "mensaje", "detalle"}}."""
import logging
import uuid

from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

_CODIGOS_HTTP = {
    400: "SOLICITUD_INVALIDA",
    401: "NO_AUTENTICADO",
    403: "PROHIBIDO",
    404: "NO_ENCONTRADO",
    405: "METODO_NO_PERMITIDO",
    409: "CONFLICTO",
    413: "CUERPO_DEMASIADO_GRANDE",
}


class ApiError(Exception):
    """Error de negocio o de validación que se convierte en una respuesta HTTP."""

    def __init__(self, status: int, codigo: str, mensaje: str, detalle: dict | None = None):
        super().__init__(mensaje)
        self.status = status
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle or {}


def error_view(codigo: str, mensaje: str, detalle: dict | None = None) -> dict:
    return {"error": {"codigo": codigo, "mensaje": mensaje, "detalle": detalle or {}}}


def validation_error(campos: list[dict]) -> ApiError:
    """400 con el detalle de cada campo inválido: [{"campo": ..., "problema": ...}]."""
    return ApiError(400, "VALIDACION", "Los datos enviados no son válidos", {"campos": campos})


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        return error_view(e.codigo, e.mensaje, e.detalle), e.status

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        codigo = _CODIGOS_HTTP.get(e.code, "ERROR_HTTP")
        return error_view(codigo, e.description or e.name), e.code

    @app.errorhandler(Exception)
    def _unexpected(e: Exception):
        # No se exponen detalles internos: solo un id para buscar el error en los logs.
        id_error = str(uuid.uuid4())
        logger.exception("ERROR_INTERNO %s", id_error)
        return error_view("ERROR_INTERNO", "Ocurrió un error inesperado", {"id_error": id_error}), 500
