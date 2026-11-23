"""Archivos guardados por el servicio de almacenamiento (ver service.py)."""
from sqlalchemy import Integer, LargeBinary, String

from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, CreatedAt, UuidPk


class Archivo(Base, UuidPk, CreatedAt):
    """Contenido de un archivo (familiograma, PDF, CSV...). Los modelos guardan solo su ruta ("db/<id>")."""

    __tablename__ = "archivo"
    nombre: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(100))  # media type, ej. image/svg+xml
    tamano: Mapped[int] = mapped_column(Integer)  # bytes
    contenido: Mapped[bytes] = mapped_column(LargeBinary)
