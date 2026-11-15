"""Módulo 5 (Bioinformática, Apigen): genes por patología, genes de hallazgos secundarios y variantes
por gen.

    from src.adapters.bioinformatica import get_bioinformatica

    for variante in get_bioinformatica().variantes_por_gen("GLA"):
        variante.codigo, variante.nombre, variante.clasificacion
"""
from src.adapters import crear_adaptador
from src.adapters.bioinformatica.interfaz import Bioinformatica, Variante
from src.adapters.bioinformatica.mock import BioinformaticaMock
from src.adapters.bioinformatica.real import BioinformaticaReal


def get_bioinformatica() -> Bioinformatica:
    return crear_adaptador("BIOINFORMATICA", mock=BioinformaticaMock, real=BioinformaticaReal,
                           header_api_key="apikey")


__all__ = ["Bioinformatica", "Variante", "get_bioinformatica"]
