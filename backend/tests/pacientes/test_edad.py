"""Menor de 4 meses (Pompe urgente), en meses de calendario (sin base de datos)."""
from datetime import date

import pytest

from src.core.clinico.edad import edad_para_familiograma, es_menor_de_4_meses, es_menor_de_edad, sumar_meses


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


def test_menor_de_edad():
    assert es_menor_de_edad(date(2008, 11, 20), date(2026, 11, 19))      # cumple 18 mañana
    assert not es_menor_de_edad(date(2008, 11, 19), date(2026, 11, 19))  # cumple 18 hoy


@pytest.mark.parametrize("nacimiento, esperado", [
    (date(2006, 4, 25), 20),          # años cumplidos, no 20,59
    (date(2025, 11, 20), 0.92),       # 11 meses (cumple un año mañana): nunca "1 año" antes de tiempo
    (date(2026, 7, 19), 0.33),        # 4 meses: en años con decimales (la API recibe solo años)
    (date(2026, 11, 5), 0.04),        # recién nacido de dos semanas: por días
    (date(2025, 11, 19), 1),
])
def test_edad_para_familiograma(nacimiento, esperado):
    assert edad_para_familiograma(nacimiento, date(2026, 11, 19)) == esperado
