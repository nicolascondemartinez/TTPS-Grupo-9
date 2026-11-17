import uuid
import pytest

from src.adapters.recorridos import CentroParaOrdenar, get_recorridos
from src.adapters.recorridos.mock import RecorridosMock

def _centro(nombre: str, lat: float, lon: float) -> CentroParaOrdenar:
    return CentroParaOrdenar(
        id=uuid.uuid4(),
        nombre=nombre,
        direccion=f"Dir {nombre}",
        latitud=lat,
        longitud=lon,
    )

@pytest.fixture
def recorridos():
    return RecorridosMock()

def test_get_recorridos_usa_el_mock_por_defecto(monkeypatch):
    monkeypatch.delenv("RECORRIDOS_MODE", raising=False)
    monkeypatch.delenv("ADAPTERS_MODE", raising=False)
    assert isinstance(get_recorridos(), RecorridosMock)

def test_lista_vacia(recorridos):
    assert recorridos.optimizar([]).paradas == []

def test_un_solo_centro(recorridos):
    c = _centro("A", -34.60, -58.38)
    assert recorridos.optimizar([c]).paradas == [c]
    
def test_multiples_centros_orden_determinista_sin_perder_ni_repetir(recorridos):
    a = _centro("A - CABA", -34.60, -58.38)
    b = _centro("B - Córdoba", -31.41, -64.18)
    c = _centro("C - La Plata", -34.92, -57.95)
    r1 = recorridos.optimizar([b, c, a]).paradas
    r2 = recorridos.optimizar([c, a, b]).paradas
    # Siempre arranca por "A - CABA" y sigue por el más cercano ("C - La Plata", luego "B - Córdoba")
    assert r1 == [a, c, b]
    assert r2 == [a, c, b]
    assert len(r1) == 3 and len({p.id for p in r1}) == 3