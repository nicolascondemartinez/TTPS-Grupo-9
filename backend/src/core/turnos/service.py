"""Turnos de extracción. No conoce Flask: recibe la sesión de la base y los datos ya validados.

Reglas (de la entrevista con el cliente):
- Solo se saca turno con el estudio Pagado. Cada centro tiene su propio turnero.
- Turnos de 15 minutos, de lunes a viernes de 9 a 18, sin feriados, una persona por turno.
- Los turnos libres NO se guardan: se calculan (franjas del día menos las ya ocupadas).
- Cancelar libera el turno y el estudio vuelve a Pagado. No cuenta como inasistencia.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.common.errors import ApiError
from src.core.common.validation import validar_uuid
from src.core.enums import EstadoEstudio, EstadoTurno
from src.core.estudios.service import cambiar_estado_estudio
from src.core.models import CentroExtraccion, Estudio, Provincia, Turno, Usuario, Paciente
from src.core.pagos.service import obtener_estudio
from src.core.turnos.calendario import ZONA_ARGENTINA, es_franja_valida, feriados_entre, franjas_del_dia
from src.core.turnos.documentos import DatosTurno, generar_consentimiento, generar_orden

DIAS_DE_VENTANA = 30  # hasta cuántos días para adelante se pueden sacar turnos
MAXIMO_INASISTENCIAS = 5  # a la quinta inasistencia se pierde el pago (etapa 6)


def _ahora(ahora: datetime | None) -> datetime:
    return ahora or datetime.now(timezone.utc)


def _hoy(ahora: datetime) -> date:
    return ahora.astimezone(ZONA_ARGENTINA).date()


# --- Centros ---

def listar_centros(session: Session, provincia_id: str | None = None) -> list[tuple[CentroExtraccion, str]]:
    """Centros activos con el nombre de su provincia, ordenados por provincia y nombre."""
    consulta = (
        select(CentroExtraccion, Provincia.nombre)
        .join(Provincia, Provincia.id == CentroExtraccion.provincia_id)
        .where(CentroExtraccion.activo.is_(True))
        .order_by(Provincia.nombre, CentroExtraccion.nombre)
    )
    if provincia_id:
        if not validar_uuid(provincia_id):
            return []
        consulta = consulta.where(CentroExtraccion.provincia_id == provincia_id)
    return [(centro, provincia) for centro, provincia in session.execute(consulta)]


def obtener_centro(session: Session, centro_id: str) -> CentroExtraccion:
    centro = session.get(CentroExtraccion, centro_id) if validar_uuid(centro_id) else None
    if centro is None or not centro.activo:
        raise ApiError(404, "CENTRO_NO_ENCONTRADO", "El centro de extracción no existe")
    return centro


# --- Turnos libres ---

def turnos_libres(session: Session, centro_id: str, desde: date | None = None, hasta: date | None = None,
                  ahora: datetime | None = None) -> list[tuple[date, list[datetime]]]:
    """Por cada día hábil del rango, las franjas que siguen libres. El rango se limita a [hoy, hoy + 30 días]
    y no se ofrecen horarios que ya pasaron."""
    obtener_centro(session, centro_id)
    ahora = _ahora(ahora)
    hoy = _hoy(ahora)
    desde = max(desde or hoy, hoy)
    hasta = min(hasta or hoy + timedelta(days=DIAS_DE_VENTANA), hoy + timedelta(days=DIAS_DE_VENTANA))
    if desde > hasta:
        return []

    feriados = feriados_entre(session, desde, hasta)
    inicio = datetime.combine(desde, datetime.min.time(), tzinfo=ZONA_ARGENTINA)
    fin = datetime.combine(hasta + timedelta(days=1), datetime.min.time(), tzinfo=ZONA_ARGENTINA)
    ocupados = set(session.scalars(
        select(Turno.fecha_hora).where(
            Turno.centro_id == centro_id,
            Turno.estado.in_([EstadoTurno.reservado, EstadoTurno.asistido]),
            Turno.fecha_hora >= inicio, Turno.fecha_hora < fin,
        )
    ))

    dias = []
    dia = desde
    while dia <= hasta:
        libres = [f for f in franjas_del_dia(dia, feriados) if f > ahora and f not in ocupados]
        if libres:
            dias.append((dia, libres))
        dia += timedelta(days=1)
    return dias


# --- Reservar, ver y cancelar ---

def reservar_turno(session: Session, estudio_id: str, paciente: Usuario, centro_id: str, fecha_hora: datetime,
                   ahora: datetime | None = None) -> tuple[Turno, CentroExtraccion, Estudio]:
    estudio = obtener_estudio(session, estudio_id, paciente, bloquear=True)
    if estudio.estado != EstadoEstudio.pagado:
        raise ApiError(409, "ESTADO_INVALIDO", "Para sacar turno el estudio tiene que estar pagado")
    centro = obtener_centro(session, centro_id)

    ahora = _ahora(ahora)
    if fecha_hora <= ahora:
        raise ApiError(409, "TURNO_PASADO", "Ese horario ya pasó")
    if fecha_hora.astimezone(ZONA_ARGENTINA).date() > _hoy(ahora) + timedelta(days=DIAS_DE_VENTANA):
        raise ApiError(409, "FUERA_DE_VENTANA", f"Los turnos se sacan con hasta {DIAS_DE_VENTANA} días de anticipación")
    dia = fecha_hora.astimezone(ZONA_ARGENTINA).date()
    if not es_franja_valida(fecha_hora, feriados_entre(session, dia, dia)):
        raise ApiError(409, "FRANJA_INVALIDA", "Los turnos son de lunes a viernes de 9 a 18, cada 15 minutos, sin feriados")

    turno = Turno(estudio_id=estudio.id, centro_id=centro.id, fecha_hora=fecha_hora)
    session.add(turno)
    try:
        # El índice único de la base impide dos turnos en el mismo centro y horario: si dos pacientes
        # reservan a la vez, el segundo falla acá.
        session.flush()
    except IntegrityError:
        session.rollback()
        raise ApiError(409, "TURNO_OCUPADO", "Ese turno se acaba de ocupar. Elegí otro horario.")
    cambiar_estado_estudio(session, estudio, EstadoEstudio.turno_sacado, paciente.id)
    session.commit()
    return turno, centro, estudio


def turno_vigente(session: Session, estudio_id: str, usuario: Usuario) -> tuple[Turno, CentroExtraccion, Estudio]:
    """El turno reservado del estudio (para la pantalla "Mi turno")."""
    estudio = obtener_estudio(session, estudio_id, usuario)
    turno = session.scalars(
        select(Turno).where(Turno.estudio_id == estudio.id, Turno.estado == EstadoTurno.reservado)
    ).first()
    if turno is None:
        raise ApiError(404, "SIN_TURNO", "El estudio no tiene un turno reservado")
    return turno, session.get(CentroExtraccion, turno.centro_id), estudio


def cancelar_turno(session: Session, turno_id: str, paciente: Usuario,
                   ahora: datetime | None = None) -> tuple[Turno, CentroExtraccion, Estudio]:
    turno = session.get(Turno, turno_id) if validar_uuid(turno_id) else None
    if turno is None:
        raise ApiError(404, "TURNO_NO_ENCONTRADO", "El turno no existe")
    # obtener_estudio verifica que el estudio sea del paciente (si no, 404) y lo traba hasta el commit
    estudio = obtener_estudio(session, str(turno.estudio_id), paciente, bloquear=True)
    if turno.estado != EstadoTurno.reservado:
        raise ApiError(409, "TURNO_NO_CANCELABLE", "El turno ya no está reservado")
    if turno.fecha_hora <= _ahora(ahora):
        raise ApiError(409, "TURNO_YA_PASO", "No se puede cancelar un turno que ya pasó")

    turno.estado = EstadoTurno.cancelado
    cambiar_estado_estudio(session, estudio, EstadoEstudio.pagado, paciente.id)
    session.commit()
    return turno, session.get(CentroExtraccion, turno.centro_id), estudio


# --- Documentos (orden de extracción y consentimiento) ---

def documento_del_turno(session: Session, turno_id: str, usuario: Usuario, tipo: str) -> tuple[bytes, str]:
    """PDF del turno reservado: tipo "orden" o "consentimiento". Devuelve el contenido y el nombre del archivo."""
    turno = session.get(Turno, turno_id) if validar_uuid(turno_id) else None
    if turno is None:
        raise ApiError(404, "TURNO_NO_ENCONTRADO", "El turno no existe")
    estudio = obtener_estudio(session, str(turno.estudio_id), usuario)  # si no es su estudio, 404
    if turno.estado != EstadoTurno.reservado:
        raise ApiError(409, "TURNO_NO_VIGENTE", "Solo se descargan los documentos de un turno reservado")

    paciente = session.get(Paciente, estudio.paciente_id)
    centro = session.get(CentroExtraccion, turno.centro_id)
    datos = DatosTurno(
        paciente=f"{paciente.usuario.apellido}, {paciente.usuario.nombre}", dni=paciente.dni,
        fecha_nacimiento=paciente.fecha_nacimiento, estudio_id=str(estudio.id), fecha_hora=turno.fecha_hora,
        centro=centro.nombre, direccion=centro.direccion,
    )
    if tipo == "orden":
        return generar_orden(datos), "orden-de-extraccion.pdf"
    return generar_consentimiento(datos), "consentimiento-informado.pdf"
