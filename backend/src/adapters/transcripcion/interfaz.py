from typing import Protocol

# Lo que graba MediaRecorder: webm (Chrome, Android, Firefox), ogg (Firefox) y mp4 (Safari en iPhone y Mac).
FORMATOS_ACEPTADOS = ("audio/webm", "audio/ogg", "audio/mp4")


class FormatoNoSoportado(ValueError):
    """El audio no está en uno de los FORMATOS_ACEPTADOS."""


class AudioIlegible(ValueError):
    """El formato es aceptado pero el contenido no se puede leer (archivo cortado o dañado)."""


def tipo_base(tipo: str | None) -> str:
    """El tipo sin parámetros y en minúsculas: "audio/webm;codecs=opus" -> "audio/webm"."""
    return (tipo or "").split(";")[0].strip().lower()


def es_formato_aceptado(tipo: str | None) -> bool:
    return tipo_base(tipo) in FORMATOS_ACEPTADOS


class Transcripcion(Protocol):
    def transcribir(self, audio: bytes, tipo: str) -> str:
        """El texto del audio. `tipo` es el formato que informa el navegador (ej. "audio/webm;codecs=opus").
        Lanza FormatoNoSoportado si el formato no es uno de los aceptados y AudioIlegible si no se puede leer."""
        ...
