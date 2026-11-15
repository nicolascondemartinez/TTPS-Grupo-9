"""Adaptador real del módulo 2 (API de síntomas SNOMED CT, edición argentina)."""
from src.adapters import HttpClient, RespuestaInvalida
from src.adapters.snomed.interfaz import LIMITE_POR_DEFECTO, SintomaSnomed, texto_buscable

LIMITE_MAXIMO = 50  # la API responde 400 fuera de 1..50
REGION = "us-east-1"  # según la presentación, baja la respuesta de ~8 s a ~1,2 s


class SnomedReal:
    def __init__(self, http: HttpClient):
        self.http = http
        self.http.session.headers["x-region"] = REGION

    def buscar_sintomas(self, texto: str, limite: int = LIMITE_POR_DEFECTO) -> list[SintomaSnomed]:
        texto = texto_buscable(texto)
        if texto is None:
            return []
        limite = max(1, min(limite, LIMITE_MAXIMO))
        respuesta = self.http.get("/sintomas", params={"q": texto, "limite": limite})
        try:
            return [
                SintomaSnomed(snomed_code=str(r["sctid"]), termino=r["termino_preferido"])
                for r in respuesta["resultados"]
            ]
        except (KeyError, TypeError):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "sintomas"})
