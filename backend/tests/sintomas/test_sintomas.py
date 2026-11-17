"""GET /api/sintomas: búsqueda de síntomas SNOMED para el autocompletado (con el mock del módulo 2)."""
import pytest

from src.adapters import AdaptadorNoDisponible
from src.core.clinico import service as clinico_service
from src.core.enums import RolUsuario


@pytest.fixture(autouse=True)
def snomed_mock(monkeypatch):
    monkeypatch.setenv("SNOMED_MODE", "mock")


def test_el_medico_busca_y_recibe_codigo_y_termino(api, crear_usuario):
    crear_usuario(rol=RolUsuario.medico)
    r = api.get("/api/sintomas?q=esplenomegalia", api.token())
    assert r.status_code == 200
    assert r.get_json()["sintomas"][0] == {"snomed_code": "16294009", "termino": "esplenomegalia"}


def test_el_gerente_medico_tambien_puede_buscar(api, crear_usuario):
    crear_usuario(rol=RolUsuario.gerente_medico, correo="g@exoma.test")
    r = api.get("/api/sintomas?q=hepato", api.token(correo="g@exoma.test"))
    assert r.status_code == 200
    assert {"snomed_code": "80515008", "termino": "hepatomegalia"} in r.get_json()["sintomas"]


@pytest.mark.parametrize("ruta", ["/api/sintomas?q=he", "/api/sintomas?q=", "/api/sintomas"])
def test_con_menos_de_3_letras_devuelve_lista_vacia(api, crear_usuario, ruta):
    crear_usuario()
    r = api.get(ruta, api.token())
    assert r.status_code == 200 and r.get_json() == {"sintomas": []}


def test_sin_coincidencias_devuelve_lista_vacia(api, crear_usuario):
    crear_usuario()
    assert api.get("/api/sintomas?q=xyzxyz", api.token()).get_json() == {"sintomas": []}


def test_un_rol_sin_permiso_recibe_403(api, crear_usuario):
    crear_usuario(rol=RolUsuario.paciente, correo="p@exoma.test")
    r = api.get("/api/sintomas?q=hepato", api.token(correo="p@exoma.test"))
    assert r.status_code == 403
    assert r.get_json()["error"]["detalle"] == {"permiso": "sintoma_buscar"}


def test_sin_token_recibe_401(api):
    assert api.get("/api/sintomas?q=hepato").status_code == 401


def test_si_snomed_no_responde_devuelve_503_con_el_error_de_siempre(api, crear_usuario, monkeypatch):
    class SnomedCaido:
        def buscar_sintomas(self, texto):
            raise AdaptadorNoDisponible("SNOMED", {"motivo": "timeout"})

    monkeypatch.setattr(clinico_service, "get_snomed", lambda: SnomedCaido())
    crear_usuario()
    r = api.get("/api/sintomas?q=hepato", api.token())
    assert r.status_code == 503
    assert r.get_json()["error"]["codigo"] == "MODULO_NO_DISPONIBLE"
