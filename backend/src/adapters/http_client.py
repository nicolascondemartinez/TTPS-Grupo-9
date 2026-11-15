"""Cliente HTTP común de los adaptadores reales: timeout, header de API key y errores tipados."""
import logging

import requests

from src.adapters.errors import (
    AdaptadorNoAutorizado,
    AdaptadorNoDisponible,
    RespuestaInvalida,
    SolicitudRechazada,
)

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, modulo: str, base_url: str, api_key: str = "", timeout: float = 10,
                 header_api_key: str = "X-API-Key", session: requests.Session | None = None):
        self.modulo = modulo
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers["Accept"] = "application/json"
        if api_key:
            self.session.headers[header_api_key] = api_key

    def get(self, path: str, params: dict | None = None):
        return self.request("GET", path, params=params)

    def post(self, path: str, body: dict | None = None):
        return self.request("POST", path, json=body)

    def put(self, path: str, body: dict | None = None):
        return self.request("PUT", path, json=body)

    def delete(self, path: str):
        return self.request("DELETE", path)

    def request(self, method: str, path: str, **kwargs):
        """Devuelve el JSON de la respuesta (None si viene vacía) o lanza un AdaptadorError."""
        ruta = path.lstrip("/")
        url = f"{self.base_url}/{ruta}" if ruta else self.base_url
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.Timeout:
            logger.warning("[%s] timeout en %s %s", self.modulo, method, url)
            raise AdaptadorNoDisponible(self.modulo, {"motivo": "timeout"})
        except requests.RequestException as e:
            logger.warning("[%s] sin conexión en %s %s: %s", self.modulo, method, url, e)
            raise AdaptadorNoDisponible(self.modulo, {"motivo": "conexion"})

        status = response.status_code
        if status in (401, 403):
            logger.error("[%s] %s en %s %s: revisar la API key", self.modulo, status, method, url)
            raise AdaptadorNoAutorizado(self.modulo, status_externo=status, cuerpo=_cuerpo(response))
        if status == 429 or status >= 500:
            logger.warning("[%s] %s en %s %s", self.modulo, status, method, url)
            raise AdaptadorNoDisponible(self.modulo, {"status_externo": status})
        if status >= 400:
            raise SolicitudRechazada(self.modulo, status, _cuerpo(response))

        if status == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            logger.warning("[%s] respuesta no JSON en %s %s", self.modulo, method, url)
            raise RespuestaInvalida(self.modulo, {"motivo": "no_es_json"})


def _cuerpo(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return response.text
