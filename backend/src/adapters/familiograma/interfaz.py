from dataclasses import dataclass, field
from typing import Protocol

from src.adapters.snomed.interfaz import SintomaSnomed, normalizar
from src.core.common.errors import validation_error

TIPO_SVG = "image/svg+xml"


@dataclass(frozen=True)
class Parentesco:
    id: int
    nombre: str  # etiqueta del catálogo, la que se guarda en familiar.parentesco


@dataclass(frozen=True)
class PacienteFamiliograma:
    nombre: str
    apellido: str
    edad: float | None = None  # años, calculada de paciente.fecha_nacimiento
    sintomas: list[SintomaSnomed] = field(default_factory=list)


@dataclass(frozen=True)
class FamiliarFamiliograma:
    parentesco: str  # etiqueta del catálogo (ver parentescos())
    nombre: str  # nombre completo, como familiar.nombre: el apellido es la última palabra
    sintomas: list[SintomaSnomed] = field(default_factory=list)
    diagnostico_previo: str | None = None  # nombre de la patología diagnosticada


@dataclass(frozen=True)
class ArchivoFamiliograma:
    contenido: bytes
    tipo: str  # image/svg+xml
    advertencias: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FamiliarValidado:
    familiar: FamiliarFamiliograma
    parentesco_id: int
    nombre: str
    apellido: str


class Familiograma(Protocol):
    def parentescos(self) -> list[Parentesco]:
        """Catálogo para el selector de parentesco (sin el paciente)."""
        ...

    def generar_familiograma(self, paciente: PacienteFamiliograma,
                             familiares: list[FamiliarFamiliograma]) -> ArchivoFamiliograma | None:
        """La imagen del familiograma, o None si no hay familiares (no se llama a la API).
        Lanza un error de validación (400) si un familiar no tiene apellido o el parentesco no existe."""
        ...


def validar_familiares(familiares: list[FamiliarFamiliograma], catalogo: list[Parentesco]) -> list[FamiliarValidado]:
    ids = {normalizar(p.nombre): p.id for p in catalogo}
    validados, problemas = [], []
    for i, familiar in enumerate(familiares):
        parentesco_id = ids.get(normalizar(familiar.parentesco.strip()))
        if parentesco_id is None:
            problemas.append({"campo": f"familiares[{i}].parentesco",
                              "problema": "no es válido; opciones: " + ", ".join(p.nombre for p in catalogo)})
        partes = familiar.nombre.split()
        if len(partes) < 2:
            problemas.append({"campo": f"familiares[{i}].nombre", "problema": "ingresá nombre y apellido del familiar"})
        if not problemas:
            validados.append(FamiliarValidado(familiar, parentesco_id, " ".join(partes[:-1]), partes[-1]))
    if problemas:
        raise validation_error(problemas)
    return validados
