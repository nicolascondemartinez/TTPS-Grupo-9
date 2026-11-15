from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from src.core.common.errors import ApiError, validation_error

LARGO_MAXIMO_PREGUNTA = 1000
LARGO_MAXIMO_CONVERSACION_ID = 200


class TipoRespuesta(str, Enum):
    respuesta = "respuesta"  # del tema (también saludos)
    fuera_de_alcance = "fuera_de_alcance"  # no es sobre estudios genéticos
    derivar_medico = "derivar_medico"  # pide diagnóstico, interpretar resultados, síntomas propios o tratamientos
    sin_informacion = "sin_informacion"  # del tema, pero sin datos (plazos, precios, trámites)


@dataclass(frozen=True)
class RespuestaChatbot:
    texto: str  # mostrarlo tal cual, sea cual sea el tipo
    conversacion_id: str  # mandarlo en el mensaje siguiente para seguir la conversación
    tipo: TipoRespuesta


class DemasiadasConsultas(ApiError):
    def __init__(self, segundos: int):
        super().__init__(429, "DEMASIADAS_CONSULTAS",
                         f"Hiciste muchas consultas seguidas. Esperá {segundos} segundos y volvé a intentar.",
                         {"reintentar_en": segundos})


class Chatbot(Protocol):
    def preguntar(self, pregunta: str, conversacion_id: str | None = None) -> RespuestaChatbot:
        """No mandar datos personales en la pregunta (nombre, DNI, mail, resultados): el servicio no tapa nombres.
        Errores: validación (400), DemasiadasConsultas (429) o AdaptadorNoDisponible (503, con un mensaje
        para mostrar)."""
        ...


def validar_pregunta(pregunta: str, conversacion_id: str | None) -> str:
    pregunta = (pregunta or "").strip()
    problemas = []
    if not pregunta:
        problemas.append({"campo": "pregunta", "problema": "es obligatoria"})
    elif len(pregunta) > LARGO_MAXIMO_PREGUNTA:
        problemas.append({"campo": "pregunta", "problema": f"admite como máximo {LARGO_MAXIMO_PREGUNTA} caracteres"})
    if conversacion_id is not None and len(conversacion_id) > LARGO_MAXIMO_CONVERSACION_ID:
        problemas.append({"campo": "conversacion_id",
                          "problema": f"admite como máximo {LARGO_MAXIMO_CONVERSACION_ID} caracteres"})
    if problemas:
        raise validation_error(problemas)
    return pregunta
