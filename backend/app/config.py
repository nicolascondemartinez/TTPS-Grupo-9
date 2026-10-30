"""Configuración por entorno. Los valores salen de variables de entorno (ver .env.example)."""
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambiar-en-produccion")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    ADAPTERS_MODE = os.environ.get("ADAPTERS_MODE", "mock")  # mock | real
    TIMEZONE = "America/Argentina/Buenos_Aires"


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


_CONFIGS = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}


def get_config(name: str | None):
    return _CONFIGS[name or os.environ.get("FLASK_ENV", "development")]
