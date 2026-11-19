import pytest

from src.adapters.snomed import SintomaSnomed, get_snomed
from src.adapters.snomed.mock import SINTOMAS, SINTOMAS_POR_PATOLOGIA, SnomedMock
from src.core.seeds.seed_catalogos import PATOLOGIAS


@pytest.fixture
def snomed():
    return SnomedMock()


def terminos(resultado):
    return [s.termino for s in resultado]


def test_get_snomed_usa_el_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("SNOMED_MODE", raising=False)
    monkeypatch.delenv("ADAPTERS_MODE", raising=False)
    assert isinstance(get_snomed(), SnomedMock)


@pytest.mark.parametrize("texto", ["", "  ", "a", "he", " he ", None])
def test_menos_de_3_caracteres_no_busca(snomed, texto):
    assert snomed.buscar_sintomas(texto) == []


def test_devuelve_codigo_y_termino(snomed):
    resultado = snomed.buscar_sintomas("Esplenomegalia")
    assert resultado[0] == SintomaSnomed("16294009", "esplenomegalia")


def test_sin_distinguir_mayusculas_ni_tildes(snomed):
    assert terminos(snomed.buscar_sintomas("TONO MUSCULAR")) == ["tono muscular disminuido"]
    assert terminos(snomed.buscar_sintomas("óseo")) == terminos(snomed.buscar_sintomas("oseo")) == ["dolor óseo"]


def test_ordena_por_coincidencia(snomed):
    # exacto > empieza con > una palabra empieza con > lo contiene (y alfabético dentro de cada nivel)
    assert terminos(snomed.buscar_sintomas("esplenomegalia")) == ["esplenomegalia", "hepatoesplenomegalia"]
    assert terminos(snomed.buscar_sintomas("dolor")) == ["dolor abdominal", "dolor neuropático", "dolor óseo"]
    assert terminos(snomed.buscar_sintomas("hepato")) == ["hepatoesplenomegalia", "hepatomegalia"]
    assert terminos(snomed.buscar_sintomas("pulmonar")) == ["enfermedad pulmonar intersticial"]
    assert terminos(snomed.buscar_sintomas("megalia")) == ["esplenomegalia", "hepatoesplenomegalia", "hepatomegalia"]


def test_respeta_el_limite(snomed):
    assert len(snomed.buscar_sintomas("megalia", limite=2)) == 2


def test_sin_resultados(snomed):
    assert snomed.buscar_sintomas("xyz") == []


def test_cada_patologia_del_seed_tiene_cardinales_y_secundarios():
    assert set(SINTOMAS_POR_PATOLOGIA) == set(PATOLOGIAS)
    for definicion in SINTOMAS_POR_PATOLOGIA.values():
        assert definicion["cardinales"] and all(isinstance(c, SintomaSnomed) for c in definicion["cardinales"])
        assert len(definicion["secundarios"]) >= 3
        assert not set(definicion["cardinales"]) & set(definicion["secundarios"])


def test_todos_los_sintomas_de_las_patologias_se_encuentran_buscando(snomed):
    for definicion in SINTOMAS_POR_PATOLOGIA.values():
        for sintoma in (*definicion["cardinales"], *definicion["secundarios"]):
            assert sintoma in snomed.buscar_sintomas(sintoma.termino), sintoma


def test_codigos_unicos():
    codigos = [s.snomed_code for s in SINTOMAS]
    assert len(codigos) == len(set(codigos))
