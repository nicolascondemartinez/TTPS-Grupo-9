"""Adaptadores de los módulos externos (mock | real). Ver README.md para agregar un módulo."""
from src.adapters.errors import (
    AdaptadorError,
    AdaptadorNoAutorizado,
    AdaptadorNoDisponible,
    RespuestaInvalida,
    SolicitudRechazada,
)
from src.adapters.factory import ConfigAdaptador, crear_adaptador, leer_config
from src.adapters.http_client import HttpClient

__all__ = [
    "AdaptadorError",
    "AdaptadorNoAutorizado",
    "AdaptadorNoDisponible",
    "RespuestaInvalida",
    "SolicitudRechazada",
    "ConfigAdaptador",
    "crear_adaptador",
    "leer_config",
    "HttpClient",
]
