"""Calendario laboral: días hábiles y franjas de turno (no usa la base de datos)."""
from datetime import date, datetime, timezone

import pytest

from src.core.turnos.calendario import (ZONA_ARGENTINA, dias_habiles, es_dia_habil, es_franja_valida,
                                        franjas_del_dia, proximo_dia_habil)

MARTES = date(2026, 11, 17)
VIERNES = date(2026, 11, 20)
SABADO = date(2026, 11, 21)
DOMINGO = date(2026, 11, 22)
LUNES_FERIADO = date(2026, 11, 23)  # Día de la Soberanía Nacional
MARTES_SIGUIENTE = date(2026, 11, 24)
FERIADOS = {LUNES_FERIADO}


def hora(fecha: date, h: int, m: int) -> datetime:
    return datetime(fecha.year, fecha.month, fecha.day, h, m, tzinfo=ZONA_ARGENTINA)


# --- Días hábiles ---

def test_lunes_a_viernes_son_habiles():
    assert es_dia_habil(MARTES, FERIADOS)
    assert es_dia_habil(VIERNES, FERIADOS)


@pytest.mark.parametrize("fecha", [SABADO, DOMINGO, LUNES_FERIADO])
def test_fin_de_semana_y_feriado_no_son_habiles(fecha):
    assert not es_dia_habil(fecha, FERIADOS)


def test_dias_habiles_de_una_semana_con_feriado():
    # del lunes 23 (feriado) al domingo 29: quedan martes a viernes
    assert dias_habiles(LUNES_FERIADO, date(2026, 11, 29), FERIADOS) == [
        date(2026, 11, 24), date(2026, 11, 25), date(2026, 11, 26), date(2026, 11, 27),
    ]


def test_proximo_dia_habil_saltea_fin_de_semana_y_feriado():
    assert proximo_dia_habil(VIERNES, FERIADOS) == MARTES_SIGUIENTE
    assert proximo_dia_habil(VIERNES, set()) == LUNES_FERIADO


# --- Franjas de turno ---

def test_un_dia_habil_tiene_36_franjas_de_9_a_17_45():
    franjas = franjas_del_dia(MARTES, FERIADOS)
    assert len(franjas) == 36
    assert franjas[0] == hora(MARTES, 9, 0)
    assert franjas[1] == hora(MARTES, 9, 15)
    assert franjas[-1] == hora(MARTES, 17, 45)


@pytest.mark.parametrize("fecha", [SABADO, DOMINGO, LUNES_FERIADO])
def test_dias_no_habiles_no_tienen_franjas(fecha):
    assert franjas_del_dia(fecha, FERIADOS) == []


@pytest.mark.parametrize("h, m", [(9, 0), (12, 30), (17, 45)])
def test_franjas_validas(h, m):
    assert es_franja_valida(hora(MARTES, h, m), FERIADOS)


@pytest.mark.parametrize("h, m", [(8, 45), (9, 10), (18, 0)])
def test_franjas_invalidas_por_horario(h, m):
    assert not es_franja_valida(hora(MARTES, h, m), FERIADOS)


def test_franja_invalida_en_dia_no_habil():
    assert not es_franja_valida(hora(SABADO, 10, 0), FERIADOS)
    assert not es_franja_valida(hora(LUNES_FERIADO, 10, 0), FERIADOS)


def test_acepta_el_horario_en_utc():
    # 12:00 UTC = 9:00 en Argentina (así puede llegar desde la base o el frontend)
    assert es_franja_valida(datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc), FERIADOS)


def test_horario_sin_zona_horaria_da_error():
    with pytest.raises(ValueError):
        es_franja_valida(datetime(2026, 11, 17, 9, 0), FERIADOS)
