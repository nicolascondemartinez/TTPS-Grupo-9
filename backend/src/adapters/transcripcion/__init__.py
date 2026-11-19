"""Transcripción de audio (escenario "Grabar el resumen de la historia clínica").

    from src.adapters.transcripcion import get_transcripcion

    texto = get_transcripcion().transcribir(audio, "audio/webm;codecs=opus")

No es uno de los módulos de otros grupos: el reparto lo marca como simulado, así que solo hay mock (devuelve
un texto de ejemplo). Por eso no sigue ADAPTERS_MODE: con ADAPTERS_MODE=real (por ejemplo, al desplegar) sigue
usando el mock. TRANSCRIPCION_MODE=real da error hasta que haya un servicio real (por ejemplo, Whisper en el
backend): para sumarlo, agregar real.py con la misma interfaz y crearlo con crear_adaptador como los demás.
"""
import os

from src.adapters.transcripcion.interfaz import (FORMATOS_ACEPTADOS, FormatoNoSoportado, Transcripcion,
                                                 es_formato_aceptado, tipo_base)
from src.adapters.transcripcion.mock import TranscripcionMock


def get_transcripcion() -> Transcripcion:
    if (os.environ.get("TRANSCRIPCION_MODE") or "").strip().lower() == "real":
        raise RuntimeError("TRANSCRIPCION_MODE=real: todavía no hay un servicio de transcripción real (usar mock)")
    return TranscripcionMock()


__all__ = ["FORMATOS_ACEPTADOS", "FormatoNoSoportado", "Transcripcion", "es_formato_aceptado", "get_transcripcion",
           "tipo_base"]
