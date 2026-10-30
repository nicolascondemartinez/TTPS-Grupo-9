"""Engine y sesión. DATABASE_URL: postgresql+psycopg2://user:pass@host:port/db

Supabase: usar el pooler (puerto 6543, modo transacción) para la app y la conexión
directa / session pooler (5432) para Alembic.
"""
import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependencia estilo FastAPI; en Flask usar `with SessionLocal() as s:`."""
    with SessionLocal() as session:
        yield session
