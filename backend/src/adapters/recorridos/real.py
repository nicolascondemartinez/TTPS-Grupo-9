from src.adapters import HttpClient, RespuestaInvalida
from src.adapters.recorridos.interfaz import CentroParaOrdenar, RecorridoOptimizado

MODULO = "RECORRIDOS"
TOLERANCIA_COORD = 1e-4

def _emparejar_centro(lat: float, lon: float, disponibles: list[CentroParaOrdenar]) -> CentroParaOrdenar:
    for centro in disponibles:
        if abs(centro.latitud - lat) <= TOLERANCIA_COORD and abs(centro.longitud - lon) <= TOLERANCIA_COORD:
            disponibles.remove(centro)
            return centro
    raise RespuestaInvalida(MODULO, {"motivo": "coordenada desconocida en respuesta", "lat": lat, "lon": lon})

class RecorridosReal:
    def __init__(self, http: HttpClient):
        self._http = http
    
    def optimizar(self, centros: list[CentroParaOrdenar]) -> RecorridoOptimizado:
        if len(centros) <= 2:
            return RecorridoOptimizado(paradas=list(centros))
        
        body = {
            "coordenadas": [
                {"lat": c.latitud, "lon": c.longitud}
                for c in centros
            ]
        }
        datos = self._http.post("/api/optimizacion", body)
        
        if not isinstance(datos, dict) or not isinstance(datos.get("coordenadas"), list):
            raise RespuestaInvalida(MODULO, {"motivo": "falta lista 'coordenadas'"})
        coords = datos["coordenadas"]
        
        if len(coords) != len(centros):
            raise RespuestaInvalida(MODULO, {"motivo": "cantidad de coordenadas distinta a la enviada"})
        disponibles = list(centros)
        ordenadas: list[CentroParaOrdenar] = []
        
        for punto in coords:
            if not isinstance(punto, dict) or "lat" not in punto or "lon" not in punto:
                raise RespuestaInvalida(MODULO, {"motivo": "punto inválido en 'coordenadas'"})
            try:
                lat = float(punto["lat"])
                lon = float(punto["lon"])
            except (TypeError, ValueError):
                raise RespuestaInvalida(MODULO, {"motivo": "lat/lon no numéricos"})
            ordenadas.append(_emparejar_centro(lat, lon, disponibles))
        return RecorridoOptimizado(paradas=ordenadas)