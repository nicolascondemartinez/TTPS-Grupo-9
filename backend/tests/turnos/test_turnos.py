"""Turnos: centros, turnos libres, reservar y cancelar (usan la base de datos)."""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from io import BytesIO

from src.core.enums import EstadoEstudio, EstadoTurno, RolUsuario, TipoSospecha
from src.core.models import (Archivo, CentroExtraccion, ConsentimientoFirmado, Estudio, EstudioHistorialEstado, Feriado,
                             Medico, Paciente, Patologia, Provincia, Turno)
from src.core.turnos.calendario import ZONA_ARGENTINA, proximo_dia_habil

PACIENTE = "paciente@exoma.test"
OTRO_PACIENTE = "otro.paciente@exoma.test"
DIA = proximo_dia_habil(datetime.now(ZONA_ARGENTINA).date(), set())  # primer día hábil después de hoy


def a_las(dia: date, h: int, m: int = 0) -> str:
    return datetime(dia.year, dia.month, dia.day, h, m, tzinfo=ZONA_ARGENTINA).isoformat()


@pytest.fixture(autouse=True)
def tablas_vacias(app, db):
    db.execute(text("TRUNCATE turno, estudio, patologia, centro_extraccion, provincia, feriado, archivo CASCADE"))
    db.commit()


@pytest.fixture
def centro(db):
    provincia = Provincia(nombre="Buenos Aires")
    db.add(provincia)
    db.flush()
    centro = CentroExtraccion(nombre="Centro La Plata", direccion="Calle 7 nº 450", provincia_id=provincia.id,
                              latitud=-34.92, longitud=-57.95)
    db.add(centro)
    db.commit()
    return centro


@pytest.fixture
def crear_estudio(db, crear_usuario):
    """Paciente con un estudio en el estado indicado (por defecto, Pagado)."""
    medico = crear_usuario(rol=RolUsuario.medico, correo="medico@exoma.test")
    db.add(Medico(usuario_id=medico.id, matricula="MP-0001"))
    patologia = Patologia(nombre="Fabry")
    db.add(patologia)
    db.commit()

    def _crear(correo=PACIENTE, dni="30111222", estado=EstadoEstudio.pagado):
        usuario = crear_usuario(rol=RolUsuario.paciente, correo=correo)
        db.add(Paciente(
            usuario_id=usuario.id, dni=dni, fecha_nacimiento=date(1990, 1, 1), medico_alta_id=medico.id,
            diagnostico_presuntivo=[patologia], tipo_sospecha=TipoSospecha.clinica, historia_clinica="Resumen",
        ))
        db.flush()
        estudio = Estudio(paciente_id=usuario.id, medico_id=medico.id, estado=estado)
        db.add(estudio)
        db.commit()
        return estudio

    return _crear


def post(api, ruta, token, cuerpo=None):
    return api.client.post(ruta, json=cuerpo, headers={"Authorization": f"Bearer {token}"})


def reservar(api, token, estudio, centro, fecha_hora):
    return post(api, f"/api/estudios/{estudio.id}/turno", token, {"centro_id": str(centro.id), "fecha_hora": fecha_hora})


def codigo_error(respuesta):
    return respuesta.get_json()["error"]["codigo"]


# ---------- Centros y turnos libres ----------

def test_lista_los_centros_con_su_provincia(api, centro, crear_estudio):
    crear_estudio()
    [c] = api.get("/api/centros", api.token(correo=PACIENTE)).get_json()["centros"]
    assert c["nombre"] == "Centro La Plata"
    assert c["provincia"] == "Buenos Aires"
    assert c["latitud"] == "-34.920000"


def test_un_dia_habil_tiene_36_turnos_libres(api, centro, crear_estudio):
    crear_estudio()
    token = api.token(correo=PACIENTE)
    r = api.get(f"/api/centros/{centro.id}/turnos-libres?desde={DIA}&hasta={DIA}", token)
    assert r.status_code == 200
    [dia] = r.get_json()["dias"]
    assert dia["fecha"] == DIA.isoformat()
    assert len(dia["franjas"]) == 36
    assert dia["franjas"][0] == a_las(DIA, 9)


def test_un_feriado_no_tiene_turnos(api, db, centro, crear_estudio):
    crear_estudio()
    db.add(Feriado(fecha=DIA, descripcion="Feriado de prueba"))
    db.commit()
    r = api.get(f"/api/centros/{centro.id}/turnos-libres?desde={DIA}&hasta={DIA}", api.token(correo=PACIENTE))
    assert r.get_json()["dias"] == []


def test_fecha_mal_escrita_da_400(api, centro, crear_estudio):
    crear_estudio()
    r = api.get(f"/api/centros/{centro.id}/turnos-libres?desde=24-11-2026", api.token(correo=PACIENTE))
    assert r.status_code == 400


# ---------- Reservar ----------

def test_reservar_saca_el_turno_y_lo_quita_de_los_libres(api, db, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)

    r = reservar(api, token, estudio, centro, a_las(DIA, 9, 15))
    assert r.status_code == 201, r.get_json()
    cuerpo = r.get_json()
    assert cuerpo["fecha_hora"] == a_las(DIA, 9, 15)
    assert cuerpo["estado_estudio"] == "turno_sacado"
    assert cuerpo["centro"]["nombre"] == "Centro La Plata"
    assert (cuerpo["inasistencias"], cuerpo["inasistencias_maximas"]) == (0, 5)

    db.expire_all()
    assert db.get(Estudio, estudio.id).estado == EstadoEstudio.turno_sacado
    historial = db.scalars(select(EstudioHistorialEstado).where(EstudioHistorialEstado.estudio_id == estudio.id)).one()
    assert (historial.estado_anterior, historial.estado_nuevo) == (EstadoEstudio.pagado, EstadoEstudio.turno_sacado)

    franjas = api.get(f"/api/centros/{centro.id}/turnos-libres?desde={DIA}&hasta={DIA}", token).get_json()["dias"][0]["franjas"]
    assert a_las(DIA, 9, 15) not in franjas
    assert len(franjas) == 35


def test_no_se_saca_turno_sin_pagar(api, centro, crear_estudio):
    estudio = crear_estudio(estado=EstadoEstudio.creado)
    r = reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(DIA, 10))
    assert r.status_code == 409
    assert codigo_error(r) == "ESTADO_INVALIDO"


@pytest.mark.parametrize("h, m", [(9, 10), (8, 45), (18, 0)])
def test_horario_fuera_de_la_grilla(api, centro, crear_estudio, h, m):
    estudio = crear_estudio()
    r = reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(DIA, h, m))
    assert r.status_code == 409
    assert codigo_error(r) == "FRANJA_INVALIDA"


def test_no_se_reserva_un_feriado(api, db, centro, crear_estudio):
    estudio = crear_estudio()
    db.add(Feriado(fecha=DIA, descripcion="Feriado de prueba"))
    db.commit()
    r = reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(DIA, 10))
    assert codigo_error(r) == "FRANJA_INVALIDA"


def test_no_se_reserva_en_el_pasado(api, centro, crear_estudio):
    estudio = crear_estudio()
    r = reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(date(2020, 1, 6), 10))
    assert codigo_error(r) == "TURNO_PASADO"


def test_no_se_reserva_a_mas_de_30_dias(api, centro, crear_estudio):
    estudio = crear_estudio()
    lejos = proximo_dia_habil(DIA + timedelta(days=31), set())
    r = reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(lejos, 10))
    assert codigo_error(r) == "FUERA_DE_VENTANA"


def test_dos_pacientes_no_pueden_tener_el_mismo_turno(api, centro, crear_estudio):
    estudio = crear_estudio()
    otro = crear_estudio(correo=OTRO_PACIENTE, dni="30999888")
    assert reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(DIA, 11)).status_code == 201
    r = reservar(api, api.token(correo=OTRO_PACIENTE), otro, centro, a_las(DIA, 11))
    assert r.status_code == 409
    assert codigo_error(r) == "TURNO_OCUPADO"


def test_un_estudio_no_tiene_dos_turnos(api, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    reservar(api, token, estudio, centro, a_las(DIA, 11))
    r = reservar(api, token, estudio, centro, a_las(DIA, 12))
    assert codigo_error(r) == "ESTADO_INVALIDO"


def test_horario_sin_zona_horaria_da_400(api, centro, crear_estudio):
    estudio = crear_estudio()
    r = reservar(api, api.token(correo=PACIENTE), estudio, centro, f"{DIA}T10:00:00")
    assert r.status_code == 400


# ---------- Ver y cancelar ----------

def test_el_paciente_ve_su_turno(api, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    assert codigo_error(api.get(f"/api/estudios/{estudio.id}/turno", token)) == "SIN_TURNO"
    reservar(api, token, estudio, centro, a_las(DIA, 14, 30))
    r = api.get(f"/api/estudios/{estudio.id}/turno", token)
    assert r.status_code == 200
    assert r.get_json()["fecha_hora"] == a_las(DIA, 14, 30)


def test_cancelar_libera_el_turno_y_vuelve_a_pagado(api, db, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    turno_id = reservar(api, token, estudio, centro, a_las(DIA, 10)).get_json()["id"]

    r = post(api, f"/api/turnos/{turno_id}/cancelar", token)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["estado"] == "cancelado"
    assert r.get_json()["estado_estudio"] == "pagado"

    db.expire_all()
    assert db.get(Turno, turno_id).estado == EstadoTurno.cancelado
    assert db.get(Estudio, estudio.id).inasistencias == 0  # cancelar no es faltar
    franjas = api.get(f"/api/centros/{centro.id}/turnos-libres?desde={DIA}&hasta={DIA}", token).get_json()["dias"][0]["franjas"]
    assert a_las(DIA, 10) in franjas
    # y puede volver a sacar turno
    assert reservar(api, token, estudio, centro, a_las(DIA, 10)).status_code == 201


def test_no_se_cancela_dos_veces(api, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    turno_id = reservar(api, token, estudio, centro, a_las(DIA, 10)).get_json()["id"]
    post(api, f"/api/turnos/{turno_id}/cancelar", token)
    r = post(api, f"/api/turnos/{turno_id}/cancelar", token)
    assert codigo_error(r) == "TURNO_NO_CANCELABLE"


def test_un_paciente_no_cancela_el_turno_de_otro(api, centro, crear_estudio):
    estudio = crear_estudio()
    crear_estudio(correo=OTRO_PACIENTE, dni="30999888")
    turno_id = reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(DIA, 10)).get_json()["id"]
    r = post(api, f"/api/turnos/{turno_id}/cancelar", api.token(correo=OTRO_PACIENTE))
    assert r.status_code == 404



# ---------- Documentos del turno ----------

def test_el_paciente_descarga_la_orden_y_el_consentimiento(api, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    turno_id = reservar(api, token, estudio, centro, a_las(DIA, 10)).get_json()["id"]

    for documento in ("orden", "consentimiento"):
        r = api.get(f"/api/turnos/{turno_id}/{documento}.pdf", token)
        assert r.status_code == 200
        assert r.mimetype == "application/pdf"
        assert r.data.startswith(b"%PDF")
        assert "attachment" in r.headers["Content-Disposition"]


def test_otro_paciente_no_descarga_los_documentos(api, centro, crear_estudio):
    estudio = crear_estudio()
    crear_estudio(correo=OTRO_PACIENTE, dni="30999888")
    turno_id = reservar(api, api.token(correo=PACIENTE), estudio, centro, a_las(DIA, 10)).get_json()["id"]
    r = api.get(f"/api/turnos/{turno_id}/orden.pdf", api.token(correo=OTRO_PACIENTE))
    assert r.status_code == 404

def test_un_turno_cancelado_no_tiene_documentos(api, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    turno_id = reservar(api, token, estudio, centro, a_las(DIA, 10)).get_json()["id"]
    post(api, f"/api/turnos/{turno_id}/cancelar", token)
    r = api.get(f"/api/turnos/{turno_id}/orden.pdf", token)
    assert r.status_code == 409
    assert codigo_error(r) == "TURNO_NO_VIGENTE"


# ---------- Consentimiento informado firmado ----------

PDF_FIRMADO = b"%PDF-1.4\n% consentimiento firmado de prueba\n%%EOF"
ADMINISTRATIVO = "admin@exoma.test"


def subir_consentimiento(api, token, estudio, contenido=PDF_FIRMADO, nombre="firmado.pdf"):
    return api.client.post(
        f"/api/estudios/{estudio.id}/consentimiento",
        data={"archivo": (BytesIO(contenido), nombre)},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def admin(api, crear_usuario):
    crear_usuario(rol=RolUsuario.administrativo, correo=ADMINISTRATIVO)
    return api.token(correo=ADMINISTRATIVO)


def test_el_paciente_sube_el_consentimiento_firmado(api, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    reservar(api, token, estudio, centro, a_las(DIA, 10))
    assert api.get(f"/api/estudios/{estudio.id}/consentimiento", token).get_json()["cargado"] is False

    r = subir_consentimiento(api, token, estudio)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["cargado"] is True
    assert r.get_json()["subido_at"] is not None

    pdf = api.get(f"/api/estudios/{estudio.id}/consentimiento.pdf", token)
    assert pdf.status_code == 200
    assert pdf.data == PDF_FIRMADO


def test_subir_otro_reemplaza_al_anterior(api, db, crear_estudio):
    estudio = crear_estudio()  # pagado: lo puede subir aunque todavía no haya sacado turno
    token = api.token(correo=PACIENTE)
    subir_consentimiento(api, token, estudio)
    otro = b"%PDF-1.4\n% segunda version\n%%EOF"
    assert subir_consentimiento(api, token, estudio, otro).status_code == 201

    assert db.scalar(select(func.count()).select_from(ConsentimientoFirmado)) == 1
    assert db.scalar(select(func.count()).select_from(Archivo)) == 1  # el archivo viejo se borró
    assert api.get(f"/api/estudios/{estudio.id}/consentimiento.pdf", token).data == otro


def test_el_consentimiento_tiene_que_ser_un_pdf(api, crear_estudio):
    estudio = crear_estudio()
    r = subir_consentimiento(api, api.token(correo=PACIENTE), estudio, b"no soy un pdf", "foto.pdf")
    assert r.status_code == 400


def test_sin_archivo_da_400(api, crear_estudio):
    estudio = crear_estudio()
    r = api.client.post(f"/api/estudios/{estudio.id}/consentimiento", data={},
                        content_type="multipart/form-data",
                        headers={"Authorization": f"Bearer {api.token(correo=PACIENTE)}"})
    assert r.status_code == 400


def test_no_se_sube_sin_haber_pagado(api, crear_estudio):
    estudio = crear_estudio(estado=EstadoEstudio.creado)
    r = subir_consentimiento(api, api.token(correo=PACIENTE), estudio)
    assert r.status_code == 409
    assert codigo_error(r) == "ESTADO_INVALIDO"


def test_otro_paciente_no_sube_ni_ve_el_consentimiento(api, crear_estudio):
    estudio = crear_estudio()
    crear_estudio(correo=OTRO_PACIENTE, dni="30999888")
    subir_consentimiento(api, api.token(correo=PACIENTE), estudio)
    otro = api.token(correo=OTRO_PACIENTE)
    assert subir_consentimiento(api, otro, estudio).status_code == 404
    assert api.get(f"/api/estudios/{estudio.id}/consentimiento.pdf", otro).status_code == 404


def test_sin_consentimiento_no_se_registra_la_extraccion(api, admin, centro, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    turno_id = reservar(api, token, estudio, centro, a_las(DIA, 10)).get_json()["id"]

    r = post(api, f"/api/turnos/{turno_id}/extraccion", admin)
    assert r.status_code == 409
    assert codigo_error(r) == "CONSENTIMIENTO_FALTANTE"

    subir_consentimiento(api, token, estudio)
    # el administrativo puede verlo antes de registrar la extracción
    assert api.get(f"/api/estudios/{estudio.id}/consentimiento.pdf", admin).status_code == 200
    r = post(api, f"/api/turnos/{turno_id}/extraccion", admin)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["estado_estudio"] == "listo_para_retirar"