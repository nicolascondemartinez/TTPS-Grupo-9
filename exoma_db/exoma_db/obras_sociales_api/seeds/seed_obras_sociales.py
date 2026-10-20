"""Carga el listado de obras sociales desde un CSV y les asigna un % de cobertura.

El listado oficial está en https://www.sssalud.gob.ar/?page=listRnosc&tipo=7 (SSSalud no publica
porcentajes: los define el grupo). Exportalo a CSV con columnas: rnos,nombre,sigla

    DATABASE_URL=postgresql+psycopg2://... python -m seeds.seed_obras_sociales --csv obras_sociales.csv

Los porcentajes se reparten en ciclo entre PORCENTAJES (determinístico: mismo CSV -> mismo resultado),
con algunas al 100% para poder probar el escenario de cobertura total. Idempotente por código RNOS
(no pisa el porcentaje de una obra social ya cargada).
"""
import argparse
import csv
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert

from app.db.models import ObraSocial
from app.db.session import SessionLocal

PORCENTAJES = [Decimal(p) for p in ("100", "80", "70", "50", "100", "60", "40", "90")]


def run(csv_path: str) -> None:
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    registros = [
        {
            "rnos_codigo": fila["rnos"].strip(),
            "nombre": fila["nombre"].strip(),
            "sigla": (fila.get("sigla") or "").strip() or None,
            "porcentaje_cobertura": PORCENTAJES[i % len(PORCENTAJES)],
        }
        for i, fila in enumerate(filas)
    ]
    with SessionLocal() as s:
        s.execute(insert(ObraSocial).values(registros).on_conflict_do_nothing(index_elements=["rnos_codigo"]))
        s.commit()
    print(f"{len(registros)} obras sociales procesadas")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    run(ap.parse_args().csv)
