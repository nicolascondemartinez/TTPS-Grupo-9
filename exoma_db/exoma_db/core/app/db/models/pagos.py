"""Presupuesto, cobertura, cupones y movimientos financieros."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, Text, func, text)
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAt, UuidPk, pg_enum
from app.db.enums import ConceptoPago, OrigenPago


class Presupuesto(Base, UuidPk):
    """Foto del costo al emitirlo (USD 500 hasta 5 genes + USD 30 por gen adicional; precio fijo)."""

    __tablename__ = "presupuesto"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="RESTRICT"), unique=True)
    cantidad_genes: Mapped[int] = mapped_column(Integer)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    emitido_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    emitido_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("cantidad_genes >= 1", name="genes_positivo"),
        CheckConstraint("monto_total >= 0", name="monto_no_negativo"),
    )


class Cobertura(Base, UuidPk, CreatedAt):
    """Solo existe si el paciente eligió obra social. Los datos de la obra social son una foto
    del módulo 6 (no hay FK: es otro schema/servicio)."""

    __tablename__ = "cobertura"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="RESTRICT"), unique=True)
    obra_social_externa_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True))
    obra_social_nombre: Mapped[str] = mapped_column(String(200))
    porcentaje_cobertura: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    monto_obra_social: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto_paciente: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    solicitud_externa_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))  # id devuelto por el módulo 6

    __table_args__ = (
        CheckConstraint("porcentaje_cobertura BETWEEN 0 AND 100", name="porcentaje_rango"),
        CheckConstraint("monto_obra_social >= 0 AND monto_paciente >= 0", name="montos_no_negativos"),
    )


class DocumentacionJudicial(Base, UuidPk):
    __tablename__ = "documentacion_judicial"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="RESTRICT"), index=True)
    archivo_url: Mapped[str] = mapped_column(Text)
    subido_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cupon(Base, UuidPk, CreatedAt):
    """Espejo local de un voucher del módulo 3 (la vigencia y el uso los decide ese módulo)."""

    __tablename__ = "cupon"
    codigo_externo: Mapped[str] = mapped_column(String(100), unique=True)
    descuento_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    pdf_url: Mapped[str | None] = mapped_column(Text)
    gerente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gerente_medico.usuario_id", ondelete="RESTRICT"))
    medico_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("medico.usuario_id", ondelete="RESTRICT"))
    paciente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("paciente.usuario_id", ondelete="RESTRICT"))
    estudio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("estudio.id", ondelete="RESTRICT"))
    emitido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    asignado_medico_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    asignado_paciente_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("descuento_porcentaje > 0 AND descuento_porcentaje <= 100", name="descuento_rango"),
        CheckConstraint("paciente_id IS NULL OR medico_id IS NOT NULL", name="paciente_requiere_medico"),
        CheckConstraint("(usado_at IS NULL) = (estudio_id IS NULL)", name="uso_requiere_estudio"),
        Index("ix_cupon_medico_id", "medico_id"),
        Index("ix_cupon_paciente_id", "paciente_id"),
    )


class MovimientoFinanciero(Base, UuidPk, CreatedAt):
    """Un pago (del paciente o de la obra social). Base del tablero de caja y deudas."""

    __tablename__ = "movimiento_financiero"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="RESTRICT"))
    origen: Mapped[OrigenPago] = mapped_column(pg_enum(OrigenPago, "origen_pago"))
    concepto: Mapped[ConceptoPago] = mapped_column(pg_enum(ConceptoPago, "concepto_pago"))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # ya con el descuento aplicado
    monto_descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), server_default=text("0"))
    moneda: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    cupon_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cupon.id", ondelete="RESTRICT"))
    registrado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))

    __table_args__ = (
        CheckConstraint("monto > 0", name="monto_positivo"),
        CheckConstraint("monto_descuento >= 0", name="descuento_no_negativo"),
        Index("ix_movimiento_financiero_estudio_id", "estudio_id"),
        Index("ix_movimiento_financiero_created_at", "created_at"),
    )
