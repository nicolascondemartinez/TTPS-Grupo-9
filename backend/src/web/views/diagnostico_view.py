"""JSON de la validación del diagnóstico presuntivo: un resultado por patología, con el motivo para el médico."""


def resultado_diagnostico_view(resultado) -> dict:
    return {
        "patologia_id": resultado.patologia_id,
        "patologia": resultado.patologia,
        "valido": resultado.valido,
        "motivo": resultado.motivo,
        "cardinal_presente": resultado.cardinal_presente,
        "secundarios_presentes": list(resultado.secundarios_presentes),
    }


def validacion_diagnostico_view(resultados) -> dict:
    return {
        "valido": all(r.valido for r in resultados),
        "resultados": [resultado_diagnostico_view(r) for r in resultados],
    }
