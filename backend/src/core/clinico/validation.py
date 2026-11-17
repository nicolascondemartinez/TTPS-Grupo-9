"""Validación de las entradas de patologías: devuelve los datos limpios o lanza un 400 con el detalle de
cada campo (mismo formato que la validación de autenticación)."""
import re

from src.core.common.errors import validation_error

NOMBRE_MAX = 100
TERMINO_MAX = 255
_SCTID_RE = re.compile(r"^\d{6,18}$")  # los códigos SNOMED CT son numéricos


def _sintoma(valor, campo: str, problemas: list[dict]) -> dict | None:
    """{snomed_code, termino} limpio, o None (y el problema anotado) si no es válido."""
    if not isinstance(valor, dict):
        problemas.append({"campo": campo, "problema": "debe ser un síntoma elegido de SNOMED"})
        return None
    codigo, termino = valor.get("snomed_code"), valor.get("termino")
    codigo = codigo.strip() if isinstance(codigo, str) else ""
    termino = termino.strip() if isinstance(termino, str) else ""
    if not _SCTID_RE.match(codigo):
        problemas.append({"campo": campo, "problema": "no tiene un código SNOMED válido"})
        return None
    if not termino or len(termino) > TERMINO_MAX:
        problemas.append({"campo": campo, "problema": "no tiene un término válido"})
        return None
    return {"snomed_code": codigo, "termino": termino}


def _sintomas(datos: dict, problemas: list[dict]) -> tuple[dict | None, list[dict]]:
    """Exactamente un cardinal y al menos un secundario, sin repetidos ni el cardinal entre los secundarios."""
    cardinal = None
    if datos.get("cardinal") is None:
        problemas.append({"campo": "cardinal", "problema": "es obligatorio"})
    else:
        cardinal = _sintoma(datos["cardinal"], "cardinal", problemas)

    secundarios_crudos = datos.get("secundarios")
    if not isinstance(secundarios_crudos, list) or not secundarios_crudos:
        problemas.append({"campo": "secundarios", "problema": "tiene que haber al menos un síntoma secundario"})
        return cardinal, []

    secundarios, vistos = [], set()
    for i, valor in enumerate(secundarios_crudos):
        sintoma = _sintoma(valor, f"secundarios[{i}]", problemas)
        if sintoma is None:
            continue
        if cardinal and sintoma["snomed_code"] == cardinal["snomed_code"]:
            problemas.append({"campo": f"secundarios[{i}]", "problema": "el síntoma cardinal no puede ser también secundario"})
        elif sintoma["snomed_code"] in vistos:
            problemas.append({"campo": f"secundarios[{i}]", "problema": "el síntoma está repetido"})
        else:
            vistos.add(sintoma["snomed_code"])
            secundarios.append(sintoma)
    return cardinal, secundarios


def _cuerpo(datos) -> dict:
    if not isinstance(datos, dict):
        raise validation_error([{"campo": "(cuerpo)", "problema": "se esperaba un JSON en el cuerpo de la petición"}])
    return datos


def validar_alta_patologia(datos) -> tuple[str, dict, list[dict]]:
    datos = _cuerpo(datos)
    problemas = []
    nombre = datos.get("nombre")
    nombre = " ".join(nombre.split()) if isinstance(nombre, str) else ""
    if not nombre:
        problemas.append({"campo": "nombre", "problema": "es obligatorio"})
    elif len(nombre) > NOMBRE_MAX:
        problemas.append({"campo": "nombre", "problema": f"admite como máximo {NOMBRE_MAX} caracteres"})
    cardinal, secundarios = _sintomas(datos, problemas)
    if problemas:
        raise validation_error(problemas)
    return nombre, cardinal, secundarios


def validar_modificacion_patologia(datos) -> tuple[dict, list[dict]]:
    """Al modificar solo cambian los síntomas: el nombre queda fijo (Bioinformática busca los genes por nombre)."""
    datos = _cuerpo(datos)
    problemas = []
    if "nombre" in datos:
        problemas.append({"campo": "nombre", "problema": "no se puede modificar"})
    cardinal, secundarios = _sintomas(datos, problemas)
    if problemas:
        raise validation_error(problemas)
    return cardinal, secundarios
