"""Avisos internos del sistema, con mail opcional. Los llaman análisis, turnos, pagos, etc."""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from src.core.avisos.mail_service import MailSender
from src.core.avisos.models import Aviso
from src.core.common.errors import ApiError
from src.core.common.validation import validar_uuid
from src.core.enums import RolUsuario, TipoAviso
from src.core.models import Usuario

logger = logging.getLogger(__name__)


def notificar(session: Session, usuario: Usuario, tipo: TipoAviso, titulo: str, mensaje: str, *,
              estudio_id=None, turno_id=None, mail: MailSender | None = None) -> Aviso:
    """Crea el aviso en la sesión actual (sin commit) y, si se pasa `mail`, manda también el mail.
    Si el mail falla se registra en el log y no se deshace nada."""
    aviso = Aviso(usuario_id=usuario.id, tipo=tipo, titulo=titulo, mensaje=mensaje,
                  estudio_id=estudio_id, turno_id=turno_id)
    session.add(aviso)
    if mail is not None:
        try:
            mail.send(usuario.email, titulo, mensaje)
        except Exception:
            logger.exception("No se pudo enviar el mail del aviso a %s", usuario.email)
    return aviso


def notificar_rol(session: Session, rol: RolUsuario, tipo: TipoAviso, titulo: str, mensaje: str, *,
                  estudio_id=None, mail: MailSender | None = None) -> int:
    """Avisa a todos los usuarios activos de un rol (ej: a todos los bioinformáticos). Sin commit."""
    usuarios = list(session.scalars(select(Usuario).where(Usuario.rol == rol, Usuario.activo.is_(True))))
    for usuario in usuarios:
        notificar(session, usuario, tipo, titulo, mensaje, estudio_id=estudio_id, mail=mail)
    return len(usuarios)


def listar_avisos(session: Session, usuario_id, solo_pendientes: bool = False, limite: int = 50) -> list[Aviso]:
    consulta = select(Aviso).where(Aviso.usuario_id == usuario_id)
    if solo_pendientes:
        consulta = consulta.where(Aviso.leido.is_(False))
    return list(session.scalars(consulta.order_by(Aviso.created_at.desc()).limit(limite)))


def contar_pendientes(session: Session, usuario_id) -> int:
    return session.scalar(
        select(func.count()).select_from(Aviso).where(Aviso.usuario_id == usuario_id, Aviso.leido.is_(False))
    ) or 0


def marcar_leido(session: Session, usuario_id, aviso_id: str) -> Aviso:
    aviso = None
    if validar_uuid(aviso_id):
        # filtrar por usuario_id hace que el aviso de otra persona responda 404, igual que uno inexistente
        aviso = session.scalar(select(Aviso).where(Aviso.id == uuid.UUID(aviso_id), Aviso.usuario_id == usuario_id))
    if aviso is None:
        raise ApiError(404, "AVISO_NO_ENCONTRADO", "El aviso no existe")
    if not aviso.leido:
        aviso.leido, aviso.leido_at = True, datetime.now(timezone.utc)
        session.commit()
    return aviso


def marcar_todos_leidos(session: Session, usuario_id) -> int:
    resultado = session.execute(
        update(Aviso).where(Aviso.usuario_id == usuario_id, Aviso.leido.is_(False))
        .values(leido=True, leido_at=datetime.now(timezone.utc))
    )
    session.commit()
    return resultado.rowcount