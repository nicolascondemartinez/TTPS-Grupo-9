"""JSON de las patologías: nombre, síntomas cardinales y secundarios (código SNOMED y término)."""
from src.web.views.sintoma_view import sintoma_view


def patologia_view(patologia) -> dict:
    cardinales = sorted((ps.sintoma for ps in patologia.sintomas if ps.es_cardinal), key=lambda s: s.termino)
    secundarios = sorted((ps.sintoma for ps in patologia.sintomas if not ps.es_cardinal), key=lambda s: s.termino)
    return {
        "id": str(patologia.id),
        "nombre": patologia.nombre,
        "cardinales": [sintoma_view(s) for s in cardinales],
        "secundarios": [sintoma_view(s) for s in secundarios],
    }


def patologias_view(patologias) -> dict:
    return {"patologias": [patologia_view(p) for p in patologias]}
