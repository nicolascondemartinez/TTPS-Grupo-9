"""Fixtures de los tests.

- `client`: la app sin base de datos (alcanza para /api/health y los errores generales).
- Los tests que usan la base (`app`, `api`, `crear_usuario`, ...) necesitan un Postgres de prueba:

      TEST_DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/ttps_test poetry run pytest

  Si TEST_DATABASE_URL no está definida, esos tests se saltean. La base se recrea sola (drop_all + 
  create_all) y se vacía antes de cada test.
"""
import os
import re

import pytest
from flask import Blueprint
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.web import create_app
from src.web.security import require_permission
from src.core.enums import RolUsuario
from src.core.models import Dispositivo, Usuario
from src.core.auth.service import huella_dispositivo
from src.core.avisos.mail_service import MemoryMailSender
from src.core.auth.password import hash_contrasena
from src.core.seeds.seed_permisos import cargar_permisos

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
DEVICE = "dispositivo-de-prueba-0123456789"
OTRO_DEVICE = "otro-dispositivo-de-prueba-987654"
CONTRASENA = "Clave-segura-1"


@pytest.fixture
def client():
    return create_app("testing").test_client()


@pytest.fixture(scope="session")
def database_url():
    if not TEST_DATABASE_URL:
        pytest.skip("Definir TEST_DATABASE_URL para correr los tests que usan la base")
    from src.core.database import Base, import_all_models

    import_all_models()
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    return TEST_DATABASE_URL

_ruta_de_prueba = Blueprint("ruta_de_prueba", __name__)


@_ruta_de_prueba.get("/_test/paciente-crear")
@require_permission("paciente_crear")
def _paciente_crear():
    return {"ok": True}


@pytest.fixture
def app(database_url):
    app = create_app("testing")
    app.config["DATABASE_URL"] = database_url
    app.extensions["mail_sender"] = MemoryMailSender()
    app.register_blueprint(_ruta_de_prueba, url_prefix="/api")
    engine = create_engine(database_url)
    with engine.begin() as conexion:
        conexion.execute(text("TRUNCATE usuario, permiso RESTART IDENTITY CASCADE"))
    with Session(engine) as session:
        cargar_permisos(session)
    engine.dispose()
    yield app
    if "db_engine" in app.extensions:
        app.extensions["db_engine"].dispose()


@pytest.fixture
def mail(app):
    return app.extensions["mail_sender"]


@pytest.fixture
def db(database_url, app):
    engine = create_engine(database_url)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def crear_usuario(db):
    def _crear(rol=RolUsuario.medico, correo="medico@exoma.test", contrasena=CONTRASENA,
               debe_cambiar=False, activo=True, dispositivo=DEVICE):
        usuario = Usuario(
            email=correo, password_hash=hash_contrasena(contrasena), nombre="Nombre", apellido="Apellido",
            telefono="1100000000", rol=rol, debe_cambiar_password=debe_cambiar, activo=activo,
        )
        db.add(usuario)
        db.flush()
        if dispositivo:  # dispositivo ya verificado: el login no pide código por mail
            db.add(Dispositivo(usuario_id=usuario.id, huella=huella_dispositivo(dispositivo)))
        db.commit()
        return usuario

    return _crear


class Api:
    """Atajos para llamar a los endpoints de autenticación en los tests."""

    def __init__(self, client):
        self.client = client

    def login(self, correo="medico@exoma.test", contrasena=CONTRASENA, device=DEVICE):
        headers = {"X-Device-Id": device} if device else {}
        return self.client.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena}, headers=headers)

    def verificar(self, desafio_id, codigo, device=DEVICE):
        return self.client.post("/api/auth/verify-device", json={"desafio_id": desafio_id, "codigo": codigo},
                                headers={"X-Device-Id": device})

    def cambiar_contrasena(self, token, actual, nueva, device=DEVICE):
        return self.client.post("/api/auth/change-password",
                                json={"contrasena_actual": actual, "contrasena_nueva": nueva},
                                headers={"Authorization": f"Bearer {token}", "X-Device-Id": device})

    def me(self, token):
        return self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    def logout(self, token):
        return self.client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    def get(self, ruta, token=None):
        return self.client.get(ruta, headers={"Authorization": f"Bearer {token}"} if token else {})

    def token(self, **kwargs):
        r = self.login(**kwargs)
        assert r.status_code == 200 and r.get_json()["estado"] == "autenticado", r.get_json()
        return r.get_json()["token"]


@pytest.fixture
def api(app):
    return Api(app.test_client())


def codigo_del_ultimo_mail(mail) -> str:
    """Extrae el código de 6 dígitos del último mail simulado."""
    return re.search(r"es: (\d{6})", mail.enviados[-1].cuerpo).group(1)
