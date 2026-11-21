"""Familiograma simulado: un SVG simple con la lista de familiares (el real también devuelve SVG).
Aplica las mismas reglas de vínculos que la API real (averiguadas contra ella, sin modificarla), con sus
mensajes ya legibles: así en desarrollo no aparecen sorpresas al pasar a modo real."""
from xml.sax.saxutils import escape

from src.core.common.errors import validation_error

from src.adapters.familiograma.interfaz import (TIPO_SVG, ArchivoFamiliograma, FamiliarFamiliograma,
                                                PacienteFamiliograma, Parentesco, validar_familiares)

PARENTESCOS = [Parentesco(i, nombre) for i, nombre in enumerate([
    "progenitor", "hermano/a", "abuelo/a materno/a", "abuelo/a paterno/a", "tío/a materno/a",
    "tío/a paterno/a", "primo/a materno/a", "primo/a paterno/a", "hijo/a", "medio hermano/a materno/a",
    "medio hermano/a paterno/a", "pareja del paciente", "suegro/a", "sobrino/a", "nieto/a",
], start=1)]

ALTO_LINEA = 20

PROGENITOR, HERMANO, ABUELO_MAT, ABUELO_PAT, TIO_MAT, TIO_PAT, PRIMO_MAT, PRIMO_PAT = range(1, 9)
HIJO, MEDIO_MAT, MEDIO_PAT, PAREJA, SUEGRO, SOBRINO, NIETO = range(9, 16)
LADO_MATERNO = {ABUELO_MAT, TIO_MAT, MEDIO_MAT}  # necesitan exactamente un progenitor mujer
LADO_PATERNO = {ABUELO_PAT, TIO_PAT, MEDIO_PAT}  # necesitan exactamente un progenitor hombre
REFERENCIAS = {  # parentesco -> (parentesco que tiene que estar en la lista, cómo se nombra)
    HERMANO: (PROGENITOR, "al menos un progenitor"),
    TIO_MAT: (ABUELO_MAT, "al menos un abuelo/a materno/a"),
    TIO_PAT: (ABUELO_PAT, "al menos un abuelo/a paterno/a"),
    PRIMO_MAT: (TIO_MAT, "un tío/a materno/a"),
    PRIMO_PAT: (TIO_PAT, "un tío/a paterno/a"),
    SOBRINO: (HERMANO, "un hermano/a"),
    NIETO: (HIJO, "un hijo/a del paciente"),
    SUEGRO: (PAREJA, "la pareja del paciente"),
}


class FamiliogramaMock:
    def parentescos(self) -> list[Parentesco]:
        return list(PARENTESCOS)

    def generar_familiograma(self, paciente: PacienteFamiliograma,
                             familiares: list[FamiliarFamiliograma]) -> ArchivoFamiliograma | None:
        if not familiares:
            return None
        etiquetas = {p.id: p.nombre for p in PARENTESCOS}
        validados = validar_familiares(familiares, PARENTESCOS)
        _verificar_vinculos(validados, etiquetas)
        lineas = ["Familiograma (simulado)", f"Paciente: {paciente.nombre} {paciente.apellido}", ""]
        for v in validados:
            sintomas = ", ".join(f"{s.termino} ({s.snomed_code})" for s in v.familiar.sintomas) or "ninguno"
            lineas += [
                f"{etiquetas[v.parentesco_id]}: {v.nombre} {v.apellido}",
                f"    Diagnóstico previo: {v.familiar.diagnostico_previo or 'ninguno'}",
                f"    Síntomas: {sintomas}",
            ]
        return ArchivoFamiliograma(_svg(lineas), TIPO_SVG)


def _verificar_vinculos(validados, etiquetas) -> None:
    """Las reglas de la API real: 422 allá, 400 por familiar acá (igual que lo traduce el adaptador real)."""
    presentes = {v.parentesco_id for v in validados}
    progenitores = [v for v in validados if v.parentesco_id == PROGENITOR]
    problemas, parejas = [], 0
    for i, v in enumerate(validados):
        quien = f'"{v.nombre} {v.apellido}" ({etiquetas[v.parentesco_id]})'
        problema = None
        if v.parentesco_id == PROGENITOR and progenitores.index(v) >= 2:
            problema = f'"{v.nombre} {v.apellido}": el paciente tiene como máximo dos progenitores.'
        elif v.parentesco_id == PAREJA:
            parejas += 1
            if parejas > 1:
                problema = f'"{v.nombre} {v.apellido}": el paciente tiene una sola pareja.'
        elif v.parentesco_id in LADO_MATERNO | LADO_PATERNO:
            sexo = "mujer" if v.parentesco_id in LADO_MATERNO else "hombre"
            cantidad = sum(1 for p in progenitores if p.familiar.sexo == sexo)
            if cantidad != 1:
                problema = f"{quien} necesita que haya exactamente un progenitor de sexo {sexo}; hay {cantidad}."
        if problema is None and v.parentesco_id in REFERENCIAS:
            requerido, nombre = REFERENCIAS[v.parentesco_id]
            if requerido not in presentes:
                problema = f"{quien} necesita {nombre} en la lista."
        if problema:
            problemas.append({"campo": f"familiares[{i}].parentesco", "problema": problema})
    if problemas:
        raise validation_error(problemas)


def _svg(lineas: list[str]) -> bytes:
    alto = ALTO_LINEA * (len(lineas) + 1)
    textos = "\n".join(
        f'<text x="20" y="{ALTO_LINEA * (i + 1)}" xml:space="preserve">{escape(linea)}</text>'
        for i, linea in enumerate(lineas)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{alto}" viewBox="0 0 800 {alto}">\n'
        f'<rect width="800" height="{alto}" fill="white"/>\n'
        f'<g font-family="Arial,sans-serif" font-size="14" fill="#172b3a">\n{textos}\n</g>\n</svg>\n'
    ).encode("utf-8")
