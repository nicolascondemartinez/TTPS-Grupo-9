"""Credenciales del paciente (entrevista: "le va a llegar un mail con un usuario y una contraseña").

Al dar de alta se genera una contraseña temporal: en la base queda solo su hash y el paciente tiene que cambiarla
en el primer ingreso (lo resuelve el login). El mail sale después del commit del alta: si falla, el alta no se
pierde y el médico lo reenvía mientras el paciente no haya ingresado (reenviar genera una contraseña nueva,
porque la anterior no se puede recuperar).

La contraseña nunca se escribe en logs, avisos internos ni respuestas de la API. La única excepción es el mail
simulado de desarrollo (MAIL_MODE=console), que escribe el mail completo en la consola, igual que los códigos de
verificación: en producción los mails salen por SMTP (MAIL_MODE=smtp).

Si el login de pacientes pasa a ser por DNI (ver el problema de hermanos con el mismo mail), actualizar el texto
del mail: hoy el usuario es el mail.
"""
import logging
import secrets
from datetime import date

from sqlalchemy.orm import Session

from src.core.auth.password import hash_contrasena
from src.core.avisos.mail_service import MailSender
from src.core.clinico.acceso import obtener_paciente_visible
from src.core.clinico.edad import es_menor_de_edad
from src.core.common.errors import ApiError
from src.core.models import Paciente, Usuario

logger = logging.getLogger(__name__)

LARGO_CONTRASENA = 12
# Sin caracteres que se confunden al leerlos o copiarlos a mano (0/O, 1/l/I).
_ALFABETO = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ASUNTO = "Tu acceso al Sistema de Exoma Clínico"


def generar_contrasena_temporal() -> str:
    return "".join(secrets.choice(_ALFABETO) for _ in range(LARGO_CONTRASENA))


def asignar_contrasena_temporal(usuario: Usuario) -> str:
    """Pone una contraseña temporal nueva (solo el hash) y obliga a cambiarla. Devuelve la contraseña en claro
    para mandarla por mail: no guardarla ni loguearla. Sin commit."""
    contrasena = generar_contrasena_temporal()
    usuario.password_hash = hash_contrasena(contrasena)
    usuario.debe_cambiar_password = True
    return contrasena


def cuerpo_del_mail(paciente: Paciente, contrasena: str, url_ingreso: str, hoy: date) -> str:
    usuario = paciente.usuario
    nombre = f"{usuario.nombre} {usuario.apellido}"
    if es_menor_de_edad(paciente.fecha_nacimiento, hoy):
        saludo = (f"Hola. Te escribimos como padre, madre o tutor de {nombre}, que fue dado/a de alta en el "
                  f"Sistema de Exoma Clínico. Con estos datos vas a poder seguir su estudio:")
    else:
        saludo = f"Hola, {usuario.nombre}. Te dimos de alta en el Sistema de Exoma Clínico. Estos son tus datos de acceso:"
    return (
        f"{saludo}\n\n"
        f"Usuario: {usuario.email}\n"
        f"Contraseña temporal: {contrasena}\n\n"
        f"Ingresá en {url_ingreso}. La primera vez te vamos a pedir que cambies la contraseña.\n\n"
        "Si no esperabas este mail, ignoralo."
    )


def enviar_credenciales(paciente: Paciente, contrasena: str, mail: MailSender, url_ingreso: str,
                        hoy: date | None = None) -> bool:
    """True si el mail salió. Si falla, se registra en el log (sin la contraseña) y devuelve False."""
    try:
        mail.send(paciente.usuario.email, ASUNTO, cuerpo_del_mail(paciente, contrasena, url_ingreso, hoy or date.today()))
        return True
    except Exception:  # noqa: BLE001 - cualquier falla del proveedor de mails
        logger.exception("No se pudo enviar el mail de credenciales del paciente %s", paciente.usuario_id)
        return False


def reenviar_credenciales(session: Session, paciente_id: str, medico: Usuario, mail: MailSender,
                          url_ingreso: str) -> bool:
    """Contraseña temporal nueva y mail de nuevo. Solo el médico del paciente y solo si todavía no ingresó."""
    paciente = obtener_paciente_visible(session, paciente_id, medico)
    if not paciente.usuario.debe_cambiar_password:
        raise ApiError(409, "PACIENTE_YA_INGRESO",
                       "El paciente ya ingresó al sistema: si olvidó su contraseña, la recupera desde el ingreso.")
    contrasena = asignar_contrasena_temporal(paciente.usuario)
    session.commit()
    return enviar_credenciales(paciente, contrasena, mail, url_ingreso)
