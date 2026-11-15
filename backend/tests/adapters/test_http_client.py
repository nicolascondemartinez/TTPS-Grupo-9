import pytest
import requests
from flask import Blueprint

from src.adapters import (
    AdaptadorNoAutorizado,
    AdaptadorNoDisponible,
    HttpClient,
    RespuestaInvalida,
    SolicitudRechazada,
)
from src.web import create_app


class SesionFalsa(requests.Session):
    """Devuelve una respuesta armada o lanza una excepción, sin salir a la red."""

    def __init__(self, status=200, contenido=b"", excepcion=None):
        super().__init__()
        self.status, self.contenido, self.excepcion = status, contenido, excepcion
        self.pedidos = []

    def request(self, method, url, **kwargs):
        self.pedidos.append((method, url, kwargs))
        if self.excepcion:
            raise self.excepcion
        response = requests.Response()
        response.status_code = self.status
        response._content = self.contenido
        return response


def cliente(**kwargs) -> tuple[HttpClient, SesionFalsa]:
    sesion = SesionFalsa(**kwargs)
    return HttpClient("PRUEBA", "https://api.example.test/", "clave", timeout=5, session=sesion), sesion


def test_devuelve_el_json_y_manda_timeout_y_api_key():
    http, sesion = cliente(contenido=b'{"ok": true}')

    assert http.get("/afiliados/1", params={"x": 1}) == {"ok": True}

    method, url, kwargs = sesion.pedidos[0]
    assert (method, url) == ("GET", "https://api.example.test/afiliados/1")
    assert kwargs["timeout"] == 5 and kwargs["params"] == {"x": 1}
    assert http.session.headers["X-API-Key"] == "clave"


@pytest.mark.parametrize("path", ["", "/"])
def test_path_vacio_usa_la_url_base_sin_barra_final(path):
    http, sesion = cliente(contenido=b"{}")
    http.post(path, {})
    assert sesion.pedidos[0][1] == "https://api.example.test"


def test_respuesta_vacia_devuelve_none():
    http, _ = cliente(status=204)
    assert http.post("/algo", {"a": 1}) is None


@pytest.mark.parametrize("excepcion", [requests.Timeout(), requests.ConnectionError()])
def test_timeout_o_sin_conexion(excepcion):
    http, _ = cliente(excepcion=excepcion)
    with pytest.raises(AdaptadorNoDisponible):
        http.get("/x")


@pytest.mark.parametrize("status", [500, 502, 503, 429])
def test_5xx_y_429_no_disponible(status):
    http, _ = cliente(status=status)
    with pytest.raises(AdaptadorNoDisponible):
        http.get("/x")


def test_no_disponible_conserva_status_cuerpo_y_retry_after():
    sesion = SesionFalsa(status=429, contenido=b'{"detail": "espera"}')
    original = sesion.request

    def con_retry_after(*args, **kwargs):
        response = original(*args, **kwargs)
        response.headers["Retry-After"] = "7"
        return response

    sesion.request = con_retry_after
    http = HttpClient("PRUEBA", "https://api.example.test", session=sesion)
    with pytest.raises(AdaptadorNoDisponible) as e:
        http.get("/x")
    assert (e.value.status_externo, e.value.cuerpo, e.value.reintentar_en) == (429, {"detail": "espera"}, 7)
    assert e.value.detalle["reintentar_en"] == 7


@pytest.mark.parametrize("status", [401, 403])
def test_401_403_no_autorizado_conserva_status_y_cuerpo(status):
    http, _ = cliente(status=status, contenido=b'{"message": "no"}')
    with pytest.raises(AdaptadorNoAutorizado) as e:
        http.get("/x")
    assert e.value.status_externo == status and e.value.cuerpo == {"message": "no"}


def test_otro_4xx_trae_status_y_cuerpo():
    http, _ = cliente(status=404, contenido=b'{"error": "no existe"}')
    with pytest.raises(SolicitudRechazada) as e:
        http.get("/x")
    assert e.value.status_externo == 404
    assert e.value.cuerpo == {"error": "no existe"}


def test_respuesta_no_json():
    http, _ = cliente(contenido=b"<html>error</html>")
    with pytest.raises(RespuestaInvalida):
        http.get("/x")


_ruta = Blueprint("ruta_adaptador_caido", __name__)


@_ruta.get("/_test/adaptador-caido")
def _adaptador_caido():
    http, _ = cliente(excepcion=requests.ConnectionError())
    return http.get("/x")


def test_un_error_no_atrapado_responde_json_y_no_500():
    app = create_app("testing")
    app.register_blueprint(_ruta, url_prefix="/api")

    r = app.test_client().get("/api/_test/adaptador-caido")

    assert r.status_code == 503
    assert r.get_json()["error"]["codigo"] == "MODULO_NO_DISPONIBLE"
    assert r.get_json()["error"]["detalle"]["modulo"] == "PRUEBA"
