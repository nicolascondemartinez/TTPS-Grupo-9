from src.adapters.recorridos.interfaz import CentroParaOrdenar, RecorridoOptimizado

def _distancia_cuadrada(a: CentroParaOrdenar, b: CentroParaOrdenar) -> float:
    return (a.latitud - b.latitud) ** 2 + (a.longitud - b.longitud) ** 2

class RecorridosMock:
    def optimizar(self, centros: list[CentroParaOrdenar]) -> RecorridoOptimizado:
        if len(centros) <= 1:
            return RecorridoOptimizado(paradas=list(centros))
        
        pendientes = sorted(centros, key=lambda c: (c.nombre, str(c.id)))
        actual = pendientes.pop(0)
        ordenadas = [actual]
        
        while pendientes:
            siguiente = min(pendientes, key=lambda c: _distancia_cuadrada(actual, c))
            pendientes.remove(siguiente)
            ordenadas.append(siguiente)
            actual = siguiente
        return RecorridoOptimizado(paradas=ordenadas)