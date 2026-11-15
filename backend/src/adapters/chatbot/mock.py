"""Chatbot simulado: respuestas fijas sobre las 5 patologías (no es una referencia clínica).

Recuerda EN MEMORIA la última patología de cada conversación, así "¿y cómo se hereda?" sigue el tema
(se pierde al reiniciar el backend). Devuelve los mismos tipos que la API real para probar la pantalla."""
import re
import threading
import uuid

from src.adapters.chatbot.interfaz import RespuestaChatbot, TipoRespuesta, validar_pregunta
from src.adapters.snomed.interfaz import normalizar

RESPUESTA_SALUDO = (
    "¡Hola! Puedo responder preguntas generales sobre estudios genéticos y sobre la enfermedad de Fabry, "
    "la enfermedad de Pompe, la mucopolisacaridosis tipo 1, la enfermedad de Gaucher y el déficit de "
    "esfingomielinasa ácida (ASMD). ¿Qué querés saber?"
)
RESPUESTA_FUERA_DE_ALCANCE = (
    "Solo puedo responder sobre estudios genéticos y sobre Fabry, Pompe, mucopolisacaridosis tipo 1, "
    "Gaucher y ASMD."
)
RESPUESTA_DERIVAR = (
    "No puedo dar diagnósticos, interpretar resultados ni hablar de síntomas propios o tratamientos. "
    "Consultalo con tu médico."
)

# (sinónimos normalizados, respuesta), en el orden de la tabla patologia
PATOLOGIAS = [
    (["fabry", "anderson-fabry"],
     "La enfermedad de Fabry es un trastorno lisosomal causado por variantes en el gen GLA, que reducen la "
     "actividad de la enzima alfa-galactosidasa A. Se hereda ligada al cromosoma X. Puede causar dolor en manos "
     "y pies, lesiones en la piel (angioqueratomas) y menor sudoración, y con el tiempo afectar riñones, "
     "corazón y cerebro."),
    (["pompe", "glucogenosis tipo 2", "glucogenosis tipo ii", "maltasa acida"],
     "La enfermedad de Pompe (glucogenosis tipo II) se debe a variantes en el gen GAA, que codifica la enzima "
     "alfa-glucosidasa ácida. Se hereda de forma autosómica recesiva: hacen falta las dos copias del gen "
     "afectadas. Afecta sobre todo a los músculos (debilidad e hipotonía) y, en la forma infantil, también "
     "al corazón y a la respiración."),
    (["mucopolisacaridosis 1", "mucopolisacaridosis tipo 1", "mucopolisacaridosis i", "mucopolisacaridosis tipo i",
      "mps 1", "mps1", "mps i", "mps-1", "hurler"],
     "La mucopolisacaridosis tipo 1 se debe a variantes en el gen IDUA (enzima alfa-L-iduronidasa). Se hereda "
     "de forma autosómica recesiva: hacen falta las dos copias del gen afectadas. Puede causar rigidez "
     "articular, opacidad de la córnea, agrandamiento del hígado y el bazo, hernias y baja estatura."),
    (["gaucher"],
     "La enfermedad de Gaucher se debe a variantes en el gen GBA1 (enzima glucocerebrosidasa). Se hereda de "
     "forma autosómica recesiva: hacen falta las dos copias del gen afectadas. Es frecuente el agrandamiento "
     "del bazo y del hígado, la anemia, la baja de plaquetas y el dolor óseo."),
    (["asmd", "esfingomielinasa", "niemann-pick", "niemann pick"],
     "El déficit de esfingomielinasa ácida (ASMD, antes llamado Niemann-Pick tipos A y B) se debe a variantes "
     "en el gen SMPD1. Se hereda de forma autosómica recesiva: hacen falta las dos copias del gen afectadas. "
     "Suele causar agrandamiento del hígado y el bazo, compromiso pulmonar, baja de plaquetas y alteraciones "
     "de los lípidos."),
]


def _patron(palabras: list[str]) -> re.Pattern:
    return re.compile(r"\b(" + "|".join(re.escape(p) for p in palabras) + r")\b")


_PATRONES = [(_patron(sinonimos), respuesta) for sinonimos, respuesta in PATOLOGIAS]
_DERIVAR = _patron(["tratamiento", "tratamientos", "medicamento", "medicacion", "mi resultado", "mis resultados",
                    "mi estudio", "me duele", "tengo sintomas", "diagnostico", "diagnosticar"])
_SALUDO = _patron(["hola", "buenas", "buen dia", "buenos dias", "buenas tardes", "gracias"])

_conversaciones: dict[str, list[str]] = {}
_lock = threading.Lock()


def reiniciar() -> None:
    """Olvida todas las conversaciones simuladas (para los tests)."""
    with _lock:
        _conversaciones.clear()


class ChatbotMock:
    def preguntar(self, pregunta: str, conversacion_id: str | None = None) -> RespuestaChatbot:
        texto = normalizar(validar_pregunta(pregunta, conversacion_id))
        conversacion_id = conversacion_id or str(uuid.uuid4())
        with _lock:
            tipo, respuestas = self._responder(texto, _conversaciones.get(conversacion_id, []))
            if tipo == TipoRespuesta.respuesta and respuestas[0] != RESPUESTA_SALUDO:
                _conversaciones[conversacion_id] = respuestas
        return RespuestaChatbot("\n\n".join(respuestas), conversacion_id, tipo)

    def _responder(self, texto: str, tema_anterior: list[str]) -> tuple[TipoRespuesta, list[str]]:
        if _DERIVAR.search(texto):
            return TipoRespuesta.derivar_medico, [RESPUESTA_DERIVAR]
        patologias = [respuesta for patron, respuesta in _PATRONES if patron.search(texto)]
        if patologias:
            return TipoRespuesta.respuesta, patologias
        if _SALUDO.search(texto):
            return TipoRespuesta.respuesta, [RESPUESTA_SALUDO]
        if tema_anterior:  # seguimiento: "¿y cómo se hereda?"
            return TipoRespuesta.respuesta, tema_anterior
        return TipoRespuesta.fuera_de_alcance, [RESPUESTA_FUERA_DE_ALCANCE]
