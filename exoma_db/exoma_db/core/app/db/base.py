"""Base declarativa, convención de nombres y mixins comunes (core, schema public)."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, MetaData, Uuid, func, text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UuidPk:
    """PK UUID generada por Postgres (gen_random_uuid) o por Python si se crea antes del flush."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class CreatedAt:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Timestamps(CreatedAt):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def pg_enum(py_enum: type[PyEnum], name: str, schema: str | None = None) -> ENUM:
    """ENUM nativo de Postgres que guarda el .value de cada miembro.

    create_type=False: los tipos se crean explícitamente en la migración, así un mismo
    tipo se puede usar en varias columnas (p. ej. estado_estudio en estudio e historial).
    """
    return ENUM(
        py_enum,
        name=name,
        schema=schema,
        create_type=False,
        values_callable=lambda e: [m.value for m in e],
    )
