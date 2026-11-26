"""Centros de extracción, feriados y turnos."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Index, Numeric,
                        String, Text, func, text)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, Timestamps, UuidPk, pg_enum
from src.core.enums import EstadoTurno


class CentroExtraccion(Base, UuidPk):
    """Laboratorio tercerizado (~100 en el país). No opera en el sistema: solo es dato."""

    __tablename__ = "centro_extraccion"
    nombre: Mapped[str] = mapped_column(String(150), unique=True)
    direccion: Mapped[str] = mapped_column(String(255))
    provincia_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("provincia.id", ondelete="RESTRICT"), index=True)
    latitud: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Feriado(Base):
    __tablename__ = "feriado"
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(150))


class Turno(Base, UuidPk, Timestamps):
    """Solo se guardan los turnos reservados; los libres se calculan (L a V, 9 a 18, cada 15 min,
    sin feriados). La grilla horaria se valida en la aplicación."""

    __tablename__ = "turno"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="RESTRICT"))
    centro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("centro_extraccion.id", ondelete="RESTRICT"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[EstadoTurno] = mapped_column(
        pg_enum(EstadoTurno, "estado_turno"),
        default=EstadoTurno.reservado,
        server_default=EstadoTurno.reservado.value,
    )

    __table_args__ = (
        # un solo paciente por centro y horario
        Index(
            "uq_turno_slot_ocupado", "centro_id", "fecha_hora", unique=True,
            postgresql_where=text("estado IN ('reservado', 'asistido')"),
        ),
        # un estudio no puede tener dos turnos reservados a la vez
        Index("uq_turno_estudio_reservado", "estudio_id", unique=True, postgresql_where=text("estado = 'reservado'")),
        Index("ix_turno_estudio_id", "estudio_id"),
    )



class ConsentimientoFirmado(Base, UuidPk):
    """Consentimiento informado firmado que sube el paciente (uno por estudio; si sube otro, se reemplaza).
    El archivo se guarda con el servicio de almacenamiento: acá queda solo su ruta."""

    __tablename__ = "consentimiento_firmado"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="CASCADE"), unique=True)
    archivo_url: Mapped[str] = mapped_column(Text)
    subido_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    subido_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())