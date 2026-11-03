"""Sesión de SQLAlchemy por request para Flask.

El motor se crea la primera vez que se pide una sesión (no al crear la app), así los tests
que no usan la base (por ejemplo /api/health) no necesitan DATABASE_URL.
"""
from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


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


def get_db() -> Session:
    """Sesión de la base asociada al request actual."""
    if "db" not in g:
        g.db = _sessionmaker()()
    return g.db
