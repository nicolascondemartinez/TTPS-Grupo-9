"""Reglas de negocio del alta de usuarios. No conoce Flask."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.auth.password import hash_contrasena
from src.core.common.errors import ApiError, validation_error
from src.core.common.validation import DatosRegistro
from src.core.enums import RolUsuario
from src.core.models import Especialidad, GerenteMedico, Medico, Usuario


def listar_especialidades(db: Session) -> list[Especialidad]:
    return list(db.scalars(select(Especialidad).order_by(Especialidad.nombre)))


def _verificar_duplicados(db: Session, datos: DatosRegistro) -> None:
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == datos.correo)) is not None:
        raise ApiError(
            409, "CORREO_DUPLICADO", "Ya existe una cuenta con ese correo",
            {"campos": [{"campo": "correo", "problema": "ya está registrado"}]},
        )
    if datos.matricula is not None:
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