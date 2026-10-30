"""Avisos internos y configuración del sistema."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAt, UuidPk, pg_enum
from app.db.enums import TipoAviso


class Aviso(Base, UuidPk, CreatedAt):
    """Notificación dentro del sistema (incluye los recordatorios de turno)."""

    __tablename__ = "aviso"
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    tipo: Mapped[TipoAviso] = mapped_column(pg_enum(TipoAviso, "tipo_aviso"))
    titulo: Mapped[str] = mapped_column(String(200))
    mensaje: Mapped[str] = mapped_column(Text)
    estudio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("estudio.id", ondelete="CASCADE"))
    turno_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("turno.id", ondelete="CASCADE"))
    leido: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    leido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_aviso_usuario_id_leido", "usuario_id", "leido"),)


class Configuracion(Base):
    """Pares clave/valor. Hoy: `cdss_estrategia` (ver EstrategiaCdss)."""

    __tablename__ = "configuracion"
    clave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valor: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
