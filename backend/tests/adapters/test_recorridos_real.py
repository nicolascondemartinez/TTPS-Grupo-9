import json
import uuid

import pytest
import requests

from src.adapters import AdaptadorNoDisponible, HttpClient, RespuestaInvalida
from src.adapters.recorridos import CentroParaOrdenar, get_recorridos
from src.adapters.recorridos.real import RecorridosReal

URL = "https://optimizacionapi.vercel.app"


def _centro(nombre: str, lat: float, lon: float) -> CentroParaOrdenar:
    return CentroParaOrdenar(
        id=uuid.uuid4(),
        nombre=nombre,
        direccion=f"Dir {nombre}",
        latitud=lat,
        longitud=lon,
    )


class Api(requests.Session):
    def __init__(self, status=200, cuerpo=None):
        super().__init__()
        self.status = status
        self.cuerpo = cuerpo if cuerpo is not None else {}
        self.pedidos = []

    def request(self, method, url, **kwargs):
        self.pedidos.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = self.status
        response._content = json.dumps(self.cuerpo).encode()
        return response


def real(**kwargs) -> tuple[RecorridosReal, Api]:
    sesion = Api(**kwargs)
    return RecorridosReal(HttpClient("RECORRIDOS", URL, session=sesion)), sesion


def test_get_recorridos_usa_real_si_esta_configurado(monkeypatch):
    monkeypatch.setenv("RECORRIDOS_MODE", "real")
    monkeypatch.setenv("RECORRIDOS_API_URL", URL)
    assert isinstance(get_recorridos(), RecorridosReal)


def test_hasta_dos_centros_no_llama_a_la_api():
    c1, c2 = _centro("A", -34.60, -58.38), _centro("B", -34.92, -57.95)
    adapter, sesion = real()

    res = adapter.optimizar([c1, c2])

    assert res.paradas == [c1, c2]
    assert sesion.pedidos == []


def test_optimizar_envia_coordenadas_y_reconstruye_centros():
    c1 = _centro("Partida", -38.7196, -62.2724)
    c2 = _centro("Mar del Plata", -38.0055, -57.5562)
    c3 = _centro("Tandil", -37.3217, -59.1332)
    c4 = _centro("Destino", -34.9214, -57.9545)

    adapter, sesion = real(cuerpo={
        "coordenadas": [
            {"lat": -38.7196, "lon": -62.2724},
            {"lat": -37.3217, "lon": -59.1332},  # Tandil antes que Mar del Plata
            {"lat": -38.0055, "lon": -57.5562},
            {"lat": -34.9214, "lon": -57.9545},
        ]
    })

    res = adapter.optimizar([c1, c2, c3, c4])

    assert res.paradas == [c1, c3, c2, c4]
    metodo, url, kwargs = sesion.pedidos[0]
    assert metodo == "POST"
    assert url == f"{URL}/api/optimizacion"
    assert kwargs["json"] == {
        "coordenadas": [
            {"lat": -38.7196, "lon": -62.2724},
            {"lat": -38.0055, "lon": -57.5562},
            {"lat": -37.3217, "lon": -59.1332},
            {"lat": -34.9214, "lon": -57.9545},
        ]
    }


def test_respuesta_sin_coordenadas_lanza_respuesta_invalida():
    centros = [_centro("A", -34.6, -58.3), _centro("B", -34.7, -58.4), _centro("C", -34.8, -58.5)]
    adapter, _ = real(cuerpo={"otro": []})
    with pytest.raises(RespuestaInvalida):
        adapter.optimizar(centros)


def test_coordenada_desconocida_lanza_respuesta_invalida():
    centros = [_centro("A", -34.6, -58.3), _centro("B", -34.7, -58.4), _centro("C", -34.8, -58.5)]
    adapter, _ = real(cuerpo={"coordenadas": [
        {"lat": -34.6, "lon": -58.3},
        {"lat": 0.0, "lon": 0.0},
        {"lat": -34.8, "lon": -58.5},
    ]})
    with pytest.raises(RespuestaInvalida):
        adapter.optimizar(centros)


def test_error_503_lanza_adaptador_no_disponible():
    centros = [_centro("A", -34.6, -58.3), _centro("B", -34.7, -58.4), _centro("C", -34.8, -58.5)]
    adapter, _ = real(status=503, cuerpo={"error": "down"})
    with pytest.raises(AdaptadorNoDisponible):
        adapter.optimizar(centros)