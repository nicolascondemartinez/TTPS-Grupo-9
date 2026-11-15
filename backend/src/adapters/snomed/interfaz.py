import unicodedata
from dataclasses import dataclass
from typing import Protocol

MINIMO_CARACTERES = 3
LIMITE_POR_DEFECTO = 20


@dataclass(frozen=True)
class SintomaSnomed:
    snomed_code: str  # mismos nombres que el modelo Sintoma (caché local)
    termino: str


class Snomed(Protocol):
    def buscar_sintomas(self, texto: str, limite: int = LIMITE_POR_DEFECTO) -> list[SintomaSnomed]:
        """Síntomas cuyo término coincide con el texto, ordenados por coincidencia.
        Con menos de 3 caracteres devuelve [] sin consultar."""
        ...


def texto_buscable(texto: str) -> str | None:
    """El texto listo para buscar, o None si no llega al mínimo de caracteres."""
    texto = (texto or "").strip()
    return texto if len(texto) >= MINIMO_CARACTERES else None


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: "Músculo" -> "musculo"."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.lower()
