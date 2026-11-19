"""Pacientes, familiares, patologías y síntomas."""
import uuid
from datetime import date

from sqlalchemy import (Boolean, Column, Date, ForeignKey, Index, String, Table,
                        Text, text)
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base, CreatedAt, UuidPk, pg_enum
from src.core.enums import TipoSospecha


class Patologia(Base, UuidPk, CreatedAt):
    __tablename__ = "patologia"
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)

    sintomas: Mapped[list["PatologiaSintoma"]] = relationship(back_populates="patologia", cascade="all, delete-orphan")


class Sintoma(Base, UuidPk):
    """Caché local de términos SNOMED (se completa al seleccionar un síntoma desde el módulo 2)."""

    __tablename__ = "sintoma"
    snomed_code: Mapped[str] = mapped_column(String(30), unique=True)
    termino: Mapped[str] = mapped_column(String(255))


class PatologiaSintoma(Base):
    """Definición de la patología (la edita el gerente médico): uno o más cardinales y N secundarios.
    Un mismo síntoma puede ser cardinal de varias patologías."""

    __tablename__ = "patologia_sintoma"
    patologia_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patologia.id", ondelete="CASCADE"), primary_key=True)
    sintoma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sintoma.id", ondelete="RESTRICT"), primary_key=True)
    es_cardinal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    patologia: Mapped["Patologia"] = relationship(back_populates="sintomas")
    sintoma: Mapped["Sintoma"] = relationship()


class Paciente(Base, CreatedAt):
    """Perfil 1:1 con usuario (nombre, apellido, teléfono y mail están en `usuario`). Si es menor, el mail/teléfono
    del usuario son los del padre/madre. El diagnóstico presuntivo es una o más patologías (al menos una se valida
    en el alta). Los datos clínicos solo los ven el médico que lo dio de alta y el propio paciente (se filtra en
    la aplicación, como en pagos: si no es suyo, 404)."""

    __tablename__ = "paciente"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
    dni: Mapped[str] = mapped_column(String(15), unique=True)
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    medico_alta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medico.usuario_id", ondelete="RESTRICT"))
    tipo_sospecha: Mapped[TipoSospecha] = mapped_column(pg_enum(TipoSospecha, "tipo_sospecha"))
    historia_clinica: Mapped[str] = mapped_column(Text)  # texto transcripto y confirmado (no se guarda el audio)
    familiograma_url: Mapped[str | None] = mapped_column(Text)  # PDF del módulo 1 en Storage; opcional

    usuario: Mapped["Usuario"] = relationship()  # noqa: F821
    sintomas: Mapped[list["Sintoma"]] = relationship(secondary="paciente_sintoma")
    familiares: Mapped[list["Familiar"]] = relationship(back_populates="paciente", cascade="all, delete-orphan")
    diagnostico_presuntivo: Mapped[list["Patologia"]] = relationship(secondary="paciente_patologia")

    __table_args__ = (Index("ix_paciente_medico_alta_id", "medico_alta_id"),)


paciente_sintoma = Table(
    "paciente_sintoma",
    Base.metadata,
    Column("paciente_id", Uuid(as_uuid=True), ForeignKey("paciente.usuario_id", ondelete="CASCADE"), primary_key=True),
    Column("sintoma_id", Uuid(as_uuid=True), ForeignKey("sintoma.id", ondelete="RESTRICT"), primary_key=True),
)

# Diagnóstico presuntivo: las patologías que el médico sospecha (una o más).
paciente_patologia = Table(
    "paciente_patologia",
    Base.metadata,
    Column("paciente_id", Uuid(as_uuid=True), ForeignKey("paciente.usuario_id", ondelete="CASCADE"), primary_key=True),
    Column("patologia_id", Uuid(as_uuid=True), ForeignKey("patologia.id", ondelete="RESTRICT"), primary_key=True),
)


class Familiar(Base, UuidPk):
    __tablename__ = "familiar"
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("paciente.usuario_id", ondelete="CASCADE"), index=True)
    parentesco: Mapped[str] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(150))
    patologia_diagnosticada_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patologia.id", ondelete="RESTRICT"))

    paciente: Mapped["Paciente"] = relationship(back_populates="familiares")
    sintomas: Mapped[list["Sintoma"]] = relationship(secondary="familiar_sintoma")


familiar_sintoma = Table(
    "familiar_sintoma",
    Base.metadata,
    Column("familiar_id", Uuid(as_uuid=True), ForeignKey("familiar.id", ondelete="CASCADE"), primary_key=True),
    Column("sintoma_id", Uuid(as_uuid=True), ForeignKey("sintoma.id", ondelete="RESTRICT"), primary_key=True),
)
