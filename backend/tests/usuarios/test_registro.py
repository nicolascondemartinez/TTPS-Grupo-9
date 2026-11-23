"""Registro de médico, gerente médico, administrativo y bioinformático."""
import pytest
from sqlalchemy import func, select

from src.core.models import Dispositivo, Especialidad, GerenteMedico, Medico, Usuario

from ..conftest import CONTRASENA

CORREO = "marta.lopez@exoma.test"


@pytest.fixture
def especialidades(db):
    lista = [Especialidad(nombre="Cardiología"), Especialidad(nombre="Pediatría")]
    db.add_all(lista)
    db.commit()
    return lista


def datos_base(**cambios):
    datos = {
        "nombre": "Marta", "apellido": "López", "telefono": "+54 221 555-0100",
        "correo": "Marta.Lopez@Exoma.test", "contrasena": CONTRASENA, "rol": "administrativo",
    }
    datos.update(cambios)
    return datos


def datos_profesional(especialidades, rol="medico", **cambios):
    return datos_base(rol=rol, matricula="MP-1234", especialidades=[str(e.id) for e in especialidades], **cambios)


def registrar(api, datos):
    return api.client.post("/api/registro", json=datos)  # sin token: el registro es público


def campos_con_error(respuesta) -> set[str]:
    return {c["campo"].split("[")[0] for c in respuesta.get_json()["error"]["detalle"]["campos"]}


def test_registra_un_medico_con_su_matricula_y_especialidades(api, db, especialidades):
    r = registrar(api, datos_profesional(especialidades))
    cuerpo = r.get_json()
    assert r.status_code == 201
    assert cuerpo["usuario"]["correo"] == CORREO  # se guarda en minúsculas
    assert cuerpo["usuario"]["rol"] == "medico"
    assert "password" not in str(cuerpo).lower() and "hash" not in str(cuerpo).lower()
    usuario = db.scalar(select(Usuario).where(Usuario.email == CORREO))
    assert db.get(Medico, usuario.id).matricula == "MP-1234"
    assert {e.nombre for e in usuario.especialidades} == {"Cardiología", "Pediatría"}
    assert usuario.activo and not usuario.debe_cambiar_password


def test_registra_un_gerente_medico(api, db, especialidades):
    r = registrar(api, datos_profesional(especialidades[:1], rol="gerente_medico"))
    assert r.status_code == 201 and r.get_json()["usuario"]["rol"] == "gerente_medico"
    usuario = db.scalar(select(Usuario).where(Usuario.email == CORREO))
    assert db.get(GerenteMedico, usuario.id).matricula == "MP-1234"
    assert db.get(Medico, usuario.id) is None


@pytest.mark.parametrize("rol", ["administrativo", "bioinformatico"])
def test_administrativo_y_bioinformatico_no_tienen_perfil_y_se_ignoran_matricula_y_especialidades(
    api, db, especialidades, rol
):
    r = registrar(api, datos_profesional(especialidades, rol=rol))
    assert r.status_code == 201 and r.get_json()["usuario"]["rol"] == rol
    usuario = db.scalar(select(Usuario).where(Usuario.email == CORREO))
    assert db.get(Medico, usuario.id) is None and db.get(GerenteMedico, usuario.id) is None
    assert usuario.especialidades == []


def test_la_contrasena_se_guarda_con_hash(api, db):
    registrar(api, datos_base())
    guardado = db.scalar(select(Usuario.password_hash).where(Usuario.email == CORREO))
    assert guardado != CONTRASENA and guardado.startswith("$argon2id$")


def test_el_registro_no_registra_el_dispositivo_y_el_primer_login_pide_codigo(api, db, mail):
    registrar(api, datos_base())
    assert db.scalar(select(func.count()).select_from(Dispositivo)) == 0
    assert mail.enviados == []
    r = api.login(correo=CORREO)
    assert r.get_json()["estado"] == "verificacion_requerida"
    assert len(mail.enviados) == 1 and mail.enviados[0].destino == CORREO


def test_valida_los_datos_obligatorios(api):
    r = registrar(api, {})
    assert r.status_code == 400 and r.get_json()["error"]["codigo"] == "VALIDACION"
    assert campos_con_error(r) == {"nombre", "apellido", "telefono", "correo", "contrasena", "rol"}
    r = api.client.post("/api/registro", data="no es json")
    assert r.status_code == 400 and r.get_json()["error"]["codigo"] == "VALIDACION"


@pytest.mark.parametrize("rol", ["medico", "gerente_medico"])
def test_medico_y_gerente_exigen_matricula_y_especialidades(api, rol):
    r = registrar(api, datos_base(rol=rol))
    assert r.status_code == 400 and campos_con_error(r) == {"matricula", "especialidades"}


@pytest.mark.parametrize("rol", ["paciente", "transportista", "superadmin", None, 7])
def test_solo_se_pueden_registrar_los_cuatro_roles(api, rol):
    r = registrar(api, datos_base(rol=rol))
    assert r.status_code == 400 and campos_con_error(r) == {"rol"}


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("telefono", "abc"),
        ("correo", "no-es-un-correo"),
        ("contrasena", "corta"),
        ("contrasena", CORREO),  # igual al correo
        ("nombre", "x" * 101),
    ],
)
def test_valida_formatos(api, campo, valor):
    r = registrar(api, datos_base(**{campo: valor}))
    assert r.status_code == 400 and campos_con_error(r) == {campo}


def test_especialidades_con_formato_invalido_o_inexistentes(api, especialidades):
    base = datos_profesional(especialidades)
    r = registrar(api, {**base, "especialidades": ["no-es-uuid"]})
    assert r.status_code == 400 and campos_con_error(r) == {"especialidades"}
    inexistente = "00000000-0000-4000-8000-000000000000"
    r = registrar(api, {**base, "especialidades": [inexistente]})
    assert r.status_code == 400 and r.get_json()["error"]["codigo"] == "VALIDACION"
    assert campos_con_error(r) == {"especialidades"}


def test_correo_duplicado_sin_importar_mayusculas(api, db):
    assert registrar(api, datos_base()).status_code == 201
    r = registrar(api, datos_base(correo="MARTA.LOPEZ@exoma.test", rol="bioinformatico"))
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "CORREO_DUPLICADO"
    assert campos_con_error(r) == {"correo"}
    assert db.scalar(select(func.count()).select_from(Usuario)) == 1


def test_matricula_duplicada_tambien_entre_medico_y_gerente(api, especialidades):
    assert registrar(api, datos_profesional(especialidades)).status_code == 201
    otro = datos_profesional(especialidades, correo="otro@exoma.test")
    r = registrar(api, otro)
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "MATRICULA_DUPLICADA"
    gerente = datos_profesional(especialidades, rol="gerente_medico", correo="gerente@exoma.test")
    r = registrar(api, gerente)
    assert r.status_code == 409 and campos_con_error(r) == {"matricula"}