"""Síntomas cardinales y secundarios de las 5 patologías iniciales (las crea seed_catalogos).

    poetry run flask --app main:create_app seed-db

Los códigos SNOMED son los del mock del módulo 2 (verificados contra la API real), así los tests de la
validación del diagnóstico y la base usan los mismos datos. Idempotente: solo completa las patologías
que todavía no tienen síntomas, para no pisar lo que haya modificado el gerente médico.
"""
from dataclasses import asdict

from sqlalchemy import select

from src.adapters.snomed.mock import SINTOMAS_POR_PATOLOGIA
from src.core.clinico.service import asignar_sintomas
from src.core.database import nueva_sesion
from src.core.models import Patologia


def cargar_sintomas_de_patologias(session) -> int:
    """Completa las patologías sin síntomas. Devuelve cuántas completó. No hace commit."""
    completadas = 0
    for nombre, definicion in SINTOMAS_POR_PATOLOGIA.items():
        patologia = session.scalar(select(Patologia).where(Patologia.nombre == nombre))
        if patologia is None or patologia.sintomas:
            continue
        asignar_sintomas(
            session, patologia,
            [asdict(s) for s in definicion["cardinales"]],
            [asdict(s) for s in definicion["secundarios"]],
        )
        completadas += 1
    return completadas


def run() -> None:
    with nueva_sesion() as session:
        completadas = cargar_sintomas_de_patologias(session)
        session.commit()
        print(f"síntomas de patologías: {completadas} completadas ({len(SINTOMAS_POR_PATOLOGIA) - completadas} ya tenían)")
