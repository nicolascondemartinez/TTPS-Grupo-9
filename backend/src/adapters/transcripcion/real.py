"""Transcripción real con Whisper (faster-whisper), corriendo en el propio backend: el audio no sale del sistema.

Es opcional: necesita `poetry install --with transcripcion` y TRANSCRIPCION_MODE=real. El modelo (TRANSCRIPCION_MODELO,
"base" por defecto, unos 145 MB) se descarga la primera vez y se carga una sola vez, con la primera grabación.
"""
import io

from src.adapters.transcripcion.interfaz import (FORMATOS_ACEPTADOS, AudioIlegible, FormatoNoSoportado,
                                                 es_formato_aceptado)

MODELO_POR_DEFECTO = "base"

# Vocabulario de referencia: ayuda a que Whisper escriba bien los nombres de las patologías y los síntomas.
VOCABULARIO = (
    "Resumen de historia clínica. Al examen se observa. Enfermedad de Fabry, Pompe, Gaucher, Mucopolisacaridosis "
    "tipo 1, ASMD. Dolor neuropático, angioqueratoma, hipohidrosis, opacidad corneal, proteinuria, debilidad "
    "muscular, tono muscular disminuido, cardiomegalia, disnea, macroglosia, hepatomegalia, esplenomegalia, "
    "hepatoesplenomegalia, rigidez articular, hernia umbilical, trombocitopenia, anemia, osteopenia."
)


class TranscripcionWhisper:
    def __init__(self, modelo: str = MODELO_POR_DEFECTO):
        try:
            from faster_whisper import WhisperModel  # import tardío: es una dependencia opcional
        except ImportError as e:
            raise RuntimeError(
                "TRANSCRIPCION_MODE=real necesita faster-whisper: correr `poetry install --with transcripcion`"
            ) from e
        self._modelo = WhisperModel(modelo, device="cpu", compute_type="int8")

    def transcribir(self, audio: bytes, tipo: str) -> str:
        if not es_formato_aceptado(tipo):
            raise FormatoNoSoportado(f"Formato de audio no soportado: {tipo!r} (se aceptan {', '.join(FORMATOS_ACEPTADOS)})")
        try:
            segmentos, _ = self._modelo.transcribe(
                io.BytesIO(audio), language="es", vad_filter=True, initial_prompt=VOCABULARIO,
            )
            return " ".join(s.text.strip() for s in segmentos).strip()  # los segmentos se calculan al recorrerlos
        except Exception as e:  # PyAV no pudo decodificar el audio
            raise AudioIlegible("No se pudo leer el audio") from e
