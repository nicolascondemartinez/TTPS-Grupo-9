"""ABM de patologías (sin baja): permisos, validaciones, caché de síntomas y seed de las 5 patologías."""
import uuid

import pytest
from sqlalchemy import func, select, text

from src.adapters.snomed.mock import SINTOMAS_POR_PATOLOGIA
from src.core.enums import RolUsuario
from src.core.models import Patologia, PatologiaSintoma, Sintoma
from src.core.seeds.seed_catalogos import PATOLOGIAS
from src.core.seeds.seed_patologias import cargar_sintomas_de_patologias

GERENTE = "gerente@exoma.test"
FIEBRE = {"snomed_code": "386661006", "termino": "fiebre"}
CEFALEA = {"snomed_code": "25064002", "termino": "cefalea"}
FATIGA = {"snomed_code": "84229001", "termino": "fatiga"}
DIARREA = {"snomed_code": "62315008", "termino": "diarrea"}


@pytest.fixture(autouse=True)
def tablas_vacias(app, db):
    db.execute(text("TRUNCATE patologia, sintoma CASCADE"))
    db.commit()


@pytest.fixture
def gerente(api, crear_usuario):
    crear_usuario(rol=RolUsuario.gerente_medico, correo=GERENTE)
    return api.token(correo=GERENTE)


def alta(nombre="Patología de prueba", cardinal=FIEBRE, secundarios=(CEFALEA, FATIGA)):
    return {"nombre": nombre, "cardinal": cardinal, "secundarios": list(secundarios)}


def post(api, token, cuerpo):
    return api.client.post("/api/patologias", json=cuerpo, headers={"Authorization": f"Bearer {token}"})


def put(api, token, patologia_id, cuerpo):
    return api.client.put(f"/api/patologias/{patologia_id}", json=cuerpo, headers={"Authorization": f"Bearer {token}"})


def campos_con_problema(respuesta):
    assert respuesta.status_code == 400, respuesta.get_json()
    return {c["campo"]: c["problema"] for c in respuesta.get_json()["error"]["detalle"]["campos"]}


# ---------- Alta, listado y modificación ----------

def test_el_gerente_crea_una_patologia_con_cardinal_y_secundarios(api, gerente):
    r = post(api, gerente, alta())
    assert r.status_code == 201
    creada = r.get_json()
    assert creada["nombre"] == "Patología de prueba"
    assert creada["cardinal"] == FIEBRE
    assert creada["secundarios"] == [CEFALEA, FATIGA]  # ordenados por término
    assert api.get(f"/api/patologias/{creada['id']}", gerente).get_json() == creada


def test_el_listado_trae_todas_ordenadas_por_nombre(api, gerente):
    post(api, gerente, alta("Zeta"))
    post(api, gerente, alta("Alfa"))
    r = api.get("/api/patologias", gerente)
    assert r.status_code == 200
    assert [p["nombre"] for p in r.get_json()["patologias"]] == ["Alfa", "Zeta"]


def test_el_gerente_modifica_los_sintomas(api, gerente):
    creada = post(api, gerente, alta()).get_json()
    r = put(api, gerente, creada["id"], {"cardinal": CEFALEA, "secundarios": [FIEBRE, DIARREA]})
    assert r.status_code == 200
    modificada = r.get_json()
    assert modificada["nombre"] == creada["nombre"]
    assert modificada["cardinal"] == CEFALEA
    assert modificada["secundarios"] == [DIARREA, FIEBRE]
    assert api.get(f"/api/patologias/{creada['id']}", gerente).get_json() == modificada


def test_los_sintomas_se_guardan_una_sola_vez_en_la_cache(api, gerente, db):
    post(api, gerente, alta("Una", FIEBRE, [CEFALEA]))
    post(api, gerente, alta("Otra", CEFALEA, [FIEBRE, FATIGA]))
    assert db.scalar(select(func.count()).select_from(Sintoma)) == 3


def test_el_nombre_se_normaliza_y_no_se_puede_repetir(api, gerente):
    assert post(api, gerente, alta("  Enfermedad   de  prueba ")).get_json()["nombre"] == "Enfermedad de prueba"
    r = post(api, gerente, alta("ENFERMEDAD DE PRUEBA"))
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "PATOLOGIA_DUPLICADA"


# ---------- Permisos ----------

def test_el_medico_lista_pero_no_crea_ni_modifica(api, gerente, crear_usuario):
    creada = post(api, gerente, alta()).get_json()
    crear_usuario(rol=RolUsuario.medico, correo="m@exoma.test")
    medico = api.token(correo="m@exoma.test")
    assert api.get("/api/patologias", medico).status_code == 200
    assert post(api, medico, alta("Otra")).status_code == 403
    assert put(api, medico, creada["id"], {"cardinal": CEFALEA, "secundarios": [FIEBRE]}).status_code == 403


@pytest.mark.parametrize("rol", [RolUsuario.paciente, RolUsuario.administrativo, RolUsuario.bioinformatico])
def test_otros_roles_no_acceden(api, crear_usuario, rol):
    crear_usuario(rol=rol, correo="otro@exoma.test")
    token = api.token(correo="otro@exoma.test")
    assert api.get("/api/patologias", token).status_code == 403
    assert post(api, token, alta()).status_code == 403


def test_sin_token_recibe_401(api):
    assert api.get("/api/patologias").status_code == 401
    assert api.client.post("/api/patologias", json=alta()).status_code == 401


# ---------- Validaciones ----------

def test_sin_cardinal_ni_secundarios(api, gerente):
    problemas = campos_con_problema(post(api, gerente, {"nombre": "X", "secundarios": []}))
    assert problemas == {"cardinal": "es obligatorio", "secundarios": "tiene que haber al menos un síntoma secundario"}


def test_sin_nombre(api, gerente):
    assert campos_con_problema(post(api, gerente, alta(nombre="   "))) == {"nombre": "es obligatorio"}


def test_el_cardinal_no_puede_repetirse_como_secundario(api, gerente):
    problemas = campos_con_problema(post(api, gerente, alta(cardinal=FIEBRE, secundarios=[CEFALEA, FIEBRE])))
    assert problemas == {"secundarios[1]": "el síntoma cardinal no puede ser también secundario"}


def test_un_secundario_no_puede_repetirse(api, gerente):
    problemas = campos_con_problema(post(api, gerente, alta(secundarios=[CEFALEA, CEFALEA])))
    assert problemas == {"secundarios[1]": "el síntoma está repetido"}


@pytest.mark.parametrize("sintoma", [
    "fiebre",                                          # texto libre
    {"snomed_code": "abc", "termino": "fiebre"},       # código que no es SNOMED
    {"snomed_code": "386661006", "termino": "  "},     # sin término
])
def test_no_acepta_sintomas_que_no_vengan_de_snomed(api, gerente, sintoma):
    assert "cardinal" in campos_con_problema(post(api, gerente, alta(cardinal=sintoma)))


def test_al_modificar_el_nombre_queda_fijo(api, gerente):
    creada = post(api, gerente, alta()).get_json()
    r = put(api, gerente, creada["id"], {"nombre": "Otro", "cardinal": FIEBRE, "secundarios": [CEFALEA]})
    assert campos_con_problema(r) == {"nombre": "no se puede modificar"}


def test_modificar_valida_igual_que_el_alta(api, gerente):
    creada = post(api, gerente, alta()).get_json()
    r = put(api, gerente, creada["id"], {"cardinal": FIEBRE, "secundarios": []})
    assert "secundarios" in campos_con_problema(r)
    assert api.get(f"/api/patologias/{creada['id']}", gerente).get_json() == creada  # no cambió nada


@pytest.mark.parametrize("patologia_id", [str(uuid.uuid4()), "no-es-un-uuid"])
def test_patologia_inexistente_da_404(api, gerente, patologia_id):
    assert api.get(f"/api/patologias/{patologia_id}", gerente).status_code == 404
    r = put(api, gerente, patologia_id, {"cardinal": FIEBRE, "secundarios": [CEFALEA]})
    assert r.status_code == 404 and r.get_json()["error"]["codigo"] == "PATOLOGIA_NO_ENCONTRADA"


# ---------- Seed ----------

def _cargar_las_5(db):
    db.add_all(Patologia(nombre=n) for n in PATOLOGIAS)
    db.commit()


def test_el_seed_deja_las_5_patologias_con_un_cardinal_y_secundarios(db):
    _cargar_las_5(db)
    assert cargar_sintomas_de_patologias(db) == 5
    db.commit()
    for nombre in PATOLOGIAS:
        patologia = db.scalar(select(Patologia).where(Patologia.nombre == nombre))
        cardinales = [ps.sintoma.snomed_code for ps in patologia.sintomas if ps.es_cardinal]
        secundarios = {ps.sintoma.snomed_code for ps in patologia.sintomas if not ps.es_cardinal}
        esperado = SINTOMAS_POR_PATOLOGIA[nombre]
        assert cardinales == [esperado["cardinal"].snomed_code]
        assert secundarios == {s.snomed_code for s in esperado["secundarios"]}


def test_el_seed_se_puede_repetir_y_no_pisa_lo_que_modifico_el_gerente(api, gerente, db):
    _cargar_las_5(db)
    cargar_sintomas_de_patologias(db)
    db.commit()
    fabry = next(p for p in api.get("/api/patologias", gerente).get_json()["patologias"] if p["nombre"] == "Fabry")
    put(api, gerente, fabry["id"], {"cardinal": FIEBRE, "secundarios": [CEFALEA]})

    db.expire_all()
    assert cargar_sintomas_de_patologias(db) == 0
    db.commit()
    assert db.scalar(select(func.count()).select_from(PatologiaSintoma)) == 2 + sum(
        1 + len(d["secundarios"]) for n, d in SINTOMAS_POR_PATOLOGIA.items() if n != "Fabry"
    )
    assert api.get(f"/api/patologias/{fabry['id']}", gerente).get_json()["cardinal"] == FIEBRE
