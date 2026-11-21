"""Edad del paciente a partir de su fecha de nacimiento (sin base de datos).

Pompe urgente: un paciente con sospecha de Pompe y menor de 4 meses al darse de alta tiene prioridad en el
análisis (lo marca la Persona 4 en `estudio.es_pompe_urgente`). Los meses se cuentan de calendario: quien nació
el 19/7 deja de ser menor de 4 meses el 19/11. Si ese día no existe en el mes (nació el 31/10), se toma el
último día del mes (28 o 29/2).
"""
import calendar
from datetime import date

MESES_POMPE_URGENTE = 4


def sumar_meses(fecha: date, meses: int) -> date:
    """La misma fecha `meses` meses después; si el día no existe en ese mes, el último día del mes."""
    total = fecha.month - 1 + meses
    anio, mes = fecha.year + total // 12, total % 12 + 1
    return date(anio, mes, min(fecha.day, calendar.monthrange(anio, mes)[1]))


def es_menor_de_meses(fecha_nacimiento: date, meses: int, al_dia: date) -> bool:
    """True si al `al_dia` todavía no cumplió `meses` meses de calendario."""
    return al_dia < sumar_meses(fecha_nacimiento, meses)


def es_menor_de_4_meses(fecha_nacimiento: date, al_dia: date) -> bool:
    """Para el Pompe urgente: menor de 4 meses de calendario al `al_dia` (normalmente, el día del alta)."""
    return es_menor_de_meses(fecha_nacimiento, MESES_POMPE_URGENTE, al_dia)


def anios_cumplidos(fecha_nacimiento: date, al_dia: date) -> int:
    return al_dia.year - fecha_nacimiento.year - ((al_dia.month, al_dia.day) < (fecha_nacimiento.month, fecha_nacimiento.day))


def edad_para_familiograma(fecha_nacimiento: date, al_dia: date) -> float:
    """Años cumplidos (20, no 20,59). Menores de un año: meses cumplidos en años (4 meses -> 0.33),
    porque la API del familiograma recibe la edad solo en años y es ella la que escribe "años" en la imagen."""
    anios = anios_cumplidos(fecha_nacimiento, al_dia)
    if anios >= 1:
        return anios
    meses = (al_dia.year - fecha_nacimiento.year) * 12 + al_dia.month - fecha_nacimiento.month - (al_dia.day < fecha_nacimiento.day)
    if meses >= 1:
        return round(meses / 12, 2)  # meses cumplidos: 11 meses -> 0.92 (nunca redondea a 1)
    return round((al_dia - fecha_nacimiento).days / 365.25, 2)  # recién nacido: por días


MAYORIA_DE_EDAD = 18


def es_menor_de_edad(fecha_nacimiento: date, al_dia: date) -> bool:
    """Menor de 18 años al `al_dia`: el mail de contacto es el del padre, la madre o el tutor."""
    return es_menor_de_meses(fecha_nacimiento, MAYORIA_DE_EDAD * 12, al_dia)
