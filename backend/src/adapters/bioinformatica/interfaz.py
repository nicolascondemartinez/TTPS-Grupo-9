from dataclasses import dataclass
from typing import Protocol

from src.core.enums import ClasificacionVariante


@dataclass(frozen=True)
class Variante:
    codigo: str  # se guarda en analisis_variante.variante_codigo
    nombre: str  # notación HGVS, la que se muestra
    clasificacion: ClasificacionVariante


class Bioinformatica(Protocol):
    def genes_por_patologia(self, patologia: str) -> list[str]:
        """Símbolos de los genes asociados a la patología (por nombre, como en la tabla patologia).
        Lista vacía si la patología no existe en el módulo."""
        ...

    def genes_hallazgos_secundarios(self) -> list[str]:
        """Símbolos de los genes que se leen cuando el paciente pide hallazgos secundarios."""
        ...

    def variantes_por_gen(self, gen: str) -> list[Variante]:
        """Variantes conocidas del gen (por símbolo). Lista vacía si el gen no existe en el módulo."""
        ...
