"""Servicio de almacenamiento: guarda en la base y participa de la transacción de quien lo usa."""
import pytest
from sqlalchemy import func, select

from src.core.almacenamiento import service as almacenamiento
from src.core.almacenamiento.models import Archivo
from src.core.common.errors import ApiError


@pytest.fixture(autouse=True)
def sin_archivos(app, db):
    db.query(Archivo).delete()
    db.commit()


def test_guardar_y_leer(db):
    ruta = almacenamiento.guardar(db, b"<svg/>", "image/svg+xml", "familiograma.svg")
    db.commit()
    assert ruta.startswith("db/")
    archivo = almacenamiento.leer(db, ruta)
    assert (archivo.contenido, archivo.tipo, archivo.nombre) == (b"<svg/>", "image/svg+xml", "familiograma.svg")


def test_si_la_transaccion_se_deshace_el_archivo_no_queda(db):
    almacenamiento.guardar(db, b"x", "text/plain", "x.txt")
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Archivo)) == 0


def test_borrar(db):
    ruta = almacenamiento.guardar(db, b"x", "text/plain", "x.txt")
    almacenamiento.borrar(db, ruta)
    db.commit()
    with pytest.raises(ApiError) as e:
        almacenamiento.leer(db, ruta)
    assert e.value.status == 404


@pytest.mark.parametrize("ruta", ["", "db/no-es-uuid", "db/00000000-0000-0000-0000-000000000000", "supabase/x"])
def test_ruta_inexistente_da_404(db, ruta):
    with pytest.raises(ApiError) as e:
        almacenamiento.leer(db, ruta)
    assert e.value.codigo == "ARCHIVO_NO_ENCONTRADO"
