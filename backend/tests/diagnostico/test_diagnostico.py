"""Tests unitarios de la regla del diagnóstico presuntivo (sin base de datos): válido con el síntoma cardinal
o con al menos dos secundarios de la patología sospechada. Usa los síntomas reales de las 5 patologías."""
import uuid

import pytest

from src.adapters.snomed import mock as s
from src.adapters.snomed.mock import SINTOMAS_POR_PATOLOGIA
from src.core.clinico.diagnostico import MINIMO_SECUNDARIOS, validar_diagnostico, validar_diagnosticos
from src.core.models import Patologia, PatologiaSintoma, Sintoma


def patologia(nombre: str) -> Patologia:
    """La patología en memoria, con su cardinal y secundarios como quedan después del seed."""
    definicion = SINTOMAS_POR_PATOLOGIA[nombre]
    sintomas = [(definicion["cardinal"], True)] + [(x, False) for x in definicion["secundarios"]]
    return Patologia(
        id=uuid.uuid4(),
        nombre=nombre,
        sintomas=[PatologiaSintoma(sintoma=Sintoma(snomed_code=x.snomed_code, termino=x.termino), es_cardinal=c)
                  for x, c in sintomas],
    )


def codigos(*sintomas) -> list[str]:
    return [x.snomed_code for x in sintomas]


@pytest.fixture
def fabry():
    return patologia("Fabry")


def test_la_regla_pide_dos_secundarios():
    assert MINIMO_SECUNDARIOS == 2


# ---------- Cardinal presente: válido ----------

def test_cardinal_presente_es_valido(fabry):
    r = validar_diagnostico(fabry, codigos(s.DOLOR_NEUROPATICO))
    assert r.valido and r.cardinal_presente
    assert r.secundarios_presentes == ()
    assert r.motivo == "El paciente presenta el síntoma cardinal de Fabry (dolor neuropático)."


def test_cardinal_con_un_secundario_es_valido(fabry):
    r = validar_diagnostico(fabry, codigos(s.DOLOR_NEUROPATICO, s.PROTEINURIA))
    assert r.valido and r.cardinal_presente
    assert r.secundarios_presentes == ("proteinuria",)


# ---------- Sin cardinal y con dos o más secundarios: válido ----------

def test_sin_cardinal_con_dos_secundarios_es_valido(fabry):
    r = validar_diagnostico(fabry, codigos(s.PROTEINURIA, s.HIPOHIDROSIS))
    assert r.valido and not r.cardinal_presente
    assert r.secundarios_presentes == ("hipohidrosis", "proteinuria")
    assert r.motivo == "El paciente presenta 2 síntomas secundarios de Fabry: hipohidrosis, proteinuria."


def test_sin_cardinal_con_todos_los_secundarios_es_valido(fabry):
    todos = SINTOMAS_POR_PATOLOGIA["Fabry"]["secundarios"]
    r = validar_diagnostico(fabry, codigos(*todos))
    assert r.valido and len(r.secundarios_presentes) == len(todos)


# ---------- Sin cardinal y con uno o ningún secundario: inválido, con mensaje ----------

def test_sin_cardinal_con_un_secundario_es_invalido(fabry):
    r = validar_diagnostico(fabry, codigos(s.PROTEINURIA))
    assert not r.valido and not r.cardinal_presente
    assert r.secundarios_presentes == ("proteinuria",)
    assert r.motivo == (
        "El diagnóstico de Fabry no es consistente: el paciente no presenta el síntoma cardinal (dolor neuropático) "
        "y presenta solo 1 de los 2 síntomas secundarios necesarios (proteinuria)."
    )


def test_sin_cardinal_ni_secundarios_es_invalido(fabry):
    fiebre = s.OTROS_SINTOMAS[0]  # no es síntoma de ninguna de las 5 patologías
    r = validar_diagnostico(fabry, codigos(fiebre))
    assert not r.valido and r.secundarios_presentes == ()
    assert r.motivo == (
        "El diagnóstico de Fabry no es consistente: el paciente no presenta el síntoma cardinal (dolor neuropático) "
        "ni ningún síntoma secundario (se necesitan al menos 2)."
    )


def test_paciente_sin_sintomas_es_invalido(fabry):
    r = validar_diagnostico(fabry, [])
    assert not r.valido and "ni ningún síntoma secundario" in r.motivo


# ---------- Casos borde ----------

def test_los_sintomas_de_otra_patologia_no_cuentan(fabry):
    # Cardinal de Pompe y secundarios de Gaucher: nada de Fabry.
    r = validar_diagnostico(fabry, codigos(s.DEBILIDAD_MUSCULAR, s.ANEMIA, s.OSTEOPENIA))
    assert not r.valido and r.secundarios_presentes == ()


def test_un_codigo_repetido_no_cuenta_dos_veces(fabry):
    r = validar_diagnostico(fabry, codigos(s.PROTEINURIA, s.PROTEINURIA))
    assert not r.valido and r.secundarios_presentes == ("proteinuria",)


def test_un_sintoma_compartido_cuenta_para_cada_patologia_que_lo_tiene():
    # La opacidad corneal es secundaria de Fabry y de Mucopolisacaridosis 1.
    pacientes = codigos(s.OPACIDAD_CORNEAL, s.PROTEINURIA, s.HERNIA_UMBILICAL)
    fabry, mps1 = validar_diagnosticos([patologia("Fabry"), patologia("Mucopolisacaridosis 1")], pacientes)
    assert fabry.valido and fabry.secundarios_presentes == ("opacidad corneal", "proteinuria")
    assert mps1.valido and mps1.secundarios_presentes == ("hernia umbilical", "opacidad corneal")


def test_patologia_sin_cardinal_definido_no_rompe():
    sin_cardinal = Patologia(nombre="Incompleta", sintomas=[
        PatologiaSintoma(sintoma=Sintoma(snomed_code="29738008", termino="proteinuria"), es_cardinal=False),
    ])
    r = validar_diagnostico(sin_cardinal, ["29738008"])
    assert not r.valido and r.patologia_id is None
    assert "no presenta el síntoma cardinal y presenta solo 1" in r.motivo


# ---------- Varias patologías sospechadas: se valida cada una ----------

def test_con_varias_patologias_se_valida_cada_una():
    sospechadas = [patologia("Fabry"), patologia("Pompe"), patologia("Gaucher")]
    resultados = validar_diagnosticos(sospechadas, codigos(s.DOLOR_NEUROPATICO, s.HEPATOMEGALIA, s.ANEMIA))
    assert [(r.patologia, r.valido) for r in resultados] == [
        ("Fabry", True),    # cardinal
        ("Pompe", False),   # solo un secundario (hepatomegalia)
        ("Gaucher", True),  # dos secundarios (hepatomegalia y anemia)
    ]
    assert [r.patologia_id for r in resultados] == [str(p.id) for p in sospechadas]


@pytest.mark.parametrize("nombre", list(SINTOMAS_POR_PATOLOGIA))
def test_las_5_patologias_validan_con_su_cardinal_y_no_con_un_solo_secundario(nombre):
    definicion = SINTOMAS_POR_PATOLOGIA[nombre]
    assert validar_diagnostico(patologia(nombre), codigos(definicion["cardinal"])).valido
    assert not validar_diagnostico(patologia(nombre), codigos(definicion["secundarios"][0])).valido
    assert validar_diagnostico(patologia(nombre), codigos(*definicion["secundarios"][:2])).valido
