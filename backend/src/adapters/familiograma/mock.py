"""Familiograma simulado: un SVG simple con la lista de familiares (el real también devuelve SVG).
No aplica las reglas de personas de referencia de la API (por ejemplo, tío sin abuelo)."""
from xml.sax.saxutils import escape

from src.adapters.familiograma.interfaz import (TIPO_SVG, ArchivoFamiliograma, FamiliarFamiliograma,
                                                PacienteFamiliograma, Parentesco, validar_familiares)

PARENTESCOS = [Parentesco(i, nombre) for i, nombre in enumerate([
    "progenitor", "hermano/a", "abuelo/a materno/a", "abuelo/a paterno/a", "tío/a materno/a",
    "tío/a paterno/a", "primo/a materno/a", "primo/a paterno/a", "hijo/a", "medio hermano/a materno/a",
    "medio hermano/a paterno/a", "pareja del paciente", "suegro/a", "sobrino/a", "nieto/a",
], start=1)]

ALTO_LINEA = 20


class FamiliogramaMock:
    def parentescos(self) -> list[Parentesco]:
        return list(PARENTESCOS)

    def generar_familiograma(self, paciente: PacienteFamiliograma,
                             familiares: list[FamiliarFamiliograma]) -> ArchivoFamiliograma | None:
        if not familiares:
            return None
        etiquetas = {p.id: p.nombre for p in PARENTESCOS}
        lineas = ["Familiograma (simulado)", f"Paciente: {paciente.nombre} {paciente.apellido}", ""]
        for v in validar_familiares(familiares, PARENTESCOS):
            sintomas = ", ".join(f"{s.termino} ({s.snomed_code})" for s in v.familiar.sintomas) or "ninguno"
            lineas += [
                f"{etiquetas[v.parentesco_id]}: {v.nombre} {v.apellido}",
                f"    Diagnóstico previo: {v.familiar.diagnostico_previo or 'ninguno'}",
                f"    Síntomas: {sintomas}",
            ]
        return ArchivoFamiliograma(_svg(lineas), TIPO_SVG)


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
