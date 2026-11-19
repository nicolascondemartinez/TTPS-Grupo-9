"""Síntomas fijos para desarrollo y tests: no son una referencia clínica.

Códigos y términos verificados contra la API real (términos en minúscula, como los devuelve).
SINTOMAS_POR_PATOLOGIA (cardinales y secundarios por patología, como patologia_sintoma)
está para que los tests de la validación del diagnóstico usen los mismos datos.
"""
from src.adapters.snomed.interfaz import LIMITE_POR_DEFECTO, SintomaSnomed, normalizar, texto_buscable

_S = SintomaSnomed
DOLOR_NEUROPATICO = _S("247398009", "dolor neuropático")
ANGIOQUERATOMA = _S("254788004", "angioqueratoma cutáneo")
HIPOHIDROSIS = _S("45004005", "hipohidrosis")
OPACIDAD_CORNEAL = _S("64634000", "opacidad corneal")
PROTEINURIA = _S("29738008", "proteinuria")
AUDICION_DISMINUIDA = _S("103276001", "audición disminuida")
DEBILIDAD_MUSCULAR = _S("26544005", "debilidad muscular")
TONO_MUSCULAR_DISMINUIDO = _S("398151007", "tono muscular disminuido")
CARDIOMEGALIA = _S("8186001", "corazón agrandado")
DISNEA = _S("267036007", "disnea")
MACROGLOSIA = _S("25273001", "agrandamiento de la lengua")
HEPATOMEGALIA = _S("80515008", "hepatomegalia")
RIGIDEZ_ARTICULAR = _S("84445001", "rigidez articular")
HEPATOESPLENOMEGALIA = _S("36760000", "hepatoesplenomegalia")
HERNIA_UMBILICAL = _S("396347007", "hernia umbilical")
HERNIA_INGUINAL = _S("396232000", "hernia inguinal")
BAJA_ESTATURA = _S("277266007", "baja estatura")
ESPLENOMEGALIA = _S("16294009", "esplenomegalia")
TROMBOCITOPENIA = _S("302215000", "trastorno trombocitopénico")
ANEMIA = _S("271737000", "anemia")
DOLOR_OSEO = _S("12584003", "dolor óseo")
OSTEOPENIA = _S("312894000", "osteopenia")
ENFERMEDAD_PULMONAR_INTERSTICIAL = _S("233703007", "enfermedad pulmonar intersticial")
HIPERLIPIDEMIA = _S("55822004", "hiperlipidemia")

SINTOMAS_POR_PATOLOGIA = {
    "Fabry": {
        "cardinales": (DOLOR_NEUROPATICO,),
        "secundarios": (ANGIOQUERATOMA, HIPOHIDROSIS, OPACIDAD_CORNEAL, PROTEINURIA, AUDICION_DISMINUIDA),
    },
    "Pompe": {
        "cardinales": (DEBILIDAD_MUSCULAR,),
        "secundarios": (TONO_MUSCULAR_DISMINUIDO, CARDIOMEGALIA, DISNEA, MACROGLOSIA, HEPATOMEGALIA),
    },
    "Mucopolisacaridosis 1": {
        "cardinales": (RIGIDEZ_ARTICULAR,),
        "secundarios": (OPACIDAD_CORNEAL, HEPATOESPLENOMEGALIA, HERNIA_UMBILICAL, HERNIA_INGUINAL, BAJA_ESTATURA),
    },
    "Gaucher": {
        "cardinales": (ESPLENOMEGALIA,),
        "secundarios": (HEPATOMEGALIA, TROMBOCITOPENIA, ANEMIA, DOLOR_OSEO, OSTEOPENIA),
    },
    "ASMD": {
        "cardinales": (HEPATOESPLENOMEGALIA,),
        "secundarios": (ENFERMEDAD_PULMONAR_INTERSTICIAL, TROMBOCITOPENIA, HIPERLIPIDEMIA, BAJA_ESTATURA),
    },
}

# Síntomas que no son de ninguna de las 5 patologías, para probar la búsqueda y el diagnóstico.
OTROS_SINTOMAS = (
    _S("386661006", "fiebre"),
    _S("25064002", "cefalea"),
    _S("84229001", "fatiga"),
    _S("21522001", "dolor abdominal"),
    _S("62315008", "diarrea"),
)

SINTOMAS = tuple(
    {s.snomed_code: s for p in SINTOMAS_POR_PATOLOGIA.values() for s in (*p["cardinales"], *p["secundarios"])}.values()
) + OTROS_SINTOMAS


def _nivel_de_coincidencia(termino: str, texto: str) -> int | None:
    """0 exacto, 1 empieza con el texto, 2 alguna palabra empieza con el texto, 3 lo contiene."""
    if termino == texto:
        return 0
    if termino.startswith(texto):
        return 1
    if any(palabra.startswith(texto) for palabra in termino.split()):
        return 2
    if texto in termino:
        return 3
    return None


class SnomedMock:
    def buscar_sintomas(self, texto: str, limite: int = LIMITE_POR_DEFECTO) -> list[SintomaSnomed]:
        texto = texto_buscable(texto)
        if texto is None:
            return []
        buscado = normalizar(texto)
        coincidencias = []
        for sintoma in SINTOMAS:
            termino = normalizar(sintoma.termino)
            nivel = _nivel_de_coincidencia(termino, buscado)
            if nivel is not None:
                coincidencias.append((nivel, termino, sintoma))
        coincidencias.sort(key=lambda c: (c[0], c[1]))
        return [sintoma for _, _, sintoma in coincidencias[:limite]]
