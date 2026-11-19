"""Servicio de transcripción (#7): solo mock, acepta los formatos que graba el navegador."""
import pytest

from src.adapters.transcripcion import FormatoNoSoportado, get_transcripcion, tipo_base
from src.adapters.transcripcion.mock import TEXTO_DE_EJEMPLO, TranscripcionMock


def test_usa_el_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("TRANSCRIPCION_MODE", raising=False)
    monkeypatch.delenv("ADAPTERS_MODE", raising=False)
    assert isinstance(get_transcripcion(), TranscripcionMock)


def test_sigue_con_el_mock_aunque_los_demas_modulos_esten_en_real(monkeypatch):
    monkeypatch.delenv("TRANSCRIPCION_MODE", raising=False)
    monkeypatch.setenv("ADAPTERS_MODE", "real")
    assert isinstance(get_transcripcion(), TranscripcionMock)


def test_en_modo_real_avisa_que_no_hay_servicio(monkeypatch):
    monkeypatch.setenv("TRANSCRIPCION_MODE", "real")
    with pytest.raises(RuntimeError, match="no hay un servicio de transcripción real"):
        get_transcripcion()


@pytest.mark.parametrize("tipo", [
    "audio/webm", "audio/webm;codecs=opus",  # Chrome y Android
    "audio/ogg;codecs=opus",                 # Firefox
    "audio/mp4", "AUDIO/MP4",                # Safari (iPhone y Mac)
])
def test_acepta_los_formatos_del_navegador(tipo):
    assert TranscripcionMock().transcribir(b"audio", tipo) == TEXTO_DE_EJEMPLO


@pytest.mark.parametrize("tipo", ["", None, "video/mp4", "audio/wav", "application/pdf", "text/plain"])
def test_rechaza_otros_formatos(tipo):
    with pytest.raises(FormatoNoSoportado):
        TranscripcionMock().transcribir(b"audio", tipo)


def test_tipo_base_saca_los_parametros():
    assert tipo_base(" Audio/WebM ; codecs=opus") == "audio/webm"
    assert tipo_base(None) == ""
