"""Estado de la API (lo usa el deploy para saber si está viva)."""
from flask import Blueprint

from app.views.health_view import health_view

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return health_view()
