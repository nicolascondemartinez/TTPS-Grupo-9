"""Módulo 8 (Chatbot): preguntas en texto libre sobre estudios genéticos y las 5 patologías.

    from src.adapters.chatbot import get_chatbot

    primera = get_chatbot().preguntar("¿Qué es la enfermedad de Pompe?")
    siguiente = get_chatbot().preguntar("¿Y cómo se hereda?", conversacion_id=primera.conversacion_id)
    siguiente.texto  # mostrarlo tal cual; la pantalla debe aclarar que es un asistente automático

Errores: validación (400), DemasiadasConsultas (429, "esperá N segundos") o AdaptadorNoDisponible (503,
con un mensaje para mostrar). Nunca mandar datos personales en la pregunta.
"""
from src.adapters import crear_adaptador
from src.adapters.chatbot.interfaz import (LARGO_MAXIMO_PREGUNTA, Chatbot, DemasiadasConsultas, RespuestaChatbot,
                                          TipoRespuesta)
from src.adapters.chatbot.mock import ChatbotMock
from src.adapters.chatbot.real import ChatbotReal

TIMEOUT_SEGUNDOS = 20  # recomendado por la documentación del servicio


def get_chatbot() -> Chatbot:
    return crear_adaptador("CHATBOT", mock=ChatbotMock, real=ChatbotReal,
                           header_api_key="x-chatbot-token", timeout=TIMEOUT_SEGUNDOS)


__all__ = ["LARGO_MAXIMO_PREGUNTA", "Chatbot", "DemasiadasConsultas", "RespuestaChatbot", "TipoRespuesta",
           "get_chatbot"]
