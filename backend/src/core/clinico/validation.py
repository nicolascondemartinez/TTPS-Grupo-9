"""Validación de las entradas de patologías: devuelve los datos limpios o lanza un 400 con el detalle de
cada campo (mismo formato que la validación de autenticación)."""
import re
from datetime import date

from src.core.common.errors import ApiError, validation_error
from src.core.common.validation import _EMAIL_RE, validar_uuid
from src.adapters.snomed.interfaz import normalizar
from src.core.enums import Sexo, TipoSospecha

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


# ---------- Familiares del paciente ----------

PARENTESCO_MAX = 50
EDAD_MAXIMA = 120
NOMBRE_FAMILIAR_MAX = 150


def validar_familiares(datos) -> list[dict]:
    """Lista de familiares del alta (puede venir vacía o no venir) -> lista limpia:
    [{parentesco, nombre, sexo, sintomas: [{snomed_code, termino}], patologia_id: str | None}].
    El nombre tiene que traer nombre y apellido (el familiograma usa la última palabra como apellido).
    El sexo es hombre, mujer o no_identificado (si no viene). No se acepta el mismo familiar dos veces (mismo
    nombre y parentesco); el mismo nombre con otro parentesco sí (por ejemplo, padre e hijo homónimos)."""
    if datos is None:
        return []
    if not isinstance(datos, list):
        raise validation_error([{"campo": "familiares", "problema": "debe ser una lista"}])
    problemas, familiares, cargados = [], [], set()
    for i, crudo in enumerate(datos):
        campo = f"familiares[{i}]"
        if not isinstance(crudo, dict):
            problemas.append({"campo": campo, "problema": "no es un familiar válido"})
            continue
        parentesco = crudo.get("parentesco")
        parentesco = " ".join(parentesco.split()) if isinstance(parentesco, str) else ""
        if not parentesco:
            problemas.append({"campo": f"{campo}.parentesco", "problema": "es obligatorio"})
        elif len(parentesco) > PARENTESCO_MAX:
            problemas.append({"campo": f"{campo}.parentesco", "problema": f"admite como máximo {PARENTESCO_MAX} caracteres"})
        nombre = crudo.get("nombre")
        nombre = " ".join(nombre.split()) if isinstance(nombre, str) else ""
        if len(nombre.split()) < 2:
            problemas.append({"campo": f"{campo}.nombre", "problema": "ingresá nombre y apellido del familiar"})
        elif len(nombre) > NOMBRE_FAMILIAR_MAX:
            problemas.append({"campo": f"{campo}.nombre", "problema": f"admite como máximo {NOMBRE_FAMILIAR_MAX} caracteres"})
        clave = (normalizar(nombre), normalizar(parentesco))
        if nombre and parentesco and clave in cargados:
            problemas.append({"campo": f"{campo}.nombre", "problema": "ya cargaste a este familiar con el mismo parentesco"})
        cargados.add(clave)
        sexo = crudo.get("sexo") or Sexo.no_identificado.value
        if sexo not in {s.value for s in Sexo}:
            problemas.append({"campo": f"{campo}.sexo", "problema": "elegí hombre, mujer o no sé"})
            sexo = Sexo.no_identificado.value
        edad = crudo.get("edad")
        if edad in (None, ""):
            edad = None
        elif isinstance(edad, bool) or not isinstance(edad, int) or not 0 <= edad <= EDAD_MAXIMA:
            problemas.append({"campo": f"{campo}.edad", "problema": f"tiene que ser un número de años entre 0 y {EDAD_MAXIMA}"})
            edad = None
        fallecido = crudo.get("fallecido", False)
        if not isinstance(fallecido, bool):
            problemas.append({"campo": f"{campo}.fallecido", "problema": "tiene que ser sí o no"})
            fallecido = False
        sintomas_crudos = crudo.get("sintomas") or []
        sintomas, vistos = [], set()
        if not isinstance(sintomas_crudos, list):
            problemas.append({"campo": f"{campo}.sintomas", "problema": "debe ser una lista de síntomas de SNOMED"})
            sintomas_crudos = []
        for j, valor in enumerate(sintomas_crudos):
            sintoma = _sintoma(valor, f"{campo}.sintomas[{j}]", problemas)
            if sintoma and sintoma["snomed_code"] not in vistos:  # repetidos: se ignoran
                vistos.add(sintoma["snomed_code"])
                sintomas.append(sintoma)
        patologia_id = crudo.get("patologia_id")
        if patologia_id is not None and (not isinstance(patologia_id, str) or not validar_uuid(patologia_id)):
            problemas.append({"campo": f"{campo}.patologia_id", "problema": "no es una patología válida"})
        familiares.append({"parentesco": parentesco, "nombre": nombre, "sexo": Sexo(sexo), "edad": edad,
                           "fallecido": fallecido, "sintomas": sintomas, "patologia_id": patologia_id})
    if problemas:
        raise validation_error(problemas)
    return familiares


# ---------- Alta del paciente ----------

NOMBRE_PERSONA_MAX = 100
TELEFONO_MAX = 30
EMAIL_MAX = 254
HISTORIA_CLINICA_MAX = 20000
_DNI_RE = re.compile(r"^\d{7,8}$")  # DNI argentino
_TELEFONO_RE = re.compile(r"^\+?[\d\s()-]{6,30}$")


def _texto(datos: dict, campo: str, maximo: int, problemas: list[dict], obligatorio_msg: str = "es obligatorio") -> str:
    valor = datos.get(campo)
    valor = " ".join(valor.split()) if isinstance(valor, str) else ""
    if not valor:
        problemas.append({"campo": campo, "problema": obligatorio_msg})
    elif len(valor) > maximo:
        problemas.append({"campo": campo, "problema": f"admite como máximo {maximo} caracteres"})
    return valor


def validar_alta_paciente(datos, hoy: date) -> dict:
    """Datos del formulario de alta -> datos limpios. Todo es obligatorio salvo los familiares; los síntomas son
    obligatorios solo con sospecha clínica (con sospecha familiar el paciente puede no tener síntomas todavía)."""
    datos = _cuerpo(datos)
    problemas: list[dict] = []
    limpio = {
        "nombre": _texto(datos, "nombre", NOMBRE_PERSONA_MAX, problemas),
        "apellido": _texto(datos, "apellido", NOMBRE_PERSONA_MAX, problemas),
    }

    dni = datos.get("dni")
    dni = re.sub(r"[.\s-]", "", dni) if isinstance(dni, str) else ""
    if not dni:
        problemas.append({"campo": "dni", "problema": "es obligatorio"})
    elif not _DNI_RE.match(dni):
        problemas.append({"campo": "dni", "problema": "tiene que tener 7 u 8 números"})
    limpio["dni"] = dni

    fecha = datos.get("fecha_nacimiento")
    try:
        fecha = date.fromisoformat(fecha) if isinstance(fecha, str) else None
    except ValueError:
        fecha = None
    if fecha is None:
        problemas.append({"campo": "fecha_nacimiento", "problema": "es obligatoria (AAAA-MM-DD)"})
    elif fecha > hoy:
        problemas.append({"campo": "fecha_nacimiento", "problema": "no puede ser posterior a hoy"})
    elif fecha.year < hoy.year - EDAD_MAXIMA:
        problemas.append({"campo": "fecha_nacimiento", "problema": "no es válida"})
    limpio["fecha_nacimiento"] = fecha

    telefono = _texto(datos, "telefono", TELEFONO_MAX, problemas)
    if telefono and not _TELEFONO_RE.match(telefono):
        problemas.append({"campo": "telefono", "problema": "no es un teléfono válido"})
    limpio["telefono"] = telefono

    email = datos.get("email")
    email = email.strip().lower() if isinstance(email, str) else ""
    if not email:
        problemas.append({"campo": "email", "problema": "es obligatorio"})
    elif len(email) > EMAIL_MAX or not _EMAIL_RE.match(email):
        problemas.append({"campo": "email", "problema": "no tiene un formato de correo válido"})
    limpio["email"] = email

    tipo = datos.get("tipo_sospecha")
    if tipo not in {t.value for t in TipoSospecha}:
        problemas.append({"campo": "tipo_sospecha", "problema": "elegí sospecha clínica o familiar"})
        tipo = None
    limpio["tipo_sospecha"] = TipoSospecha(tipo) if tipo else None

    ids = datos.get("patologia_ids")
    if not isinstance(ids, list) or not ids:
        problemas.append({"campo": "patologia_ids", "problema": "elegí al menos una patología sospechada"})
        ids = []
    elif not all(isinstance(i, str) and validar_uuid(i) for i in ids):
        problemas.append({"campo": "patologia_ids", "problema": "hay una patología que no es válida"})
    limpio["patologia_ids"] = list(dict.fromkeys(i for i in ids if isinstance(i, str)))

    sintomas_crudos = datos.get("sintomas") or []
    sintomas, vistos = [], set()
    if not isinstance(sintomas_crudos, list):
        problemas.append({"campo": "sintomas", "problema": "debe ser una lista de síntomas de SNOMED"})
        sintomas_crudos = []
    for i, valor in enumerate(sintomas_crudos):
        sintoma = _sintoma(valor, f"sintomas[{i}]", problemas)
        if sintoma and sintoma["snomed_code"] not in vistos:
            vistos.add(sintoma["snomed_code"])
            sintomas.append(sintoma)
    if not sintomas_crudos and tipo == TipoSospecha.clinica.value:
        problemas.append({"campo": "sintomas", "problema": "con sospecha clínica, elegí al menos un síntoma"})
    limpio["sintomas"] = sintomas

    historia = datos.get("historia_clinica")
    historia = historia.strip() if isinstance(historia, str) else ""
    if not historia:
        problemas.append({"campo": "historia_clinica", "problema": "es obligatorio: grabalo o escribilo"})
    elif len(historia) > HISTORIA_CLINICA_MAX:
        problemas.append({"campo": "historia_clinica", "problema": f"admite como máximo {HISTORIA_CLINICA_MAX} caracteres"})
    limpio["historia_clinica"] = historia

    try:
        limpio["familiares"] = validar_familiares(datos.get("familiares"))
    except ApiError as e:
        problemas.extend(e.detalle.get("campos", []))
        limpio["familiares"] = []
    limpio["sin_familiograma"] = datos.get("sin_familiograma") is True

    if problemas:
        raise validation_error(problemas)
    return limpio
