"""Login, dispositivo nuevo, primer ingreso, cambio de contraseña y sesiones."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from src.core.enums import RolUsuario
from src.core.models import CodigoVerificacion, Sesion, Usuario

from .conftest import CONTRASENA, DEVICE, OTRO_DEVICE, codigo_del_ultimo_mail

NUEVA = "Otra-clave-2026"


# --------------------------------------------------------------------------- login
def test_login_con_dispositivo_conocido_devuelve_token_usuario_y_permisos(api, crear_usuario, db):
    crear_usuario()
    r = api.login()
    cuerpo = r.get_json()
    assert r.status_code == 200
    assert cuerpo["estado"] == "autenticado"
    assert cuerpo["usuario"]["correo"] == "medico@exoma.test"
    assert cuerpo["usuario"]["rol"] == "medico"
    assert "paciente_crear" in cuerpo["permisos"] and "cupon_crear" not in cuerpo["permisos"]
    assert "password" not in str(cuerpo).lower() and "hash" not in str(cuerpo).lower()
    # el token en claro no se guarda: solo su hash
    sesion = db.scalar(select(Sesion))
    assert sesion.token_hash != cuerpo["token"] and len(sesion.token_hash) == 64


def test_login_ignora_mayusculas_y_espacios_del_correo(api, crear_usuario):
    crear_usuario()
    assert api.login(correo="  MEDICO@Exoma.TEST ").status_code == 200


def test_correo_inexistente_y_contrasena_incorrecta_dan_el_mismo_error(api, crear_usuario):
    crear_usuario()
    a = api.login(contrasena="incorrecta-123")
    b = api.login(correo="nadie@exoma.test")
    assert a.status_code == b.status_code == 401
    assert a.get_json() == b.get_json()
    assert a.get_json()["error"]["codigo"] == "CREDENCIALES_INVALIDAS"


def test_usuario_inactivo_recibe_mensaje_claro_solo_con_la_contrasena_correcta(api, crear_usuario):
    crear_usuario(activo=False)
    ok = api.login()
    assert ok.status_code == 403 and ok.get_json()["error"]["codigo"] == "CUENTA_INACTIVA"
    mala = api.login(contrasena="incorrecta-123")
    assert mala.status_code == 401  # no se revela que la cuenta existe


def test_login_valida_los_datos_de_entrada(api, client):
    r = api.client.post("/api/auth/login", json={}, headers={"X-Device-Id": DEVICE})
    campos = {c["campo"] for c in r.get_json()["error"]["detalle"]["campos"]}
    assert r.status_code == 400 and campos == {"correo", "contrasena"}
    r = api.login(correo="no-es-un-correo")
    assert r.status_code == 400 and r.get_json()["error"]["detalle"]["campos"][0]["campo"] == "correo"
    r = api.client.post("/api/auth/login", data="no es json", headers={"X-Device-Id": DEVICE})
    assert r.status_code == 400 and r.get_json()["error"]["codigo"] == "VALIDACION"


def test_login_exige_el_identificador_de_dispositivo(api, crear_usuario):
    crear_usuario()
    r = api.login(device=None)
    assert r.status_code == 400
    assert r.get_json()["error"]["detalle"]["campos"][0]["campo"] == "X-Device-Id"
    assert api.login(device="corto").status_code == 400


# --------------------------------------------------------------------------- dispositivo nuevo
def test_dispositivo_nuevo_pide_codigo_por_mail_y_no_da_token(api, crear_usuario, mail):
    crear_usuario(dispositivo=None)
    r = api.login()
    cuerpo = r.get_json()
    assert r.status_code == 200 and cuerpo["estado"] == "verificacion_requerida"
    assert "token" not in cuerpo and cuerpo["desafio_id"]
    assert cuerpo["correo"].startswith("me") and "*" in cuerpo["correo"]  # correo enmascarado
    assert len(mail.enviados) == 1 and mail.enviados[0].destino == "medico@exoma.test"
    assert len(codigo_del_ultimo_mail(mail)) == 6


def test_con_el_codigo_correcto_entra_y_el_dispositivo_queda_registrado(api, crear_usuario, mail):
    crear_usuario(dispositivo=None)
    desafio = api.login().get_json()["desafio_id"]
    r = api.verificar(desafio, codigo_del_ultimo_mail(mail))
    assert r.status_code == 200 and r.get_json()["estado"] == "autenticado" and r.get_json()["token"]
    # la próxima vez, desde el mismo dispositivo, no pide código
    otra = api.login().get_json()
    assert otra["estado"] == "autenticado" and len(mail.enviados) == 1
    # desde otro dispositivo sí
    assert api.login(device=OTRO_DEVICE).get_json()["estado"] == "verificacion_requerida"


def test_el_codigo_se_guarda_con_hash(api, crear_usuario, mail, db):
    crear_usuario(dispositivo=None)
    api.login()
    guardado = db.scalar(select(CodigoVerificacion)).codigo_hash
    assert codigo_del_ultimo_mail(mail) not in guardado and len(guardado) == 64


def test_codigo_incorrecto_informa_los_intentos_restantes(api, crear_usuario, mail):
    crear_usuario(dispositivo=None)
    desafio = api.login().get_json()["desafio_id"]
    codigo = codigo_del_ultimo_mail(mail)
    mal = "000000" if codigo != "000000" else "111111"
    for esperado in (4, 3):
        r = api.verificar(desafio, mal)
        assert r.status_code == 401
        assert r.get_json()["error"]["codigo"] == "CODIGO_INCORRECTO"
        assert r.get_json()["error"]["detalle"]["intentos_restantes"] == esperado
    assert api.verificar(desafio, codigo).status_code == 200  # el correcto sigue funcionando


def test_cinco_codigos_incorrectos_agotan_el_desafio(api, crear_usuario, mail):
    crear_usuario(dispositivo=None)
    desafio = api.login().get_json()["desafio_id"]
    codigo = codigo_del_ultimo_mail(mail)
    mal = "000000" if codigo != "000000" else "111111"
    codigos = [api.verificar(desafio, mal).get_json()["error"]["codigo"] for _ in range(5)]
    assert codigos == ["CODIGO_INCORRECTO"] * 4 + ["DESAFIO_AGOTADO"]
    # ya ni el código correcto sirve: hay que volver a ingresar
    r = api.verificar(desafio, codigo)
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "DESAFIO_INVALIDO"


def test_codigo_vencido(api, crear_usuario, mail, db):
    crear_usuario(dispositivo=None)
    desafio = api.login().get_json()["desafio_id"]
    db.execute(update(CodigoVerificacion).values(expira_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    db.commit()
    r = api.verificar(desafio, codigo_del_ultimo_mail(mail))
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "CODIGO_VENCIDO"


def test_el_codigo_solo_vale_para_el_dispositivo_que_lo_pidio_y_una_sola_vez(api, crear_usuario, mail):
    crear_usuario(dispositivo=None)
    desafio = api.login().get_json()["desafio_id"]
    codigo = codigo_del_ultimo_mail(mail)
    r = api.verificar(desafio, codigo, device=OTRO_DEVICE)
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "DESAFIO_INVALIDO"
    assert api.verificar(desafio, codigo).status_code == 200
    r = api.verificar(desafio, codigo)  # reutilizar
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "DESAFIO_INVALIDO"


def test_un_nuevo_login_invalida_el_codigo_anterior(api, crear_usuario, mail):
    crear_usuario(dispositivo=None)
    primero = api.login().get_json()["desafio_id"]
    codigo1 = codigo_del_ultimo_mail(mail)
    segundo = api.login().get_json()["desafio_id"]
    codigo2 = codigo_del_ultimo_mail(mail)
    assert api.verificar(primero, codigo1).get_json()["error"]["codigo"] == "DESAFIO_INVALIDO"
    assert api.verificar(segundo, codigo2).status_code == 200


def test_verificacion_valida_la_entrada(api):
    r = api.client.post("/api/auth/verify-device", json={"desafio_id": "", "codigo": "12"}, headers={"X-Device-Id": DEVICE})
    campos = {c["campo"] for c in r.get_json()["error"]["detalle"]["campos"]}
    assert r.status_code == 400 and campos == {"desafio_id", "codigo"}
    assert api.verificar("no-es-uuid", "123456").get_json()["error"]["codigo"] == "DESAFIO_INVALIDO"


def test_si_falla_el_envio_del_mail_responde_503(api, crear_usuario, app):
    crear_usuario(dispositivo=None)

    class MailRoto:
        def send(self, *a):
            raise OSError("SMTP caído")

    app.extensions["mail_sender"] = MailRoto()
    r = api.login()
    assert r.status_code == 503 and r.get_json()["error"]["codigo"] == "MAIL_NO_DISPONIBLE"
    assert "SMTP" not in str(r.get_json())


# --------------------------------------------------------------------------- primer ingreso
def test_primer_ingreso_da_un_token_limitado_sin_pedir_codigo(api, crear_usuario, mail):
    crear_usuario(rol=RolUsuario.paciente, correo="paciente@exoma.test", debe_cambiar=True, dispositivo=None)
    r = api.login(correo="paciente@exoma.test")
    cuerpo = r.get_json()
    assert r.status_code == 200 and cuerpo["estado"] == "cambio_contrasena_requerido" and cuerpo["token"]
    assert mail.enviados == []  # el cliente pidió que en el primer ingreso alcance con cambiar la contraseña
    token = cuerpo["token"]
    me = api.me(token).get_json()
    assert me["estado"] == "cambio_contrasena_requerido" and me["permisos"] == []
    # con el token limitado no se puede usar el resto de la API
    r = api.get("/api/_test/paciente-crear", token)
    assert r.status_code == 403 and r.get_json()["error"]["codigo"] == "CAMBIO_CONTRASENA_REQUERIDO"


def test_cambio_de_contrasena_del_primer_ingreso(api, crear_usuario, mail, db):
    crear_usuario(rol=RolUsuario.paciente, correo="paciente@exoma.test", debe_cambiar=True, dispositivo=None)
    limitado = api.login(correo="paciente@exoma.test").get_json()["token"]
    r = api.cambiar_contrasena(limitado, CONTRASENA, NUEVA)
    cuerpo = r.get_json()
    assert r.status_code == 200 and cuerpo["estado"] == "autenticado" and cuerpo["token"] != limitado
    assert "aviso_listar" in cuerpo["permisos"]
    # el token limitado quedó revocado y el nuevo funciona
    assert api.me(limitado).get_json()["error"]["codigo"] == "TOKEN_INVALIDO"
    assert api.me(cuerpo["token"]).status_code == 200
    assert db.scalar(select(Usuario.debe_cambiar_password).where(Usuario.email == "paciente@exoma.test")) is False
    # con la contraseña nueva entra directo (el dispositivo quedó registrado) y con la vieja no
    assert api.login(correo="paciente@exoma.test", contrasena=NUEVA).get_json()["estado"] == "autenticado"
    assert api.login(correo="paciente@exoma.test").status_code == 401
    assert mail.enviados == []


def test_cambio_de_contrasena_rechaza_datos_invalidos_sin_usar_401(api, crear_usuario):
    crear_usuario()
    token = api.token()
    mal = api.cambiar_contrasena(token, "no-es-la-actual", NUEVA)
    # 400 y no 401: un 401 con token hace que el frontend cierre la sesión
    assert mal.status_code == 400 and mal.get_json()["error"]["codigo"] == "CONTRASENA_ACTUAL_INCORRECTA"
    for nueva in ("corta", CONTRASENA, "medico@exoma.test"):
        r = api.cambiar_contrasena(token, CONTRASENA, nueva)
        assert r.status_code == 400 and r.get_json()["error"]["codigo"] == "VALIDACION", nueva
    assert api.me(token).status_code == 200  # la sesión sigue viva


def test_cambiar_la_contrasena_cierra_las_demas_sesiones(api, crear_usuario):
    crear_usuario()
    a, b = api.token(), api.token()
    assert api.cambiar_contrasena(a, CONTRASENA, NUEVA).status_code == 200
    assert api.me(a).status_code == 401 and api.me(b).status_code == 401


# --------------------------------------------------------------------------- sesiones
def test_logout_revoca_el_token(api, crear_usuario):
    crear_usuario()
    token = api.token()
    assert api.logout(token).status_code == 204
    r = api.me(token)
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "TOKEN_INVALIDO"


def test_token_ausente_invalido_o_vencido_da_401_sin_evaluar_nada_mas(api, crear_usuario, db):
    crear_usuario()
    assert api.get("/api/auth/me").get_json()["error"]["codigo"] == "TOKEN_AUSENTE"
    assert api.me("token-inventado").get_json()["error"]["codigo"] == "TOKEN_INVALIDO"
    r = api.client.get("/api/auth/me", headers={"Authorization": "Token abc"})
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "TOKEN_AUSENTE"
    token = api.token()
    db.execute(update(Sesion).values(expira_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    db.commit()
    r = api.me(token)
    assert r.status_code == 401 and r.get_json()["error"]["codigo"] == "TOKEN_EXPIRADO"


def test_el_token_dura_8_horas(api, crear_usuario, db):
    crear_usuario()
    api.token()
    sesion = db.scalar(select(Sesion))
    duracion = sesion.expira_at - sesion.creada_at
    assert timedelta(hours=7, minutes=59) < duracion < timedelta(hours=8, minutes=1)


def test_si_se_desactiva_al_usuario_pierde_la_sesion(api, crear_usuario, db):
    crear_usuario()
    token = api.token()
    db.execute(update(Usuario).values(activo=False))
    db.commit()
    assert api.me(token).status_code == 401


def test_me_devuelve_el_usuario_y_sus_permisos(api, crear_usuario):
    crear_usuario(rol=RolUsuario.transportista, correo="t@exoma.test")
    cuerpo = api.me(api.token(correo="t@exoma.test")).get_json()
    assert cuerpo["usuario"]["rol"] == "transportista"
    assert cuerpo["permisos"] == ["aviso_listar", "orden_dia_entregar", "orden_dia_recoger", "orden_dia_ver"]
