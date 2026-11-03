"""Piezas que no necesitan base de datos: contraseñas, mails, validaciones y formato de errores."""
import logging
import smtplib

import pytest

from app.errors import ApiError
from app.services import password_service
from app.services.mail_service import (
    ConsoleMailSender, MemoryMailSender, SmtpMailSender, crear_mail_sender, enviar_codigo_verificacion,
)
from app.services.validation import validar_cambio_contrasena, validar_login, validar_verificacion


def test_las_contrasenas_se_guardan_con_argon2id():
    h = password_service.hash_contrasena("Clave-segura-1")
    assert h.startswith("$argon2id$") and "Clave-segura-1" not in h
    assert h != password_service.hash_contrasena("Clave-segura-1")  # sal distinta cada vez
    assert password_service.verificar_contrasena(h, "Clave-segura-1")
    assert not password_service.verificar_contrasena(h, "otra")
    assert not password_service.verificar_contrasena("no-es-un-hash", "x")


def test_mail_simulado_escribe_en_el_log(caplog):
    with caplog.at_level(logging.INFO):
        enviar_codigo_verificacion(ConsoleMailSender(), "a@b.com", "123456", 10)
    assert "123456" in caplog.text and "a@b.com" in caplog.text


def test_mail_en_memoria_guarda_lo_enviado():
    m = MemoryMailSender()
    enviar_codigo_verificacion(m, "a@b.com", "654321", 10)
    assert m.enviados[0].destino == "a@b.com" and "654321" in m.enviados[0].cuerpo and "10 minutos" in m.enviados[0].cuerpo


def test_mail_smtp_arma_y_envia_el_mensaje(monkeypatch):
    llamadas = []

    class SmtpFalso:
        def __init__(self, host, port, timeout):
            llamadas.append(("conectar", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            llamadas.append(("starttls",))

        def login(self, user, password):
            llamadas.append(("login", user, password))

        def send_message(self, mensaje):
            llamadas.append(("enviar", mensaje["To"], mensaje["From"], mensaje["Subject"], mensaje.get_content()))

    monkeypatch.setattr(smtplib, "SMTP", SmtpFalso)
    SmtpMailSender("smtp.test", 587, "user", "clave", "from@exoma.test").send("to@x.com", "Asunto", "Cuerpo")
    assert llamadas[0] == ("conectar", "smtp.test", 587) and ("starttls",) in llamadas and ("login", "user", "clave") in llamadas
    assert llamadas[-1][1:4] == ("to@x.com", "from@exoma.test", "Asunto") and "Cuerpo" in llamadas[-1][4]


def test_la_configuracion_de_mails_se_valida():
    base = {"MAIL_FROM": "x", "SMTP_HOST": "", "SMTP_PORT": 587, "SMTP_USER": "", "SMTP_PASSWORD": "", "SMTP_USE_TLS": True}
    assert isinstance(crear_mail_sender({**base, "MAIL_MODE": "console"}), ConsoleMailSender)
    with pytest.raises(RuntimeError):
        crear_mail_sender({**base, "MAIL_MODE": "smtp"})  # falta SMTP_HOST
    with pytest.raises(RuntimeError):
        crear_mail_sender({**base, "MAIL_MODE": "paloma"})


def test_validaciones_de_entrada():
    assert validar_login({"correo": " A@B.com ", "contrasena": "x"}) == ("a@b.com", "x")
    with pytest.raises(ApiError) as e:
        validar_login(None)
    assert e.value.status == 400
    assert validar_verificacion({"desafio_id": "abc", "codigo": "123456"}) == ("abc", "123456")
    for codigo in ("12345", "1234567", "abcdef", 123456, None):
        with pytest.raises(ApiError):
            validar_verificacion({"desafio_id": "abc", "codigo": codigo})
    assert validar_cambio_contrasena({"contrasena_actual": "a", "contrasena_nueva": "Nueva-clave-1"}, "x@y.com")[1] == "Nueva-clave-1"


def test_errores_generales_tienen_el_formato_de_la_api(client):
    r = client.get("/api/no-existe")
    assert r.status_code == 404
    assert r.get_json()["error"]["codigo"] == "NO_ENCONTRADO" and r.get_json()["error"]["detalle"] == {}
    r = client.post("/api/health")
    assert r.status_code == 405 and r.get_json()["error"]["codigo"] == "METODO_NO_PERMITIDO"
