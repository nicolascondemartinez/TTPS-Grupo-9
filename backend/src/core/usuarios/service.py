"""Reglas de negocio del alta de usuarios. No conoce Flask."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.models import Especialidad


def listar_especialidades(db: Session) -> list[Especialidad]:
    return list(db.scalars(select(Especialidad).order_by(Especialidad.nombre)))