"""Alembic del módulo 6. Maneja SOLO el schema `obras_sociales`; la tabla de versiones también vive ahí,
así no se mezcla con la del core (public.alembic_version)."""
import os

from alembic import context
from sqlalchemy import create_engine, pool, text

import app.db.models  # noqa: F401
from app.db.base import SCHEMA, Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Definí DATABASE_URL (postgresql+psycopg2://...)")
    return url


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == SCHEMA
    return True


_opts = dict(
    target_metadata=target_metadata,
    include_schemas=True,
    include_name=include_name,
    version_table_schema=SCHEMA,
    compare_type=True,
)


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, **_opts)
    with context.begin_transaction():
        context.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()
        context.configure(connection=connection, **_opts)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
