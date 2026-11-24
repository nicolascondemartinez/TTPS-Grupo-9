"""Alta de transportistas por el administrativo, y sus listados."""
import re

import pytest
from sqlalchemy import func, select

from src.core.avisos.mail_service import MemoryMailSender
from src.core.enums import RolUsuario
from src.core.models import Provincia, Transportista, Usuario

CORREO = "tomas.ruiz@exoma.test"


@pytest.fixture
def provincias(db):
    lista = [Provincia(nombre="Buenos Aires"), Provincia(nombre="Córdoba"), Provincia(nombre="Formosa")]
    db.add_all(lista)
    db.commit()
    return lista


@pytest.fixture
def admin(api, crear_usuario):
    crear_usuario(rol=RolUsuario.administrativo, correo="admin@exoma.test")
    return api.token(correo="admin@exoma.test")


def datos(provincia, **cambios):
    cuerpo = {
        "nombre": "Tomás", "apellido": "Ruiz", "telefono": "+54 11 4000-0000",
        "correo": "Tomas.Ruiz@Exoma.test", "provincia_id": str(provincia.id),
    }
    cuerpo.update(cambios)
    return cuerpo


def alta(api, token, cuerpo):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return api.client.post("/api/transportistas", json=cuerpo, headers=headers)


def campos_con_error(respuesta) -> set[str]:
    return {c["campo"] for c in respuesta.get_json()["error"]["detalle"]["campos"]}


def test_el_administrativo_da_de_alta_un_transportista_y_le_llegan_las_credenciales(api, db, mail, admin, provincias):
    r = alta(api, admin, datos(provincias[0]))
    cuerpo = r.get_json()
    assert r.status_code == 201
    assert cuerpo["correo"] == CORREO and cuerpo["provincia"]["nombre"] == "Buenos Aires"

    usuario = db.scalar(select(Usuario).where(Usuario.email == CORREO))
    assert usuario.rol == RolUsuario.transportista and usuario.debe_cambiar_password and usuario.activo
    assert db.get(Transportista, usuario.id).provincia_id == provincias[0].id

    assert len(mail.enviados) == 1 and mail.enviados[0].destino == CORREO
    temporal = re.search(r"Contraseña temporal: (\S+)", mail.enviados[0].cuerpo).group(1)
    assert temporal not in str(cuerpo) and usuario.password_hash != temporal  # solo viaja por mail y se guarda con hash

    # con esa contraseña entra, pero solo para cambiarla (primer ingreso)
    r = api.login(correo=CORREO, contrasena=temporal)
    assert r.status_code == 200 and r.get_json()["estado"] == "cambio_contrasena_requerido"


def test_una_provincia_solo_puede_tener_un_transportista(api, db, mail, admin, provincias):
    assert alta(api, admin, datos(provincias[0])).status_code == 201
    r = alta(api, admin, datos(provincias[0], correo="otro@exoma.test"))
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "PROVINCIA_OCUPADA"
    assert campos_con_error(r) == {"provincia_id"}
    assert db.scalar(select(func.count()).select_from(Transportista)) == 1
    assert len(mail.enviados) == 1  # al rechazado no se le manda nada
    assert alta(api, admin, datos(provincias[1], correo="otro@exoma.test")).status_code == 201


def test_correo_ya_registrado(api, mail, admin, provincias):
    r = alta(api, admin, datos(provincias[0], correo="ADMIN@exoma.test"))
    assert r.status_code == 409 and r.get_json()["error"]["codigo"] == "CORREO_DUPLICADO"
    assert campos_con_error(r) == {"correo"} and mail.enviados == []


def test_valida_los_datos(api, admin, provincias):
    r = alta(api, admin, {})
    assert r.status_code == 400 and r.get_json()["error"]["codigo"] == "VALIDACION"
    assert campos_con_error(r) == {"nombre", "apellido", "telefono", "correo", "provincia_id"}
    r = alta(api, admin, datos(provincias[0], provincia_id="no-es-uuid"))
    assert r.status_code == 400 and campos_con_error(r) == {"provincia_id"}
    r = alta(api, admin, datos(provincias[0], provincia_id="00000000-0000-4000-8000-000000000000"))
    assert r.status_code == 400 and campos_con_error(r) == {"provincia_id"}
    r = alta(api, admin, datos(provincias[0], correo="no-es-un-correo", telefono="abc"))
    assert r.status_code == 400 and campos_con_error(r) == {"correo", "telefono"}


def test_si_falla_el_mail_no_se_crea_el_transportista(api, db, app, admin, provincias):
    class MailRoto:
        def send(self, *a):
            raise OSError("SMTP caído")

    app.extensions["mail_sender"] = MailRoto()
    r = alta(api, admin, datos(provincias[0]))
    assert r.status_code == 503 and r.get_json()["error"]["codigo"] == "MAIL_NO_DISPONIBLE"
    assert "SMTP" not in str(r.get_json())
    assert db.scalar(select(func.count()).select_from(Transportista)) == 0
    assert db.scalar(select(Usuario.id).where(Usuario.email == CORREO)) is None
    # la provincia y el correo siguen libres: con el mail funcionando, el alta se puede repetir
    app.extensions["mail_sender"] = MemoryMailSender()
    assert alta(api, admin, datos(provincias[0])).status_code == 201


@pytest.mark.parametrize("metodo, ruta", [("get", "/api/provincias"), ("get", "/api/transportistas"), ("post", "/api/transportistas")])
def test_solo_el_administrativo_puede_usar_estos_endpoints(api, crear_usuario, metodo, ruta):
    sin_token = getattr(api.client, metodo)(ruta)
    assert sin_token.status_code == 401 and sin_token.get_json()["error"]["codigo"] == "TOKEN_AUSENTE"
    crear_usuario(rol=RolUsuario.medico, correo="medico@exoma.test")
    token = api.token(correo="medico@exoma.test")
    r = getattr(api.client, metodo)(ruta, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403 and r.get_json()["error"]["codigo"] == "PERMISO_DENEGADO"


def test_lista_los_transportistas_por_provincia_y_marca_las_provincias_ocupadas(api, admin, provincias):
    alta(api, admin, datos(provincias[1]))  # Córdoba
    alta(api, admin, datos(provincias[0], correo="otro@exoma.test"))  # Buenos Aires
    lista = api.get("/api/transportistas", admin).get_json()["transportistas"]
    assert [t["provincia"]["nombre"] for t in lista] == ["Buenos Aires", "Córdoba"]
    assert set(lista[0]) == {"id", "nombre", "apellido", "correo", "telefono", "activo", "provincia"}

    ocupadas = api.get("/api/provincias", admin).get_json()["provincias"]
    assert {p["nombre"]: p["tiene_transportista"] for p in ocupadas} == {
        "Buenos Aires": True, "Córdoba": True, "Formosa": False,
    }