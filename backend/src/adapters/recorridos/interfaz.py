import uuid
from dataclasses import dataclass, field
from typing import Protocol

@dataclass(frozen=True)
class CentroParaOrdenar:
    id: uuid.UUID
    nombre: str
    direccion: str
    latitud: float
    longitud: float

@dataclass(frozen=True)
class RecorridoOptimizado: 
    paradas: list[CentroParaOrdenar]

class Recorridos(Protocol):
    def optimizar(self, centros: list[CentroParaOrdenar]) -> RecorridoOptimizado: ...