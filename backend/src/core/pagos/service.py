"""Presupuesto y pago del estudio.Reglas de negocio.
 No conoce Flask: recibe la sesión de la base y los datos ya validados.

Reglas (de la entrevista con el cliente):
- Precio fijo, no editable: USD 500 hasta 5 genes y USD 30 por cada gen adicional.
- El administrativo emite el presupuesto; el paciente lo ve y paga en un solo pago (simulado).
- Sin pago no hay turno: al pagar, el estudio pasa de Creado a Pagado.
- Cada pago queda en el registro financiero (MovimientoFinanciero) para el tablero futuro.
"""
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.avisos.mail_service import MailSender
from src.core.common.errors import ApiError
from src.core.common.validation import validar_uuid
from src.core.enums import ConceptoPago, EstadoEstudio, OrigenPago, RolUsuario, TipoAviso
from src.core.estudios.service import cambiar_estado_estudio
from src.core.models import Aviso, Estudio, MovimientoFinanciero, Presupuesto, Usuario

logger = logging.getLogger(__name__)

PRECIO_BASE = Decimal("500.00")
GENES_INCLUIDOS = 5
PRECIO_GEN_ADICIONAL = Decimal("30.00")


# --- Precio ---

def precio(cantidad_genes: int) -> Decimal:
    """USD 500 hasta 5 genes y USD 30 por cada gen adicional."""
    if cantidad_genes < 1:
        raise ValueError("El estudio tiene que tener al menos un gen")
    return PRECIO_BASE + PRECIO_GEN_ADICIONAL * max(0, cantidad_genes - GENES_INCLUIDOS)


def cantidad_de_genes(estudio: Estudio) -> int:
    """Genes pedidos en el análisis original (el número 1). Los re-análisis no se presupuestan acá."""
    original = next((a for a in estudio.analisis if a.numero == 1), None)
    return len(original.genes) if original else 0


# --- Busqueda y acceso ---

def obtener_estudio(session: Session, estudio_id: str, usuario: Usuario, bloquear: bool = False) -> Estudio:
    """El estudio, si existe y el usuario lo puede ver. Un paciente solo ve los suyos: si no es suyo,
    se responde 404 (y no 403) para no revelar que el estudio existe.

    bloquear=True traba la fila hasta el commit: si llegan dos pagos a la vez, el segundo espera
    al primero y después encuentra el estudio ya pagado.
    """
    if not validar_uuid(estudio_id):
        raise ApiError(404, "ESTUDIO_NO_ENCONTRADO", "El estudio no existe")
    consulta = select(Estudio).where(Estudio.id == estudio_id)
    if bloquear:
        consulta = consulta.with_for_update()
    estudio = session.scalars(consulta).first()
    if estudio is None or (usuario.rol == RolUsuario.paciente and estudio.paciente_id != usuario.id):
        raise ApiError(404, "ESTUDIO_NO_ENCONTRADO", "El estudio no existe")
    return estudio


def _presupuesto_de(session: Session, estudio: Estudio) -> Presupuesto | None:
    return session.scalars(select(Presupuesto).where(Presupuesto.estudio_id == estudio.id)).first()


# --- Presupuesto ---

def listar_pendientes_de_presupuesto(session: Session) -> list[tuple[Estudio, int]]:
    """Estudios en Creado sin presupuesto, del más viejo al más nuevo, con su cantidad de genes."""
    consulta = (
        select(Estudio)
        .outerjoin(Presupuesto, Presupuesto.estudio_id == Estudio.id)
        .where(Estudio.estado == EstadoEstudio.creado, Presupuesto.id.is_(None))
        .order_by(Estudio.created_at)
    )
    return [(e, cantidad_de_genes(e)) for e in session.scalars(consulta)]


def emitir_presupuesto(session: Session, estudio_id: str, administrativo: Usuario, mail: MailSender) -> Presupuesto:
    estudio = obtener_estudio(session, estudio_id, administrativo, bloquear=True)
    if estudio.estado != EstadoEstudio.creado:
        raise ApiError(409, "ESTADO_INVALIDO", "Solo se puede presupuestar un estudio en estado Creado")
    if _presupuesto_de(session, estudio):
        raise ApiError(409, "PRESUPUESTO_YA_EMITIDO", "El estudio ya tiene un presupuesto emitido")
    genes = cantidad_de_genes(estudio)
    if genes == 0:
        raise ApiError(409, "ESTUDIO_SIN_GENES", "El estudio no tiene genes para presupuestar")

    presupuesto = Presupuesto(
        estudio_id=estudio.id, cantidad_genes=genes, monto_total=precio(genes), emitido_por_id=administrativo.id,
    )
    session.add(presupuesto)
    paciente = estudio.paciente.usuario
    titulo, mensaje = "Tu presupuesto está disponible", f"El presupuesto de tu estudio es de USD {presupuesto.monto_total}."
    _crear_aviso(session, paciente, TipoAviso.presupuesto_emitido, titulo, mensaje, estudio)
    session.commit()
    _enviar_mail(mail, paciente, titulo, mensaje)
    return presupuesto


def obtener_presupuesto(session: Session, estudio_id: str, usuario: Usuario) -> Presupuesto:
    estudio = obtener_estudio(session, estudio_id, usuario)
    presupuesto = _presupuesto_de(session, estudio)
    if presupuesto is None:
        raise ApiError(404, "PRESUPUESTO_NO_EMITIDO", "El estudio todavía no tiene presupuesto")
    return presupuesto


# --- Pago particular ---

def pagar_particular(session: Session, estudio_id: str, paciente: Usuario, mail: MailSender) -> tuple[MovimientoFinanciero, Estudio]:
    """Pago simulado del total, en un solo pago. Registra el movimiento y pasa el estudio a Pagado."""
    estudio = obtener_estudio(session, estudio_id, paciente, bloquear=True)
    if estudio.estado != EstadoEstudio.creado:
        raise ApiError(409, "ESTADO_INVALIDO", "El estudio no está pendiente de pago")
    presupuesto = _presupuesto_de(session, estudio)
    if presupuesto is None:
        raise ApiError(409, "PRESUPUESTO_NO_EMITIDO", "El estudio todavía no tiene presupuesto")

    movimiento = MovimientoFinanciero(
        estudio_id=estudio.id, origen=OrigenPago.paciente, concepto=ConceptoPago.estudio,
        monto=presupuesto.monto_total, registrado_por_id=paciente.id,
    )
    session.add(movimiento)
    cambiar_estado_estudio(session, estudio, EstadoEstudio.pagado, paciente.id)
    titulo, mensaje = "Pago registrado", "Ya podés sacar el turno para la extracción de sangre."
    _crear_aviso(session, paciente, TipoAviso.puede_sacar_turno, titulo, mensaje, estudio)
    session.commit()
    _enviar_mail(mail, paciente, titulo, mensaje)
    return movimiento, estudio


# --- Avisos ---

def _crear_aviso(session: Session, usuario: Usuario, tipo: TipoAviso, titulo: str, mensaje: str, estudio: Estudio) -> None:
    """Aviso dentro del sistema. Se guarda en la misma transacción que el cambio que lo origina."""
    session.add(Aviso(usuario_id=usuario.id, tipo=tipo, titulo=titulo, mensaje=mensaje, estudio_id=estudio.id))


def _enviar_mail(mail: MailSender, usuario: Usuario, titulo: str, mensaje: str) -> None:
    """Se manda después del commit: si el mail falla, el pago o el presupuesto ya quedaron guardados."""
    try:
        mail.send(usuario.email, titulo, mensaje)
    except Exception:
        logger.exception("No se pudo enviar el mail '%s' a %s", titulo, usuario.email)
