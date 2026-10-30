"""Punto de entrada: `flask run` en desarrollo (puerto 5001, ver .flaskenv), `gunicorn wsgi:app` en producción."""
from app import create_app

app = create_app()
