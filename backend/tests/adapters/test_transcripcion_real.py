"""Transcripción real con Whisper. Usa un faster_whisper falso: no descarga el modelo ni necesita tener
instalado el grupo opcional `transcripcion`."""
import sys
import types
from dataclasses import dataclass

import pytest

from src.adapters import transcripcion
from src.adapters.transcripcion import AudioIlegible, FormatoNoSoportado, get_transcripcion
from src.adapters.transcripcion.real import VOCABULARIO, TranscripcionWhisper


@dataclass
class Segmento:
    text: str


class WhisperFalso:
    creados = []

    def __init__(self, modelo, device, compute_type):
        self.modelo, self.pedidos = modelo, []
        WhisperFalso.creados.append(self)

    def transcribe(self, audio, **opciones):
        contenido = audio.read()
        self.pedidos.append((contenido, opciones))
        if contenido == b"roto":
            raise ValueError("Invalid data found when processing input")  # lo que lanza PyAV
        return iter([Segmento(" Paciente de doce años "), Segmento(" con hepatomegalia. ")]), None


@pytest.fixture(autouse=True)
def whisper_falso(monkeypatch):
    WhisperFalso.creados = []
    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=WhisperFalso))
    transcripcion._whisper.cache_clear()
    yield
    transcripcion._whisper.cache_clear()


def test_une_los_segmentos_y_pide_español_con_el_vocabulario():
    texto = TranscripcionWhisper().transcribir(b"audio", "audio/webm;codecs=opus")
    assert texto == "Paciente de doce años con hepatomegalia."
    contenido, opciones = WhisperFalso.creados[0].pedidos[0]
    assert contenido == b"audio"
    assert opciones["language"] == "es" and opciones["initial_prompt"] == VOCABULARIO


def test_rechaza_formatos_que_no_graba_el_navegador():
    with pytest.raises(FormatoNoSoportado):
        TranscripcionWhisper().transcribir(b"audio", "audio/wav")


def test_audio_que_no_se_puede_leer():
    with pytest.raises(AudioIlegible):
        TranscripcionWhisper().transcribir(b"roto", "audio/mp4")


def test_modo_real_usa_whisper_base_y_lo_carga_una_sola_vez(monkeypatch):
    monkeypatch.setenv("TRANSCRIPCION_MODE", "real")
    monkeypatch.delenv("TRANSCRIPCION_MODELO", raising=False)
    assert get_transcripcion() is get_transcripcion()
    assert [w.modelo for w in WhisperFalso.creados] == ["base"]


def test_se_puede_elegir_otro_modelo(monkeypatch):
    monkeypatch.setenv("TRANSCRIPCION_MODE", "real")
    monkeypatch.setenv("TRANSCRIPCION_MODELO", "small")
    get_transcripcion()
    assert WhisperFalso.creados[0].modelo == "small"


def test_sin_la_libreria_explica_como_instalarla(monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)  # import faster_whisper -> ImportError
    with pytest.raises(RuntimeError, match="poetry install --with transcripcion"):
        TranscripcionWhisper()
