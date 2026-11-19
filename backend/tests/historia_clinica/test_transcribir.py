"""POST /api/historia-clinica/transcribir (#12): el médico manda el audio grabado y recibe el texto para editar."""
from io import BytesIO

import pytest

from src.adapters.transcripcion.mock import TEXTO_DE_EJEMPLO
from src.core.clinico.historia_clinica import MAXIMO_AUDIO_BYTES
from src.core.enums import RolUsuario

RUTA = "/api/historia-clinica/transcribir"


@pytest.fixture(autouse=True)
def transcripcion_mock(monkeypatch):
    """Siempre el mock, aunque el .env local tenga TRANSCRIPCION_MODE=real."""
    monkeypatch.setenv("TRANSCRIPCION_MODE", "mock")


@pytest.fixture
def medico(api, crear_usuario):
    crear_usuario(rol=RolUsuario.medico, correo="medico@exoma.test")
    return api.token(correo="medico@exoma.test")


def enviar(api, token, audio=b"audio grabado", tipo="audio/webm;codecs=opus", nombre="grabacion.webm"):
    datos = {} if audio is None else {"audio": (BytesIO(audio), nombre, tipo)}
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return api.client.post(RUTA, data=datos, content_type="multipart/form-data", headers=headers)


def problema(respuesta):
    assert respuesta.status_code == 400, respuesta.get_json()
    return {c["campo"]: c["problema"] for c in respuesta.get_json()["error"]["detalle"]["campos"]}["audio"]


@pytest.mark.parametrize("tipo, nombre", [
    ("audio/webm;codecs=opus", "grabacion.webm"),  # Chrome y Android
    ("audio/ogg;codecs=opus", "grabacion.ogg"),    # Firefox
    ("audio/mp4", "grabacion.mp4"),                # Safari en iPhone
])
def test_el_medico_recibe_el_texto_transcripto(api, medico, tipo, nombre):
    r = enviar(api, medico, tipo=tipo, nombre=nombre)
    assert r.status_code == 200
    assert r.get_json() == {"texto": TEXTO_DE_EJEMPLO}


def test_sin_audio(api, medico):
    assert problema(enviar(api, medico, audio=None)) == "es obligatorio"


def test_audio_vacio(api, medico):
    assert problema(enviar(api, medico, audio=b"")) == "está vacío: grabá de nuevo"


@pytest.mark.parametrize("tipo, nombre", [("application/pdf", "estudio.pdf"), ("audio/wav", "grabacion.wav")])
def test_formato_no_soportado(api, medico, tipo, nombre):
    assert "no es un formato de audio soportado" in problema(enviar(api, medico, tipo=tipo, nombre=nombre))



def test_audio_que_no_se_puede_leer(api, medico, monkeypatch):
    from src.adapters.transcripcion import AudioIlegible
    from src.adapters.transcripcion.mock import TranscripcionMock

    def ilegible(self, audio, tipo):
        raise AudioIlegible("dañado")
    monkeypatch.setattr(TranscripcionMock, "transcribir", ilegible)
    assert problema(enviar(api, medico)) == "no se pudo leer: grabá de nuevo"

def test_audio_demasiado_grande(api, medico):
    r = enviar(api, medico, audio=b"0" * (MAXIMO_AUDIO_BYTES + 1))
    assert r.status_code == 413 and r.get_json()["error"]["codigo"] == "AUDIO_DEMASIADO_GRANDE"


def test_sin_token_recibe_401(api):
    assert enviar(api, None).status_code == 401


@pytest.mark.parametrize("rol", [RolUsuario.gerente_medico, RolUsuario.paciente, RolUsuario.administrativo])
def test_solo_el_medico_puede_transcribir(api, crear_usuario, rol):
    crear_usuario(rol=rol, correo="otro@exoma.test")
    assert enviar(api, api.token(correo="otro@exoma.test")).status_code == 403
