"""Aplicación Flask del core (API REST que consume el frontend en React).

Capas (MVC):
- Modelo:       app/db/models/   (SQLAlchemy, tablas y migraciones con Alembic)
- Vista:        app/views/       (arman el JSON que devuelve cada endpoint)
- Controlador:  app/controllers/ (rutas: reciben el request, validan permisos y llaman a los servicios)
- Servicios:    app/services/    (reglas de negocio, testeables sin HTTP)

Los imports de Flask van dentro de create_app para que Alembic pueda importar
app.db.models sin levantar la aplicación.
"""


def create_app(config_name: str | None = None):
    from dotenv import load_dotenv

    # El .env se carga antes de importar la configuración: ahí se leen las variables de entorno.
    load_dotenv()

    from flask import Flask
    from flask_cors import CORS

    from app.config import get_config
    from app.controllers import register_controllers
    from app.db.flask_db import init_db
    from app.errors import register_error_handlers
    from app.services.mail_service import init_mail

    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    CORS(app, origins=[app.config["FRONTEND_URL"]], supports_credentials=True)
    init_db(app)
    init_mail(app)
    register_error_handlers(app)
    register_controllers(app)
    return app
