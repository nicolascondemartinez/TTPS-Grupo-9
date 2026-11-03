"""Permisos modulo_accion por rol y decoradores de seguridad."""
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.enums import RolUsuario
from app.db.models import Permiso, RolPermiso
from seeds.seed_permisos import PERMISOS_POR_ROL, cargar_permisos

from .conftest import DEVICE


def test_require_permission_deja_pasar_al_rol_que_lo_tiene(api, crear_usuario):
    crear_usuario(rol=RolUsuario.medico)
    r = api.get("/api/_test/paciente-crear", api.token())
    assert r.status_code == 200 and r.get_json() == {"ok": True}


def test_require_permission_rechaza_con_403_a_otro_rol(api, crear_usuario):
    crear_usuario(rol=RolUsuario.gerente_medico, correo="g@exoma.test")
    r = api.get("/api/_test/paciente-crear", api.token(correo="g@exoma.test"))
    assert r.status_code == 403
    assert r.get_json()["error"] == {
        "codigo": "PERMISO_DENEGADO", "mensaje": "No tenés permiso para realizar esta acción",
        "detalle": {"permiso": "paciente_crear"},
    }


def test_sin_token_el_401_se_resuelve_antes_que_el_permiso(api):
    r = api.get("/api/_test/paciente-crear")
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "TOKEN_AUSENTE"
    assert api.get("/api/_test/paciente-crear", "basura").status_code == 401


def test_los_permisos_nuevos_se_aplican_sin_reiniciar(api, crear_usuario, db):
    crear_usuario(rol=RolUsuario.transportista, correo="t@exoma.test")
    token = api.token(correo="t@exoma.test")
    assert api.get("/api/_test/paciente-crear", token).status_code == 403
    permiso = db.scalar(select(Permiso).where(Permiso.nombre == "paciente_crear"))
    db.add(RolPermiso(rol=RolUsuario.transportista, permiso_id=permiso.id))
    db.commit()
    assert api.get("/api/_test/paciente-crear", token).status_code == 200


def test_la_matriz_inicial_es_coherente():
    nombre_valido = re.compile(r"^[a-z]+(_[a-z]+)+$")  # patrón modulo_accion
    assert set(PERMISOS_POR_ROL) == set(RolUsuario)
    for rol, permisos in PERMISOS_POR_ROL.items():
        assert len(permisos) == len(set(permisos)), f"permisos repetidos en {rol}"
        assert "aviso_listar" in permisos, f"{rol} debería poder ver sus avisos"
        assert all(nombre_valido.match(p) for p in permisos), rol


def test_el_seed_de_permisos_se_puede_repetir(database_url, app, db):
    antes = db.scalar(select(func.count()).select_from(RolPermiso))
    with Session(db.get_bind()) as otra:
        cargar_permisos(otra)
        cargar_permisos(otra)
    assert db.scalar(select(func.count()).select_from(RolPermiso)) == antes == sum(len(v) for v in PERMISOS_POR_ROL.values())
