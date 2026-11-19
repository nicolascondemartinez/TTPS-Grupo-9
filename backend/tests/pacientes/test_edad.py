"""Menor de 4 meses (Pompe urgente), en meses de calendario (sin base de datos)."""
from datetime import date

import pytest

from src.core.clinico.edad import es_menor_de_4_meses, sumar_meses


@pytest.mark.parametrize("fecha, meses, esperado", [
    (date(2026, 7, 19), 4, date(2026, 11, 19)),
    (date(2026, 10, 31), 4, date(2027, 2, 28)),  # febrero no tiene 31: último día del mes
    (date(2027, 10, 31), 4, date(2028, 2, 29)),  # año bisiesto
    (date(2026, 9, 15), 4, date(2027, 1, 15)),   # cambia el año
    (date(2026, 1, 31), 1, date(2026, 2, 28)),
])
def test_sumar_meses(fecha, meses, esperado):
    assert sumar_meses(fecha, meses) == esperado


def test_menor_de_4_meses_en_meses_de_calendario():
    nacimiento = date(2026, 7, 19)
    assert es_menor_de_4_meses(nacimiento, date(2026, 7, 19))       # recién nacido
    assert es_menor_de_4_meses(nacimiento, date(2026, 11, 18))      # un día antes de cumplir 4 meses
    assert not es_menor_de_4_meses(nacimiento, date(2026, 11, 19))  # el día que cumple 4 meses
    assert not es_menor_de_4_meses(date(1990, 5, 14), date(2026, 11, 19))


def test_nacido_un_31_cumple_4_meses_el_ultimo_dia_de_febrero():
    nacimiento = date(2026, 10, 31)
    assert es_menor_de_4_meses(nacimiento, date(2027, 2, 27))
    assert not es_menor_de_4_meses(nacimiento, date(2027, 2, 28))
