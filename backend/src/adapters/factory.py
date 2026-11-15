"""Fábrica: devuelve la implementación mock o real de un módulo según sus variables de entorno.

Por módulo (MODULO en mayúsculas, por ejemplo OBRAS_SOCIALES):
    MODULO_MODE     mock | real  (si está vacía se usa ADAPTERS_MODE, y si no, mock)
    MODULO_API_URL  URL base de la API real
    MODULO_API_KEY  API key que se manda en el header
    MODULO_TIMEOUT  segundos (opcional, 10 por defecto)

Se lee de os.environ (no de la config de Flask) para poder usarla también en seeds, scripts y tests.
"""
import os
from dataclasses import dataclass
from typing import Callable, TypeVar

from src.adapters.http_client import HttpClient

T = TypeVar("T")
MODOS = ("mock", "real")
TIMEOUT_POR_DEFECTO = 10.0


@dataclass(frozen=True)
class ConfigAdaptador:
    modulo: str
    modo: str
    url: str
    api_key: str
    timeout: float


def leer_config(modulo: str, timeout_por_defecto: float = TIMEOUT_POR_DEFECTO) -> ConfigAdaptador:
    prefijo = modulo.upper()
    modo = (os.environ.get(f"{prefijo}_MODE") or os.environ.get("ADAPTERS_MODE") or "mock").strip().lower()
    if modo not in MODOS:
        raise RuntimeError(f"{prefijo}_MODE inválido: {modo!r} (mock | real)")
    timeout = os.environ.get(f"{prefijo}_TIMEOUT") or timeout_por_defecto
    return ConfigAdaptador(
        modulo=prefijo,
        modo=modo,
        url=os.environ.get(f"{prefijo}_API_URL", "").strip(),
        api_key=os.environ.get(f"{prefijo}_API_KEY", "").strip(),
        timeout=float(timeout),
    )


def crear_adaptador(modulo: str, mock: Callable[[], T], real: Callable[[HttpClient], T],
                    header_api_key: str = "X-API-Key", timeout: float = TIMEOUT_POR_DEFECTO) -> T:
    """`mock` se llama sin argumentos; `real` recibe un HttpClient ya configurado para el módulo.
    `timeout` es el valor por defecto del módulo; MODULO_TIMEOUT lo pisa."""
    config = leer_config(modulo, timeout)
    if config.modo == "mock":
        return mock()
    if not config.url:
        raise RuntimeError(f"{config.modulo}_MODE=real requiere {config.modulo}_API_URL")
    return real(HttpClient(config.modulo, config.url, config.api_key, config.timeout, header_api_key))
