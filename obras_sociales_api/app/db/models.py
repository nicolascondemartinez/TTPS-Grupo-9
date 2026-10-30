import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey,
                        Index, Numeric, String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAt, UuidPk, pg_enum


class EstadoSolicitud(str, Enum):
    pendiente = "pendiente"
    autorizada = "autorizada"
    rechazada = "rechazada"


PG_ENUMS = [("estado_solicitud", EstadoSolicitud)]


class ObraSocial(Base, UuidPk):
    """Listado tomado de SSSalud (RNOS) con un % de cobertura asignado por nosotros."""

    __tablename__ = "obra_social"
    rnos_codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    sigla: Mapped[str | None] = mapped_column(String(50))
    porcentaje_cobertura: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    __table_args__ = (CheckConstraint("porcentaje_cobertura BETWEEN 0 AND 100", name="porcentaje_rango"),)


class Consumidor(Base, UuidPk, CreatedAt):
    """Cada grupo que usa la API. La API key (hasheada) lo identifica y limita la web de
    autorizar/rechazar a sus propias solicitudes."""

    __tablename__ = "consumidor"
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class SolicitudEstudio(Base, UuidPk, CreatedAt):
    """'Alta de estudio' del módulo: nombre del paciente + fecha. La resuelve (autoriza/rechaza) la web."""

    __tablename__ = "solicitud_estudio"
    consumidor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obras_sociales.consumidor.id", ondelete="RESTRICT"))
    obra_social_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obras_sociales.obra_social.id", ondelete="RESTRICT"))
    paciente_nombre: Mapped[str] = mapped_column(String(200))
    fecha: Mapped[date] = mapped_column(Date)
    referencia_externa: Mapped[str | None] = mapped_column(String(100))  # id del estudio en el core del grupo
    estado: Mapped[EstadoSolicitud] = mapped_column(
        pg_enum(EstadoSolicitud, "estado_solicitud"),
        default=EstadoSolicitud.pendiente,
        server_default=EstadoSolicitud.pendiente.value,
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)
    resuelta_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    consumidor: Mapped["Consumidor"] = relationship()
    obra_social: Mapped["ObraSocial"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "(estado = 'pendiente') = (resuelta_at IS NULL)", name="resuelta_si_no_pendiente"
        ),
        CheckConstraint("estado <> 'rechazada' OR motivo_rechazo IS NOT NULL", name="rechazo_con_motivo"),
        Index("ix_solicitud_estudio_consumidor_id_estado", "consumidor_id", "estado"),
        Index("ix_solicitud_estudio_obra_social_id", "obra_social_id"),
    )
