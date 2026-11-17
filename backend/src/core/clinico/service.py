from src.adapters.snomed import SintomaSnomed, get_snomed


def buscar_sintomas(texto: str) -> list[SintomaSnomed]:
    """Síntomas SNOMED que coinciden con el texto (módulo 2). Con menos de 3 caracteres devuelve []
    sin consultar. Si el módulo externo falla, el error del adaptador llega como 502/503."""
    return get_snomed().buscar_sintomas(texto)
