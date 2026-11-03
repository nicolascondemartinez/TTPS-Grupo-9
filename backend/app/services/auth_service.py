"""Reglas de negocio del acceso: login, verificación de dispositivo nuevo, cambio de contraseña,
sesiones (tokens) y permisos. No conoce Flask: recibe la sesión de la base y los datos ya validados.

Flujo de /auth/login (todas las respuestas exitosas son 200, el campo `estado` indica cuál es):
  1. correo o contraseña incorrectos            -> 401 CREDENCIALES_INVALIDAS (mensaje genérico)
  2. usuario inactivo (con contraseña correcta)  -> 403 CUENTA_INACTIVA
  3. debe cambiar la contraseña (primer ingreso) -> estado "cambio_contrasena_requerido" + token limitado
  4. dispositivo ya verificado                   -> estado "autenticado" + token
  5. dispositivo nuevo                           -> estado "verificacion_requerida" + código por mail
"""
import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.enums import AlcanceSesion, RolUsuario
from app.db.models import CodigoVerificacion, Dispositivo, Permiso, RolPermiso, Sesion, Usuario
from app.errors import ApiError
from app.services import password_service
from app.services.mail_service import MailSender, enviar_codigo_verificacion
from app.services.validation import validar_uuid

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthSettings:
    session_ttl: timedelta
    limited_session_ttl: timedelta
    code_ttl_minutes: int
    code_max_attempts: int
    secret_key: str

    @classmethod
    def from_config(cls, config) -> "AuthSettings":
        return cls(
            session_ttl=timedelta(hours=config["SESSION_TTL_HOURS"]),
            limited_session_ttl=timedelta(minutes=config["LIMITED_SESSION_TTL_MINUTES"]),
            code_ttl_minutes=config["VERIFICATION_CODE_TTL_MINUTES"],
            code_max_attempts=config["VERIFICATION_CODE_MAX_ATTEMPTS"],
            secret_key=config["SECRET_KEY"],
        )


@dataclass
class Autenticacion:
    """Resultado de un login o de una verificación."""

    estado: str  # autenticado | cambio_contrasena_requerido | verificacion_requerida
    usuario: Usuario
    token: str | None = None
    expira_at: datetime | None = None
    desafio_id: str | None = None


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def huella_dispositivo(device_id: str) -> str:
    """En la base se guarda el hash del identificador del dispositivo, nunca el valor crudo."""
    return _sha256(device_id)


def _hash_codigo(secret_key: str, desafio_id: uuid.UUID, codigo: str) -> str:
    # HMAC con la clave del servidor: un código de 6 dígitos con un hash simple se podría
    # recuperar por fuerza bruta si se filtrara la base.
    return hmac.new(secret_key.encode(), f"{desafio_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Sesiones (tokens)
# ---------------------------------------------------------------------------
def _crear_sesion(db: Session, usuario: Usuario, alcance: AlcanceSesion, ttl: timedelta) -> tuple[str, Sesion]:
    """Crea la sesión y devuelve (token en claro, sesión). El token en claro solo existe acá."""
    token = secrets.token_urlsafe(32)
    sesion = Sesion(usuario_id=usuario.id, token_hash=_sha256(token), alcance=alcance, expira_at=_ahora() + ttl)
    db.add(sesion)
    db.flush()
    return token, sesion


def autenticar_token(db: Session, token: str | None) -> tuple[Usuario, Sesion]:
    """Valida el token de un request (Authorization: Bearer ...). 401 si falta, es inválido o venció."""
    if not token:
        raise ApiError(401, "TOKEN_AUSENTE", "Falta el token de acceso")
    sesion = db.scalar(select(Sesion).where(Sesion.token_hash == _sha256(token)))
    if sesion is None or sesion.revocada_at is not None:
        raise ApiError(401, "TOKEN_INVALIDO", "La sesión no es válida. Ingresá de nuevo.")
    if _ahora() >= sesion.expira_at:
        raise ApiError(401, "TOKEN_EXPIRADO", "La sesión expiró. Ingresá de nuevo.")
    usuario = sesion.usuario
    if not usuario.activo:
        raise ApiError(401, "TOKEN_INVALIDO", "La sesión no es válida. Ingresá de nuevo.")
    return usuario, sesion


def cerrar_sesion(db: Session, sesion: Sesion) -> None:
    sesion.revocada_at = _ahora()
    db.commit()


def _registrar_dispositivo(db: Session, usuario: Usuario, huella: str) -> None:
    existente = db.scalar(select(Dispositivo).where(Dispositivo.usuario_id == usuario.id, Dispositivo.huella == huella))
    if existente is None:
        db.add(Dispositivo(usuario_id=usuario.id, huella=huella, ultimo_acceso=_ahora()))
    else:
        existente.ultimo_acceso = _ahora()
    db.flush()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def iniciar_sesion(
    db: Session, correo: str, contrasena: str, device_id: str, settings: AuthSettings, mailer: MailSender
) -> Autenticacion:
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == correo))
    # Si el correo no existe se verifica igual contra un hash ficticio: así la respuesta tarda lo
    # mismo y no se puede averiguar qué correos están registrados.
    coincide = password_service.verificar_contrasena(
        usuario.password_hash if usuario else password_service.HASH_FICTICIO, contrasena
    )
    if usuario is None or not coincide:
        raise ApiError(401, "CREDENCIALES_INVALIDAS", "Correo o contraseña incorrectos")
    if not usuario.activo:
        raise ApiError(403, "CUENTA_INACTIVA", "Tu cuenta está inactiva. Consultá con el laboratorio.")
    if password_service.requiere_rehash(usuario.password_hash):
        usuario.password_hash = password_service.hash_contrasena(contrasena)

    # Primer ingreso: solo puede cambiar la contraseña (sin código por mail, como pidió el cliente)
    if usuario.debe_cambiar_password:
        token, sesion = _crear_sesion(db, usuario, AlcanceSesion.cambio_contrasena, settings.limited_session_ttl)
        db.commit()
        return Autenticacion("cambio_contrasena_requerido", usuario, token, sesion.expira_at)

    huella = huella_dispositivo(device_id)
    conocido = db.scalar(select(Dispositivo).where(Dispositivo.usuario_id == usuario.id, Dispositivo.huella == huella))
    if conocido is not None:
        conocido.ultimo_acceso = _ahora()
        token, sesion = _crear_sesion(db, usuario, AlcanceSesion.completo, settings.session_ttl)
        db.commit()
        return Autenticacion("autenticado", usuario, token, sesion.expira_at)

    # Dispositivo nuevo: se envía un código al mail. Solo vale el último que se pidió.
    ahora = _ahora()
    db.execute(
        update(CodigoVerificacion)
        .where(CodigoVerificacion.usuario_id == usuario.id, CodigoVerificacion.usado_at.is_(None))
        .values(usado_at=ahora)
    )
    codigo = f"{secrets.randbelow(10**6):06d}"
    desafio_id = uuid.uuid4()
    db.add(
        CodigoVerificacion(
            id=desafio_id,
            usuario_id=usuario.id,
            huella=huella,
            codigo_hash=_hash_codigo(settings.secret_key, desafio_id, codigo),
            expira_at=ahora + timedelta(minutes=settings.code_ttl_minutes),
            intentos=0,
        )
    )
    db.commit()
    try:
        enviar_codigo_verificacion(mailer, usuario.email, codigo, settings.code_ttl_minutes)
    except Exception:  # noqa: BLE001 - cualquier falla del proveedor de mails
        logger.exception("No se pudo enviar el código de verificación")
        raise ApiError(503, "MAIL_NO_DISPONIBLE", "No pudimos enviar el código por mail. Intentá de nuevo en unos minutos.")
    return Autenticacion("verificacion_requerida", usuario, desafio_id=str(desafio_id))


def verificar_dispositivo(
    db: Session, desafio_id: str, codigo: str, device_id: str, settings: AuthSettings
) -> Autenticacion:
    invalido = ApiError(401, "DESAFIO_INVALIDO", "La verificación no es válida. Volvé a ingresar para recibir un código nuevo.")
    if not validar_uuid(desafio_id):
        raise invalido
    huella = huella_dispositivo(device_id)
    desafio = db.scalar(
        select(CodigoVerificacion).where(CodigoVerificacion.id == uuid.UUID(desafio_id)).with_for_update()
    )
    # El código solo vale para el dispositivo que lo pidió
    if desafio is None or desafio.usado_at is not None or not hmac.compare_digest(desafio.huella, huella):
        raise invalido

    ahora = _ahora()
    if ahora >= desafio.expira_at:
        desafio.usado_at = ahora
        db.commit()
        raise ApiError(401, "CODIGO_VENCIDO", "El código venció. Volvé a ingresar para recibir uno nuevo.")

    if not hmac.compare_digest(desafio.codigo_hash, _hash_codigo(settings.secret_key, desafio.id, codigo)):
        desafio.intentos += 1
        restantes = settings.code_max_attempts - desafio.intentos
        if restantes <= 0:
            desafio.usado_at = ahora
            db.commit()
            raise ApiError(401, "DESAFIO_AGOTADO", "Superaste el máximo de intentos. Volvé a ingresar para recibir un código nuevo.")
        db.commit()
        raise ApiError(401, "CODIGO_INCORRECTO", "El código ingresado es incorrecto", {"intentos_restantes": restantes})

    usuario = db.get(Usuario, desafio.usuario_id)
    if not usuario.activo:
        raise ApiError(403, "CUENTA_INACTIVA", "Tu cuenta está inactiva. Consultá con el laboratorio.")
    desafio.usado_at = ahora
    _registrar_dispositivo(db, usuario, huella)
    token, sesion = _crear_sesion(db, usuario, AlcanceSesion.completo, settings.session_ttl)
    db.commit()
    return Autenticacion("autenticado", usuario, token, sesion.expira_at)


# ---------------------------------------------------------------------------
# Cambio de contraseña
# ---------------------------------------------------------------------------
def cambiar_contrasena(
    db: Session, usuario: Usuario, actual: str, nueva: str, device_id: str, settings: AuthSettings
) -> Autenticacion:
    """Cambia la contraseña, cierra todas las sesiones del usuario y abre una nueva (completa).

    Si el cambio es el del primer ingreso, el dispositivo queda registrado y no se pide código por mail.
    El error de contraseña actual incorrecta es 400 y no 401: un 401 con token hace que el frontend
    cierre la sesión.
    """
    if not password_service.verificar_contrasena(usuario.password_hash, actual):
        raise ApiError(
            400, "CONTRASENA_ACTUAL_INCORRECTA", "La contraseña actual es incorrecta",
            {"campos": [{"campo": "contrasena_actual", "problema": "es incorrecta"}]},
        )
    usuario.password_hash = password_service.hash_contrasena(nueva)
    usuario.debe_cambiar_password = False
    db.execute(
        update(Sesion).where(Sesion.usuario_id == usuario.id, Sesion.revocada_at.is_(None)).values(revocada_at=_ahora())
    )
    _registrar_dispositivo(db, usuario, huella_dispositivo(device_id))
    token, sesion = _crear_sesion(db, usuario, AlcanceSesion.completo, settings.session_ttl)
    db.commit()
    return Autenticacion("autenticado", usuario, token, sesion.expira_at)


# ---------------------------------------------------------------------------
# Permisos (patrón modulo_accion)
# ---------------------------------------------------------------------------
def permisos_del_rol(db: Session, rol: RolUsuario) -> list[str]:
    return list(
        db.scalars(
            select(Permiso.nombre)
            .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
            .where(RolPermiso.rol == rol)
            .order_by(Permiso.nombre)
        )
    )


def tiene_permiso(db: Session, rol: RolUsuario, nombre: str) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .where(RolPermiso.rol == rol, Permiso.nombre == nombre)
        )
        > 0
    )
