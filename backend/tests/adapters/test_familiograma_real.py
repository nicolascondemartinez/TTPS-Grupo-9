import base64
import json

import pytest
import requests

from src.adapters import AdaptadorNoDisponible, HttpClient, RespuestaInvalida
from src.adapters.familiograma import FamiliarFamiliograma, PacienteFamiliograma, get_familiograma
from src.adapters.familiograma.real import FamiliogramaReal
from src.adapters.snomed import SintomaSnomed
from src.core.common.errors import ApiError

BASE = "https://familiograma.test/functions/v1/familiograma"
CATALOGO = [{"id": i, "parentesco": p} for i, p in enumerate(["paciente", "progenitor", "hermano/a", "abuelo/a materno/a"])]
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
OK = {"advertencias": ["aviso"], "imagen": {"tipo": "image/svg+xml", "base64": base64.b64encode(SVG).decode()}}


class Api(requests.Session):
    def __init__(self, post=(200, OK)):
        super().__init__()
        self.respuesta_post = post
        self.pedidos = []

    def request(self, method, url, **kwargs):
        self.pedidos.append((method, url, kwargs))
        status, cuerpo = (200, CATALOGO) if url.endswith("/parentescos") else self.respuesta_post
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(cuerpo).encode()
        return response


def real(**kwargs) -> tuple[FamiliogramaReal, Api]:
    sesion = Api(**kwargs)
    return FamiliogramaReal(HttpClient("FAMILIOGRAMA", BASE, "clave", session=sesion)), sesion


PACIENTE = PacienteFamiliograma("Tomás", "Ruiz", edad=9, sintomas=[SintomaSnomed("247398009", "dolor neuropático")])
FAMILIARES = [
    FamiliarFamiliograma("Progenitor", "Carolina Ruiz", diagnostico_previo="Fabry"),
    FamiliarFamiliograma("hermano/a", "Sofía Belén Ruiz", [SintomaSnomed("45004005", "hipohidrosis")]),
]


def test_get_familiograma_real(monkeypatch):
    monkeypatch.setenv("FAMILIOGRAMA_MODE", "real")
    monkeypatch.setenv("FAMILIOGRAMA_API_URL", BASE)
    monkeypatch.setenv("FAMILIOGRAMA_API_KEY", "clave")
    familiograma = get_familiograma()
    assert isinstance(familiograma, FamiliogramaReal)
    assert familiograma.http.session.headers["X-API-Key"] == "clave"


def test_parentescos_sin_el_paciente():
    familiograma, _ = real()
    assert [p.nombre for p in familiograma.parentescos()] == ["progenitor", "hermano/a", "abuelo/a materno/a"]


def test_cero_familiares_no_llama_a_la_api():
    familiograma, sesion = real()
    assert familiograma.generar_familiograma(PACIENTE, []) is None
    assert sesion.pedidos == []


def test_arma_el_pedido_y_devuelve_el_svg():
    familiograma, sesion = real()

    archivo = familiograma.generar_familiograma(PACIENTE, FAMILIARES)

    assert archivo.contenido == SVG and archivo.tipo == "image/svg+xml" and archivo.advertencias == ["aviso"]
    method, url, kwargs = sesion.pedidos[-1]
    assert (method, url) == ("POST", BASE)
    assert kwargs["json"] == {"personas": [
        {"parentesco": 0, "nombre": "Tomás", "apellido": "Ruiz", "sexo": "no_identificado", "edad": 9,
         "sintomas": [{"codigo": "247398009", "nombre": "dolor neuropático"}]},
        {"parentesco": 1, "nombre": "Carolina", "apellido": "Ruiz", "sexo": "no_identificado", "sintomas": [],
         "diagnosticos": [{"codigo": "FABRY", "nombre": "Fabry"}]},
        {"parentesco": 2, "nombre": "Sofía Belén", "apellido": "Ruiz", "sexo": "no_identificado",
         "sintomas": [{"codigo": "45004005", "nombre": "hipohidrosis"}]},
    ]}


def test_familiar_sin_apellido_no_llama_al_post():
    familiograma, sesion = real()
    with pytest.raises(ApiError) as e:
        familiograma.generar_familiograma(PACIENTE, [FamiliarFamiliograma("progenitor", "Carolina")])
    assert e.value.detalle["campos"][0]["campo"] == "familiares[0].nombre"
    assert all(m == "GET" for m, _, _ in sesion.pedidos)


def test_422_se_convierte_en_error_de_validacion_con_los_indices_de_familiares():
    error = {"error": {"codigo": "ENTRADA_INVALIDA", "mensaje": "Revisá los campos indicados.", "detalles": [
        {"ruta": "personas.2.parentesco", "mensaje": "FALTA_PERSONA_DE_REFERENCIA: necesita un abuelo/a"},
        {"ruta": "personas.0.edad", "mensaje": "NUMERO_INVALIDO"},
        {"ruta": "personas", "mensaje": "PACIENTE_REQUERIDO"},
    ]}}
    familiograma, _ = real(post=(422, error))

    with pytest.raises(ApiError) as e:
        familiograma.generar_familiograma(PACIENTE, FAMILIARES)

    assert e.value.status == 400 and e.value.codigo == "VALIDACION"
    assert e.value.detalle["campos"] == [
        {"campo": "familiares[1].parentesco", "problema": "FALTA_PERSONA_DE_REFERENCIA: necesita un abuelo/a"},
        {"campo": "paciente.edad", "problema": "NUMERO_INVALIDO"},
        {"campo": "personas", "problema": "PACIENTE_REQUERIDO"},
    ]


def test_error_del_servidor():
    familiograma, _ = real(post=(502, {"error": {"mensaje": "x"}}))
    with pytest.raises(AdaptadorNoDisponible):
        familiograma.generar_familiograma(PACIENTE, FAMILIARES)


@pytest.mark.parametrize("cuerpo", [{"advertencias": []}, {"imagen": {"tipo": "image/svg+xml", "base64": "no-es-base64!"}}])
def test_respuesta_sin_imagen_valida(cuerpo):
    familiograma, _ = real(post=(200, cuerpo))
    with pytest.raises(RespuestaInvalida):
        familiograma.generar_familiograma(PACIENTE, FAMILIARES)
