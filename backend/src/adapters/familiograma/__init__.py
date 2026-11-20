"""Módulo 1 (Familiograma): se envían el paciente y todos los familiares juntos y vuelve una imagen SVG.

    from src.adapters.familiograma import FamiliarFamiliograma, PacienteFamiliograma, get_familiograma

    familiograma = get_familiograma()
    familiograma.parentescos()  # catálogo para el selector: guardar la etiqueta en familiar.parentesco
    archivo = familiograma.generar_familiograma(
        PacienteFamiliograma("Ana", "Pérez", edad=9),
        [FamiliarFamiliograma("progenitor", "Laura Gómez", diagnostico_previo="Gaucher")],
    )  # archivo.contenido (bytes) y archivo.tipo ("image/svg+xml"), o None si no hay familiares
"""
from src.adapters import crear_adaptador
from src.adapters.familiograma.interfaz import (ArchivoFamiliograma, FamiliarFamiliograma, Familiograma,
                                                PacienteFamiliograma, Parentesco)
from src.adapters.familiograma.mock import FamiliogramaMock
from src.adapters.familiograma.real import FamiliogramaReal


# Con la regla de sospecha activa (rayado), la API tarda más de 10 s. FAMILIOGRAMA_TIMEOUT lo pisa.
TIMEOUT_SEGUNDOS = 45


def get_familiograma() -> Familiograma:
    return crear_adaptador("FAMILIOGRAMA", mock=FamiliogramaMock, real=FamiliogramaReal, timeout=TIMEOUT_SEGUNDOS)


__all__ = ["ArchivoFamiliograma", "FamiliarFamiliograma", "Familiograma", "PacienteFamiliograma", "Parentesco",
           "get_familiograma"]
