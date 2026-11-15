"""Adaptador real del módulo 8 (chatbot de GenLab).

Límite del servicio: 20 consultas por minuto para TODO el grupo; no consultar en bucle."""
import os

from src.adapters import AdaptadorNoDisponible, HttpClient, RespuestaInvalida, SolicitudRechazada
from src.adapters.chatbot.interfaz import (DemasiadasConsultas, RespuestaChatbot, TipoRespuesta,
                                          validar_pregunta)
from src.core.common.errors import validation_error

ESPERA_POR_DEFECTO = 5  # segundos, si el 429 no trae Retry-After


class ChatbotReal:
    def __init__(self, http: HttpClient):
        clave_publica = os.environ.get("CHATBOT_PUBLISHABLE_KEY", "").strip()
        if not clave_publica:
            raise RuntimeError("CHATBOT_MODE=real requiere CHATBOT_PUBLISHABLE_KEY")
        self.http = http
        self.http.session.headers["apikey"] = clave_publica

    def preguntar(self, pregunta: str, conversacion_id: str | None = None) -> RespuestaChatbot:
        pregunta = validar_pregunta(pregunta, conversacion_id)
        try:
            datos = self.http.post("", {"mensaje": pregunta, "conversacion_id": conversacion_id})
        except SolicitudRechazada as e:
            if e.status_externo == 422:
                raise validation_error(_campos_invalidos(e.cuerpo))
            raise
        except AdaptadorNoDisponible as e:
            if e.status_externo == 429:
                raise DemasiadasConsultas(e.reintentar_en or ESPERA_POR_DEFECTO)
            detalle = e.cuerpo.get("detail") if isinstance(e.cuerpo, dict) else None
            if e.status_externo == 503 and isinstance(detalle, str) and detalle.strip():
                e.mensaje = detalle  # la API pide mostrarlo tal cual (chatbot apagado)
            raise
        try:
            tipo = datos["tipo"]
            # Un tipo nuevo no tiene que romper la pantalla: el texto se muestra igual.
            tipo = TipoRespuesta(tipo) if tipo in TipoRespuesta._value2member_map_ else TipoRespuesta.respuesta
            return RespuestaChatbot(str(datos["respuesta"]), str(datos["conversacion_id"]), tipo)
        except (KeyError, TypeError):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "chat"})


def _campos_invalidos(cuerpo) -> list[dict]:
    detalle = cuerpo.get("detail") if isinstance(cuerpo, dict) else None
    if isinstance(detalle, list):
        campos = [{"campo": "pregunta", "problema": str(d.get("msg", d)) if isinstance(d, dict) else str(d)}
                  for d in detalle]
        if campos:
            return campos
    return [{"campo": "pregunta", "problema": str(detalle or "no es válida")}]
