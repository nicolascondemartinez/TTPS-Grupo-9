"""JSON de centros y turnos. Los horarios van en hora argentina (ej. "2026-11-24T09:15:00-03:00")."""
from src.core.turnos.calendario import ZONA_ARGENTINA
from src.core.turnos.service import MAXIMO_INASISTENCIAS


def _hora_local(momento) -> str:
    return momento.astimezone(ZONA_ARGENTINA).isoformat()


def centro_view(centro, provincia: str | None = None) -> dict:
    return {
        "id": str(centro.id),
        "nombre": centro.nombre,
        "direccion": centro.direccion,
        "provincia": provincia,
        "latitud": str(centro.latitud),
        "longitud": str(centro.longitud),
    }


def centros_view(centros) -> dict:
    """centros: [(centro, nombre de la provincia)]."""
    return {"centros": [centro_view(c, p) for c, p in centros]}


def turnos_libres_view(centro_id: str, dias) -> dict:
    """dias: [(fecha, [horarios libres])]."""
    return {
        "centro_id": centro_id,
        "dias": [{"fecha": d.isoformat(), "franjas": [_hora_local(f) for f in franjas]} for d, franjas in dias],
    }


def turno_view(turno, centro, estudio) -> dict:
    return {
        "id": str(turno.id),
        "estudio_id": str(estudio.id),
        "estado": turno.estado.value,
        "fecha_hora": _hora_local(turno.fecha_hora),
        "centro": centro_view(centro),
        "estado_estudio": estudio.estado.value,
        "inasistencias": estudio.inasistencias,
        "inasistencias_maximas": MAXIMO_INASISTENCIAS,
    }
