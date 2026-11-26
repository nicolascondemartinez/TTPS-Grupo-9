"""Controlador para orden del día, la recolección, la entrega y la ubicación de muestras"""
import hmac
import os
import uuid
from datetime import date

from flask import Blueprint, g, request

from src.core.auth import service as auth_service
from src.core.common.errors import ApiError, validation_error
from src.core.common.validation import validar_uuid
from src.core.database import get_db
from src.core.enums import AlcanceSesion
from src.core.logistica import service as logistica_service
from src.web.security import require_permission
from src.web.views.logistica_view import (
    orden_del_dia_view,
    orden_entregada_view,
    orden_generada_view,
    parada_recogida_view,
    ubicacion_muestra_view,
)
bp = Blueprint("logistica", __name__)

def _parsear_uuid(valor: str, campo: str) -> uuid.UUID:
    """Valida que el parámetro sea un UUID válido o lanza error 400."""
    if not validar_uuid(valor):
        raise validation_error([{"campo": campo, "problema": "no es un UUID válido"}])
    return uuid.UUID(valor)


def _autorizar_generacion() -> None:
    """Permite generar órdenes mediante INTERNAL_JOBS_TOKEN (cron) o sesión con permiso orden_dia_generar."""
    token_cron = os.environ.get("INTERNAL_JOBS_TOKEN", "").strip()
    cabecera_cron = request.headers.get("X-Internal-Token", "").strip()
    if token_cron and cabecera_cron and hmac.compare_digest(token_cron, cabecera_cron):
        return

    cabecera = request.headers.get("Authorization", "")
    esquema, _, token = cabecera.partition(" ")
    token_bearer = token.strip() if esquema.lower() == "bearer" and token.strip() else None
    usuario, sesion = auth_service.autenticar_token(get_db(), token_bearer)
    
    if sesion.alcance != AlcanceSesion.completo:
        raise ApiError(403, "CAMBIO_CONTRASENA_REQUERIDO", "Tenés que cambiar la contraseña antes de continuar")
    if not auth_service.tiene_permiso(get_db(), usuario.rol, "orden_dia_generar"):
        raise ApiError(403, "PERMISO_DENEGADO", "No tenés permiso para realizar esta acción", {"permiso": "orden_dia_generar"})


@bp.post("/logistica/ordenes-del-dia/generar")
def generar_ordenes():
    """Genera las órdenes del día para una fecha hábil (por defecto hoy)."""
    _autorizar_generacion()
    datos = request.get_json(silent=True) or {}
    fecha_raw = datos.get("fecha")
    fecha = None
    if fecha_raw is not None:
        try:
            fecha = date.fromisoformat(str(fecha_raw))
        except ValueError:
            raise validation_error([{"campo": "fecha", "problema": "debe tener formato YYYY-MM-DD"}])

    ordenes = logistica_service.generar_ordenes_del_dia(get_db(), fecha=fecha)
    return orden_generada_view(ordenes), 201


@bp.get("/transportista/orden-del-dia")
@require_permission("orden_dia_ver")
def ver_orden_del_dia():
    """Devuelve la orden del día actual del transportista autenticado."""
    data = logistica_service.obtener_orden_del_dia_actual(get_db(), g.usuario.id)
    return orden_del_dia_view(data)


@bp.post("/transportista/paradas/<parada_id>/recoger")
@require_permission("orden_dia_recoger")
def recoger_parada(parada_id: str):
    """Marca una parada de la orden del día como recogida."""
    parada = logistica_service.marcar_parada_recogida(
        get_db(), g.usuario.id, _parsear_uuid(parada_id, "parada_id")
    )
    return parada_recogida_view(parada)


@bp.post("/transportista/ordenes/<orden_id>/entregar")
@require_permission("orden_dia_entregar")
def entregar_orden(orden_id: str):
    """Registra la llegada del transportista al laboratorio central con las muestras."""
    orden = logistica_service.registrar_llegada_laboratorio_central(
        get_db(), g.usuario.id, _parsear_uuid(orden_id, "orden_id")
    )
    return orden_entregada_view(orden)


@bp.get("/estudios/<estudio_id>/ubicacion")
@require_permission("estudio_ubicacion_ver")
def ver_ubicacion_muestra(estudio_id: str):
    """Devuelve la ubicación simulada del transportista y el recorrido de un estudio en tránsito."""
    data = logistica_service.obtener_ubicacion_muestra(
        get_db(), _parsear_uuid(estudio_id, "estudio_id")
    )
    return ubicacion_muestra_view(data)