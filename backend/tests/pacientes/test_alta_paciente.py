"""Alta del paciente (#14): POST /api/pacientes y listado del médico."""
from datetime import date

import pytest
from sqlalchemy import func, select, text

from src.adapters import AdaptadorNoDisponible
from src.adapters.familiograma.mock import FamiliogramaMock
from src.adapters.snomed import mock as s
from src.core.clinico import familiares as familiares_service
from src.core.enums import RolUsuario
from src.core.models import Familiar, Medico, Paciente, Patologia, Usuario
from src.core.seeds.seed_catalogos import PATOLOGIAS
from src.core.seeds.seed_patologias import cargar_sintomas_de_patologias

MEDICO = "medico@exoma.test"


def sintoma(x):
    return {"snomed_code": x.snomed_code, "termino": x.termino}


@pytest.fixture(autouse=True)
def entorno(monkeypatch, app, db):
    monkeypatch.setenv("FAMILIOGRAMA_MODE", "mock")
    db.execute(text("TRUNCATE patologia, sintoma, archivo CASCADE"))
    db.add_all(Patologia(nombre=n) for n in PATOLOGIAS)
    db.commit()
    cargar_sintomas_de_patologias(db)
    db.commit()


@pytest.fixture
def ids(db):
    return {p.nombre: str(p.id) for p in db.scalars(select(Patologia))}


@pytest.fixture
def medico(api, db, crear_usuario):
    usuario = crear_usuario(rol=RolUsuario.medico, correo=MEDICO)
    db.add(Medico(usuario_id=usuario.id, matricula="MP-0001"))
    db.commit()
    return api.token(correo=MEDICO)


@pytest.fixture
def alta(ids):
    """Alta válida con sospecha clínica de Fabry (tiene el cardinal) y un familiar."""
    def _alta(**cambios):
        return {
            "nombre": "Ana", "apellido": "Pérez", "dni": "45.123.456", "fecha_nacimiento": "2017-03-01",
            "telefono": "+54 221 555-1234", "email": "Mama.Ana@Example.com", "tipo_sospecha": "clinica",
            "patologia_ids": [ids["Fabry"]], "sintomas": [sintoma(s.DOLOR_NEUROPATICO)],
            "historia_clinica": "Dolor urente en manos y pies desde hace dos años.",
            "familiares": [{"parentesco": "progenitor", "nombre": "Laura Pérez", "sintomas": [], "patologia_id": None}],
            **cambios,
        }
    return _alta


def post(api, token, cuerpo):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return api.client.post("/api/pacientes", json=cuerpo, headers=headers)


def campos(r):
    assert r.status_code == 400, r.get_json()
    return {c["campo"]: c["problema"] for c in r.get_json()["error"]["detalle"]["campos"]}


def pacientes_creados(db):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Paciente)), \
        db.scalar(select(func.count()).select_from(Usuario).where(Usuario.rol == RolUsuario.paciente))


# ---------- Alta correcta ----------

def test_alta_completa(api, db, medico, alta, ids):
    r = post(api, medico, alta())
    assert r.status_code == 201, r.get_json()
    cuerpo = r.get_json()
    assert cuerpo["dni"] == "45123456" and cuerpo["patologias"] == ["Fabry"] and cuerpo["tiene_familiograma"]
    db.expire_all()
    paciente = db.get(Paciente, cuerpo["id"])
    assert paciente.usuario.email == "mama.ana@example.com" and paciente.usuario.rol == RolUsuario.paciente
    assert paciente.usuario.debe_cambiar_password is True
    assert [x.termino for x in paciente.sintomas] == ["dolor neuropático"]
    assert [(f.parentesco, f.nombre) for f in paciente.familiares] == [("progenitor", "Laura Pérez")]
    assert paciente.medico_alta_id == db.scalar(select(Usuario.id).where(Usuario.email == MEDICO))


def test_con_cero_familiares_funciona_y_no_llama_al_modulo(api, medico, alta, monkeypatch):
    def no_llamar():
        raise AssertionError("no se tenía que llamar al módulo de familiograma")
    monkeypatch.setattr(familiares_service, "get_familiograma", no_llamar)
    r = post(api, medico, alta(familiares=[]))
    assert r.status_code == 201 and r.get_json()["tiene_familiograma"] is False


# ---------- Campos obligatorios ----------

def test_todos_los_campos_son_obligatorios_salvo_los_familiares(api, medico):
    assert campos(post(api, medico, {})) == {
        "nombre": "es obligatorio", "apellido": "es obligatorio", "dni": "es obligatorio",
        "fecha_nacimiento": "es obligatoria (AAAA-MM-DD)", "telefono": "es obligatorio", "email": "es obligatorio",
        "tipo_sospecha": "elegí sospecha clínica o familiar",
        "patologia_ids": "elegí al menos una patología sospechada",
        "historia_clinica": "es obligatorio: grabalo o escribilo",
    }


def test_con_sospecha_clinica_los_sintomas_son_obligatorios(api, medico, alta):
    assert campos(post(api, medico, alta(sintomas=[]))) == {"sintomas": "con sospecha clínica, elegí al menos un síntoma"}


@pytest.mark.parametrize("cambios, campo", [
    ({"dni": "12A45678"}, "dni"), ({"dni": "123"}, "dni"),
    ({"fecha_nacimiento": "2999-01-01"}, "fecha_nacimiento"), ({"fecha_nacimiento": "01/03/2017"}, "fecha_nacimiento"),
    ({"email": "sin-arroba"}, "email"), ({"telefono": "abc"}, "telefono"), ({"tipo_sospecha": "otra"}, "tipo_sospecha"),
])
def test_datos_invalidos(api, medico, alta, cambios, campo):
    assert campo in campos(post(api, medico, alta(**cambios)))


def test_un_familiar_invalido_se_marca_en_su_campo(api, medico, alta):
    r = post(api, medico, alta(familiares=[{"parentesco": "progenitor", "nombre": "Laura"}]))
    assert campos(r) == {"familiares[0].nombre": "ingresá nombre y apellido del familiar"}


# ---------- Duplicados ----------

def test_dni_repetido(api, medico, alta):
    assert post(api, medico, alta()).status_code == 201
    r = post(api, medico, alta(email="otro@example.com", dni="45123456"))
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "DNI_DUPLICADO"


def test_mail_repetido_aunque_cambien_mayusculas(api, medico, alta):
    assert post(api, medico, alta()).status_code == 201
    r = post(api, medico, alta(dni="45123457", email="MAMA.ANA@example.com"))
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "MAIL_EN_USO"


# ---------- Diagnóstico presuntivo ----------

def test_diagnostico_clinico_inconsistente_no_crea_nada(api, db, medico, alta, ids):
    r = post(api, medico, alta(patologia_ids=[ids["Fabry"], ids["Pompe"]]))  # sin síntomas de Pompe
    assert r.status_code == 409
    error = r.get_json()["error"]
    assert error["codigo"] == "DIAGNOSTICO_INCONSISTENTE"
    pompe = next(x for x in error["detalle"]["resultados"] if x["patologia"] == "Pompe")
    assert pompe["valido"] is False and "no es consistente" in pompe["motivo"]
    assert pacientes_creados(db) == (0, 0)


def familiar_con(patologia_id, nombre="Tomás Pérez", parentesco="hermano/a"):
    return {"parentesco": parentesco, "nombre": nombre, "sintomas": [], "patologia_id": patologia_id}


def test_sospecha_familiar_sin_sintomas_con_un_familiar_diagnosticado(api, medico, alta, ids):
    r = post(api, medico, alta(tipo_sospecha="familiar", sintomas=[], familiares=[familiar_con(ids["Fabry"])]))
    assert r.status_code == 201, r.get_json()


def test_sospecha_familiar_alcanza_con_una_de_las_patologias(api, medico, alta, ids):
    """Sospecha familiar de Fabry (el hermano la tiene) y además Gaucher por sus propios motivos."""
    r = post(api, medico, alta(tipo_sospecha="familiar", sintomas=[], patologia_ids=[ids["Fabry"], ids["Gaucher"]],
                               familiares=[familiar_con(ids["Fabry"])]))
    assert r.status_code == 201, r.get_json()


def test_sospecha_familiar_sin_familiar_diagnosticado(api, db, medico, alta, ids):
    r = post(api, medico, alta(tipo_sospecha="familiar", sintomas=[], familiares=[familiar_con(ids["Gaucher"])]))
    assert r.status_code == 409
    [resultado] = r.get_json()["error"]["detalle"]["resultados"]
    assert resultado["motivo"] == "Ningún familiar cargado tiene diagnóstico de Fabry."
    assert pacientes_creados(db) == (0, 0)


def test_patologia_inexistente(api, medico, alta):
    r = post(api, medico, alta(patologia_ids=["00000000-0000-0000-0000-000000000000"]))
    assert r.status_code == 404


# ---------- Familiograma caído: reintentar o seguir sin él ----------

class Caido(FamiliogramaMock):
    def generar_familiograma(self, paciente, familiares):
        raise AdaptadorNoDisponible("FAMILIOGRAMA")


def test_si_el_familiograma_falla_no_se_crea_nada_y_se_puede_seguir_sin_el(api, db, medico, alta, monkeypatch):
    monkeypatch.setattr(familiares_service, "get_familiograma", Caido)
    r = post(api, medico, alta())
    assert r.status_code == 503 and r.get_json()["error"]["codigo"] == "FAMILIOGRAMA_NO_DISPONIBLE"
    assert pacientes_creados(db) == (0, 0)

    r = post(api, medico, alta(sin_familiograma=True))
    assert r.status_code == 201 and r.get_json()["tiene_familiograma"] is False
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Familiar)) == 1  # los familiares se guardan igual


def test_reintentar_cuando_el_modulo_vuelve(api, medico, alta, monkeypatch):
    monkeypatch.setattr(familiares_service, "get_familiograma", Caido)
    assert post(api, medico, alta()).status_code == 503
    monkeypatch.setattr(familiares_service, "get_familiograma", FamiliogramaMock)
    r = post(api, medico, alta())
    assert r.status_code == 201 and r.get_json()["tiene_familiograma"] is True


def test_si_algo_falla_en_el_medio_no_queda_un_paciente_a_medias(api, db, medico, alta, monkeypatch):
    def falla(*args):
        raise RuntimeError("se cortó la luz")
    monkeypatch.setattr(familiares_service, "guardar_familiograma", falla)
    r = post(api, medico, alta())
    assert r.status_code == 500 and r.get_json()["error"]["codigo"] == "ERROR_INTERNO"
    assert pacientes_creados(db) == (0, 0)
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Familiar)) == 0


# ---------- Quién puede dar de alta ----------

@pytest.mark.parametrize("rol", [RolUsuario.gerente_medico, RolUsuario.paciente, RolUsuario.administrativo])
def test_solo_el_medico_da_de_alta(api, crear_usuario, alta, rol):
    crear_usuario(rol=rol, correo="otro@exoma.test")
    assert post(api, api.token(correo="otro@exoma.test"), alta()).status_code == 403


def test_sin_token(api, alta):
    assert post(api, None, alta()).status_code == 401


def test_medico_sin_perfil(api, crear_usuario, alta):
    crear_usuario(rol=RolUsuario.medico, correo="sinperfil@exoma.test")
    r = post(api, api.token(correo="sinperfil@exoma.test"), alta())
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "SIN_PERFIL_MEDICO"


# ---------- Listado del médico ----------

def test_el_medico_ve_solo_sus_pacientes(api, db, crear_usuario, medico, alta):
    post(api, medico, alta())
    otro = crear_usuario(rol=RolUsuario.medico, correo="otro.medico@exoma.test")
    db.add(Medico(usuario_id=otro.id, matricula="MP-0002"))
    db.commit()
    token_otro = api.token(correo="otro.medico@exoma.test")
    post(api, token_otro, alta(dni="30111222", email="otra@example.com", nombre="Beto"))

    mios = api.get("/api/pacientes", medico).get_json()["pacientes"]
    assert [(p["nombre"], p["dni"]) for p in mios] == [("Ana", "45123456")]
    assert [p["nombre"] for p in api.get("/api/pacientes", token_otro).get_json()["pacientes"]] == ["Beto"]
