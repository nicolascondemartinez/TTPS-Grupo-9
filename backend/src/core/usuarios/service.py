"""Reglas de negocio del alta de usuarios. No conoce Flask."""
import logging
import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.core.avisos.mail_service import MailSender, enviar_credenciales
from src.core.auth.password import hash_contrasena
from src.core.common.errors import ApiError, validation_error
from src.core.common.validation import DatosRegistro, DatosTransportista
from src.core.enums import RolUsuario
from src.core.models import Especialidad, GerenteMedico, Medico, Provincia, Transportista, Usuario

logger = logging.getLogger(__name__)

def listar_especialidades(db: Session) -> list[Especialidad]:
    return list(db.scalars(select(Especialidad).order_by(Especialidad.nombre)))


def _verificar_correo_libre(db: Session, correo: str) -> None:
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == correo)) is not None:
        raise ApiError(
            409, "CORREO_DUPLICADO", "Ya existe una cuenta con ese correo",
            {"campos": [{"campo": "correo", "problema": "ya está registrado"}]},
        )


def _verificar_duplicados(db: Session, datos: DatosRegistro) -> None:
    _verificar_correo_libre(db, datos.correo)
    if datos.matricula is not None:
        ...  # el resto queda igual
        # La matrícula es única por tabla; acá se exige que lo sea entre médicos y gerentes juntos.
        en_medico = db.scalar(select(Medico.usuario_id).where(Medico.matricula == datos.matricula))
        en_gerente = db.scalar(select(GerenteMedico.usuario_id).where(GerenteMedico.matricula == datos.matricula))
        if en_medico is not None or en_gerente is not None:
            raise ApiError(
                409, "MATRICULA_DUPLICADA", "Ya existe un profesional con esa matrícula",
                {"campos": [{"campo": "matricula", "problema": "ya está registrada"}]},
            )


def _buscar_especialidades(db: Session, ids) -> list[Especialidad]:
    if not ids:
        return []
    encontradas = list(db.scalars(select(Especialidad).where(Especialidad.id.in_(ids))))
    if len(encontradas) != len(ids):
        raise validation_error([{"campo": "especialidades", "problema": "incluye una especialidad que no existe"}])
    return encontradas


def registrar_usuario(db: Session, datos: DatosRegistro) -> Usuario:
    """Auto-registro. No abre sesión ni registra el dispositivo: el primer ingreso pide el código por mail,
    que además confirma que el correo es real."""
    _verificar_duplicados(db, datos)
    especialidades = _buscar_especialidades(db, datos.especialidad_ids)
    # El hash (Argon2) es lento a propósito: recién se calcula cuando ya pasaron las demás validaciones.
    usuario = Usuario(
        email=datos.correo, password_hash=hash_contrasena(datos.contrasena), nombre=datos.nombre,
        apellido=datos.apellido, telefono=datos.telefono, rol=datos.rol, debe_cambiar_password=False,
    )
    usuario.especialidades = especialidades
    try:
        db.add(usuario)
        db.flush()  # genera el id para el perfil
        if datos.rol == RolUsuario.medico:
            db.add(Medico(usuario_id=usuario.id, matricula=datos.matricula))
        elif datos.rol == RolUsuario.gerente_medico:
            db.add(GerenteMedico(usuario_id=usuario.id, matricula=datos.matricula))
        db.commit()
    except IntegrityError:
        # Dos registros simultáneos con el mismo correo o matrícula: gana el primero.
        db.rollback()
        _verificar_duplicados(db, datos)
        raise ApiError(409, "CONFLICTO", "Ya existe un usuario con esos datos")
    return usuario


# --------------------------------------------------------------------------- transportistas
def listar_provincias(db: Session) -> list[tuple[Provincia, bool]]:
    """Todas las provincias, cada una con un indicador de si ya tiene transportista."""
    filas = db.execute(
        select(Provincia, Transportista.usuario_id)
        .outerjoin(Transportista, Transportista.provincia_id == Provincia.id)
        .order_by(Provincia.nombre)
    ).all()
    return [(provincia, usuario_id is not None) for provincia, usuario_id in filas]


def listar_transportistas(db: Session) -> list[Transportista]:
    transportistas = db.scalars(
        select(Transportista).options(selectinload(Transportista.usuario), selectinload(Transportista.provincia))
    ).all()
    return sorted(transportistas, key=lambda t: t.provincia.nombre)


def _verificar_provincia_libre(db: Session, provincia_id) -> None:
    if db.scalar(select(Transportista.usuario_id).where(Transportista.provincia_id == provincia_id)) is not None:
        raise ApiError(
            409, "PROVINCIA_OCUPADA", "Esa provincia ya tiene un transportista asignado",
            {"campos": [{"campo": "provincia_id", "problema": "ya tiene un transportista asignado"}]},
        )


def crear_transportista(db: Session, datos: DatosTransportista, mailer: MailSender) -> Transportista:
    """Alta por el administrativo: crea el usuario con una contraseña temporal y se la manda por mail.

    La contraseña solo existe en ese mail, así que el mail se envía ANTES del commit: si falla, se
    deshace todo (503) y el alta se puede repetir. En el primer ingreso el login obliga a cambiarla.
    """
    _verificar_correo_libre(db, datos.correo)
    provincia = db.get(Provincia, datos.provincia_id)
    if provincia is None:
        raise validation_error([{"campo": "provincia_id", "problema": "no corresponde a una provincia"}])
    _verificar_provincia_libre(db, provincia.id)

    contrasena = secrets.token_urlsafe(12)
    usuario = Usuario(
        email=datos.correo, password_hash=hash_contrasena(contrasena), nombre=datos.nombre,
        apellido=datos.apellido, telefono=datos.telefono, rol=RolUsuario.transportista,
        debe_cambiar_password=True,
    )
    transportista = Transportista(usuario=usuario, provincia=provincia)
    try:
        db.add(transportista)
        db.flush()
    except IntegrityError:
        # Dos altas simultáneas con el mismo correo o la misma provincia: gana la primera.
        db.rollback()
        _verificar_correo_libre(db, datos.correo)
        _verificar_provincia_libre(db, datos.provincia_id)
        raise ApiError(409, "CONFLICTO", "Ya existe un usuario o un transportista con esos datos")

    try:
        enviar_credenciales(mailer, usuario.email, usuario.email, contrasena)
    except Exception:  # noqa: BLE001 - cualquier falla del proveedor de mails
        logger.exception("No se pudo enviar el mail con las credenciales del transportista")
        db.rollback()
        raise ApiError(
            503, "MAIL_NO_DISPONIBLE",
            "No pudimos enviar el mail con las credenciales, así que el transportista no se creó. Intentá de nuevo en unos minutos.",
        )
    db.commit()
    return transportista