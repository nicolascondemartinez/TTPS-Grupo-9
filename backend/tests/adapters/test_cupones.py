from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.adapters.cupones import (CuponInexistente, CuponNoDisponible, CuponNoHabilitado, EstadoCupon,
                                  get_cupones)
from src.adapters.cupones import mock as cupones_mock
from src.adapters.cupones.interfaz import GERENTE_ID
from src.adapters.cupones.mock import CuponesMock
from src.core.common.errors import ApiError

MEDICO, OTRO_MEDICO, PACIENTE, OTRO_PACIENTE = "m-1", "m-2", "p-1", "p-2"


@pytest.fixture(autouse=True)
def sin_cupones():
    cupones_mock.reiniciar()
    yield
    cupones_mock.reiniciar()


@pytest.fixture
def cupones():
    return CuponesMock()


def asignado_al_paciente(cupones, descuento=15) -> str:
    [cupon] = cupones.generar_cupones(descuento)
    cupones.asignar_a_medico(MEDICO, cupon.codigo)
    cupones.asignar_a_paciente(MEDICO, PACIENTE, cupon.codigo)
    return cupon.codigo


def vencer(codigo: str) -> None:
    cupones_mock._cupones[codigo] = replace(cupones_mock._cupones[codigo],
                                            fecha_vencimiento=date.today() - timedelta(days=1))


def test_get_cupones_usa_el_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("CUPONES_MODE", raising=False)
    monkeypatch.delenv("ADAPTERS_MODE", raising=False)
    assert isinstance(get_cupones(), CuponesMock)


def test_generar_un_lote(cupones):
    nuevos = cupones.generar_cupones(Decimal("12.5"), cantidad=3)

    assert len({c.codigo for c in nuevos}) == 3
    for c in nuevos:
        assert len(c.codigo) == 8
        assert c.estado == EstadoCupon.disponible and c.gerente_id == GERENTE_ID
        assert c.descuento_porcentaje == Decimal("12.5")
        assert c.fecha_vencimiento == date.today() + timedelta(days=30)


@pytest.mark.parametrize("descuento, cantidad", [(0, 1), (100.5, 1), ("abc", 1), (10, 0), (10, 1001), (10, "2")])
def test_generar_con_datos_invalidos(cupones, descuento, cantidad):
    with pytest.raises(ApiError) as e:
        cupones.generar_cupones(descuento, cantidad)
    assert e.value.status == 400


def test_recorrido_completo_y_un_cupon_usado_deja_de_ser_valido(cupones):
    codigo = asignado_al_paciente(cupones)
    formateado = f"{codigo[:4]}-{codigo[4:]}"

    assert cupones.validar_cupon(PACIENTE, formateado).estado == EstadoCupon.paciente
    cupones.canjear_cupon(PACIENTE, formateado)

    otra = CuponesMock()  # el estado se comparte entre instancias
    info = otra.consultar_cupon(codigo)
    assert info.estado == EstadoCupon.usado and info.fecha_uso is not None
    with pytest.raises(CuponNoDisponible):
        otra.validar_cupon(PACIENTE, codigo)
    with pytest.raises(CuponNoDisponible) as e:
        otra.canjear_cupon(PACIENTE, codigo)
    assert e.value.status == 409


def test_los_pasos_tienen_que_ir_en_orden(cupones):
    [cupon] = cupones.generar_cupones(10)
    with pytest.raises(CuponInexistente):  # todavía no es de ningún médico
        cupones.asignar_a_paciente(MEDICO, PACIENTE, cupon.codigo)
    with pytest.raises(CuponInexistente):  # todavía no es de ningún paciente
        cupones.canjear_cupon(PACIENTE, cupon.codigo)

    cupones.asignar_a_medico(MEDICO, cupon.codigo)
    with pytest.raises(CuponNoHabilitado):  # ya no está disponible
        cupones.asignar_a_medico(OTRO_MEDICO, cupon.codigo)
    with pytest.raises(CuponInexistente):  # es de otro médico
        cupones.asignar_a_paciente(OTRO_MEDICO, PACIENTE, cupon.codigo)


def test_un_cupon_por_paciente_aunque_este_usado(cupones):
    codigo = asignado_al_paciente(cupones)
    cupones.canjear_cupon(PACIENTE, codigo)
    [otro] = cupones.generar_cupones(10)
    cupones.asignar_a_medico(MEDICO, otro.codigo)

    with pytest.raises(CuponNoDisponible):
        cupones.asignar_a_paciente(MEDICO, PACIENTE, otro.codigo)
    cupones.asignar_a_paciente(MEDICO, OTRO_PACIENTE, otro.codigo)


def test_cupon_de_otro_paciente(cupones):
    codigo = asignado_al_paciente(cupones)
    with pytest.raises(CuponInexistente):
        cupones.validar_cupon(OTRO_PACIENTE, codigo)


def test_cupon_vencido(cupones):
    codigo = asignado_al_paciente(cupones)
    vencer(codigo)
    assert cupones.consultar_cupon(codigo).vencido
    with pytest.raises(CuponNoHabilitado):
        cupones.validar_cupon(PACIENTE, codigo)
    with pytest.raises(CuponNoHabilitado):
        cupones.canjear_cupon(PACIENTE, codigo)


def test_listar_y_consultar(cupones):
    a, b = cupones.generar_cupones(10, cantidad=2)
    cupones.asignar_a_medico(MEDICO, a.codigo)

    assert [c.codigo for c in cupones.listar_cupones(estado=EstadoCupon.medico)] == [a.codigo]
    assert [c.codigo for c in cupones.listar_cupones(medico_id=MEDICO)] == [a.codigo]
    assert len(cupones.listar_cupones()) == 2
    assert cupones.consultar_cupon(b.codigo).estado == EstadoCupon.disponible
    assert cupones.consultar_cupon("noexiste") is None
