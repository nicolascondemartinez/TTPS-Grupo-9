"""Validación del diagnóstico presuntivo (escenarios "Validar el diagnóstico presuntivo" e "Impedir el alta
por diagnóstico inconsistente").

El diagnóstico es válido si el paciente tiene el síntoma cardinal de la patología sospechada o al menos
MINIMO_SECUNDARIOS de sus síntomas secundarios. Se compara por código SNOMED. Con varias patologías
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
    cardinal_presente: bool
    secundarios_presentes: tuple[str, ...]  # términos de los secundarios que tiene el paciente


def _motivo(nombre: str, termino_cardinal: str | None, cardinal_presente: bool, secundarios: list[str]) -> str:
    if cardinal_presente:
        return f"El paciente presenta el síntoma cardinal de {nombre} ({termino_cardinal})."
    if len(secundarios) >= MINIMO_SECUNDARIOS:
        return f"El paciente presenta {len(secundarios)} síntomas secundarios de {nombre}: {', '.join(secundarios)}."
    cardinal = f"el síntoma cardinal ({termino_cardinal})" if termino_cardinal else "el síntoma cardinal"
    inicio = f"El diagnóstico de {nombre} no es consistente: el paciente no presenta {cardinal}"
    if not secundarios:
        return f"{inicio} ni ningún síntoma secundario (se necesitan al menos {MINIMO_SECUNDARIOS})."
    return f"{inicio} y presenta solo 1 de los {MINIMO_SECUNDARIOS} síntomas secundarios necesarios ({secundarios[0]})."


def validar_diagnostico(patologia, codigos_del_paciente: Iterable[str]) -> ResultadoDiagnostico:
    """`patologia` es un modelo Patologia con `sintomas` (PatologiaSintoma) cargados;
    `codigos_del_paciente`, los códigos SNOMED de los síntomas del paciente."""
    codigos = set(codigos_del_paciente)
    cardinal = next((ps.sintoma for ps in patologia.sintomas if ps.es_cardinal), None)
    cardinal_presente = cardinal is not None and cardinal.snomed_code in codigos
    secundarios = sorted(
        ps.sintoma.termino for ps in patologia.sintomas if not ps.es_cardinal and ps.sintoma.snomed_code in codigos
    )
    valido = cardinal_presente or len(secundarios) >= MINIMO_SECUNDARIOS
    return ResultadoDiagnostico(
        patologia_id=str(patologia.id) if patologia.id else None,
        patologia=patologia.nombre,
        valido=valido,
        motivo=_motivo(patologia.nombre, cardinal.termino if cardinal else None, cardinal_presente, secundarios),
        cardinal_presente=cardinal_presente,
        secundarios_presentes=tuple(secundarios),
    )


def validar_diagnosticos(patologias, codigos_del_paciente: Iterable[str]) -> list[ResultadoDiagnostico]:
    """Un resultado por cada patología sospechada (cada una se valida por separado)."""
    codigos = set(codigos_del_paciente)
    return [validar_diagnostico(p, codigos) for p in patologias]
