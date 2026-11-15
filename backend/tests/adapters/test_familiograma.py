import xml.etree.ElementTree as ET

import pytest

from src.adapters.familiograma import FamiliarFamiliograma, PacienteFamiliograma, get_familiograma
from src.adapters.familiograma.mock import FamiliogramaMock
from src.adapters.snomed import SintomaSnomed
from src.core.common.errors import ApiError

PACIENTE = PacienteFamiliograma("Ana", "Pérez", edad=9)
FAMILIARES = [
    FamiliarFamiliograma("progenitor", "María Núñez", [SintomaSnomed("16294009", "esplenomegalia")], "Gaucher"),
    FamiliarFamiliograma("Hermano/a", "Juan <Juanchi> Pérez"),
]


@pytest.fixture
def mock():
    return FamiliogramaMock()


def test_get_familiograma_usa_el_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("FAMILIOGRAMA_MODE", raising=False)
    monkeypatch.delenv("ADAPTERS_MODE", raising=False)
    assert isinstance(get_familiograma(), FamiliogramaMock)


def test_parentescos_sin_el_paciente(mock):
    parentescos = mock.parentescos()
    assert len(parentescos) == 15
    assert parentescos[0].id == 1 and parentescos[0].nombre == "progenitor"
    assert all(p.id != 0 for p in parentescos)


def test_cero_familiares_no_genera_nada(mock):
    assert mock.generar_familiograma(PACIENTE, []) is None


def test_devuelve_un_svg_valido_con_los_familiares(mock):
    archivo = mock.generar_familiograma(PACIENTE, FAMILIARES)

    assert archivo.tipo == "image/svg+xml"
    raiz = ET.fromstring(archivo.contenido)  # XML bien formado, aunque un nombre tenga < >
    textos = [t.text for t in raiz.iter("{http://www.w3.org/2000/svg}text")]
    assert "Paciente: Ana Pérez" in textos
    assert "progenitor: María Núñez" in textos
    assert "    Diagnóstico previo: Gaucher" in textos
    assert "    Síntomas: esplenomegalia (16294009)" in textos
    assert "hermano/a: Juan <Juanchi> Pérez" in textos


def test_familiar_sin_apellido_o_parentesco_invalido_no_genera(mock):
    with pytest.raises(ApiError) as e:
        mock.generar_familiograma(PACIENTE, [FamiliarFamiliograma("madre", "Laura")])
    assert e.value.status == 400 and e.value.codigo == "VALIDACION"
    campos = {c["campo"] for c in e.value.detalle["campos"]}
    assert campos == {"familiares[0].parentesco", "familiares[0].nombre"}
