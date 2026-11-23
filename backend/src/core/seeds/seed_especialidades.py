"""Especialidades médicas estandarizadas. Idempotente: se puede correr varias veces.

    poetry run python -m seeds.seed_especialidades

Para ampliar la lista alcanza con agregar nombres a ESPECIALIDADES y volver a correr seed-db.
"""
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from src.core.database import nueva_sesion
from src.core.models import Especialidad

ESPECIALIDADES = [
    "Alergia e inmunología",
    "Anatomía patológica",
    "Anestesiología",
    "Cardiología",
    "Cardiología infantil",
    "Cirugía cardiovascular",
    "Cirugía general",
    "Cirugía pediátrica",
    "Cirugía plástica",
    "Clínica médica",
    "Dermatología",
    "Diagnóstico por imágenes",
    "Endocrinología",
    "Endocrinología infantil",
    "Gastroenterología",
    "Gastroenterología infantil",
    "Genética médica",
    "Geriatría",
    "Ginecología",
    "Hematología",
    "Infectología",
    "Kinesiología y fisiatría",
    "Medicina del trabajo",
    "Medicina familiar",
    "Medicina legal",
    "Nefrología",
    "Nefrología infantil",
    "Neonatología",
    "Neumología",
    "Neumonología infantil",
    "Neurocirugía",
    "Neurología",
    "Neurología infantil",
    "Nutrición",
    "Obstetricia",
    "Oftalmología",
    "Oncología",
    "Otorrinolaringología",
    "Pediatría",
    "Psiquiatría",
    "Reumatología",
    "Terapia intensiva",
    "Toxicología",
    "Traumatología y ortopedia",
    "Urología",
]


def run() -> None:
    with nueva_sesion() as session:
        session.execute(
            insert(Especialidad)
            .values([{"nombre": n} for n in ESPECIALIDADES])
            .on_conflict_do_nothing(index_elements=["nombre"])
        )
        session.commit()
        print("especialidades:", session.scalar(select(func.count()).select_from(Especialidad)))