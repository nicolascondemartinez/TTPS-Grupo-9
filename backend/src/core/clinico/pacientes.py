"""Alta y listado de pacientes (escenario "Dar de alta el paciente").

El alta es una sola transacción: si algo falla, no queda un paciente a medias. Orden:
1. Datos ya validados (validation.validar_alta_paciente) y perfil de médico de quien da el alta.
2. DNI y mail no repetidos (409).
3. Diagnóstico presuntivo: sospecha clínica con la regla de #10 (cada patología), familiar con la regla de
   familiares (alguna patología diagnosticada en un familiar). Si no es consistente, 409 con el motivo.
4. Familiograma (si hay familiares y no se pidió seguir sin él): se genera antes de escribir nada.
5. Usuario (rol paciente, cambio de contraseña obligatorio), paciente, síntomas, patologías, familiares y
   familiograma; commit.
"""
import secrets
from dataclasses import asdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.core.auth.password import hash_contrasena
from src.core.clinico import familiares as familiares_service
from src.core.clinico.acceso import filtro_pacientes_visibles
from src.core.clinico.diagnostico import validar_diagnosticos, validar_sospecha_familiar
from src.core.clinico.service import obtener_patologia, sintoma_en_cache
from src.core.common.errors import ApiError
from src.core.enums import RolUsuario, TipoSospecha
from src.core.models import Medico, Paciente, Usuario


def _duplicado(campo: str) -> ApiError:
    if campo == "dni":
        return ApiError(409, "DNI_DUPLICADO", "Ya existe un paciente con ese DNI", {"campo": "dni"})
    return ApiError(409, "MAIL_EN_USO", "Ya existe un usuario con ese mail", {"campo": "email"})


def _validar_diagnostico(datos: dict, patologias, familiares) -> None:
    if datos["tipo_sospecha"] == TipoSospecha.familiar:
        valido, resultados = validar_sospecha_familiar(
            patologias, [(f.nombre, f.parentesco, f.patologia.id if f.patologia else None) for f in familiares])
        mensaje = "Para una sospecha familiar, cargá al familiar que tiene diagnosticada la patología sospechada."
    else:
        codigos = [s["snomed_code"] for s in datos["sintomas"]]
        resultados = validar_diagnosticos(patologias, codigos)
        valido = all(r.valido for r in resultados)
        mensaje = "El diagnóstico presuntivo no es consistente con los síntomas del paciente."
    if not valido:
        raise ApiError(409, "DIAGNOSTICO_INCONSISTENTE", mensaje, {
            "tipo_sospecha": datos["tipo_sospecha"].value,
            "resultados": [{**asdict(r), "cardinales_presentes": list(r.cardinales_presentes),
                            "secundarios_presentes": list(r.secundarios_presentes)} for r in resultados],
        })


def dar_de_alta(session: Session, datos: dict, medico: Usuario, hoy: date | None = None) -> Paciente:
    hoy = hoy or date.today()
    if session.get(Medico, medico.id) is None:
        raise ApiError(409, "SIN_PERFIL_MEDICO", "Tu usuario no tiene perfil de médico (matrícula): pedí que lo carguen")
    if session.scalar(select(Paciente.usuario_id).where(Paciente.dni == datos["dni"])) is not None:
        raise _duplicado("dni")
    if session.scalar(select(Usuario.id).where(func.lower(Usuario.email) == datos["email"])) is not None:
        raise _duplicado("email")

    patologias = [obtener_patologia(session, i) for i in datos["patologia_ids"]]
    familiares = familiares_service.preparar_familiares(session, datos["familiares"])
    _validar_diagnostico(datos, patologias, familiares)

    familiograma = None
    if not datos["sin_familiograma"]:
        familiograma = familiares_service.generar_familiograma(
            datos["nombre"], datos["apellido"], datos["fecha_nacimiento"], datos["sintomas"], familiares, al_dia=hoy)

    try:
        usuario = Usuario(
            email=datos["email"], nombre=datos["nombre"], apellido=datos["apellido"], telefono=datos["telefono"],
            rol=RolUsuario.paciente, debe_cambiar_password=True,
            # Contraseña al azar que nadie conoce hasta que se le envíen las credenciales (#15).
            password_hash=hash_contrasena(secrets.token_urlsafe(32)),
        )
        session.add(usuario)
        session.flush()
        paciente = Paciente(
            usuario_id=usuario.id, dni=datos["dni"], fecha_nacimiento=datos["fecha_nacimiento"],
            medico_alta_id=medico.id, tipo_sospecha=datos["tipo_sospecha"], historia_clinica=datos["historia_clinica"],
            diagnostico_presuntivo=patologias,
            sintomas=[sintoma_en_cache(session, s["snomed_code"], s["termino"]) for s in datos["sintomas"]],
        )
        session.add(paciente)
        session.flush()
        familiares_service.agregar_familiares(session, paciente, familiares)
        if familiograma is not None:
            familiares_service.guardar_familiograma(session, paciente, familiograma)
        session.commit()
    except IntegrityError as e:
        # Otro médico dio de alta el mismo DNI o mail en el mismo momento.
        session.rollback()
        raise _duplicado("dni" if "dni" in str(e.orig) else "email")
    except Exception:
        session.rollback()
        raise
    return paciente


def listar_pacientes(session: Session, usuario: Usuario) -> list[Paciente]:
    """Los pacientes que el usuario puede ver (el médico, los que dio de alta), del más nuevo al más viejo."""
    consulta = (
        select(Paciente)
        .where(filtro_pacientes_visibles(usuario))
        .options(selectinload(Paciente.usuario), selectinload(Paciente.diagnostico_presuntivo))
        .order_by(Paciente.created_at.desc())
    )
    return list(session.scalars(consulta))
