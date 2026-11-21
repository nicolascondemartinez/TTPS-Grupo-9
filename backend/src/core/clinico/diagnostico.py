"""Validación del diagnóstico presuntivo (escenarios "Validar el diagnóstico presuntivo" e "Impedir el alta
por diagnóstico inconsistente").

El diagnóstico es válido si el paciente tiene alguno de los síntomas cardinales de la patología sospechada
(puede tener varios) o al menos MINIMO_SECUNDARIOS de sus síntomas secundarios. Se compara por código SNOMED. Con varias patologías
sospechadas se valida cada una por separado.

Es una regla pura (no consulta la base ni APIs): recibe la patología con sus síntomas ya cargados.
Se aplica sea la sospecha clínica o familiar (pendiente de confirmar con el cliente).
"""
from collections.abc import Iterable
from dataclasses import dataclass

MINIMO_SECUNDARIOS = 2


@dataclass(frozen=True)
class ResultadoDiagnostico:
    patologia_id: str | None
    patologia: str  # nombre
    valido: bool
    motivo: str  # texto para mostrarle al médico
    cardinal_presente: bool  # True si tiene al menos uno de los cardinales
    cardinales_presentes: tuple[str, ...]  # términos de los cardinales que tiene el paciente
    secundarios_presentes: tuple[str, ...]  # términos de los secundarios que tiene el paciente


def _motivo(nombre: str, cardinales: list[str], cardinales_presentes: list[str], secundarios: list[str]) -> str:
    if len(cardinales_presentes) == 1:
        return f"El paciente presenta el síntoma cardinal de {nombre} ({cardinales_presentes[0]})."
    if cardinales_presentes:
        return f"El paciente presenta los síntomas cardinales de {nombre}: {', '.join(cardinales_presentes)}."
    if len(secundarios) >= MINIMO_SECUNDARIOS:
        return f"El paciente presenta {len(secundarios)} síntomas secundarios de {nombre}: {', '.join(secundarios)}."
    if len(cardinales) == 1:
        cardinal = f"el síntoma cardinal ({cardinales[0]})"
    elif cardinales:
        cardinal = f"ninguno de los síntomas cardinales ({', '.join(cardinales)})"
    else:
        cardinal = "el síntoma cardinal"
    inicio = f"El diagnóstico de {nombre} no es consistente: el paciente no presenta {cardinal}"
    if not secundarios:
        return f"{inicio} ni ningún síntoma secundario (se necesitan al menos {MINIMO_SECUNDARIOS})."
    return f"{inicio} y presenta solo 1 de los {MINIMO_SECUNDARIOS} síntomas secundarios necesarios ({secundarios[0]})."


def validar_diagnostico(patologia, codigos_del_paciente: Iterable[str]) -> ResultadoDiagnostico:
    """`patologia` es un modelo Patologia con `sintomas` (PatologiaSintoma) cargados;
    `codigos_del_paciente`, los códigos SNOMED de los síntomas del paciente."""
    codigos = set(codigos_del_paciente)
    cardinales = sorted(ps.sintoma.termino for ps in patologia.sintomas if ps.es_cardinal)
    cardinales_presentes = sorted(
        ps.sintoma.termino for ps in patologia.sintomas if ps.es_cardinal and ps.sintoma.snomed_code in codigos
    )
    secundarios = sorted(
        ps.sintoma.termino for ps in patologia.sintomas if not ps.es_cardinal and ps.sintoma.snomed_code in codigos
    )
    valido = bool(cardinales_presentes) or len(secundarios) >= MINIMO_SECUNDARIOS
    return ResultadoDiagnostico(
        patologia_id=str(patologia.id) if patologia.id else None,
        patologia=patologia.nombre,
        valido=valido,
        motivo=_motivo(patologia.nombre, cardinales, cardinales_presentes, secundarios),
        cardinal_presente=bool(cardinales_presentes),
        cardinales_presentes=tuple(cardinales_presentes),
        secundarios_presentes=tuple(secundarios),
    )


def validar_diagnosticos(patologias, codigos_del_paciente: Iterable[str]) -> list[ResultadoDiagnostico]:
    """Un resultado por cada patología sospechada (cada una se valida por separado)."""
    codigos = set(codigos_del_paciente)
    return [validar_diagnostico(p, codigos) for p in patologias]


# ---------- Sospecha familiar ----------
# El paciente se estudia porque un familiar tiene la enfermedad: puede no tener síntomas todavía. El diagnóstico
# es válido si AL MENOS UNA de las patologías sospechadas está diagnosticada en algún familiar cargado (puede
# sospecharse además otra patología propia del paciente). Pendiente de confirmar con el cliente.

def validar_sospecha_familiar(patologias, familiares) -> tuple[bool, list[ResultadoDiagnostico]]:
    """`familiares`: [(nombre, parentesco, patologia_id o None)]. Devuelve (válido, un resultado por patología)."""
    resultados = []
    for patologia in patologias:
        con_diagnostico = [(n, p) for n, p, pid in familiares if pid is not None and str(pid) == str(patologia.id)]
        if con_diagnostico:
            quienes = ", ".join(f"{n} ({p})" for n, p in con_diagnostico)
            motivo = f"Un familiar tiene diagnóstico de {patologia.nombre}: {quienes}."
        else:
            motivo = f"Ningún familiar cargado tiene diagnóstico de {patologia.nombre}."
        resultados.append(ResultadoDiagnostico(
            patologia_id=str(patologia.id) if patologia.id else None, patologia=patologia.nombre,
            valido=bool(con_diagnostico), motivo=motivo,
            cardinal_presente=False, cardinales_presentes=(), secundarios_presentes=(),
        ))
    return any(r.valido for r in resultados), resultados
