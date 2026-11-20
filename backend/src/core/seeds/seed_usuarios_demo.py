"""Usuarios de PRUEBA para desarrollo: uno por rol y un paciente en su primer ingreso.

    poetry run python -m seeds.seed_usuarios_demo

Solo crea filas en `usuario` (alcanza para probar el login y los permisos; los perfiles de médico,
paciente, etc. los crea el registro de usuarios). No se ejecuta en producción.
Contraseña de todos: Exoma2026!   (la del paciente nuevo se debe cambiar en el primer ingreso)
"""
import os
import sys

from sqlalchemy import func, select
from datetime import datetime, timedelta, timezone

from src.core.avisos import service as avisos_service
from src.core.avisos.models import Aviso
from src.core.enums import RolUsuario, TipoAviso
from src.core.models import Medico, Usuario
from src.core.database import nueva_sesion
from src.core.auth.password import hash_contrasena

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
# (tipo, título, mensaje, horas atrás, leído)
AVISOS_DEMO = {
    RolUsuario.paciente: [
        (TipoAviso.resultado_disponible, "Tu resultado está disponible",
         "Ya podés descargar el informe de tu exoma desde la sección Resultados.", 1, False),
        (TipoAviso.recordatorio_turno, "Recordatorio de turno",
         "Tenés un turno de extracción mañana. Recordá que el límite es de 5 inasistencias.", 5, False),
        (TipoAviso.puede_sacar_turno, "Ya podés sacar tu turno",
         "Tu estudio fue pagado. Elegí un centro de extracción y un horario.", 30, False),
        (TipoAviso.presupuesto_emitido, "Presupuesto disponible",
         "Emitimos el presupuesto de tu estudio. Podés abonarlo o elegir tu obra social.", 72, True),
    ],
    RolUsuario.medico: [
        (TipoAviso.resultado_disponible, "Resultado disponible",
         "Ya está el informe del estudio de uno de tus pacientes.", 2, False),
        (TipoAviso.resultado_disponible, "Resultado disponible",
         "Ya está el informe de otro estudio que derivaste.", 48, True),
    ],
    RolUsuario.administrativo: [
        (TipoAviso.reautorizacion_solicitada, "Reautorización solicitada",
         "Un paciente subió documentación judicial para reautorizar su estudio.", 3, False),
        (TipoAviso.reautorizacion_solicitada, "Reautorización solicitada",
         "Otro paciente presentó una resolución judicial favorable.", 26, True),
    ],
    RolUsuario.bioinformatico: [
        (TipoAviso.resultado_para_analizar, "Nuevo resultado para analizar",
         "Llegaron los datos crudos de un estudio. Ya está en la lista de estudios disponibles.", 1, False),
        (TipoAviso.resultado_para_analizar, "Nuevo resultado para analizar",
         "Se pidió el re-análisis de un estudio ya finalizado.", 20, True),
    ],
}


def _sembrar_avisos(session) -> int:
    """Avisos de ejemplo para los usuarios demo (menos el de primer ingreso). No repite si ya tienen."""
    ahora = datetime.now(timezone.utc)
    creados = 0
    usuarios = session.scalars(
        select(Usuario).where(Usuario.rol.in_(list(AVISOS_DEMO)), Usuario.debe_cambiar_password.is_(False))
    )
    for usuario in usuarios:
        if session.scalar(select(Aviso.id).where(Aviso.usuario_id == usuario.id).limit(1)) is not None:
            continue
        for tipo, titulo, mensaje, horas, leido in AVISOS_DEMO[usuario.rol]:
            aviso = avisos_service.notificar(session, usuario, tipo, titulo, mensaje)
            aviso.created_at = ahora - timedelta(hours=horas)
            if leido:
                aviso.leido, aviso.leido_at = True, aviso.created_at
            creados += 1
    return creados


MATRICULA_DEMO = "MP-DEMO-0001"  # la misma que usa seed_estudio_demo


def _perfil_medico_demo(session) -> None:
    """El médico demo necesita su perfil (tabla medico, con matrícula) para dar de alta pacientes."""
    medico = session.scalar(select(Usuario).where(func.lower(Usuario.email) == "medico@exoma.test"))
    if medico is not None and session.get(Medico, medico.id) is None:
        session.add(Medico(usuario_id=medico.id, matricula=MATRICULA_DEMO))


def run() -> None:
    if os.environ.get("FLASK_ENV") == "production":
        sys.exit("No se crean usuarios de prueba en producción")
    with nueva_sesion() as session:
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
        _perfil_medico_demo(session)
        session.commit()
        avisos = _sembrar_avisos(session)
        session.commit()
        print(f"{creados} usuarios de prueba creados ({len(USUARIOS_DEMO) - creados} ya existían). "
              f"{avisos} avisos de prueba creados. Contraseña: {CONTRASENA_DEMO}")