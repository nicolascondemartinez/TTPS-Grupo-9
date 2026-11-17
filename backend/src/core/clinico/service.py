import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.adapters.snomed import SintomaSnomed, get_snomed
from src.core.clinico.diagnostico import ResultadoDiagnostico, validar_diagnosticos
from src.core.common.errors import ApiError
from src.core.common.validation import validar_uuid
from src.core.models import Patologia, PatologiaSintoma, Sintoma


def buscar_sintomas(texto: str) -> list[SintomaSnomed]:
    """Síntomas SNOMED que coinciden con el texto (módulo 2). Con menos de 3 caracteres devuelve []
    sin consultar. Si el módulo externo falla, el error del adaptador llega como 502/503."""
    return get_snomed().buscar_sintomas(texto)


# ---------- Patologías (las define el gerente médico) ----------

def _con_sintomas():
    return selectinload(Patologia.sintomas).selectinload(PatologiaSintoma.sintoma)


def listar_patologias(session: Session) -> list[Patologia]:
    return list(session.scalars(select(Patologia).options(_con_sintomas()).order_by(Patologia.nombre)))


def obtener_patologia(session: Session, patologia_id: str) -> Patologia:
    patologia = None
    if validar_uuid(patologia_id):
        patologia = session.scalar(
            select(Patologia).options(_con_sintomas()).where(Patologia.id == uuid.UUID(patologia_id))
        )
    if patologia is None:
        raise ApiError(404, "PATOLOGIA_NO_ENCONTRADA", "La patología no existe")
    return patologia


def sintoma_en_cache(session: Session, snomed_code: str, termino: str) -> Sintoma:
    """La fila de la caché local para ese código SNOMED (la crea si es la primera vez que se usa)."""
    sintoma = session.scalar(select(Sintoma).where(Sintoma.snomed_code == snomed_code))
    if sintoma is None:
        sintoma = Sintoma(snomed_code=snomed_code, termino=termino)
        session.add(sintoma)
        session.flush()
    return sintoma


def asignar_sintomas(session: Session, patologia: Patologia, cardinal: dict, secundarios: list[dict]) -> None:
    """Reemplaza los síntomas de la patología: un cardinal y los secundarios (ya validados). No hace commit."""
    if patologia.sintomas:
        patologia.sintomas.clear()
        session.flush()  # borra los anteriores antes de insertar (mismas PK y un solo cardinal)
    for datos, es_cardinal in [(cardinal, True), *((s, False) for s in secundarios)]:
        sintoma = sintoma_en_cache(session, datos["snomed_code"], datos["termino"])
        patologia.sintomas.append(PatologiaSintoma(sintoma=sintoma, es_cardinal=es_cardinal))


def crear_patologia(session: Session, nombre: str, cardinal: dict, secundarios: list[dict]) -> Patologia:
    if session.scalar(select(Patologia.id).where(func.lower(Patologia.nombre) == nombre.lower())) is not None:
        raise ApiError(409, "PATOLOGIA_DUPLICADA", "Ya existe una patología con ese nombre", {"campo": "nombre"})
    patologia = Patologia(nombre=nombre)
    session.add(patologia)
    session.flush()
    asignar_sintomas(session, patologia, cardinal, secundarios)
    session.commit()
    return obtener_patologia(session, str(patologia.id))


def validar_diagnostico_presuntivo(session: Session, patologia_ids: list[str], codigos_del_paciente: list[str]
                                   ) -> list[ResultadoDiagnostico]:
    """Un resultado por patología sospechada. 404 si alguna no existe."""
    patologias = [obtener_patologia(session, patologia_id) for patologia_id in patologia_ids]
    return validar_diagnosticos(patologias, codigos_del_paciente)


def modificar_patologia(session: Session, patologia_id: str, cardinal: dict, secundarios: list[dict]) -> Patologia:
    patologia = obtener_patologia(session, patologia_id)
    asignar_sintomas(session, patologia, cardinal, secundarios)
    session.commit()
    return obtener_patologia(session, patologia_id)
