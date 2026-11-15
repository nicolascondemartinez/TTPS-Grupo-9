import pytest

from src.adapters import HttpClient, crear_adaptador, leer_config


class Mock:
    pass


class Real:
    def __init__(self, http: HttpClient):
        self.http = http


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for var in ("ADAPTERS_MODE", "PRUEBA_MODE", "PRUEBA_API_URL", "PRUEBA_API_KEY", "PRUEBA_TIMEOUT"):
        monkeypatch.delenv(var, raising=False)


def test_sin_variables_usa_mock():
    assert isinstance(crear_adaptador("PRUEBA", mock=Mock, real=Real), Mock)


def test_modo_del_modulo_elige_real(monkeypatch):
    monkeypatch.setenv("PRUEBA_MODE", "real")
    monkeypatch.setenv("PRUEBA_API_URL", "https://api.example.test/v1/")
    monkeypatch.setenv("PRUEBA_API_KEY", "clave")
    monkeypatch.setenv("PRUEBA_TIMEOUT", "3")

    adaptador = crear_adaptador("PRUEBA", mock=Mock, real=Real)

    assert isinstance(adaptador, Real)
    assert adaptador.http.base_url == "https://api.example.test/v1"
    assert adaptador.http.timeout == 3
    assert adaptador.http.session.headers["X-API-Key"] == "clave"


def test_header_de_api_key_configurable(monkeypatch):
    monkeypatch.setenv("PRUEBA_MODE", "real")
    monkeypatch.setenv("PRUEBA_API_URL", "https://api.example.test")
    monkeypatch.setenv("PRUEBA_API_KEY", "clave")

    adaptador = crear_adaptador("PRUEBA", mock=Mock, real=Real, header_api_key="apikey")

    assert adaptador.http.session.headers["apikey"] == "clave"
    assert "X-API-Key" not in adaptador.http.session.headers


def test_timeout_por_defecto_del_modulo_y_la_variable_lo_pisa(monkeypatch):
    monkeypatch.setenv("PRUEBA_MODE", "real")
    monkeypatch.setenv("PRUEBA_API_URL", "https://api.example.test")
    assert crear_adaptador("PRUEBA", mock=Mock, real=Real, timeout=15).http.timeout == 15

    monkeypatch.setenv("PRUEBA_TIMEOUT", "4")
    assert crear_adaptador("PRUEBA", mock=Mock, real=Real, timeout=15).http.timeout == 4


def test_modo_del_modulo_tiene_prioridad_sobre_el_global(monkeypatch):
    monkeypatch.setenv("ADAPTERS_MODE", "real")
    monkeypatch.setenv("PRUEBA_MODE", "mock")
    assert isinstance(crear_adaptador("PRUEBA", mock=Mock, real=Real), Mock)


def test_modo_vacio_cae_al_global(monkeypatch):
    monkeypatch.setenv("ADAPTERS_MODE", "real")
    monkeypatch.setenv("PRUEBA_MODE", "")
    monkeypatch.setenv("PRUEBA_API_URL", "https://api.example.test")
    assert leer_config("prueba").modo == "real"


def test_real_sin_url_falla_al_crear(monkeypatch):
    monkeypatch.setenv("PRUEBA_MODE", "real")
    with pytest.raises(RuntimeError, match="PRUEBA_API_URL"):
        crear_adaptador("PRUEBA", mock=Mock, real=Real)


def test_modo_invalido(monkeypatch):
    monkeypatch.setenv("PRUEBA_MODE", "produccion")
    with pytest.raises(RuntimeError, match="PRUEBA_MODE"):
        leer_config("PRUEBA")
