import json

import pytest
import requests

from src.adapters import AdaptadorNoAutorizado, AdaptadorNoDisponible, HttpClient, RespuestaInvalida
from src.adapters.chatbot import DemasiadasConsultas, TipoRespuesta, get_chatbot
from src.adapters.chatbot.real import ChatbotReal
from src.core.common.errors import ApiError

URL = "https://chatbot.test/functions/v1/chat"
OK = {"respuesta": "El exoma es...", "conversacion_id": "6ba1b3fd", "tipo": "respuesta"}


class Api(requests.Session):
    def __init__(self, status=200, cuerpo=OK, headers=None):
        super().__init__()
        self.status, self.cuerpo, self.headers_respuesta, self.pedidos = status, cuerpo, headers or {}, []

    def request(self, method, url, **kwargs):
        self.pedidos.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = self.status
        response._content = json.dumps(self.cuerpo).encode()
        response.headers.update(self.headers_respuesta)
        return response


@pytest.fixture(autouse=True)
def clave_publica(monkeypatch):
    monkeypatch.setenv("CHATBOT_PUBLISHABLE_KEY", "sb_publishable_x")


def real(**kwargs) -> tuple[ChatbotReal, Api]:
    sesion = Api(**kwargs)
    return ChatbotReal(HttpClient("CHATBOT", URL, "token-del-grupo", header_api_key="x-chatbot-token",
                                  session=sesion)), sesion


def test_get_chatbot_real_manda_las_dos_credenciales(monkeypatch):
    monkeypatch.setenv("CHATBOT_MODE", "real")
    monkeypatch.setenv("CHATBOT_API_URL", URL)
    monkeypatch.setenv("CHATBOT_API_KEY", "token-del-grupo")
    monkeypatch.delenv("CHATBOT_TIMEOUT", raising=False)

    chatbot = get_chatbot()

    assert isinstance(chatbot, ChatbotReal) and chatbot.http.timeout == 20
    assert chatbot.http.session.headers["x-chatbot-token"] == "token-del-grupo"
    assert chatbot.http.session.headers["apikey"] == "sb_publishable_x"
    assert "X-API-Key" not in chatbot.http.session.headers


def test_sin_clave_publica_falla_al_crear(monkeypatch):
    monkeypatch.delenv("CHATBOT_PUBLISHABLE_KEY")
    with pytest.raises(RuntimeError, match="CHATBOT_PUBLISHABLE_KEY"):
        real()


def test_pregunta_y_devuelve_la_respuesta():
    chatbot, sesion = real()

    r = chatbot.preguntar("  ¿Qué es un exoma clínico? ", conversacion_id="6ba1b3fd")

    assert (r.texto, r.conversacion_id, r.tipo) == ("El exoma es...", "6ba1b3fd", TipoRespuesta.respuesta)
    method, url, kwargs = sesion.pedidos[0]
    assert (method, url) == ("POST", URL)
    assert kwargs["json"] == {"mensaje": "¿Qué es un exoma clínico?", "conversacion_id": "6ba1b3fd"}


def test_conversacion_nueva_manda_null():
    chatbot, sesion = real()
    chatbot.preguntar("hola")
    assert sesion.pedidos[0][2]["json"]["conversacion_id"] is None


@pytest.mark.parametrize("tipo, esperado", [
    ("derivar_medico", TipoRespuesta.derivar_medico), ("sin_informacion", TipoRespuesta.sin_informacion),
    ("tipo_nuevo", TipoRespuesta.respuesta),
])
def test_tipos(tipo, esperado):
    chatbot, _ = real(cuerpo={**OK, "tipo": tipo})
    assert chatbot.preguntar("hola").tipo == esperado


def test_pregunta_vacia_no_llama():
    chatbot, sesion = real()
    with pytest.raises(ApiError):
        chatbot.preguntar("   ")
    assert sesion.pedidos == []


def test_422_es_error_de_validacion():
    chatbot, _ = real(status=422, cuerpo={"detail": [{"loc": ["body", "mensaje"], "msg": "demasiado largo"}]})
    with pytest.raises(ApiError) as e:
        chatbot.preguntar("hola")
    assert e.value.status == 400 and e.value.detalle["campos"] == [{"campo": "pregunta", "problema": "demasiado largo"}]


def test_429_dice_cuanto_esperar():
    chatbot, _ = real(status=429, cuerpo={"detail": "límite"}, headers={"Retry-After": "12"})
    with pytest.raises(DemasiadasConsultas) as e:
        chatbot.preguntar("hola")
    assert e.value.status == 429 and e.value.detalle == {"reintentar_en": 12} and "12 segundos" in e.value.mensaje


def test_429_sin_retry_after():
    chatbot, _ = real(status=429, cuerpo={"detail": "límite"})
    with pytest.raises(DemasiadasConsultas) as e:
        chatbot.preguntar("hola")
    assert e.value.detalle == {"reintentar_en": 5}


def test_503_muestra_el_detail_de_la_api():
    chatbot, _ = real(status=503, cuerpo={"detail": "El chatbot está apagado por mantenimiento."})
    with pytest.raises(AdaptadorNoDisponible) as e:
        chatbot.preguntar("hola")
    assert e.value.status == 503 and e.value.mensaje == "El chatbot está apagado por mantenimiento."


def test_500_mensaje_generico():
    chatbot, _ = real(status=500, cuerpo={"detail": "Traceback interno"})
    with pytest.raises(AdaptadorNoDisponible) as e:
        chatbot.preguntar("hola")
    assert "no está disponible" in e.value.mensaje


def test_si_no_responde_el_error_es_tipado():
    sesion = Api()
    sesion.request = lambda *a, **k: (_ for _ in ()).throw(requests.Timeout())
    chatbot = ChatbotReal(HttpClient("CHATBOT", URL, "t", session=sesion))
    with pytest.raises(AdaptadorNoDisponible) as e:
        chatbot.preguntar("hola")
    assert e.value.status == 503 and e.value.codigo == "MODULO_NO_DISPONIBLE"


def test_401_es_error_de_configuracion():
    chatbot, _ = real(status=401, cuerpo={"detail": "token inválido"})
    with pytest.raises(AdaptadorNoAutorizado):
        chatbot.preguntar("hola")


def test_respuesta_sin_campos():
    chatbot, _ = real(cuerpo={"otra": 1})
    with pytest.raises(RespuestaInvalida):
        chatbot.preguntar("hola")
