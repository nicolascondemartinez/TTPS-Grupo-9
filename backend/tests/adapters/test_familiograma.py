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


# ---------- Reglas de vínculos (las mismas que la API real) ----------

def _f(parentesco, nombre, sexo="no_identificado"):
    return FamiliarFamiliograma(parentesco, nombre, sexo=sexo)


def _problemas(mock, familiares):
    from src.core.common.errors import ApiError
    with pytest.raises(ApiError) as e:
        mock.generar_familiograma(PACIENTE, familiares)
    return {c["campo"]: c["problema"] for c in e.value.detalle["campos"]}


@pytest.mark.parametrize("familiares", [
    [_f("progenitor", "Ana Ruiz", "mujer"), _f("abuelo/a materno/a", "Eva Ruiz")],
    [_f("progenitor", "Juan Ruiz", "hombre"), _f("abuelo/a paterno/a", "Leo Ruiz"), _f("tío/a paterno/a", "Tito Ruiz"),
     _f("primo/a paterno/a", "Pepe Ruiz")],
    [_f("progenitor", "Ana Ruiz", "mujer"), _f("hermano/a", "Sol Ruiz"), _f("sobrino/a", "Teo Ruiz")],
    [_f("hijo/a", "Mia Ruiz"), _f("nieto/a", "Lu Ruiz"), _f("pareja del paciente", "Mar Ruiz"), _f("suegro/a", "Ro Ruiz")],
])
def test_vinculos_validos(mock, familiares):
    assert mock.generar_familiograma(PACIENTE, familiares) is not None


def test_vinculos_invalidos(mock):
    assert _problemas(mock, [
        _f("progenitor", "Ana Ruiz", "mujer"), _f("progenitor", "Eva Ruiz", "mujer"), _f("progenitor", "Ivi Ruiz"),
        _f("abuelo/a materno/a", "Abu Ruiz"), _f("tío/a paterno/a", "Tito Ruiz"), _f("sobrino/a", "Teo Ruiz"),
        _f("pareja del paciente", "Mar Ruiz"), _f("pareja del paciente", "Lin Ruiz"),
    ]) == {
        "familiares[2].parentesco": '"Ivi Ruiz": el paciente tiene como máximo dos progenitores.',
        "familiares[3].parentesco": '"Abu Ruiz" (abuelo/a materno/a) necesita que haya exactamente un progenitor de '
                                    "sexo mujer; hay 2.",
        "familiares[4].parentesco": '"Tito Ruiz" (tío/a paterno/a) necesita que haya exactamente un progenitor de '
                                    "sexo hombre; hay 0.",
        "familiares[5].parentesco": '"Teo Ruiz" (sobrino/a) necesita un hermano/a en la lista.',
        "familiares[7].parentesco": '"Lin Ruiz": el paciente tiene una sola pareja.',
    }
