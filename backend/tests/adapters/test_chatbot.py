import pytest

from src.adapters.chatbot import LARGO_MAXIMO_PREGUNTA, TipoRespuesta, get_chatbot
from src.adapters.chatbot import mock as chatbot_mock
from src.adapters.chatbot.mock import (RESPUESTA_DERIVAR, RESPUESTA_FUERA_DE_ALCANCE, RESPUESTA_SALUDO,
                                       ChatbotMock)
from src.core.common.errors import ApiError


@pytest.fixture(autouse=True)
def sin_conversaciones():
    chatbot_mock.reiniciar()
    yield
    chatbot_mock.reiniciar()


@pytest.fixture
def chatbot():
    return ChatbotMock()


def test_get_chatbot_usa_el_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("CHATBOT_MODE", raising=False)
    monkeypatch.delenv("ADAPTERS_MODE", raising=False)
    assert isinstance(get_chatbot(), ChatbotMock)


@pytest.mark.parametrize("pregunta, gen", [
    ("¿Qué es la enfermedad de Fabry?", "GLA"),
    ("pompe", "GAA"),
    ("Contame de la Mucopolisacaridosis 1", "IDUA"),
    ("¿Qué es el síndrome de Hurler?", "IDUA"),
    ("¿MPS I es grave?", "IDUA"),
    ("GAUCHER", "GBA1"),
    ("déficit de esfingomielinasa ácida", "SMPD1"),
    ("¿Niemann-Pick es lo mismo que ASMD?", "SMPD1"),
])
def test_responde_sobre_cada_patologia(chatbot, pregunta, gen):
    r = chatbot.preguntar(pregunta)
    assert gen in r.texto and r.tipo == TipoRespuesta.respuesta and r.conversacion_id


def test_mps_10_no_es_mps_1(chatbot):
    assert chatbot.preguntar("¿Qué es MPS 10?").tipo == TipoRespuesta.fuera_de_alcance


def test_varias_patologias_en_la_misma_pregunta(chatbot):
    texto = chatbot.preguntar("¿En qué se diferencian Gaucher y Fabry?").texto
    assert "GLA" in texto and "GBA1" in texto


def test_sigue_la_conversacion(chatbot):
    primera = chatbot.preguntar("¿Qué es Pompe?")
    seguimiento = ChatbotMock().preguntar("¿Y cómo se hereda?", conversacion_id=primera.conversacion_id)
    assert "GAA" in seguimiento.texto and seguimiento.conversacion_id == primera.conversacion_id
    assert chatbot.preguntar("¿Y cómo se hereda?").tipo == TipoRespuesta.fuera_de_alcance  # conversación nueva


def test_saludo(chatbot):
    r = chatbot.preguntar("Hola!")
    assert r.texto == RESPUESTA_SALUDO and r.tipo == TipoRespuesta.respuesta


@pytest.mark.parametrize("pregunta", ["¿Cuál es el tratamiento de Fabry?", "¿Qué significa mi resultado?",
                                      "Me duele la pierna"])
def test_deriva_al_medico(chatbot, pregunta):
    r = chatbot.preguntar(pregunta)
    assert r.texto == RESPUESTA_DERIVAR and r.tipo == TipoRespuesta.derivar_medico


def test_fuera_de_alcance(chatbot):
    r = chatbot.preguntar("¿Quién ganó el partido?")
    assert r.texto == RESPUESTA_FUERA_DE_ALCANCE and r.tipo == TipoRespuesta.fuera_de_alcance


@pytest.mark.parametrize("pregunta, conversacion_id, campo", [
    ("", None, "pregunta"), ("   ", None, "pregunta"), (None, None, "pregunta"),
    ("x" * (LARGO_MAXIMO_PREGUNTA + 1), None, "pregunta"), ("hola", "c" * 201, "conversacion_id"),
])
def test_datos_invalidos(chatbot, pregunta, conversacion_id, campo):
    with pytest.raises(ApiError) as e:
        chatbot.preguntar(pregunta, conversacion_id)
    assert e.value.status == 400 and e.value.detalle["campos"][0]["campo"] == campo
