"""Presupuesto (lo emite el administrativo) y pago particular (lo hace el paciente)."""
import uuid
from datetime import date

import pytest
from sqlalchemy import func, select, text

from src.core.enums import ConceptoPago, EstadoEstudio, OrigenGen, OrigenPago, RolUsuario, TipoAviso, TipoSospecha
from src.core.models import (Analisis, AnalisisGen, Aviso, Estudio, EstudioHistorialEstado, Gen, Medico,
                             MovimientoFinanciero, Paciente, Patologia)

ADMINISTRATIVO = "admin@exoma.test"
PACIENTE = "paciente@exoma.test"
OTRO_PACIENTE = "otro.paciente@exoma.test"


@pytest.fixture(autouse=True)
def tablas_vacias(app, db):
    db.execute(text("TRUNCATE estudio, patologia, gen CASCADE"))
    db.commit()


@pytest.fixture
def crear_estudio(db, crear_usuario):
    """Crea un paciente con un estudio en estado Creado y `genes` genes pedidos en el análisis original."""
    medico = crear_usuario(rol=RolUsuario.medico, correo="medico@exoma.test")
    db.add(Medico(usuario_id=medico.id, matricula="MP-0001"))
    patologia = Patologia(nombre="Fabry")
    db.add(patologia)
    db.commit()

    def _crear(correo=PACIENTE, dni="30111222", genes=8):
        usuario = crear_usuario(rol=RolUsuario.paciente, correo=correo)
        db.add(Paciente(
            usuario_id=usuario.id, dni=dni, fecha_nacimiento=date(1990, 1, 1), medico_alta_id=medico.id,
            diagnostico_presuntivo_id=patologia.id, tipo_sospecha=TipoSospecha.clinica, historia_clinica="Resumen",
        ))
        db.flush()
        estudio = Estudio(paciente_id=usuario.id, medico_id=medico.id)
        db.add(estudio)
        db.flush()
        analisis = Analisis(estudio_id=estudio.id, numero=1)
        db.add(analisis)
        db.flush()
        for i in range(genes):
            gen = Gen(simbolo=f"{dni}-GEN{i}")
            db.add(gen)
            db.flush()
            db.add(AnalisisGen(analisis_id=analisis.id, gen_id=gen.id, origen=OrigenGen.patologia))
        db.commit()
        return estudio

    return _crear


@pytest.fixture
def admin(api, crear_usuario):
    crear_usuario(rol=RolUsuario.administrativo, correo=ADMINISTRATIVO)
    return api.token(correo=ADMINISTRATIVO)


def post(api, ruta, token):
    return api.client.post(ruta, headers={"Authorization": f"Bearer {token}"})


def emitir(api, admin, estudio):
    return post(api, f"/api/estudios/{estudio.id}/presupuesto", admin)


def pagar(api, token, estudio):
    return post(api, f"/api/estudios/{estudio.id}/pagos", token)


def codigo_error(respuesta):
    return respuesta.get_json()["error"]["codigo"]


# ---------- Presupuesto ----------

def test_el_administrativo_ve_los_estudios_pendientes_de_presupuesto(api, admin, crear_estudio):
    estudio = crear_estudio(genes=8)
    r = api.get("/api/presupuestos/pendientes", admin)
    assert r.status_code == 200
    [pendiente] = r.get_json()["estudios"]
    assert pendiente["estudio_id"] == str(estudio.id)
    assert pendiente["cantidad_genes"] == 8
    assert pendiente["monto_estimado"] == "590.00"


def test_emitir_presupuesto_calcula_el_precio_y_avisa_al_paciente(api, db, mail, admin, crear_estudio):
    estudio = crear_estudio(genes=8)
    r = emitir(api, admin, estudio)
    assert r.status_code == 201, r.get_json()
    cuerpo = r.get_json()
    assert cuerpo["cantidad_genes"] == 8
    assert cuerpo["genes_adicionales"] == 3
    assert cuerpo["monto_total"] == "590.00"
    assert cuerpo["moneda"] == "USD"

    aviso = db.scalars(select(Aviso).where(Aviso.estudio_id == estudio.id)).one()
    assert aviso.tipo == TipoAviso.presupuesto_emitido
    assert aviso.usuario_id == estudio.paciente_id
    assert mail.enviados[-1].destino == PACIENTE

    # ya no figura entre los pendientes
    assert api.get("/api/presupuestos/pendientes", admin).get_json()["estudios"] == []


def test_no_se_emite_dos_veces(api, admin, crear_estudio):
    estudio = crear_estudio()
    emitir(api, admin, estudio)
    r = emitir(api, admin, estudio)
    assert r.status_code == 409
    assert codigo_error(r) == "PRESUPUESTO_YA_EMITIDO"


def test_el_paciente_no_puede_emitir_presupuestos(api, crear_estudio):
    estudio = crear_estudio()
    token = api.token(correo=PACIENTE)
    r = emitir(api, token, estudio)
    assert r.status_code == 403


def test_el_paciente_ve_su_presupuesto(api, admin, crear_estudio):
    estudio = crear_estudio(genes=5)
    token = api.token(correo=PACIENTE)
    r = api.get(f"/api/estudios/{estudio.id}/presupuesto", token)
    assert r.status_code == 404
    assert codigo_error(r) == "PRESUPUESTO_NO_EMITIDO"

    emitir(api, admin, estudio)
    r = api.get(f"/api/estudios/{estudio.id}/presupuesto", token)
    assert r.status_code == 200
    assert r.get_json()["monto_total"] == "500.00"


def test_un_paciente_no_ve_el_estudio_de_otro(api, admin, crear_estudio):
    estudio_ajeno = crear_estudio(correo=OTRO_PACIENTE, dni="30999888")
    crear_estudio(correo=PACIENTE, dni="30111222")
    emitir(api, admin, estudio_ajeno)
    token = api.token(correo=PACIENTE)
    r = api.get(f"/api/estudios/{estudio_ajeno.id}/presupuesto", token)
    assert r.status_code == 404
    assert codigo_error(r) == "ESTUDIO_NO_ENCONTRADO"


@pytest.mark.parametrize("estudio_id", ["no-es-un-uuid", str(uuid.uuid4())])
def test_estudio_inexistente_da_404(api, admin, estudio_id):
    r = post(api, f"/api/estudios/{estudio_id}/presupuesto", admin)
    assert r.status_code == 404
    assert codigo_error(r) == "ESTUDIO_NO_ENCONTRADO"


# ---------- Pago particular ----------

def test_pagar_registra_el_movimiento_y_pasa_el_estudio_a_pagado(api, db, admin, crear_estudio):
    estudio = crear_estudio(genes=8)
    emitir(api, admin, estudio)
    token = api.token(correo=PACIENTE)

    r = pagar(api, token, estudio)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["monto"] == "590.00"
    assert r.get_json()["estado_estudio"] == "pagado"

    db.expire_all()
    assert db.get(Estudio, estudio.id).estado == EstadoEstudio.pagado
    movimiento = db.scalars(select(MovimientoFinanciero).where(MovimientoFinanciero.estudio_id == estudio.id)).one()
    assert (movimiento.origen, movimiento.concepto) == (OrigenPago.paciente, ConceptoPago.estudio)
    assert str(movimiento.monto) == "590.00"

    # auditoría: el cambio de estado quedó con el usuario que pagó
    historial = db.scalars(select(EstudioHistorialEstado).where(EstudioHistorialEstado.estudio_id == estudio.id)).one()
    assert (historial.estado_anterior, historial.estado_nuevo) == (EstadoEstudio.creado, EstadoEstudio.pagado)
    assert historial.usuario_id == estudio.paciente_id

    tipos = set(db.scalars(select(Aviso.tipo).where(Aviso.estudio_id == estudio.id)))
    assert TipoAviso.puede_sacar_turno in tipos


def test_no_se_paga_sin_presupuesto(api, crear_estudio):
    estudio = crear_estudio()
    r = pagar(api, api.token(correo=PACIENTE), estudio)
    assert r.status_code == 409
    assert codigo_error(r) == "PRESUPUESTO_NO_EMITIDO"


def test_no_se_paga_dos_veces(api, db, admin, crear_estudio):
    estudio = crear_estudio()
    emitir(api, admin, estudio)
    token = api.token(correo=PACIENTE)
    pagar(api, token, estudio)

    r = pagar(api, token, estudio)
    assert r.status_code == 409
    assert codigo_error(r) == "ESTADO_INVALIDO"
    total = db.scalar(select(func.count()).select_from(MovimientoFinanciero).where(
        MovimientoFinanciero.estudio_id == estudio.id))
    assert total == 1


def test_un_paciente_no_paga_el_estudio_de_otro(api, admin, crear_estudio):
    estudio_ajeno = crear_estudio(correo=OTRO_PACIENTE, dni="30999888")
    crear_estudio(correo=PACIENTE, dni="30111222")
    emitir(api, admin, estudio_ajeno)
    r = pagar(api, api.token(correo=PACIENTE), estudio_ajeno)
    assert r.status_code == 404


def test_el_administrativo_no_puede_pagar(api, admin, crear_estudio):
    estudio = crear_estudio()
    emitir(api, admin, estudio)
    r = pagar(api, admin, estudio)
    assert r.status_code == 403
