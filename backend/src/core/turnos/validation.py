"""Validación de los datos que llegan a los endpoints de turnos (formato, no reglas de negocio)."""
from datetime import date, datetime

from src.core.common.errors import validation_error
from src.core.common.validation import validar_uuid


def validar_reserva(datos) -> tuple[str, datetime]:
    """Cuerpo de POST /estudios/<id>/turno: {"centro_id": uuid, "fecha_hora": ISO 8601 con zona horaria}."""
    datos = datos if isinstance(datos, dict) else {}
    problemas = []
    centro_id = datos.get("centro_id")
    if not isinstance(centro_id, str) or not validar_uuid(centro_id):
        problemas.append({"campo": "centro_id", "problema": "Elegí un centro de extracción"})
    fecha_hora = None
    texto = datos.get("fecha_hora")
    try:
        fecha_hora = datetime.fromisoformat(texto) if isinstance(texto, str) else None
    except ValueError:
        pass
    if fecha_hora is None:
        problemas.append({"campo": "fecha_hora", "problema": "Elegí un horario"})
    elif fecha_hora.tzinfo is None:
        problemas.append({"campo": "fecha_hora", "problema": "El horario tiene que incluir la zona horaria"})
    if problemas:
        raise validation_error(problemas)
    return centro_id, fecha_hora


def validar_fecha_opcional(texto: str | None, campo: str) -> date | None:
    """Parámetro ?desde= o ?hasta= con formato AAAA-MM-DD (opcional)."""
    if texto is None:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise validation_error([{"campo": campo, "problema": "La fecha tiene que tener el formato AAAA-MM-DD"}])
