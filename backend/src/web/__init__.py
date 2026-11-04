def create_app(config_name: str | None = None):
    from dotenv import load_dotenv
    load_dotenv()

    from flask import Flask
    from flask_cors import CORS

    from src.config import get_config
    from src.web.controllers import register_controllers
    from src.core.database import init_db, import_all_models
    from src.core.common.errors import register_error_handlers
    from src.core.avisos.mail_service import init_mail

    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    CORS(app, origins=[app.config["FRONTEND_URL"]], supports_credentials=True)
    import_all_models()
    init_db(app)
    init_mail(app)
    register_error_handlers(app)
    register_controllers(app)

    @app.cli.command("reset-db")
    def _reset_db():
        from src.core.database import reset_db
        reset_db()

    @app.cli.command("seed-db")
    def _seed_db():
        from src.core.database import seed_db
        seed_db()

    return app