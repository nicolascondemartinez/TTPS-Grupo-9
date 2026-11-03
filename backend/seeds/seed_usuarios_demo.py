"""Usuarios de PRUEBA para desarrollo: uno por rol y un paciente en su primer ingreso.

    poetry run python -m seeds.seed_usuarios_demo

Solo crea filas en `usuario` (alcanza para probar el login y los permisos; los perfiles de médico,
paciente, etc. los crea el registro de usuarios). No se ejecuta en producción.
Contraseña de todos: Exoma2026!   (la del paciente nuevo se debe cambiar en el primer ingreso)
"""
import os
import sys

from sqlalchemy import func, select

from app.db.enums import RolUsuario
from app.db.models import Usuario
from app.db.session import SessionLocal
from app.services.password_service import hash_contrasena

CONTRASENA_DEMO = "Exoma2026!"

USUARIOS_DEMO = [
    ("paciente@exoma.test", "Paula", "Paciente", RolUsuario.paciente, False),
    ("paciente.nuevo@exoma.test", "Nicolás", "Primer Ingreso", RolUsuario.paciente, True),
    ("medico@exoma.test", "Marta", "Médica", RolUsuario.medico, False),
    ("gerente@exoma.test", "Gabriel", "Gerente", RolUsuario.gerente_medico, False),
    ("administrativo@exoma.test", "Ana", "Administrativa", RolUsuario.administrativo, False),
    ("bioinformatico@exoma.test", "Bruno", "Bioinformático", RolUsuario.bioinformatico, False),
    ("transportista@exoma.test", "Tomás", "Transportista", RolUsuario.transportista, False),
]


def run() -> None:
    if os.environ.get("FLASK_ENV") == "production":
        sys.exit("No se crean usuarios de prueba en producción")
    with SessionLocal() as session:
        creados = 0
        for correo, nombre, apellido, rol, debe_cambiar in USUARIOS_DEMO:
            if session.scalar(select(Usuario.id).where(func.lower(Usuario.email) == correo)) is None:
                session.add(
                    Usuario(
                        email=correo, password_hash=hash_contrasena(CONTRASENA_DEMO), nombre=nombre,
                        apellido=apellido, telefono="0000000000", rol=rol, debe_cambiar_password=debe_cambiar,
                    )
                )
                creados += 1
        session.commit()
        print(f"{creados} usuarios de prueba creados ({len(USUARIOS_DEMO) - creados} ya existían). Contraseña: {CONTRASENA_DEMO}")


if __name__ == "__main__":
    run()
