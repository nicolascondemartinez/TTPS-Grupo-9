import json

import pytest
import requests

from src.adapters import AdaptadorNoAutorizado, AdaptadorNoDisponible, HttpClient, RespuestaInvalida
from src.adapters.snomed import SintomaSnomed, get_snomed
from src.adapters.snomed.real import SnomedReal


class ApiSnomed(requests.Session):
    def __init__(self, status=200, cuerpo=None):
        super().__init__()
        self.status, self.cuerpo = status, cuerpo if cuerpo is not None else {"resultados": []}
        self.pedidos = []

    def request(self, method, url, **kwargs):
        self.pedidos.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = self.status
        response._content = json.dumps(self.cuerpo).encode()
        return response


def real(**kwargs) -> tuple[SnomedReal, ApiSnomed]:
    sesion = ApiSnomed(**kwargs)
    http = HttpClient("SNOMED", "https://snomed.test/terminologia", "clave", session=sesion)
    return SnomedReal(http), sesion


def test_get_snomed_real(monkeypatch):
    monkeypatch.setenv("SNOMED_MODE", "real")
    monkeypatch.setenv("SNOMED_API_URL", "https://snomed.test/terminologia")
    monkeypatch.setenv("SNOMED_API_KEY", "clave")
    monkeypatch.delenv("SNOMED_TIMEOUT", raising=False)

    snomed = get_snomed()

    assert isinstance(snomed, SnomedReal)
    assert snomed.http.timeout == 15
    assert snomed.http.session.headers["X-API-Key"] == "clave"
    assert snomed.http.session.headers["x-region"] == "us-east-1"


def test_busca_y_traduce_la_respuesta():
    cuerpo = {"publicacion": "2026-08-20", "resultados": [
        {"sctid": "386661006", "termino_preferido": "fiebre", "termino_coincidente": "fiebre",
         "estrategia": "exacta", "similitud": None, "origen": "snomed"},
        {"sctid": 304213008, "termino_preferido": "fiebre baja", "estrategia": "prefijo", "similitud": None},
    ]}
    snomed, sesion = real(cuerpo=cuerpo)

    resultado = snomed.buscar_sintomas("  fiebre ", limite=5)

    assert resultado == [SintomaSnomed("386661006", "fiebre"), SintomaSnomed("304213008", "fiebre baja")]
    method, url, kwargs = sesion.pedidos[0]
    assert (method, url) == ("GET", "https://snomed.test/terminologia/sintomas")
    assert kwargs["params"] == {"q": "fiebre", "limite": 5}


@pytest.mark.parametrize("texto", ["", "ab", " ab ", None])
def test_menos_de_3_caracteres_no_consulta(texto):
    snomed, sesion = real()
    assert snomed.buscar_sintomas(texto) == []
    assert sesion.pedidos == []


@pytest.mark.parametrize("pedido, enviado", [(0, 1), (100, 50), (20, 20)])
def test_el_limite_se_ajusta_al_rango_de_la_api(pedido, enviado):
    snomed, sesion = real()
    snomed.buscar_sintomas("fiebre", limite=pedido)
    assert sesion.pedidos[0][2]["params"]["limite"] == enviado


def test_sin_resultados():
    snomed, _ = real(cuerpo={"resultados": []})
    assert snomed.buscar_sintomas("xyzxyz") == []


@pytest.mark.parametrize("status, error", [(401, AdaptadorNoAutorizado), (503, AdaptadorNoDisponible)])
def test_errores_http(status, error):
    snomed, _ = real(status=status, cuerpo={"detalle": "x"})
    with pytest.raises(error):
        snomed.buscar_sintomas("fiebre")


@pytest.mark.parametrize("cuerpo", [{"otra": []}, {"resultados": [{"sctid": "1"}]}])
def test_respuesta_con_formato_inesperado(cuerpo):
    snomed, _ = real(cuerpo=cuerpo)
    with pytest.raises(RespuestaInvalida):
        snomed.buscar_sintomas("fiebre")
