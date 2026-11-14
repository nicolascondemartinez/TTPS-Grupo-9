import uuid
from sqlalchemy.orm import Session
from src.core.enums import EstadoEstudio
from src.core.models import Estudio, EstudioHistorialEstado

def cambiar_estado_estudio(session: Session, estudio: Estudio, nuevo_estado: EstadoEstudio, usuario_id: uuid.UUID | None = None) -> EstudioHistorialEstado:
    """Actualiza el estado del estudio y registra en la transacción la transición en el historial (No hace commit)."""
    estado_anterior = estudio.estado
    estudio.estado = nuevo_estado
    historial = EstudioHistorialEstado(
        estudio_id=estudio.id,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        usuario_id=usuario_id,
    )
    session.add(historial)
    return historial