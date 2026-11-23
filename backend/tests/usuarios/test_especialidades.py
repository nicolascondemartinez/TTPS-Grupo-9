"""Catálogo de especialidades que usa el formulario de registro."""
from src.core.models import Especialidad
from src.core.seeds.seed_especialidades import ESPECIALIDADES


def test_lista_las_especialidades_ordenadas_sin_necesitar_sesion(api, db):
    db.add_all([Especialidad(nombre="Pediatría"), Especialidad(nombre="Cardiología")])
    db.commit()
    r = api.get("/api/especialidades")  # sin token: es público
    assert r.status_code == 200
    especialidades = r.get_json()["especialidades"]
    assert [e["nombre"] for e in especialidades] == ["Cardiología", "Pediatría"]
    assert set(especialidades[0]) == {"id", "nombre"}


def test_la_lista_de_especialidades_no_tiene_repetidas():
    assert len(ESPECIALIDADES) > 0
    assert len(ESPECIALIDADES) == len(set(ESPECIALIDADES))