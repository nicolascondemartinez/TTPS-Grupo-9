"""Reglas de negocio de logística: orden del día, recolección y ubicación de muestras."""
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.adapters.recorridos import CentroParaOrdenar, Recorridos, get_recorridos
from src.core.common.errors import ApiError
from src.core.enums import EstadoEstudio, EstadoTurno
from src.core.estudios.service import cambiar_estado_estudio
from src.core.models import (
    CentroExtraccion,
    Estudio,
    Feriado,
    OrdenDelDia,
    OrdenParada,
    ParadaEstudio,
    Provincia,
    Transportista,
    Turno,
    Usuario,
)

ZONA_AR = timezone(timedelta(hours=-3))

def es_dia_habil(session: Session, fecha: date) -> bool:
    """Devuelve True si la fecha es de lunes a viernes y no está registrada como feriado."""

    if fecha.weekday() >= 5:  # 5 = sábado, 6 = domingo
        return False
    return session.scalar(select(Feriado.fecha).where(Feriado.fecha == fecha)) is None

def _estudios_pendientes_con_centro(session: Session) -> list[tuple[Estudio, CentroExtraccion]]:
    """Obtiene los estudios listos para retirar aún sin parada asignada junto al centro de su turno asistido."""

    ya_asignados = select(ParadaEstudio.estudio_id)
    estudios = list(
        session.scalars(
            select(Estudio).where(
                Estudio.estado == EstadoEstudio.listo_para_retirar,
                Estudio.id.not_in(ya_asignados),
            )
        )
    )
    resultado = []
    for estudio in estudios:
        centro = session.scalar(
            select(CentroExtraccion)
            .join(Turno, Turno.centro_id == CentroExtraccion.id)
            .where(Turno.estudio_id == estudio.id, Turno.estado == EstadoTurno.asistido)
            .order_by(Turno.fecha_hora.desc())
        )
        if centro is not None:
            resultado.append((estudio, centro))
    return resultado


def generar_ordenes_del_dia( session: Session,
    fecha: date | None = None,
    adapter: Recorridos | None = None,
) -> list[OrdenDelDia]:
    """Agrupa por provincia los estudios listos para retirar en un día hábil y crea la orden del día optimizada."""

    fecha = fecha or datetime.now(ZONA_AR).date()
    if not es_dia_habil(session, fecha):
        raise ApiError(400, "DIA_NO_HABIL", "No se generan órdenes del día en fines de semana ni feriados")

    adapter = adapter or get_recorridos()
    por_provincia: dict[uuid.UUID, dict[uuid.UUID, tuple[CentroExtraccion, list[Estudio]]]] = defaultdict(dict)

    for estudio, centro in _estudios_pendientes_con_centro(session):
        bucket = por_provincia[centro.provincia_id]
        if centro.id not in bucket:
            bucket[centro.id] = (centro, [])
        bucket[centro.id][1].append(estudio)

    ordenes_creadas: list[OrdenDelDia] = []
    for provincia_id, centros_dict in por_provincia.items():
        transportista = session.scalar(
            select(Transportista).where(Transportista.provincia_id == provincia_id)
        )
        if transportista is None:
            raise ApiError(409, "SIN_TRANSPORTISTA", "La provincia no tiene un transportista asignado")

        ya_existe = session.scalar(
            select(OrdenDelDia).where(
                OrdenDelDia.fecha == fecha,
                OrdenDelDia.transportista_id == transportista.usuario_id,
            )
        )
        if ya_existe is not None:
            raise ApiError(409, "ORDEN_YA_EXISTE", "El transportista ya tiene una orden del día para esa fecha")

        para_ordenar = [
            CentroParaOrdenar(
                id=c.id,
                nombre=c.nombre,
                direccion=c.direccion,
                latitud=float(c.latitud),
                longitud=float(c.longitud),
            )
            for c, _ in centros_dict.values()
        ]
        recorrido = adapter.optimizar(para_ordenar)

        orden = OrdenDelDia(fecha=fecha, transportista_id=transportista.usuario_id)
        session.add(orden)
        session.flush()

        for pos, centro_ordenado in enumerate(recorrido.paradas, start=1):
            parada = OrdenParada(orden_id=orden.id, centro_id=centro_ordenado.id, posicion=pos)
            session.add(parada)
            session.flush()

            _, estudios_centro = centros_dict[centro_ordenado.id]
            for estudio in estudios_centro:
                session.add(ParadaEstudio(parada_id=parada.id, estudio_id=estudio.id))

        ordenes_creadas.append(orden)

    session.commit()
    return ordenes_creadas

def obtener_orden_del_dia_actual( session: Session, transportista_id: uuid.UUID,
    fecha: date | None = None ) -> dict | None:
    """Devuelve la orden del día del transportista para la fecha indicada con sus paradas y cantidad de muestras."""

    fecha = fecha or datetime.now(ZONA_AR).date()
    orden = session.scalar(
        select(OrdenDelDia)
        .options(selectinload(OrdenDelDia.paradas))
        .where(
            OrdenDelDia.transportista_id == transportista_id,
            OrdenDelDia.fecha == fecha,
        )
    )
    if orden is None:
        return None
    paradas_detalle = []
    for parada in orden.paradas:
        centro = session.get(CentroExtraccion, parada.centro_id)
        cantidad = session.scalar(
            select(func.count(ParadaEstudio.estudio_id)).where(ParadaEstudio.parada_id == parada.id)
        ) or 0
        paradas_detalle.append({
            "id": parada.id,
            "posicion": parada.posicion,
            "recogida_at": parada.recogida_at,
            "recogido": parada.recogida_at is not None,
            "cantidad_muestras": cantidad,
            "centro": centro,
        })
    return {"orden": orden, "paradas": paradas_detalle, "transportista": _datos_mapa_de_orden(session, orden)["transportista"]}

def marcar_parada_recogida( session: Session, transportista_id: uuid.UUID, parada_id: uuid.UUID) -> OrdenParada:
    """Registra el retiro de una parada en orden y pasa sus estudios a estado en_camino_laboratorio_central."""

    parada = session.scalar(
        select(OrdenParada).options(selectinload(OrdenParada.orden)).where(OrdenParada.id == parada_id)
    )
    if parada is None:
        raise ApiError(404, "PARADA_NO_ENCONTRADA", "La parada no existe")
    if parada.orden.transportista_id != transportista_id:
        raise ApiError(403, "PROHIBIDO", "La parada no pertenece a tu orden del día")
    if parada.orden.llegada_central_at is not None:
        raise ApiError(409, "ORDEN_CERRADA", "La orden del día ya fue entregada en el laboratorio central")
    if parada.recogida_at is not None:
        raise ApiError(409, "PARADA_YA_RECOGIDA", "La parada ya fue marcada como recogida")
    pendiente_anterior = session.scalar(
        select(OrdenParada.id).where(
            OrdenParada.orden_id == parada.orden_id,
            OrdenParada.posicion < parada.posicion,
            OrdenParada.recogida_at.is_(None),
        )
    )
    if pendiente_anterior is not None:
        raise ApiError(409, "PARADA_FUERA_DE_ORDEN", "Debés recoger las paradas en el orden indicado")
    parada.recogida_at = datetime.now(timezone.utc)
    estudios = list(
        session.scalars(
            select(Estudio)
            .join(ParadaEstudio, ParadaEstudio.estudio_id == Estudio.id)
            .where(ParadaEstudio.parada_id == parada.id)
        )
    )
    for estudio in estudios:
        cambiar_estado_estudio(
            session,
            estudio,
            EstadoEstudio.en_camino_laboratorio_central,
            usuario_id=transportista_id,
        )
    session.commit()
    return parada

def registrar_llegada_laboratorio_central(session: Session, transportista_id: uuid.UUID, orden_id: uuid.UUID) -> OrdenDelDia:
    """Cierra la orden del día al llegar al laboratorio central y pasa sus estudios al estado esperando_armado_lote."""

    orden = session.scalar(
        select(OrdenDelDia).options(selectinload(OrdenDelDia.paradas)).where(OrdenDelDia.id == orden_id)
    )
    if orden is None:
        raise ApiError(404, "ORDEN_NO_ENCONTRADA", "La orden del día no existe")
    if orden.transportista_id != transportista_id:
        raise ApiError(403, "PROHIBIDO", "La orden no te pertenece")
    if orden.llegada_central_at is not None:
        raise ApiError(409, "ORDEN_YA_ENTREGADA", "La llegada al laboratorio central ya fue registrada")
    if any(p.recogida_at is None for p in orden.paradas):
        raise ApiError(409, "PARADAS_PENDIENTES", "Todavía quedan paradas sin recoger en la orden del día")
    
    orden.llegada_central_at = datetime.now(timezone.utc)
    parada_ids = [p.id for p in orden.paradas]
    
    estudios = list(
        session.scalars(
            select(Estudio)
            .join(ParadaEstudio, ParadaEstudio.estudio_id == Estudio.id)
            .where(
                ParadaEstudio.parada_id.in_(parada_ids),
                Estudio.estado == EstadoEstudio.en_camino_laboratorio_central,
            )
        )
    )
    
    for estudio in estudios:
        cambiar_estado_estudio(
            session,
            estudio,
            EstadoEstudio.esperando_armado_lote,
            usuario_id=transportista_id,
        )

    session.commit()
    return orden

def _datos_mapa_de_orden(session: Session, orden: OrdenDelDia) -> dict:
    """Arma la posición simulada del transportista y la lista de paradas de la orden dle dia"""

    transportista = session.scalar(
        select(Transportista)
        .options(selectinload(Transportista.usuario), selectinload(Transportista.provincia))
        .where(Transportista.usuario_id == orden.transportista_id)
    )
    paradas_con_centro = [(p, session.get(CentroExtraccion, p.centro_id)) for p in orden.paradas]
    recogidas = [(p, c) for p, c in paradas_con_centro if p.recogida_at is not None]
    pendientes = [(p, c) for p, c in paradas_con_centro if p.recogida_at is None]
    posicion_gps = None
    if recogidas:
        _, ultimo_centro = recogidas[-1]
        if pendientes:
            _, siguiente_centro = pendientes[0]
            lat = (float(ultimo_centro.latitud) + float(siguiente_centro.latitud)) / 2
            lon = (float(ultimo_centro.longitud) + float(siguiente_centro.longitud)) / 2
        else:
            lat = float(ultimo_centro.latitud)
            lon = float(ultimo_centro.longitud)
        posicion_gps = {
            "nombre": f"{transportista.usuario.nombre} {transportista.usuario.apellido}",
            "provincia": transportista.provincia.nombre,
            "latitud": lat,
            "longitud": lon,
        }
    return {
        "transportista": posicion_gps,
        "paradas": [
            {
                "id": c.id,
                "posicion": p.posicion,
                "nombre": c.nombre,
                "direccion": c.direccion,
                "latitud": float(c.latitud),
                "longitud": float(c.longitud),
                "recogido": p.recogida_at is not None,
            }
            for p, c in paradas_con_centro
        ],
    }
def obtener_ubicacion_muestra(session: Session, estudio_id: uuid.UUID) -> dict:
    """Calcula la ubicación GPS simulada del transportista y el estado del recorrido para un estudio en tránsito."""
    
    estudio = session.get(Estudio, estudio_id)
    if estudio is None:
        raise ApiError(404, "ESTUDIO_NO_ENCONTRADO", "El estudio no existe")
    if estudio.estado != EstadoEstudio.en_camino_laboratorio_central:
        raise ApiError(409, "ESTUDIO_NO_EN_TRANSITO", "El estudio no se encuentra en camino al laboratorio central")
    parada_estudio = session.scalar(
        select(ParadaEstudio)
        .join(OrdenParada, OrdenParada.id == ParadaEstudio.parada_id)
        .join(OrdenDelDia, OrdenDelDia.id == OrdenParada.orden_id)
        .where(ParadaEstudio.estudio_id == estudio.id)
        .order_by(OrdenDelDia.created_at.desc())
    )
    if parada_estudio is None:
        raise ApiError(404, "ORDEN_NO_ENCONTRADA", "No se encontró una orden del día asociada al estudio")
    parada_actual = session.get(OrdenParada, parada_estudio.parada_id)
    orden = session.scalar(
        select(OrdenDelDia)
        .options(selectinload(OrdenDelDia.paradas))
        .where(OrdenDelDia.id == parada_actual.orden_id)
    )
    mapa = _datos_mapa_de_orden(session, orden)
    return {
        "estudio_id": estudio.id,
        "transportista": mapa["transportista"],
        "paradas": mapa["paradas"],
    }