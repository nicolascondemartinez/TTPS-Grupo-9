from src.adapters import crear_adaptador
from src.adapters.recorridos.interfaz import CentroParaOrdenar, Recorridos
from src.adapters.recorridos.mock import RecorridosMock
from src.adapters.recorridos.real import RecorridosReal

def get_recorridos() -> Recorridos:
    return crear_adaptador("RECORRIDOS", mock=RecorridosMock, real=RecorridosReal)