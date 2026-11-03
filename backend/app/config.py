"""Configuración por entorno. Los valores salen de variables de entorno (ver .env.example)."""
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambiar-en-produccion")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    ADAPTERS_MODE = os.environ.get("ADAPTERS_MODE", "mock")  # mock | real
    TIMEZONE = "America/Argentina/Buenos_Aires"

    # --- Autenticación ---
    SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "8"))
    LIMITED_SESSION_TTL_MINUTES = int(os.environ.get("LIMITED_SESSION_TTL_MINUTES", "30"))
    VERIFICATION_CODE_TTL_MINUTES = int(os.environ.get("VERIFICATION_CODE_TTL_MINUTES", "10"))
    VERIFICATION_CODE_MAX_ATTEMPTS = int(os.environ.get("VERIFICATION_CODE_MAX_ATTEMPTS", "5"))

    # --- Mails: "console" (simulado: escribe en el log) | "smtp" ---
    MAIL_MODE = os.environ.get("MAIL_MODE", "console")
    MAIL_FROM = os.environ.get("MAIL_FROM", "no-responder@exoma.local")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


_CONFIGS = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}


def get_config(name: str | None):
    return _CONFIGS[name or os.environ.get("FLASK_ENV", "development")]
