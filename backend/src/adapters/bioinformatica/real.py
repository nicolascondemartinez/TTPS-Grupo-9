"""Adaptador real del módulo 5 (Apigen, PostgREST sobre Supabase)."""
from src.adapters import HttpClient, RespuestaInvalida, SolicitudRechazada
from src.adapters.bioinformatica.interfaz import Variante
from src.core.enums import ClasificacionVariante

GRUPO_ID = "grupo9"
TAMANO_PAGINA = 1000  # máximo de filas que devuelve Apigen por pedido

# La tabla patologia guarda nombres; Apigen pide códigos. Las que no están acá se mandan en
# mayúsculas, por si son patologías propias del grupo dadas de alta con ese código.
CODIGOS_PATOLOGIA = {
    "fabry": "FABRY",
    "pompe": "POMPE",
    "mucopolisacaridosis 1": "MPS1",
    "gaucher": "GAUCHER",
    "asmd": "ASMD",
}

# probablemente_patogenica no existe en nuestro enum: va como vus porque tiene la misma
# consecuencia (no confirma el diagnóstico y se reevalúa al año).
CLASIFICACIONES = {
    "patogenica": ClasificacionVariante.patogenica,
    "probablemente_patogenica": ClasificacionVariante.vus,
    "vus": ClasificacionVariante.vus,
    "benigna": ClasificacionVariante.benigna,
}


class BioinformaticaReal:
    def __init__(self, http: HttpClient):
        self.http = http

    def genes_por_patologia(self, patologia: str) -> list[str]:
        nombre = patologia.strip()
        codigo = CODIGOS_PATOLOGIA.get(nombre.lower(), nombre.upper())
        try:
            genes = self.http.post("/rpc/genes_por_patologia", {"p_patologia": codigo, "p_grupo_id": GRUPO_ID})
        except SolicitudRechazada as e:
            if e.status_externo == 400 and _mensaje(e.cuerpo).startswith("Patología inexistente"):
                return []
            raise
        if not isinstance(genes, list) or not all(isinstance(g, str) for g in genes):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "genes_por_patologia"})
        return genes

    def genes_hallazgos_secundarios(self) -> list[str]:
        filas = self.http.get("/genes_hallazgos_secundarios", params={"select": "gen", "order": "gen"})
        try:
            return [fila["gen"] for fila in filas]
        except (KeyError, TypeError):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "genes_hallazgos_secundarios"})

    def variantes_por_gen(self, gen: str) -> list[Variante]:
        variantes: list[Variante] = []
        while True:
            filas = self.http.get("/variantes", params={
                "gen": f"eq.{gen.strip().upper()}",
                "select": "id,hgvs_c,proteina,clasificacion",
                "order": "id",
                "limit": TAMANO_PAGINA,
                "offset": len(variantes),
            })
            if not isinstance(filas, list):
                raise RespuestaInvalida(self.http.modulo, {"motivo": "variantes"})
            variantes.extend(self._variante(fila) for fila in filas)
            if len(filas) < TAMANO_PAGINA:
                return variantes

    def _variante(self, fila) -> Variante:
        try:
            clasificacion = CLASIFICACIONES[fila["clasificacion"]]
            nombre = fila["hgvs_c"] + (f" ({fila['proteina']})" if fila.get("proteina") else "")
            return Variante(codigo=fila["id"], nombre=nombre, clasificacion=clasificacion)
        except (KeyError, TypeError):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "variante", "id": str(fila)[:100]})


def _mensaje(cuerpo) -> str:
    return cuerpo.get("message", "") if isinstance(cuerpo, dict) else ""
