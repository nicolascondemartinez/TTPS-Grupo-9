"""Resumen de historia clínica grabado (escenario "Grabar el resumen de la historia clínica").

El médico graba con el micrófono del navegador, el audio se transcribe y el texto vuelve al formulario para que
lo revise y lo confirme. El audio no se guarda: lo único que queda es el texto confirmado, que se guarda con el
alta del paciente (`paciente.historia_clinica`).
"""
from src.adapters.transcripcion import FORMATOS_ACEPTADOS, FormatoNoSoportado, get_transcripcion
from src.core.common.errors import ApiError, validation_error

MAXIMO_AUDIO_MB = 10
MAXIMO_AUDIO_BYTES = MAXIMO_AUDIO_MB * 1024 * 1024  # unos 10 minutos de audio en webm


def transcribir_audio(audio: bytes | None, tipo: str | None) -> str:
    """El texto del audio, listo para que el médico lo edite. 400 si falta, está vacío o no es un formato que
    grabe el navegador; 413 si supera MAXIMO_AUDIO_MB."""
    if audio is None:
        raise validation_error([{"campo": "audio", "problema": "es obligatorio"}])
    if not audio:
        raise validation_error([{"campo": "audio", "problema": "está vacío: grabá de nuevo"}])
    if len(audio) > MAXIMO_AUDIO_BYTES:
        raise ApiError(413, "AUDIO_DEMASIADO_GRANDE", f"La grabación supera los {MAXIMO_AUDIO_MB} MB: grabala en partes")
    try:
        texto = get_transcripcion().transcribir(audio, tipo or "")
    except FormatoNoSoportado:
        formatos = ", ".join(f.split("/")[1] for f in FORMATOS_ACEPTADOS)
        raise validation_error([{"campo": "audio", "problema": f"no es un formato de audio soportado ({formatos})"}])
    return texto.strip()
