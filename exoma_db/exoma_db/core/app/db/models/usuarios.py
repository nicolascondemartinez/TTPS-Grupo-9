"""Usuarios, perfiles por rol y seguridad de acceso."""
import uuid
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String, Table, UniqueConstraint, func, text)
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAt, Timestamps, UuidPk, pg_enum
from app.db.enums import RolUsuario


class Provincia(Base, UuidPk):
    __tablename__ = "provincia"
    nombre: Mapped[str] = mapped_column(String(80), unique=True)


class Especialidad(Base, UuidPk):
    __tablename__ = "especialidad"
    nombre: Mapped[str] = mapped_column(String(120), unique=True)


usuario_especialidad = Table(
    "usuario_especialidad",
    Base.metadata,
    Column("usuario_id", Uuid(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True),
    Column("especialidad_id", Uuid(as_uuid=True), ForeignKey("especialidad.id", ondelete="RESTRICT"), primary_key=True),
)


class Usuario(Base, UuidPk, Timestamps):
    """Cuenta de acceso. El rol define qué perfil 1:1 corresponde (medico, gerente_medico,
    paciente, transportista). Administrativo y bioinformático no tienen datos propios."""

    __tablename__ = "usuario"
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255))
    nombre: Mapped[str] = mapped_column(String(100))
    apellido: Mapped[str] = mapped_column(String(100))
    telefono: Mapped[str] = mapped_column(String(30))
    rol: Mapped[RolUsuario] = mapped_column(pg_enum(RolUsuario, "rol_usuario"))
    debe_cambiar_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    especialidades: Mapped[list["Especialidad"]] = relationship(secondary=usuario_especialidad)
    dispositivos: Mapped[list["Dispositivo"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")

    __table_args__ = (Index("uq_usuario_email_lower", func.lower(email), unique=True),)


class Dispositivo(Base, UuidPk, CreatedAt):
    """Dispositivos ya verificados de un usuario (huella = hash, nunca el dato crudo)."""

    __tablename__ = "dispositivo"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    huella: Mapped[str] = mapped_column(String(128))
    ultimo_acceso: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="dispositivos")
    __table_args__ = (UniqueConstraint("usuario_id", "huella"),)


class CodigoVerificacion(Base, UuidPk, CreatedAt):
    """Código enviado por mail al ingresar desde un dispositivo nuevo."""

    __tablename__ = "codigo_verificacion"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    huella: Mapped[str] = mapped_column(String(128))
    codigo_hash: Mapped[str] = mapped_column(String(255))
    expira_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    intentos: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))

    __table_args__ = (Index("ix_codigo_verificacion_usuario_huella", "usuario_id", "huella"),)


class Medico(Base):
    __tablename__ = "medico"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
    matricula: Mapped[str] = mapped_column(String(30), unique=True)

    usuario: Mapped["Usuario"] = relationship()


class GerenteMedico(Base):
    __tablename__ = "gerente_medico"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
    matricula: Mapped[str] = mapped_column(String(30), unique=True)

    usuario: Mapped["Usuario"] = relationship()


class Transportista(Base):
    """Uno por provincia (UNIQUE sobre provincia_id)."""

    __tablename__ = "transportista"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
    provincia_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("provincia.id", ondelete="RESTRICT"), unique=True)

    usuario: Mapped["Usuario"] = relationship()
    provincia: Mapped["Provincia"] = relationship()
