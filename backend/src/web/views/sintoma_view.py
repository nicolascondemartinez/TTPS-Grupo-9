"""JSON de la búsqueda de síntomas SNOMED."""


def sintoma_view(sintoma) -> dict:
    return {"snomed_code": sintoma.snomed_code, "termino": sintoma.termino}


def sintomas_view(sintomas) -> dict:
    return {"sintomas": [sintoma_view(s) for s in sintomas]}
