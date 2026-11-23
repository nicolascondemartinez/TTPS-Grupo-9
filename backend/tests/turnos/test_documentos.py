"""PDF de la orden de extracción y del consentimiento (sin base de datos)."""
from datetime import date, datetime

from src.core.turnos.calendario import ZONA_ARGENTINA
from src.core.turnos.documentos import DatosTurno, es_menor, generar_consentimiento, generar_orden

DATOS = DatosTurno(
    paciente="Paciente, Paula", dni="30111222", fecha_nacimiento=date(1990, 5, 14),
    estudio_id="3f2b9c1e-0000-0000-0000-000000000000",
    fecha_hora=datetime(2026, 11, 24, 9, 15, tzinfo=ZONA_ARGENTINA),
    centro="Centro La Plata", direccion="Calle 7 nº 450",
)


def test_la_orden_es_un_pdf():
    pdf = generar_orden(DATOS)
    assert pdf.startswith(b"%PDF")


def test_el_consentimiento_es_un_pdf():
    pdf = generar_consentimiento(DATOS)
    assert pdf.startswith(b"%PDF")


def test_mayoria_de_edad():
    turno = date(2026, 11, 24)
    assert es_menor(date(2026, 9, 1), turno)            # bebé de 3 meses
    assert es_menor(date(2008, 11, 25), turno)          # cumple 18 al día siguiente
    assert not es_menor(date(2008, 11, 24), turno)      # cumple 18 ese día
    assert not es_menor(date(1990, 5, 14), turno)
