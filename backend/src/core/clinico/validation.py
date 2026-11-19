"""Validación de las entradas de patologías: devuelve los datos limpios o lanza un 400 con el detalle de
cada campo (mismo formato que la validación de autenticación)."""
import re

from src.core.common.errors import validation_error
from src.core.common.validation import validar_uuid

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


def _lista_de_sintomas(datos: dict, campo: str, minimo: str, problemas: list[dict],
                       excluidos: set[str] = frozenset()) -> list[dict]:
    """Los síntomas válidos de `datos[campo]`, sin repetidos ni códigos de `excluidos`.
    `minimo` es el problema que se anota si la lista falta o está vacía."""
    crudos = datos.get(campo)
    if not isinstance(crudos, list) or not crudos:
        problemas.append({"campo": campo, "problema": minimo})
        return []
    sintomas, vistos = [], set()
    for i, valor in enumerate(crudos):
        sintoma = _sintoma(valor, f"{campo}[{i}]", problemas)
        if sintoma is None:
            continue
        if sintoma["snomed_code"] in excluidos:
            problemas.append({"campo": f"{campo}[{i}]", "problema": "un síntoma cardinal no puede ser también secundario"})
        elif sintoma["snomed_code"] in vistos:
            problemas.append({"campo": f"{campo}[{i}]", "problema": "el síntoma está repetido"})
        else:
            vistos.add(sintoma["snomed_code"])
            sintomas.append(sintoma)
    return sintomas


def _sintomas(datos: dict, problemas: list[dict]) -> tuple[list[dict], list[dict]]:
    """Al menos un cardinal y al menos un secundario, sin repetidos ni cardinales entre los secundarios."""
    cardinales = _lista_de_sintomas(datos, "cardinales", "tiene que haber al menos un síntoma cardinal", problemas)
    secundarios = _lista_de_sintomas(
        datos, "secundarios", "tiene que haber al menos un síntoma secundario", problemas,
        excluidos={c["snomed_code"] for c in cardinales},
    )
    return cardinales, secundarios


def _cuerpo(datos) -> dict:
    if not isinstance(datos, dict):
        raise validation_error([{"campo": "(cuerpo)", "problema": "se esperaba un JSON en el cuerpo de la petición"}])
    return datos


def validar_alta_patologia(datos) -> tuple[str, list[dict], list[dict]]:
    datos = _cuerpo(datos)
    problemas = []
    nombre = datos.get("nombre")
    nombre = " ".join(nombre.split()) if isinstance(nombre, str) else ""
    if not nombre:
        problemas.append({"campo": "nombre", "problema": "es obligatorio"})
    elif len(nombre) > NOMBRE_MAX:
        problemas.append({"campo": "nombre", "problema": f"admite como máximo {NOMBRE_MAX} caracteres"})
    cardinales, secundarios = _sintomas(datos, problemas)
    if problemas:
        raise validation_error(problemas)
    return nombre, cardinales, secundarios


def validar_pedido_diagnostico(datos) -> tuple[list[str], list[str]]:
    """{patologia_ids: [uuid, ...], sintomas: [código SNOMED, ...]} -> (ids sin repetir, códigos sin repetir).
    `sintomas` puede venir vacía: el diagnóstico resulta inválido, no es un error del pedido."""
    datos = _cuerpo(datos)
    problemas = []
    ids, codigos = datos.get("patologia_ids"), datos.get("sintomas", [])
    if not isinstance(ids, list) or not ids:
        problemas.append({"campo": "patologia_ids", "problema": "tiene que haber al menos una patología sospechada"})
        ids = []
    for i, valor in enumerate(ids):
        if not isinstance(valor, str) or not validar_uuid(valor):
            problemas.append({"campo": f"patologia_ids[{i}]", "problema": "no es un identificador válido"})
    if not isinstance(codigos, list):
        problemas.append({"campo": "sintomas", "problema": "debe ser una lista de códigos SNOMED"})
        codigos = []
    for i, valor in enumerate(codigos):
        if not isinstance(valor, str) or not _SCTID_RE.match(valor.strip()):
            problemas.append({"campo": f"sintomas[{i}]", "problema": "no tiene un código SNOMED válido"})
    if problemas:
        raise validation_error(problemas)
    return list(dict.fromkeys(ids)), list(dict.fromkeys(c.strip() for c in codigos))


def validar_modificacion_patologia(datos) -> tuple[list[dict], list[dict]]:
    """Al modificar solo cambian los síntomas: el nombre queda fijo (Bioinformática busca los genes por nombre)."""
    datos = _cuerpo(datos)
    problemas = []
    if "nombre" in datos:
        problemas.append({"campo": "nombre", "problema": "no se puede modificar"})
    cardinales, secundarios = _sintomas(datos, problemas)
    if problemas:
        raise validation_error(problemas)
    return cardinales, secundarios
