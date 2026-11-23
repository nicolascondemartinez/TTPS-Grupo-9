from src.core.avisos import service as avisos
from src.core.enums import TipoAviso


def _crear_aviso(db, usuario, **kwargs):
    aviso = avisos.notificar(db, usuario, TipoAviso.resultado_disponible, "Resultado", "Ya está tu informe", **kwargs)
    db.commit()
    return aviso


def test_lista_solo_los_avisos_propios(api, crear_usuario, db):
    yo = crear_usuario(correo="yo@exoma.test")
    otro = crear_usuario(correo="otro@exoma.test")
    _crear_aviso(db, yo)
    _crear_aviso(db, otro)
    respuesta = api.get("/api/avisos", api.token(correo="yo@exoma.test"))
    assert respuesta.status_code == 200
    assert len(respuesta.get_json()["avisos"]) == 1


def test_sin_token_responde_401(api):
    assert api.get("/api/avisos").status_code == 401


def test_marcar_leido_baja_el_contador_y_no_toca_avisos_ajenos(api, crear_usuario, db):
    yo = crear_usuario(correo="yo@exoma.test")
    otro = crear_usuario(correo="otro@exoma.test")
    mio, ajeno = _crear_aviso(db, yo), _crear_aviso(db, otro)
    token = api.token(correo="yo@exoma.test")
    headers = {"Authorization": f"Bearer {token}"}

    assert api.get("/api/avisos/pendientes/cantidad", token).get_json()["cantidad"] == 1
    assert api.client.post(f"/api/avisos/{ajeno.id}/leido", headers=headers).status_code == 404
    assert api.client.post(f"/api/avisos/{mio.id}/leido", headers=headers).status_code == 200
    assert api.get("/api/avisos/pendientes/cantidad", token).get_json()["cantidad"] == 0


def test_notificar_manda_el_mail(crear_usuario, db, mail):
    usuario = crear_usuario()
    _crear_aviso(db, usuario, mail=mail)
    assert mail.enviados[0].destino == usuario.email


def test_un_mail_que_falla_no_impide_guardar_el_aviso(crear_usuario, db):
    class MailRoto:
        def send(self, *args):
            raise RuntimeError("SMTP caído")

    aviso = _crear_aviso(db, crear_usuario(), mail=MailRoto())
    assert aviso.id is not None