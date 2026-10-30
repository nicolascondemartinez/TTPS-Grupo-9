"""Orden del día del transportista y lotes hacia Corea."""
import uuid
from datetime import date, datetime

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey,
                        Index, Integer, Text, UniqueConstraint, func, text)
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAt, UuidPk, pg_enum
from app.db.enums import EstadoLote


class Lote(Base, UuidPk, CreatedAt):
    """10 muestras (o menos si hay un Pompe urgente). El tope de 10 se valida en la aplicación."""

    __tablename__ = "lote"
    estado: Mapped[EstadoLote] = mapped_column(
        pg_enum(EstadoLote, "estado_lote"),
        default=EstadoLote.esperando_autorizacion_ministerio,
        server_default=EstadoLote.esperando_autorizacion_ministerio.value,
    )
    es_urgente: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    csv_url: Mapped[str | None] = mapped_column(Text)
    autorizacion_pdf_url: Mapped[str | None] = mapped_column(Text)  # PDF del Ministerio de Salud
    token_retiro: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), unique=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )  # va en la URL que invoca FedEx (no se expone el id interno)
    sellado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retiro_programado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fedex_url_seguimiento: Mapped[str | None] = mapped_column(Text)

    estudios: Mapped[list["Estudio"]] = relationship(back_populates="lote")  # noqa: F821

    __table_args__ = (
        CheckConstraint("sellado_at IS NULL OR autorizacion_pdf_url IS NOT NULL", name="sellado_requiere_autorizacion"),
    )


class OrdenDelDia(Base, UuidPk, CreatedAt):
    __tablename__ = "orden_del_dia"
    fecha: Mapped[date] = mapped_column(Date)
    transportista_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transportista.usuario_id", ondelete="RESTRICT"))
    llegada_central_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    paradas: Mapped[list["OrdenParada"]] = relationship(
        back_populates="orden", order_by="OrdenParada.posicion", cascade="all, delete-orphan"
    )
    __table_args__ = (UniqueConstraint("fecha", "transportista_id"),)


class OrdenParada(Base, UuidPk):
    """Un centro de extracción dentro de la orden del día (posición fija, la define el módulo 9)."""

    __tablename__ = "orden_parada"
    orden_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orden_del_dia.id", ondelete="CASCADE"))
    centro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("centro_extraccion.id", ondelete="RESTRICT"))
    posicion: Mapped[int] = mapped_column(Integer)
    recogida_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    orden: Mapped["OrdenDelDia"] = relationship(back_populates="paradas")
    __table_args__ = (
        UniqueConstraint("orden_id", "posicion"),
        UniqueConstraint("orden_id", "centro_id"),
        CheckConstraint("posicion >= 1", name="posicion_positiva"),
    )


class ParadaEstudio(Base):
    """Muestras que se recogen en cada parada: permite saber qué transportista lleva un estudio."""

    __tablename__ = "parada_estudio"
    parada_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orden_parada.id", ondelete="CASCADE"), primary_key=True)
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="RESTRICT"), primary_key=True)

    __table_args__ = (Index("ix_parada_estudio_estudio_id", "estudio_id"),)
