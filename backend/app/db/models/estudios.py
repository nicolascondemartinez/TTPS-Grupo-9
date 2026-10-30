"""Estudio (caso que recorre la logística) y Análisis (cada ronda de lectura de genes)."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, Numeric, String,
                        Text, UniqueConstraint, func, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAt, Timestamps, UuidPk, pg_enum
from app.db.enums import (ClasificacionVariante, EstadoEstudio, OrigenGen,
                          ResultadoAnalisis)


class Gen(Base, UuidPk):
    """Caché local de genes (se completa al consultarlos al módulo 5, Apigen)."""

    __tablename__ = "gen"
    simbolo: Mapped[str] = mapped_column(String(50), unique=True)


class Estudio(Base, UuidPk, Timestamps):
    __tablename__ = "estudio"
    paciente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("paciente.usuario_id", ondelete="RESTRICT"))
    medico_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medico.usuario_id", ondelete="RESTRICT"))
    estado: Mapped[EstadoEstudio] = mapped_column(
        pg_enum(EstadoEstudio, "estado_estudio"),
        default=EstadoEstudio.creado,
        server_default=EstadoEstudio.creado.value,
    )
    es_pompe_urgente: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    inasistencias: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    volumen_ml: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    datos_crudos_url: Mapped[str | None] = mapped_column(Text)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lote.id", ondelete="RESTRICT"))

    paciente: Mapped["Paciente"] = relationship()  # noqa: F821
    medico: Mapped["Medico"] = relationship()  # noqa: F821
    lote: Mapped["Lote | None"] = relationship(back_populates="estudios")  # noqa: F821
    analisis: Mapped[list["Analisis"]] = relationship(back_populates="estudio", order_by="Analisis.numero")
    historial: Mapped[list["EstudioHistorialEstado"]] = relationship(back_populates="estudio")

    __table_args__ = (
        CheckConstraint("inasistencias BETWEEN 0 AND 5", name="inasistencias_rango"),
        CheckConstraint("volumen_ml IS NULL OR volumen_ml >= 0", name="volumen_no_negativo"),
        Index("ix_estudio_paciente_id", "paciente_id"),
        Index("ix_estudio_estado", "estado"),
        Index("ix_estudio_lote_id", "lote_id"),
    )


class EstudioHistorialEstado(Base, UuidPk, CreatedAt):
    """Una fila por cada cambio de estado: base del tablero (tiempos, cuellos de botella)."""

    __tablename__ = "estudio_historial_estado"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="CASCADE"))
    estado_anterior: Mapped[EstadoEstudio | None] = mapped_column(pg_enum(EstadoEstudio, "estado_estudio"))
    estado_nuevo: Mapped[EstadoEstudio] = mapped_column(pg_enum(EstadoEstudio, "estado_estudio"))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))  # NULL = sistema

    estudio: Mapped["Estudio"] = relationship(back_populates="historial")
    __table_args__ = (Index("ix_estudio_historial_estado_estudio_id_created_at", "estudio_id", "created_at"),)


class Analisis(Base, UuidPk):
    """numero=1 es el análisis original; 2+ son re-análisis sobre el mismo exoma."""

    __tablename__ = "analisis"
    estudio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estudio.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(Integer)
    incluye_hallazgos_secundarios: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    solicitado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    bioinformatico_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    tomado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resultado: Mapped[ResultadoAnalisis | None] = mapped_column(pg_enum(ResultadoAnalisis, "resultado_analisis"))
    informe_url: Mapped[str | None] = mapped_column(Text)
    informe_generado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalizado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    estudio: Mapped["Estudio"] = relationship(back_populates="analisis")
    patologias: Mapped[list["AnalisisPatologia"]] = relationship(back_populates="analisis", cascade="all, delete-orphan")
    genes: Mapped[list["AnalisisGen"]] = relationship(back_populates="analisis", cascade="all, delete-orphan")
    variantes: Mapped[list["AnalisisVariante"]] = relationship(back_populates="analisis", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("estudio_id", "numero"),
        CheckConstraint("numero >= 1", name="numero_positivo"),
        Index("ix_analisis_bioinformatico_id", "bioinformatico_id"),
    )


class AnalisisPatologia(Base):
    __tablename__ = "analisis_patologia"
    analisis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analisis.id", ondelete="CASCADE"), primary_key=True)
    patologia_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patologia.id", ondelete="RESTRICT"), primary_key=True)

    analisis: Mapped["Analisis"] = relationship(back_populates="patologias")
    patologia: Mapped["Patologia"] = relationship()  # noqa: F821


class AnalisisGen(Base):
    __tablename__ = "analisis_gen"
    analisis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analisis.id", ondelete="CASCADE"), primary_key=True)
    gen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gen.id", ondelete="RESTRICT"), primary_key=True)
    origen: Mapped[OrigenGen] = mapped_column(pg_enum(OrigenGen, "origen_gen"))

    analisis: Mapped["Analisis"] = relationship(back_populates="genes")
    gen: Mapped["Gen"] = relationship()


class AnalisisVariante(Base, UuidPk):
    """Variante hallada en un gen que fue pedido en ese análisis (FK compuesta a analisis_gen)."""

    __tablename__ = "analisis_variante"
    analisis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analisis.id", ondelete="CASCADE"))
    gen_id: Mapped[uuid.UUID] = mapped_column()
    variante_codigo: Mapped[str] = mapped_column(String(100))  # código del módulo 5 / ClinVar
    clasificacion: Mapped[ClasificacionVariante] = mapped_column(pg_enum(ClasificacionVariante, "clasificacion_variante"))

    analisis: Mapped["Analisis"] = relationship(back_populates="variantes")

    __table_args__ = (
        ForeignKeyConstraint(
            ["analisis_id", "gen_id"],
            ["analisis_gen.analisis_id", "analisis_gen.gen_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("analisis_id", "gen_id", "variante_codigo"),
    )
