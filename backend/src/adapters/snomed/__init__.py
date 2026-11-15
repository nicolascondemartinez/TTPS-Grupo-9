"""Módulo 2 (SNOMED): búsqueda de síntomas mientras el médico escribe (desde 3 caracteres).

    from src.adapters.snomed import get_snomed

    for sintoma in get_snomed().buscar_sintomas("hepato"):
        sintoma.snomed_code, sintoma.termino
"""
from src.adapters import crear_adaptador
from src.adapters.snomed.interfaz import MINIMO_CARACTERES, SintomaSnomed, Snomed
from src.adapters.snomed.mock import SnomedMock
from src.adapters.snomed.real import SnomedReal

TIMEOUT_SEGUNDOS = 15  # recomendado por la presentación de la API


def get_snomed() -> Snomed:
    return crear_adaptador("SNOMED", mock=SnomedMock, real=SnomedReal, timeout=TIMEOUT_SEGUNDOS)


__all__ = ["MINIMO_CARACTERES", "SintomaSnomed", "Snomed", "get_snomed"]
