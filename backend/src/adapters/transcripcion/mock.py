from src.adapters.transcripcion.interfaz import FORMATOS_ACEPTADOS, FormatoNoSoportado, es_formato_aceptado

TEXTO_DE_EJEMPLO = (
    "Paciente de 8 años que consulta por dolor urente en manos y pies desde hace dos años, que empeora con el "
    "ejercicio y el calor. Refiere intolerancia al calor y disminución de la sudoración. Antecedente de un tío "
    "materno con insuficiencia renal. Al examen se observan lesiones puntiformes rojo oscuras en la región "
    "periumbilical."
)


class TranscripcionMock:
    """No transcribe: devuelve siempre el mismo texto de ejemplo (el reparto marca el servicio como simulado)."""

    def transcribir(self, audio: bytes, tipo: str) -> str:
        if not es_formato_aceptado(tipo):
            raise FormatoNoSoportado(f"Formato de audio no soportado: {tipo!r} (se aceptan {', '.join(FORMATOS_ACEPTADOS)})")
        return TEXTO_DE_EJEMPLO
