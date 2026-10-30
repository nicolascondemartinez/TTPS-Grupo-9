"""Controladores (la C de MVC). Un archivo por área, cada uno con su blueprint.

Para agregar uno: crear app/controllers/<area>_controller.py con `bp = Blueprint("<area>", __name__)`
y sumarlo a CONTROLLERS. Todas las rutas quedan bajo /api.
"""
from app.controllers import health_controller

CONTROLLERS = [
    health_controller,
]


def register_controllers(app):
    for controller in CONTROLLERS:
        app.register_blueprint(controller.bp, url_prefix="/api")
