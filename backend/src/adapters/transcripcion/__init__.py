"""Transcripción de audio (escenario "Grabar el resumen de la historia clínica").

    from src.adapters.transcripcion import get_transcripcion

    texto = get_transcripcion().transcribir(audio, "audio/webm;codecs=opus")

No es uno de los módulos de otros grupos: el reparto lo marca como simulado. Por eso no sigue ADAPTERS_MODE
(con ADAPTERS_MODE=real, por ejemplo al desplegar, sigue en mock) y no usa crear_adaptador (no hay API ni URL):

    TRANSCRIPCION_MODE    vacío o mock: devuelve un texto de ejemplo (por defecto, no necesita nada)
                          real: transcribe con Whisper en el backend (`poetry install --with transcripcion`)
    TRANSCRIPCION_MODELO  modelo de Whisper en modo real: base por defecto (tiny, base, small, ...)
"""
import os
from functools import lru_cache

from src.adapters.transcripcion.interfaz import (FORMATOS_ACEPTADOS, AudioIlegible, FormatoNoSoportado,
                                                 Transcripcion, es_formato_aceptado, tipo_base)
from src.adapters.transcripcion.mock import TranscripcionMock


@lru_cache(maxsize=None)
def _whisper(modelo: str) -> Transcripcion:
    """Carga el modelo una sola vez por proceso (tarda; la primera vez además lo descarga)."""
    from src.adapters.transcripcion.real import TranscripcionWhisper
    return TranscripcionWhisper(modelo)


def get_transcripcion() -> Transcripcion:
    modo = (os.environ.get("TRANSCRIPCION_MODE") or "mock").strip().lower()
    if modo == "mock":
        return TranscripcionMock()
    if modo == "real":
        from src.adapters.transcripcion.real import MODELO_POR_DEFECTO
        return _whisper((os.environ.get("TRANSCRIPCION_MODELO") or MODELO_POR_DEFECTO).strip())
    raise RuntimeError(f"TRANSCRIPCION_MODE inválido: {modo!r} (mock | real)")


__all__ = ["FORMATOS_ACEPTADOS", "AudioIlegible", "FormatoNoSoportado", "Transcripcion", "es_formato_aceptado",
           "get_transcripcion", "tipo_base"]
