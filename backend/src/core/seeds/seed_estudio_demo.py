"""Estudio de PRUEBA para probar presupuesto, pago y turnos mientras no exista el alta de estudio (P2).

    poetry run python -m src.core.seeds.seed_estudio_demo

Usa los usuarios de prueba de seed_usuarios_demo (correr antes `seed-db`). Les crea los perfiles que les
faltan (médico y paciente) y le da a paciente@exoma.test un estudio de Fabry en estado Creado con 8 genes
(presupuesto: USD 590). Se puede correr varias veces: si el paciente ya tiene un estudio, no crea otro.
No se ejecuta en producción.
"""
import os
import sys
from datetime import date

from sqlalchemy import func, select

from src.core.database import nueva_sesion
from src.core.enums import OrigenGen, TipoSospecha
from src.core.models import Analisis, AnalisisGen, AnalisisPatologia, Estudio, Gen, Medico, Paciente, Patologia, Usuario

MEDICO = "medico@exoma.test"
PACIENTE = "paciente@exoma.test"
GENES = ["GLA", "GAA", "IDUA", "GBA1", "SMPD1", "NPC1", "LIPA", "HEXA"]  # 8 genes: 5 incluidos + 3 adicionales


def _usuario(session, correo: str) -> Usuario:
    usuario = session.scalar(select(Usuario).where(func.lower(Usuario.email) == correo))
    if usuario is None:
        sys.exit(f"No existe {correo}: corré primero `flask --app main:create_app seed-db`")
    return usuario


def run() -> None:
    if os.environ.get("FLASK_ENV") == "production":
        sys.exit("No se crean datos de prueba en producción")
    with nueva_sesion() as session:
        medico = _usuario(session, MEDICO)
        paciente = _usuario(session, PACIENTE)
        fabry = session.scalar(select(Patologia).where(Patologia.nombre == "Fabry"))

        if session.get(Medico, medico.id) is None:
            session.add(Medico(usuario_id=medico.id, matricula="MP-DEMO-0001"))
            session.flush()
        if session.get(Paciente, paciente.id) is None:
            session.add(Paciente(
                usuario_id=paciente.id, dni="30111222", fecha_nacimiento=date(1990, 5, 14), medico_alta_id=medico.id,
                diagnostico_presuntivo_id=fabry.id, tipo_sospecha=TipoSospecha.clinica,
                historia_clinica="Paciente de prueba con sospecha clínica de enfermedad de Fabry.",
            ))
            session.flush()

        if session.scalar(select(Estudio.id).where(Estudio.paciente_id == paciente.id)):
            print(f"{PACIENTE} ya tiene un estudio: no se crea otro.")
            return

        estudio = Estudio(paciente_id=paciente.id, medico_id=medico.id)
        session.add(estudio)
        session.flush()
        analisis = Analisis(estudio_id=estudio.id, numero=1)
        session.add(analisis)
        session.flush()
        session.add(AnalisisPatologia(analisis_id=analisis.id, patologia_id=fabry.id))
        for simbolo in GENES:
            gen = session.scalar(select(Gen).where(Gen.simbolo == simbolo))
            if gen is None:
                gen = Gen(simbolo=simbolo)
                session.add(gen)
                session.flush()
            session.add(AnalisisGen(analisis_id=analisis.id, gen_id=gen.id, origen=OrigenGen.patologia))
        session.commit()
        print(f"Estudio de prueba creado para {PACIENTE} ({len(GENES)} genes, estado Creado).")


if __name__ == "__main__":
    from src.web import create_app

    with create_app().app_context():
        run()
