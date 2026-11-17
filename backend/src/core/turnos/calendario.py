"""Calendario laboral: días hábiles y franjas de turno.

Reglas (de la entrevista con el cliente):
- Se trabaja de lunes a viernes, de 9 a 18. Los feriados no hay turnos ni orden del día.
- Los turnos de extracción duran 15 minutos: el primero es a las 9:00 y el último a las 17:45 (36 por día).

Las funciones reciben el conjunto de feriados ya cargado, así se pueden testear sin base de datos.
Para obtenerlo de la base: feriados_entre(session, desde, hasta).
"""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.models import Feriado

# Argentina no tiene horario de verano desde 2009: el desfase es fijo (UTC-3).
# Se usa un desfase fijo en lugar de ZoneInfo porque en Windows ZoneInfo necesita un paquete extra.
ZONA_ARGENTINA = timezone(timedelta(hours=-3), "ART")

HORA_APERTURA = time(9, 0)
HORA_CIERRE = time(18, 0)
DURACION_TURNO = timedelta(minutes=15)


def feriados_entre(session: Session, desde: date, hasta: date) -> set[date]:
    """Fechas de los feriados cargados en la base entre `desde` y `hasta` (inclusive)."""
    consulta = select(Feriado.fecha).where(Feriado.fecha.between(desde, hasta))
    return set(session.scalars(consulta))


def es_dia_habil(fecha: date, feriados: set[date]) -> bool:
    """Lunes a viernes que no sea feriado."""
    return fecha.weekday() < 5 and fecha not in feriados


def dias_habiles(desde: date, hasta: date, feriados: set[date]) -> list[date]:
    """Días hábiles entre `desde` y `hasta` (inclusive), en orden."""
    dias = []
    dia = desde
    while dia <= hasta:
        if es_dia_habil(dia, feriados):
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def proximo_dia_habil(fecha: date, feriados: set[date]) -> date:
    """Primer día hábil posterior a `fecha` (no incluye a `fecha`)."""
    dia = fecha + timedelta(days=1)
    while not es_dia_habil(dia, feriados):
        dia += timedelta(days=1)
    return dia


def franjas_del_dia(fecha: date, feriados: set[date]) -> list[datetime]:
    """Horarios de inicio de cada turno del día, con zona horaria. Vacía si el día no es hábil."""
    if not es_dia_habil(fecha, feriados):
        return []
    franjas = []
    momento = datetime.combine(fecha, HORA_APERTURA, tzinfo=ZONA_ARGENTINA)
    cierre = datetime.combine(fecha, HORA_CIERRE, tzinfo=ZONA_ARGENTINA)
    while momento < cierre:
        franjas.append(momento)
        momento += DURACION_TURNO
    return franjas


def es_franja_valida(momento: datetime, feriados: set[date]) -> bool:
    """True si `momento` es el inicio exacto de un turno (día hábil, entre 9:00 y 17:45, cada 15 min).

    `momento` tiene que tener zona horaria (por ejemplo, la que manda el frontend o la que guarda la base).
    """
    if momento.tzinfo is None:
        raise ValueError("El horario tiene que incluir la zona horaria")
    local = momento.astimezone(ZONA_ARGENTINA)
    return local in franjas_del_dia(local.date(), feriados)
