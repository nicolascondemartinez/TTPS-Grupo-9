"""Sesiones de acceso (tokens) y permisos por rol."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base, UuidPk, pg_enum
from src.core.enums import AlcanceSesion, RolUsuario


class Sesion(Base, UuidPk):
    """Una sesión abierta. El token en claro solo lo conoce el cliente: acá se guarda su hash
    SHA-256, así una filtración de la base no permite usar las sesiones."""

    __tablename__ = "sesion"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    alcance: Mapped[AlcanceSesion] = mapped_column(pg_enum(AlcanceSesion, "alcance_sesion"))
    creada_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usuario: Mapped["Usuario"] = relationship()  # noqa: F821

    __table_args__ = (Index("ix_sesion_usuario_id", "usuario_id"),)


class Permiso(Base, UuidPk):
    """Permiso con el patrón modulo_accion (por ejemplo `paciente_crear`)."""

    __tablename__ = "permiso"
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class RolPermiso(Base):
    """Qué permisos tiene cada rol (el rol es el enum de `usuario.rol`)."""

    __tablename__ = "rol_permiso"
    rol: Mapped[RolUsuario] = mapped_column(pg_enum(RolUsuario, "rol_usuario"), primary_key=True)
    permiso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permiso.id", ondelete="CASCADE"), primary_key=True
    )
