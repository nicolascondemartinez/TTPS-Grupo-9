import pytest

from src.adapters.bioinformatica import Variante, get_bioinformatica
from src.adapters.bioinformatica.mock import BioinformaticaMock
from src.core.enums import ClasificacionVariante
from src.core.seeds.seed_catalogos import PATOLOGIAS


@pytest.fixture
def mock():
    return BioinformaticaMock()


def test_get_bioinformatica_usa_el_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("BIOINFORMATICA_MODE", raising=False)
    monkeypatch.delenv("ADAPTERS_MODE", raising=False)
    assert isinstance(get_bioinformatica(), BioinformaticaMock)


@pytest.mark.parametrize("patologia", PATOLOGIAS)
def test_cada_patologia_del_seed_tiene_genes(mock, patologia):
    assert len(mock.genes_por_patologia(patologia)) >= 1


def test_patologia_sin_distinguir_mayusculas(mock):
    assert mock.genes_por_patologia("  fabry ") == mock.genes_por_patologia("Fabry") == ["GLA"]


def test_patologia_desconocida_devuelve_lista_vacia(mock):
    assert mock.genes_por_patologia("Inexistente") == []


def test_hallazgos_secundarios(mock):
    assert len(mock.genes_hallazgos_secundarios()) >= 1


def test_todo_gen_del_mock_tiene_variantes_con_nombre_y_clasificacion(mock):
    genes = [g for p in PATOLOGIAS for g in mock.genes_por_patologia(p)] + mock.genes_hallazgos_secundarios()
    for gen in genes:
        variantes = mock.variantes_por_gen(gen)
        assert variantes, gen
        for v in variantes:
            assert isinstance(v, Variante)
            assert v.codigo and v.nombre
            assert isinstance(v.clasificacion, ClasificacionVariante)


def test_estan_las_cuatro_clasificaciones(mock):
    genes = [g for p in PATOLOGIAS for g in mock.genes_por_patologia(p)] + mock.genes_hallazgos_secundarios()
    clasificaciones = {v.clasificacion for g in genes for v in mock.variantes_por_gen(g)}
    assert clasificaciones == set(ClasificacionVariante)


def test_gen_desconocido_devuelve_lista_vacia(mock):
    assert mock.variantes_por_gen("NOEXISTE") == []


def test_modificar_la_lista_devuelta_no_altera_el_mock(mock):
    mock.genes_hallazgos_secundarios().clear()
    assert mock.genes_hallazgos_secundarios()
