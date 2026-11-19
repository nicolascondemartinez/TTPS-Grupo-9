"""Restricciones del modelo de paciente y familiar en la base (DNI único, diagnóstico presuntivo con una o más
patologías, familiar con o sin diagnóstico previo)."""
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from src.core.enums import RolUsuario, TipoSospecha
from src.core.models import Familiar, Medico, Paciente, Patologia, Sintoma, paciente_patologia


@pytest.fixture(autouse=True)
def tablas_vacias(app, db):
    db.execute(text("TRUNCATE patologia, sintoma CASCADE"))
    db.commit()


@pytest.fixture
def fabry_y_pompe(db):
    fabry, pompe = Patologia(nombre="Fabry"), Patologia(nombre="Pompe")
    db.add_all([fabry, pompe])
    db.commit()
    return fabry, pompe


@pytest.fixture
def crear_paciente(db, crear_usuario, fabry_y_pompe):
    medico = crear_usuario(rol=RolUsuario.medico, correo="medico@exoma.test")
    db.add(Medico(usuario_id=medico.id, matricula="MP-0001"))
    db.commit()

    def _crear(correo="paciente@exoma.test", dni="30111222", patologias=None):
        usuario = crear_usuario(rol=RolUsuario.paciente, correo=correo)
        paciente = Paciente(
            usuario_id=usuario.id, dni=dni, fecha_nacimiento=date(1990, 1, 1), medico_alta_id=medico.id,
            diagnostico_presuntivo=list(patologias if patologias is not None else fabry_y_pompe[:1]),
            tipo_sospecha=TipoSospecha.clinica, historia_clinica="Resumen",
        )
        db.add(paciente)
        db.commit()
        return paciente

    return _crear


def test_no_se_pueden_crear_dos_pacientes_con_el_mismo_dni(db, crear_paciente):
    crear_paciente()
    with pytest.raises(IntegrityError):
        crear_paciente(correo="otro@exoma.test", dni="30111222")
    db.rollback()


def test_el_diagnostico_presuntivo_puede_tener_varias_patologias(db, crear_paciente, fabry_y_pompe):
    paciente = crear_paciente(patologias=fabry_y_pompe)
    db.expire_all()
    assert {p.nombre for p in db.get(Paciente, paciente.usuario_id).diagnostico_presuntivo} == {"Fabry", "Pompe"}


def test_no_se_borra_una_patologia_sospechada_en_un_paciente(db, crear_paciente, fabry_y_pompe):
    crear_paciente()
    db.execute(text("DELETE FROM patologia WHERE nombre = 'Pompe'"))  # Pompe no está sospechada: se puede
    db.commit()
    with pytest.raises(IntegrityError):
        db.execute(text("DELETE FROM patologia WHERE nombre = 'Fabry'"))
    db.rollback()


def test_al_borrar_el_paciente_se_borran_su_diagnostico_y_sus_familiares(db, crear_paciente, fabry_y_pompe):
    paciente = crear_paciente(patologias=fabry_y_pompe)
    paciente.familiares.append(Familiar(parentesco="madre", nombre="Ana", patologia_diagnosticada_id=None))
    db.commit()
    db.delete(paciente)
    db.commit()
    assert db.scalar(select(func.count()).select_from(paciente_patologia)) == 0
    assert db.scalar(select(func.count()).select_from(Familiar)) == 0
    assert db.scalar(select(func.count()).select_from(Patologia)) == 2  # las patologías quedan


def test_familiar_con_y_sin_diagnostico_previo(db, crear_paciente, fabry_y_pompe):
    fabry = fabry_y_pompe[0]
    paciente = crear_paciente()
    tos = Sintoma(snomed_code="49727002", termino="tos")
    paciente.familiares.extend([
        Familiar(parentesco="padre", nombre="Juan", patologia_diagnosticada_id=fabry.id, sintomas=[tos]),
        Familiar(parentesco="hermana", nombre="Sol"),  # ninguna patología diagnosticada
    ])
    db.commit()
    db.expire_all()
    familiares = {f.nombre: f for f in db.get(Paciente, paciente.usuario_id).familiares}
    assert familiares["Juan"].patologia_diagnosticada_id == fabry.id
    assert [s.termino for s in familiares["Juan"].sintomas] == ["tos"]
    assert familiares["Sol"].patologia_diagnosticada_id is None and familiares["Sol"].sintomas == []
