"""Envío de mails detrás de una interfaz, para cambiar la implementación por configuración.

- ConsoleMailSender: simulado, escribe el mail en el log (MAIL_MODE=console, valor por defecto).
- SmtpMailSender: envío real por SMTP (MAIL_MODE=smtp).
- MemoryMailSender: guarda los mails en una lista (lo usan los tests).
"""
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

logger = logging.getLogger(__name__)


class MailSender(Protocol):
    def send(self, destino: str, asunto: str, cuerpo: str) -> None: ...


class ConsoleMailSender:
    def send(self, destino: str, asunto: str, cuerpo: str) -> None:
        # WARNING y no INFO: es el nivel que se ve por defecto en la consola de Flask y de gunicorn,
        # y el mail simulado tiene que verse para poder copiar el código de verificación.
        logger.warning("[MAIL SIMULADO] Para: %s | Asunto: %s\n%s", destino, asunto, cuerpo)


@dataclass
class MailEnviado:
    destino: str
    asunto: str
    cuerpo: str


class MemoryMailSender:
    def __init__(self) -> None:
        self.enviados: list[MailEnviado] = []

    def send(self, destino: str, asunto: str, cuerpo: str) -> None:
        self.enviados.append(MailEnviado(destino, asunto, cuerpo))


class SmtpMailSender:
    def __init__(self, host: str, port: int, user: str, password: str, remitente: str, usar_tls: bool = True):
        self.host, self.port, self.user, self.password = host, port, user, password
        self.remitente, self.usar_tls = remitente, usar_tls

    def send(self, destino: str, asunto: str, cuerpo: str) -> None:
        mensaje = EmailMessage()
        mensaje["From"], mensaje["To"], mensaje["Subject"] = self.remitente, destino, asunto
        mensaje.set_content(cuerpo)
        with smtplib.SMTP(self.host, self.port, timeout=15) as servidor:
            if self.usar_tls:
                servidor.starttls()
            if self.user:
                servidor.login(self.user, self.password)
            servidor.send_message(mensaje)


def crear_mail_sender(config) -> MailSender:
    modo = config.get("MAIL_MODE", "console")
    if modo == "smtp":
        if not config.get("SMTP_HOST"):
            raise RuntimeError("MAIL_MODE=smtp requiere SMTP_HOST")
        return SmtpMailSender(
            config["SMTP_HOST"], config["SMTP_PORT"], config["SMTP_USER"], config["SMTP_PASSWORD"],
            config["MAIL_FROM"], config["SMTP_USE_TLS"],
        )
    if modo != "console":
        raise RuntimeError(f"MAIL_MODE inválido: {modo!r} (console | smtp)")
    logger.warning("MAIL_MODE=console: los mails se escriben en el log (no usar en producción)")
    return ConsoleMailSender()


def init_mail(app) -> None:
    app.extensions["mail_sender"] = crear_mail_sender(app.config)


def get_mail_sender() -> MailSender:
    from flask import current_app

    return current_app.extensions["mail_sender"]


def enviar_codigo_verificacion(sender: MailSender, destino: str, codigo: str, minutos: int) -> None:
    sender.send(
        destino,
        "Código de verificación de ingreso",
        f"Tu código de verificación es: {codigo}\n\n"
        f"Es válido por {minutos} minutos. Si no intentaste ingresar, ignorá este mensaje "
        "y cambiá tu contraseña.",
    )
