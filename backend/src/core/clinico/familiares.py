"""Familiares del paciente y familiograma (escenarios "Cargar un familiar del paciente" y "Dar de alta el paciente").

En el alta (#14), en este orden:
1. `preparar_familiares` resuelve las patologías del diagnóstico previo (400 si alguna no existe).
2. `generar_familiograma` llama al módulo 1 ANTES de escribir nada en la base. Con cero familiares no lo llama.
   Si el módulo falla, 503 FAMILIOGRAMA_NO_DISPONIBLE: el médico reintenta o da el alta sin familiograma.
3. `agregar_familiares` y `guardar_familiograma` escriben en la misma transacción que el paciente (sin commit).
"""
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.adapters import AdaptadorError
from src.adapters.familiograma import (ArchivoFamiliograma, FamiliarFamiliograma, PacienteFamiliograma, Parentesco,
                                       get_familiograma)
from src.adapters.snomed import SintomaSnomed
from src.core.almacenamiento import service as almacenamiento
from src.core.almacenamiento.service import ArchivoLeido
from src.core.clinico.acceso import obtener_paciente_visible
from src.core.clinico.service import sintoma_en_cache
from src.core.common.errors import ApiError, validation_error
from src.core.models import Familiar, Paciente, Patologia, Usuario

NOMBRE_ARCHIVO = "familiograma.svg"


@dataclass(frozen=True)
class FamiliarNuevo:
    parentesco: str
    nombre: str
    sintomas: list[dict]  # [{snomed_code, termino}]
    patologia: Patologia | None  # diagnóstico previo (None: ninguno)


def parentescos() -> list[Parentesco]:
    """Catálogo del módulo 1 para el selector (guardar la etiqueta en familiar.parentesco)."""
    return get_familiograma().parentescos()


def preparar_familiares(session: Session, familiares: list[dict]) -> list[FamiliarNuevo]:
    """`familiares` ya validados (validation.validar_familiares)."""
    ids = {f["patologia_id"] for f in familiares if f["patologia_id"]}
    patologias = {str(p.id): p for p in session.scalars(select(Patologia).where(Patologia.id.in_(ids)))} if ids else {}
    problemas = [{"campo": f"familiares[{i}].patologia_id", "problema": "la patología no existe"}
                 for i, f in enumerate(familiares) if f["patologia_id"] and f["patologia_id"] not in patologias]
    if problemas:
        raise validation_error(problemas)
    return [FamiliarNuevo(f["parentesco"], f["nombre"], f["sintomas"], patologias.get(f["patologia_id"] or ""))
            for f in familiares]


def edad_en_anios(fecha_nacimiento: date, al_dia: date) -> float:
    return round((al_dia - fecha_nacimiento).days / 365.25, 2)


def generar_familiograma(nombre: str, apellido: str, fecha_nacimiento: date, sintomas: list[dict],
                         familiares: list[FamiliarNuevo], al_dia: date | None = None) -> ArchivoFamiliograma | None:
    """El SVG del familiograma, o None si no hay familiares (no se llama al módulo).
    400 si el módulo rechaza un dato de un familiar; 503 FAMILIOGRAMA_NO_DISPONIBLE si el módulo falla."""
    if not familiares:
        return None
    paciente = PacienteFamiliograma(
        nombre, apellido, edad=edad_en_anios(fecha_nacimiento, al_dia or date.today()),
        sintomas=[SintomaSnomed(**s) for s in sintomas],
    )
    datos = [FamiliarFamiliograma(f.parentesco, f.nombre, [SintomaSnomed(**s) for s in f.sintomas],
                                  f.patologia.nombre if f.patologia else None) for f in familiares]
    try:
        return get_familiograma().generar_familiograma(paciente, datos)
    except AdaptadorError as e:
        raise ApiError(503, "FAMILIOGRAMA_NO_DISPONIBLE",
                       "No pudimos generar el familiograma. Podés reintentar o dar de alta al paciente sin familiograma.",
                       {"motivo": e.mensaje})


def agregar_familiares(session: Session, paciente: Paciente, familiares: list[FamiliarNuevo]) -> None:
    """Sin commit: va en la transacción del alta."""
    for f in familiares:
        paciente.familiares.append(Familiar(
            parentesco=f.parentesco, nombre=f.nombre,
            patologia_diagnosticada_id=f.patologia.id if f.patologia else None,
            sintomas=[sintoma_en_cache(session, s["snomed_code"], s["termino"]) for s in f.sintomas],
        ))


def guardar_familiograma(session: Session, paciente: Paciente, archivo: ArchivoFamiliograma) -> None:
    """Guarda el SVG y lo asocia al paciente (reemplaza el anterior si había). Sin commit."""
    if paciente.familiograma_url:
        almacenamiento.borrar(session, paciente.familiograma_url)
    paciente.familiograma_url = almacenamiento.guardar(session, archivo.contenido, archivo.tipo, NOMBRE_ARCHIVO)


def familiograma_del_paciente(session: Session, paciente_id: str, usuario: Usuario) -> ArchivoLeido:
    paciente = obtener_paciente_visible(session, paciente_id, usuario)
    if not paciente.familiograma_url:
        raise ApiError(404, "SIN_FAMILIOGRAMA", "El paciente no tiene familiograma")
    return almacenamiento.leer(session, paciente.familiograma_url)
