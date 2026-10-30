"""Catálogos mínimos del core. Idempotente: se puede correr varias veces.

    DATABASE_URL=postgresql+psycopg2://... python -m seeds.seed_catalogos

Las especialidades NO se siembran: el cliente pidió una lista estandarizada lo más completa posible
(cargarla desde un CSV oficial). Los centros de extracción tampoco (son ~100 y dependen de datos reales).
"""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.enums import EstrategiaCdss
from app.db.models import Configuracion, Patologia, Provincia
from app.db.session import SessionLocal

PROVINCIAS = [
    "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Catamarca", "Chaco", "Chubut", "Córdoba",
    "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", "Misiones",
    "Neuquén", "Río Negro", "Salta", "San Juan", "San Luis", "Santa Cruz", "Santa Fe",
    "Santiago del Estero", "Tierra del Fuego", "Tucumán",
]
PATOLOGIAS = ["Fabry", "Pompe", "Mucopolisacaridosis 1", "Gaucher", "ASMD"]


def run() -> None:
    with SessionLocal() as s:
        s.execute(insert(Provincia).values([{"nombre": n} for n in PROVINCIAS]).on_conflict_do_nothing(index_elements=["nombre"]))
        s.execute(insert(Patologia).values([{"nombre": n} for n in PATOLOGIAS]).on_conflict_do_nothing(index_elements=["nombre"]))
        s.execute(
            insert(Configuracion)
            .values(clave="cdss_estrategia", valor=EstrategiaCdss.mayor_cantidad_sintomas.value)
            .on_conflict_do_nothing(index_elements=["clave"])
        )
        s.commit()
        print("provincias:", len(s.scalars(select(Provincia)).all()), "| patologías:", len(s.scalars(select(Patologia)).all()))


if __name__ == "__main__":
    run()
