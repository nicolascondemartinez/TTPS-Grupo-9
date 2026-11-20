"""Usuario del paciente y envío de credenciales (alta, mail, reenvío y primer ingreso)."""
import logging
import re
from datetime import date

import pytest
from sqlalchemy import select, text

from src.core.auth.password import verificar_contrasena
from src.core.clinico.credenciales import LARGO_CONTRASENA, generar_contrasena_temporal
from src.core.enums import RolUsuario
from src.core.models import Medico, Patologia, Usuario
from src.core.seeds.seed_catalogos import PATOLOGIAS
from src.core.seeds.seed_patologias import cargar_sintomas_de_patologias

MEDICO = "medico@exoma.test"
DEVICE_PACIENTE = "dispositivo-del-paciente-0001"


@pytest.fixture(autouse=True)
def entorno(monkeypatch, app, db):
    monkeypatch.setenv("FAMILIOGRAMA_MODE", "mock")
    db.execute(text("TRUNCATE patologia, sintoma, archivo CASCADE"))
    db.add_all(Patologia(nombre=n) for n in PATOLOGIAS)
    db.commit()
    cargar_sintomas_de_patologias(db)
    db.commit()


@pytest.fixture
def medico(api, db, crear_usuario):
    usuario = crear_usuario(rol=RolUsuario.medico, correo=MEDICO)
    db.add(Medico(usuario_id=usuario.id, matricula="MP-0001"))
    db.commit()
    return api.token(correo=MEDICO)


@pytest.fixture
def alta(db):
    fabry = str(db.scalar(select(Patologia.id).where(Patologia.nombre == "Fabry")))

    def _alta(**cambios):
        return {
            "nombre": "Ana", "apellido": "Pérez", "dni": "45123456", "fecha_nacimiento": "1990-03-01",
            "telefono": "2215551234", "email": "ana@example.com", "tipo_sospecha": "clinica", "patologia_ids": [fabry],
            "sintomas": [{"snomed_code": "247398009", "termino": "dolor neuropático"}],
            "historia_clinica": "Resumen.", **cambios,
        }
    return _alta


def dar_de_alta(api, token, cuerpo):
    r = api.client.post("/api/pacientes", json=cuerpo, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.get_json()
    return r


def contrasena_del_mail(mail) -> str:
    return re.search(r"Contraseña temporal: (\S+)", mail.cuerpo).group(1)


def test_la_contrasena_temporal_es_al_azar_y_legible():
    contrasenas = {generar_contrasena_temporal() for _ in range(50)}
    assert len(contrasenas) == 50
    assert all(len(c) == LARGO_CONTRASENA and not set(c) & set("0O1lI") for c in contrasenas)


def test_al_dar_de_alta_le_llega_el_mail_y_solo_se_guarda_el_hash(api, db, medico, alta, mail, caplog):
    caplog.set_level(logging.DEBUG)
    r = dar_de_alta(api, medico, alta())
    assert r.get_json()["credenciales_enviadas"] is True and r.get_json()["primer_ingreso_pendiente"] is True

    [enviado] = [m for m in mail.enviados if m.destino == "ana@example.com"]
    assert enviado.asunto == "Tu acceso al Sistema de Exoma Clínico"
    assert "Hola, Ana." in enviado.cuerpo and "Usuario: ana@example.com" in enviado.cuerpo
    assert "http://localhost:5173/ingreso" in enviado.cuerpo
    contrasena = contrasena_del_mail(enviado)

    db.expire_all()
    usuario = db.scalar(select(Usuario).where(Usuario.email == "ana@example.com"))
    assert usuario.password_hash != contrasena and verificar_contrasena(usuario.password_hash, contrasena)
    assert usuario.debe_cambiar_password is True
    assert contrasena not in r.get_data(as_text=True)  # ni en la respuesta de la API
    assert contrasena not in caplog.text  # ni en los logs (con el mail de prueba, que no escribe en el log)


def test_si_es_menor_el_mail_va_al_padre_madre_o_tutor(api, medico, alta, mail):
    dar_de_alta(api, medico, alta(fecha_nacimiento="2017-03-01", email="mama@example.com"))
    [enviado] = [m for m in mail.enviados if m.destino == "mama@example.com"]
    assert enviado.cuerpo.startswith("Hola. Te escribimos como padre, madre o tutor de Ana Pérez")


class MailCaido:
    def send(self, destino, asunto, cuerpo):
        raise ConnectionError("el servidor de mails no responde")


def test_si_el_mail_falla_el_alta_no_se_pierde(api, app, db, medico, alta, caplog):
    app.extensions["mail_sender"] = MailCaido()
    r = dar_de_alta(api, medico, alta())
    assert r.get_json()["credenciales_enviadas"] is False
    db.expire_all()
    assert db.scalar(select(Usuario.id).where(Usuario.email == "ana@example.com")) is not None
    assert "No se pudo enviar el mail de credenciales" in caplog.text


def reenviar(api, token, paciente_id):
    return api.client.post(f"/api/pacientes/{paciente_id}/credenciales", headers={"Authorization": f"Bearer {token}"})


def test_reenviar_genera_una_contrasena_nueva(api, app, db, medico, alta, mail):
    app.extensions["mail_sender"] = MailCaido()
    paciente_id = dar_de_alta(api, medico, alta()).get_json()["id"]
    app.extensions["mail_sender"] = mail

    r = reenviar(api, medico, paciente_id)
    assert r.status_code == 200 and r.get_json() == {"credenciales_enviadas": True}
    nueva = contrasena_del_mail(mail.enviados[-1])
    r = reenviar(api, medico, paciente_id)
    otra = contrasena_del_mail(mail.enviados[-1])
    assert nueva != otra
    db.expire_all()
    hash_actual = db.scalar(select(Usuario.password_hash).where(Usuario.email == "ana@example.com"))
    assert verificar_contrasena(hash_actual, otra) and not verificar_contrasena(hash_actual, nueva)


def test_primer_ingreso_con_la_contrasena_temporal(api, medico, alta, mail):
    dar_de_alta(api, medico, alta())
    contrasena = contrasena_del_mail(mail.enviados[-1])
    r = api.login(correo="ana@example.com", contrasena=contrasena, device=DEVICE_PACIENTE)
    assert r.status_code == 200 and r.get_json()["estado"] == "cambio_contrasena_requerido"


def test_no_se_reenvia_si_el_paciente_ya_ingreso(api, db, medico, alta):
    paciente_id = dar_de_alta(api, medico, alta()).get_json()["id"]
    db.execute(text("UPDATE usuario SET debe_cambiar_password = false WHERE email = 'ana@example.com'"))
    db.commit()
    r = reenviar(api, medico, paciente_id)
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "PACIENTE_YA_INGRESO"


def test_otro_medico_no_reenvia(api, db, crear_usuario, medico, alta):
    paciente_id = dar_de_alta(api, medico, alta()).get_json()["id"]
    otro = crear_usuario(rol=RolUsuario.medico, correo="otro.medico@exoma.test")
    db.add(Medico(usuario_id=otro.id, matricula="MP-0002"))
    db.commit()
    assert reenviar(api, api.token(correo="otro.medico@exoma.test"), paciente_id).status_code == 404


def test_el_listado_indica_el_primer_ingreso_pendiente(api, medico, alta):
    dar_de_alta(api, medico, alta())
    [p] = api.get("/api/pacientes", medico).get_json()["pacientes"]
    assert p["primer_ingreso_pendiente"] is True
