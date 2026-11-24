"""Consentimiento informado firmado: el paciente lo baja (ver documentos.py), lo firma y lo sube escaneado.

Reglas (pedido del profesor, cambia lo que dijo el cliente en la entrevista):
- Es uno por estudio. Si sube otro, reemplaza al anterior.
- Se puede cargar con el estudio Pagado o con el turno ya sacado, hasta que se registre la extracción.
- Sin el consentimiento cargado, el administrativo no puede registrar la extracción (ver registrar_extraccion).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.almacenamiento import service as almacenamiento
from src.core.common.errors import ApiError, validation_error
from src.core.enums import EstadoEstudio
from src.core.models import ConsentimientoFirmado, Usuario
from src.core.pagos.service import obtener_estudio

MAXIMO_MB = 5
MAXIMO_BYTES = MAXIMO_MB * 1024 * 1024
ESTADOS_PARA_CARGAR = (EstadoEstudio.pagado, EstadoEstudio.turno_sacado)


def consentimiento_de(session: Session, estudio_id) -> ConsentimientoFirmado | None:
    return session.scalars(select(ConsentimientoFirmado).where(ConsentimientoFirmado.estudio_id == estudio_id)).first()


def ver_consentimiento(session: Session, estudio_id: str, usuario: Usuario) -> ConsentimientoFirmado | None:
    """Si el estudio tiene el consentimiento cargado (para mostrar el estado en pantalla)."""
    estudio = obtener_estudio(session, estudio_id, usuario)  # un paciente solo ve los suyos
    return consentimiento_de(session, estudio.id)


def cargar_consentimiento(session: Session, estudio_id: str, paciente: Usuario, contenido: bytes | None) -> ConsentimientoFirmado:
    estudio = obtener_estudio(session, estudio_id, paciente, bloquear=True)
    if estudio.estado not in ESTADOS_PARA_CARGAR:
        raise ApiError(409, "ESTADO_INVALIDO", "El consentimiento se carga con el estudio pagado y antes de la extracción")
    if not contenido:
        raise validation_error([{"campo": "archivo", "problema": "Elegí el archivo del consentimiento firmado"}])
    if len(contenido) > MAXIMO_BYTES:
        raise ApiError(413, "ARCHIVO_DEMASIADO_GRANDE", f"El archivo supera los {MAXIMO_MB} MB")
    if not contenido.startswith(b"%PDF"):  # se mira el contenido, no la extensión del nombre
        raise validation_error([{"campo": "archivo", "problema": "El consentimiento tiene que ser un PDF"}])

    ruta = almacenamiento.guardar(session, contenido, "application/pdf", "consentimiento-firmado.pdf")
    consentimiento = consentimiento_de(session, estudio.id)
    if consentimiento is None:
        consentimiento = ConsentimientoFirmado(estudio_id=estudio.id, archivo_url=ruta, subido_por_id=paciente.id)
        session.add(consentimiento)
    else:  # reemplaza al anterior
        almacenamiento.borrar(session, consentimiento.archivo_url)
        consentimiento.archivo_url = ruta
        consentimiento.subido_por_id = paciente.id
    session.commit()
    session.refresh(consentimiento)  # trae la fecha de carga que pone la base
    return consentimiento


def leer_consentimiento(session: Session, estudio_id: str, usuario: Usuario) -> almacenamiento.ArchivoLeido:
    """El PDF firmado, para que lo vea el paciente o el administrativo antes de registrar la extracción."""
    consentimiento = ver_consentimiento(session, estudio_id, usuario)
    if consentimiento is None:
        raise ApiError(404, "CONSENTIMIENTO_NO_CARGADO", "El paciente todavía no cargó el consentimiento firmado")
    return almacenamiento.leer(session, consentimiento.archivo_url)