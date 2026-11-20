"""Familiares del paciente y familiograma (#13)."""
from datetime import date

import pytest
from sqlalchemy import text

from src.adapters import AdaptadorNoDisponible
from src.adapters.familiograma.mock import FamiliogramaMock
from src.core.clinico import familiares as familiares_service
from src.core.clinico.familiares import FamiliarNuevo
from src.core.clinico.validation import validar_familiares
from src.core.common.errors import ApiError
from src.core.enums import RolUsuario, TipoSospecha
from src.core.models import Medico, Paciente, Patologia

@pytest.fixture(autouse=True)
def familiograma_mock(monkeypatch):
    """Siempre el mock del módulo 1, aunque el .env local tenga FAMILIOGRAMA_MODE=real."""
    monkeypatch.setenv("FAMILIOGRAMA_MODE", "mock")


TOS = {"snomed_code": "49727002", "termino": "tos"}
FIEBRE = {"snomed_code": "386661006", "termino": "fiebre"}


def familiar(**cambios):
    return {"parentesco": "progenitor", "nombre": "Laura Gómez", "sintomas": [TOS], "patologia_id": None, **cambios}


def campos(error):
    return {c["campo"]: c["problema"] for c in error.value.detalle["campos"]}


# ---------- Validación de lo que manda el formulario (sin base) ----------

@pytest.mark.parametrize("datos", [None, []])
def test_sin_familiares_es_valido(datos):
    assert validar_familiares(datos) == []


def test_limpia_los_datos():
    [f] = validar_familiares([familiar(nombre="  Laura   Gómez ", sintomas=[TOS, TOS, FIEBRE])])
    assert f == {"parentesco": "progenitor", "nombre": "Laura Gómez", "sintomas": [TOS, FIEBRE], "patologia_id": None}


def test_informa_cada_problema_por_familiar():
    with pytest.raises(ApiError) as e:
        validar_familiares([familiar(), familiar(parentesco=" ", nombre="Laura", patologia_id="x",
                                                 sintomas=[{"snomed_code": "abc", "termino": "tos"}])])
    assert campos(e) == {
        "familiares[1].parentesco": "es obligatorio",
        "familiares[1].nombre": "ingresá nombre y apellido del familiar",
        "familiares[1].sintomas[0]": "no tiene un código SNOMED válido",
        "familiares[1].patologia_id": "no es una patología válida",
    }


def test_familiares_tiene_que_ser_una_lista():
    with pytest.raises(ApiError):
        validar_familiares({"nombre": "x"})


# ---------- Familiograma (sin base: el mock del módulo 1) ----------

def nuevo(nombre="Laura Gómez", parentesco="progenitor", patologia=None):
    return FamiliarNuevo(parentesco, nombre, [TOS], patologia)


def generar(familiares):
    return familiares_service.generar_familiograma("Ana", "Pérez", date(2017, 3, 1), [FIEBRE], familiares,
                                                   al_dia=date(2026, 11, 19))


def test_con_cero_familiares_no_se_llama_al_modulo(monkeypatch):
    def no_llamar():
        raise AssertionError("no se tenía que llamar al módulo de familiograma")
    monkeypatch.setattr(familiares_service, "get_familiograma", no_llamar)
    assert generar([]) is None


def test_genera_el_svg_con_el_diagnostico_previo():
    archivo = generar([nuevo(patologia=Patologia(nombre="Gaucher"))])
    assert archivo.tipo == "image/svg+xml"
    assert b"Laura" in archivo.contenido and b"Gaucher" in archivo.contenido


def test_si_el_modulo_falla_se_puede_seguir_sin_familiograma(monkeypatch):
    class Caido(FamiliogramaMock):
        def generar_familiograma(self, paciente, familiares):
            raise AdaptadorNoDisponible("FAMILIOGRAMA")
    monkeypatch.setattr(familiares_service, "get_familiograma", Caido)
    with pytest.raises(ApiError) as e:
        generar([nuevo()])
    assert e.value.status == 503 and e.value.codigo == "FAMILIOGRAMA_NO_DISPONIBLE"


def test_si_el_modulo_rechaza_un_familiar_se_marca_el_campo():
    with pytest.raises(ApiError) as e:
        generar([nuevo(parentesco="vecino")])
    assert e.value.status == 400 and "familiares[0].parentesco" in campos(e)


def test_edad_en_anios():
    assert familiares_service.edad_en_anios(date(2017, 3, 1), date(2026, 11, 19)) == 9.72


# ---------- Con base: guardar, asociar y descargar ----------

@pytest.fixture(autouse=True)
def tablas_vacias(request):
    if "db" in request.fixturenames:
        db = request.getfixturevalue("db")
        db.execute(text("TRUNCATE patologia, sintoma, archivo CASCADE"))
        db.commit()


@pytest.fixture
def gaucher(db):
    patologia = Patologia(nombre="Gaucher")
    db.add(patologia)
    db.commit()
    return patologia


@pytest.fixture
def paciente(db, crear_usuario, gaucher):
    """Paciente dado de alta por medico@exoma.test, con un familiar y su familiograma."""
    medico = crear_usuario(rol=RolUsuario.medico, correo="medico@exoma.test")
    db.add(Medico(usuario_id=medico.id, matricula="MP-0001"))
    db.commit()
    usuario = crear_usuario(rol=RolUsuario.paciente, correo="paciente@exoma.test")
    paciente = Paciente(usuario_id=usuario.id, dni="30111222", fecha_nacimiento=date(2017, 3, 1),
                        medico_alta_id=medico.id, diagnostico_presuntivo=[gaucher],
                        tipo_sospecha=TipoSospecha.familiar, historia_clinica="Resumen")
    db.add(paciente)
    db.flush()
    preparados = familiares_service.preparar_familiares(db, validar_familiares([familiar(patologia_id=str(gaucher.id))]))
    familiares_service.agregar_familiares(db, paciente, preparados)
    familiares_service.guardar_familiograma(db, paciente, generar(preparados))
    db.commit()
    return paciente


def test_patologia_inexistente_en_un_familiar(db):
    with pytest.raises(ApiError) as e:
        familiares_service.preparar_familiares(db, validar_familiares([familiar(patologia_id="00000000-0000-0000-0000-000000000000")]))
    assert campos(e) == {"familiares[0].patologia_id": "la patología no existe"}


def test_los_familiares_y_el_familiograma_quedan_asociados(db, paciente, gaucher):
    db.expire_all()
    guardado = db.get(Paciente, paciente.usuario_id)
    [f] = guardado.familiares
    assert (f.parentesco, f.nombre, f.patologia_diagnosticada_id) == ("progenitor", "Laura Gómez", gaucher.id)
    assert [s.termino for s in f.sintomas] == ["tos"]
    assert guardado.familiograma_url.startswith("db/")


def descargar(api, token, paciente_id):
    return api.get(f"/api/pacientes/{paciente_id}/familiograma", token)


def test_el_medico_que_lo_dio_de_alta_descarga_el_familiograma(api, paciente):
    r = descargar(api, api.token(correo="medico@exoma.test"), paciente.usuario_id)
    assert r.status_code == 200 and r.mimetype == "image/svg+xml"
    assert r.headers["Content-Disposition"] == 'attachment; filename="familiograma.svg"'
    assert b"Laura" in r.data


def test_el_paciente_descarga_su_familiograma(api, paciente):
    assert descargar(api, api.token(correo="paciente@exoma.test"), paciente.usuario_id).status_code == 200


@pytest.mark.parametrize("rol", [RolUsuario.medico, RolUsuario.paciente, RolUsuario.administrativo])
def test_nadie_mas_lo_ve(api, crear_usuario, paciente, rol):
    crear_usuario(rol=rol, correo="otro@exoma.test")
    r = descargar(api, api.token(correo="otro@exoma.test"), paciente.usuario_id)
    assert r.status_code == 404 and r.get_json()["error"]["codigo"] == "PACIENTE_NO_ENCONTRADO"


def test_paciente_sin_familiograma(api, db, paciente):
    paciente.familiograma_url = None
    db.commit()
    r = descargar(api, api.token(correo="medico@exoma.test"), paciente.usuario_id)
    assert r.status_code == 404 and r.get_json()["error"]["codigo"] == "SIN_FAMILIOGRAMA"


def test_sin_token_401(api, paciente):
    assert descargar(api, None, paciente.usuario_id).status_code == 401


def test_el_medico_ve_el_catalogo_de_parentescos(api, crear_usuario):
    crear_usuario(rol=RolUsuario.medico, correo="medico@exoma.test")
    r = api.get("/api/parentescos", api.token(correo="medico@exoma.test"))
    assert r.status_code == 200
    assert {"id": 1, "nombre": "progenitor"} in r.get_json()["parentescos"]


def test_el_paciente_no_ve_el_catalogo(api, crear_usuario):
    crear_usuario(rol=RolUsuario.paciente, correo="paciente@exoma.test")
    assert api.get("/api/parentescos", api.token(correo="paciente@exoma.test")).status_code == 403
