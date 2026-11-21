"""Controladores (la C de MVC). Un archivo por área, cada uno con su blueprint.

Para agregar uno: crear src/web/controllers/<area>.py con `bp = Blueprint("<area>", __name__)`
y sumarlo a CONTROLLERS. Todas las rutas quedan bajo /api.
"""
from src.web.controllers import auth, avisos, health, historia_clinica, pacientes, pagos, patologias, sintomas, turnos

CONTROLLERS = [
    health,
    auth,
    avisos,
    sintomas,
    patologias,
    historia_clinica,
    pacientes,
    pagos,
    turnos,
]


def register_controllers(app):
    for controller in CONTROLLERS:
        app.register_blueprint(controller.bp, url_prefix="/api")