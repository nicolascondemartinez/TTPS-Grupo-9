"""Historia clínica: transcripción del resumen que el médico graba en el alta del paciente."""
from flask import Blueprint, request

from src.core.clinico.historia_clinica import MAXIMO_AUDIO_BYTES, MAXIMO_AUDIO_MB, transcribir_audio
from src.core.common.errors import ApiError
from src.web.security import require_permission

bp = Blueprint("historia_clinica", __name__)

_MARGEN_MULTIPART = 64 * 1024  # encabezados del formulario, además del audio


@bp.post("/historia-clinica/transcribir")
@require_permission("historia_clinica_grabar")
def transcribir():
    """multipart/form-data con el archivo en el campo "audio". Devuelve {"texto"}; el audio no se guarda."""
    if (request.content_length or 0) > MAXIMO_AUDIO_BYTES + _MARGEN_MULTIPART:  # antes de leer el cuerpo
        raise ApiError(413, "AUDIO_DEMASIADO_GRANDE", f"La grabación supera los {MAXIMO_AUDIO_MB} MB: grabala en partes")
    archivo = request.files.get("audio")
    audio = archivo.read() if archivo else None
    return {"texto": transcribir_audio(audio, archivo.mimetype if archivo else None)}
