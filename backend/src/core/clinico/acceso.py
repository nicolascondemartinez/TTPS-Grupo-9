"""Quién puede ver los datos de un paciente. Toda consulta de datos de un paciente pasa por acá.

Hoy: el médico que lo dio de alta y el propio paciente (criterio de #11). Un requerimiento nuevo (no asignado
todavía) pide que el paciente pueda autorizar a otros médicos: se suma en `puede_ver_paciente` y nada más.
"""
import uuid

from sqlalchemy.orm import Session

from src.core.common.errors import ApiError
from src.core.common.validation import validar_uuid
from src.core.enums import RolUsuario
from src.core.models import Paciente, Usuario


def puede_ver_paciente(usuario: Usuario, paciente: Paciente) -> bool:
    if usuario.id == paciente.usuario_id:
        return True
    return usuario.rol == RolUsuario.medico and usuario.id == paciente.medico_alta_id


def obtener_paciente_visible(session: Session, paciente_id: str, usuario: Usuario) -> Paciente:
    """El paciente, si existe y el usuario lo puede ver. Si no, 404 (y no 403) para no revelar que existe."""
    paciente = session.get(Paciente, uuid.UUID(paciente_id)) if validar_uuid(paciente_id) else None
    if paciente is None or not puede_ver_paciente(usuario, paciente):
        raise ApiError(404, "PACIENTE_NO_ENCONTRADO", "El paciente no existe")
    return paciente


def filtro_pacientes_visibles(usuario: Usuario):
    """Condición SQL con los pacientes que el usuario puede ver (para listados). Misma regla que puede_ver_paciente."""
    condicion = Paciente.usuario_id == usuario.id
    if usuario.rol == RolUsuario.medico:
        condicion = condicion | (Paciente.medico_alta_id == usuario.id)
    return condicion
