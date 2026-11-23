"""POST /api/patologias/validar-diagnostico: el formulario del médico consulta la regla en el backend."""
import uuid

import pytest
from sqlalchemy import select, text

from src.adapters.snomed import mock as s
from src.core.enums import RolUsuario
from src.core.models import Patologia
from src.core.seeds.seed_catalogos import PATOLOGIAS
from src.core.seeds.seed_patologias import cargar_sintomas_de_patologias

RUTA = "/api/patologias/validar-diagnostico"


@pytest.fixture(autouse=True)
def las_5_patologias(app, db):
    db.execute(text("TRUNCATE patologia, sintoma CASCADE"))
    db.add_all(Patologia(nombre=n) for n in PATOLOGIAS)
    db.commit()
    cargar_sintomas_de_patologias(db)
    db.commit()


@pytest.fixture
def ids(db):
    return {p.nombre: str(p.id) for p in db.scalars(select(Patologia))}


@pytest.fixture
def medico(api, crear_usuario):
    crear_usuario(rol=RolUsuario.medico)
    return api.token()


def validar(api, token, cuerpo):
    return api.client.post(RUTA, json=cuerpo, headers={"Authorization": f"Bearer {token}"} if token else {})


def test_devuelve_un_resultado_por_patologia_con_el_motivo(api, medico, ids):
    r = validar(api, medico, {
        "patologia_ids": [ids["Fabry"], ids["Pompe"]],
        "sintomas": [s.DOLOR_NEUROPATICO.snomed_code, s.HEPATOMEGALIA.snomed_code],
    })
    assert r.status_code == 200
    cuerpo = r.get_json()
    assert cuerpo["valido"] is False  # Pompe no alcanza
    fabry, pompe = cuerpo["resultados"]
    assert fabry == {
        "patologia_id": ids["Fabry"], "patologia": "Fabry", "valido": True,
        "motivo": "El paciente presenta el síntoma cardinal de Fabry (dolor neuropático).",
        "cardinal_presente": True, "cardinales_presentes": ["dolor neuropático"], "secundarios_presentes": [],
    }
    assert pompe["valido"] is False and pompe["secundarios_presentes"] == ["hepatomegalia"]
    assert "no es consistente" in pompe["motivo"]


def test_valido_si_todas_las_patologias_son_validas(api, medico, ids):
    r = validar(api, medico, {"patologia_ids": [ids["Gaucher"]],
                              "sintomas": [s.ANEMIA.snomed_code, s.OSTEOPENIA.snomed_code]})
    assert r.get_json()["valido"] is True


def test_sin_sintomas_es_invalido_pero_no_es_un_error(api, medico, ids):
    r = validar(api, medico, {"patologia_ids": [ids["Fabry"]], "sintomas": []})
    assert r.status_code == 200 and r.get_json()["valido"] is False


def test_el_gerente_tambien_puede_consultar(api, crear_usuario, ids):
    crear_usuario(rol=RolUsuario.gerente_medico, correo="g@exoma.test")
    token = api.token(correo="g@exoma.test")
    assert validar(api, token, {"patologia_ids": [ids["Fabry"]], "sintomas": []}).status_code == 200


def test_paciente_recibe_403_y_sin_token_401(api, crear_usuario, ids):
    crear_usuario(rol=RolUsuario.paciente, correo="p@exoma.test")
    cuerpo = {"patologia_ids": [ids["Fabry"]], "sintomas": []}
    assert validar(api, api.token(correo="p@exoma.test"), cuerpo).status_code == 403
    assert validar(api, None, cuerpo).status_code == 401


def test_patologia_inexistente_da_404(api, medico):
    r = validar(api, medico, {"patologia_ids": [str(uuid.uuid4())], "sintomas": []})
    assert r.status_code == 404 and r.get_json()["error"]["codigo"] == "PATOLOGIA_NO_ENCONTRADA"


@pytest.mark.parametrize("cuerpo, campo", [
    ({"sintomas": []}, "patologia_ids"),
    ({"patologia_ids": [], "sintomas": []}, "patologia_ids"),
    ({"patologia_ids": ["no-es-uuid"], "sintomas": []}, "patologia_ids[0]"),
    ({"patologia_ids": [str(uuid.uuid4())], "sintomas": ["fiebre"]}, "sintomas[0]"),
    ({"patologia_ids": [str(uuid.uuid4())], "sintomas": "386661006"}, "sintomas"),
])
def test_pedido_invalido_da_400(api, medico, cuerpo, campo):
    r = validar(api, medico, cuerpo)
    assert r.status_code == 400
    assert campo in [c["campo"] for c in r.get_json()["error"]["detalle"]["campos"]]


def test_patologias_repetidas_se_validan_una_vez(api, medico, ids):
    r = validar(api, medico, {"patologia_ids": [ids["Fabry"], ids["Fabry"]], "sintomas": []})
    assert len(r.get_json()["resultados"]) == 1
