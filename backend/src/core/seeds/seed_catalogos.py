"""Catálogos mínimos del core. Idempotente: se puede correr varias veces.

    DATABASE_URL=postgresql+psycopg2://... python -m seeds.seed_catalogos

Las especialidades NO se siembran: el cliente pidió una lista estandarizada lo más completa posible
(cargarla desde un CSV oficial). Los centros de extracción tampoco (son ~100 y dependen de datos reales).
"""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from datetime import date
from decimal import Decimal

from src.core.enums import EstrategiaCdss
from src.core.models import Configuracion, Patologia, Provincia, Feriado, CentroExtraccion
from src.core.database import nueva_sesion

PROVINCIAS = [
    "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Catamarca", "Chaco", "Chubut", "Córdoba",
    "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", "Misiones",
    "Neuquén", "Río Negro", "Salta", "San Juan", "San Luis", "Santa Cruz", "Santa Fe",
    "Santiago del Estero", "Tierra del Fuego", "Tucumán",
]
PATOLOGIAS = ["Fabry", "Pompe", "Mucopolisacaridosis 1", "Gaucher", "ASMD"]

CENTROS_EXTRACCION = [
    # Ciudad Autónoma de Buenos Aires
    {
        "nombre": "Stamboulian Belgrano",
        "direccion": "Av. del Libertador 5868, CABA",
        "provincia": "Ciudad Autónoma de Buenos Aires",
        "latitud": Decimal("-34.558190"),
        "longitud": Decimal("-58.446800"),
    },
    {
        "nombre": "Stamboulian Barrio Norte",
        "direccion": "French 3085, CABA",
        "provincia": "Ciudad Autónoma de Buenos Aires",
        "latitud": Decimal("-34.590150"),
        "longitud": Decimal("-58.403400"),
    },
    {
        "nombre": "Centro Médico Rossi Microcentro",
        "direccion": "Esmeralda 141, CABA",
        "provincia": "Ciudad Autónoma de Buenos Aires",
        "latitud": Decimal("-34.606570"),
        "longitud": Decimal("-58.377720"),
    },
    # Buenos Aires (La Plata)
    {
        "nombre": "Instituto de Diagnóstico La Plata",
        "direccion": "Calle 62 Nº 370, La Plata, Buenos Aires",
        "provincia": "Buenos Aires",
        "latitud": Decimal("-34.928400"),
        "longitud": Decimal("-57.949500"),
    },
    {
        "nombre": "Laboratorio Dr. Celada",
        "direccion": "Av. 51 Nº 1762, La Plata, Buenos Aires",
        "provincia": "Buenos Aires",
        "latitud": Decimal("-34.918000"),
        "longitud": Decimal("-57.973500"),
    },
    # Córdoba
    {
        "nombre": "Laboratorios LACE Sede Central",
        "direccion": "Av. Vélez Sársfield 528, Córdoba",
        "provincia": "Córdoba",
        "latitud": Decimal("-31.419200"),
        "longitud": Decimal("-64.188700"),
    },
    {
        "nombre": "Fundación para el Progreso de la Medicina",
        "direccion": "9 de Julio 941, Córdoba",
        "provincia": "Córdoba",
        "latitud": Decimal("-31.411600"),
        "longitud": Decimal("-64.191500"),
    },
    {
        "nombre": "Laboratorio La Cordillera",
        "direccion": "Av. La Cordillera 3890, Córdoba",
        "provincia": "Córdoba",
        "latitud": Decimal("-31.353400"),
        "longitud": Decimal("-64.242100"),
    },
]

FERIADOS = [
    (date(2026, 1, 1), "Año Nuevo"),
    (date(2026, 2, 16), "Carnaval"),
    (date(2026, 2, 17), "Carnaval"),
    (date(2026, 3, 24), "Día Nacional de la Memoria por la Verdad y la Justicia"),
    (date(2026, 4, 2), "Día del Veterano y de los Caídos en la Guerra de Malvinas"),
    (date(2026, 4, 3), "Viernes Santo"),
    (date(2026, 5, 1), "Día del Trabajador"),
    (date(2026, 5, 25), "Día de la Revolución de Mayo"),
    (date(2026, 6, 15), "Paso a la Inmortalidad del Gral. Martín Miguel de Güemes"),
    (date(2026, 6, 20), "Paso a la Inmortalidad del Gral. Manuel Belgrano"),
    (date(2026, 7, 9), "Día de la Independencia"),
    (date(2026, 8, 17), "Paso a la Inmortalidad del Gral. José de San Martín"),
    (date(2026, 10, 12), "Día del Respeto a la Diversidad Cultural"),
    (date(2026, 11, 23), "Día de la Soberanía Nacional"),
    (date(2026, 12, 8), "Inmaculada Concepción de María"),
    (date(2026, 12, 25), "Navidad"),
]

def run() -> None:
    with nueva_sesion() as s:
        s.execute(insert(Provincia).values([{"nombre": n} for n in PROVINCIAS]).on_conflict_do_nothing(index_elements=["nombre"]))
        provincias_por_nombre = { p.nombre: p.id for p in s.scalars(select(Provincia)).all() }
        s.execute(insert(Patologia).values([{"nombre": n} for n in PATOLOGIAS]).on_conflict_do_nothing(index_elements=["nombre"]))
        s.execute(
            insert(Configuracion)
            .values(clave="cdss_estrategia", valor=EstrategiaCdss.mayor_cantidad_sintomas.value)
            .on_conflict_do_nothing(index_elements=["clave"])
        )
        s.execute(
            insert(CentroExtraccion)
            .values([
                {
                    "nombre": c["nombre"],
                    "direccion": c["direccion"],
                    "provincia_id": provincias_por_nombre[c["provincia"]],
                    "latitud": c["latitud"],
                    "longitud": c["longitud"],
                }
                for c in CENTROS_EXTRACCION
            ])
            .on_conflict_do_nothing(index_elements=["nombre"])
        )
        s.execute(
            insert(Feriado)
            .values([{"fecha": f, "descripcion": d} for f, d in FERIADOS])
            .on_conflict_do_nothing(index_elements=["fecha"])
        )
        s.commit()
        print("provincias:", len(s.scalars(select(Provincia)).all()), 
        "| patologías:", len(s.scalars(select(Patologia)).all()),
        "| centros:", len(s.scalars(select(CentroExtraccion)).all()),
        "| feriados:", len(s.scalars(select(Feriado)).all())
        )