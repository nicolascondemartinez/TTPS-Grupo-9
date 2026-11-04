"""Base de datos del core: Base declarativa, mixins, sesión por request y reset/seed.

Sin migraciones: el esquema sale de los modelos. Si cambia un modelo, se corre
`flask --app main reset-db` y después `flask --app main seed-db`.
"""
import importlib
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from flask import current_app, g
from sqlalchemy import DateTime, MetaData, Uuid, create_engine, func, text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

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

    create_all / drop_all crean y borran el tipo (una sola vez aunque lo usen varias columnas).
    """
    return ENUM(py_enum, name=name, schema=schema, values_callable=lambda e: [m.value for m in e])


# --- Sesión por request ---

def init_db(app) -> None:
    """Cierra la sesión de la base al terminar cada request."""

    @app.teardown_appcontext
    def _cerrar_sesion(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()


def _sessionmaker() -> sessionmaker:
    ext = current_app.extensions
    if "db_sessionmaker" not in ext:
        url = current_app.config.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL no está configurada")
        engine = create_engine(url, pool_pre_ping=True)
        ext["db_engine"] = engine
        ext["db_sessionmaker"] = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return ext["db_sessionmaker"]


def get_engine():
    _sessionmaker()
    return current_app.extensions["db_engine"]


def get_db() -> Session:
    """Sesión de la base asociada al request actual."""
    if "db" not in g:
        g.db = _sessionmaker()()
    return g.db

def nueva_sesion() -> Session:
    """Sesión nueva, independiente del request (seeds, scripts, tests). Requiere app context."""
    return _sessionmaker()()


# --- Reset / seed ---

def import_all_models() -> None:
    """Importa todos los modelos para que SQLAlchemy resuelva las relaciones y create_all los vea."""
    import src.core.models  # noqa: F401


def reset_db() -> None:
    """Borra y vuelve a crear todas las tablas y tipos (destructivo)."""
    engine = get_engine()
    print("Reseteando la base...", flush=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Base reseteada.", flush=True)


def seed_db() -> None:
    """Carga los datos iniciales."""
    from src.core import seeds

    print("Cargando datos iniciales...", flush=True)
    seeds.run()
    print("Seed completo.", flush=True)