"""Validación de las entradas de autenticación (módulo aparte: recibe los datos y devuelve el
resultado limpio o lanza un error 400 con el detalle de cada campo)."""
import re
import uuid
from dataclasses import dataclass

from src.core.enums import RolUsuario
from src.core.common.errors import ApiError, validation_error

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_CODIGO_RE = re.compile(r"^\d{6}$")

CONTRASENA_MIN = 8
CONTRASENA_MAX = 128


def _cuerpo(datos) -> dict:
    if not isinstance(datos, dict):
        raise validation_error([{"campo": "(cuerpo)", "problema": "se esperaba un JSON en el cuerpo de la petición"}])
    return datos


def validar_login(datos) -> tuple[str, str]:
    datos = _cuerpo(datos)
    problemas = []
    correo, contrasena = datos.get("correo"), datos.get("contrasena")
    if not isinstance(correo, str) or not correo.strip():
        problemas.append({"campo": "correo", "problema": "es obligatorio"})
    elif len(correo.strip()) > 254 or not _EMAIL_RE.match(correo.strip()):
        problemas.append({"campo": "correo", "problema": "no tiene un formato de correo válido"})
    if not isinstance(contrasena, str) or contrasena == "":
        problemas.append({"campo": "contrasena", "problema": "es obligatoria"})
    elif len(contrasena) > CONTRASENA_MAX:
        problemas.append({"campo": "contrasena", "problema": f"admite como máximo {CONTRASENA_MAX} caracteres"})
    if problemas:
        raise validation_error(problemas)
    return correo.strip().lower(), contrasena


def validar_device_id(valor) -> str:
    """Identificador del dispositivo (header X-Device-Id): lo genera el navegador una sola vez."""
    if not isinstance(valor, str) or not _DEVICE_RE.match(valor):
        raise validation_error([{"campo": "X-Device-Id", "problema": "falta el identificador del dispositivo o no es válido"}])
    return valor


def validar_verificacion(datos) -> tuple[str, str]:
    datos = _cuerpo(datos)
    problemas = []
    desafio_id, codigo = datos.get("desafio_id"), datos.get("codigo")
    if not isinstance(desafio_id, str) or not desafio_id.strip():
        problemas.append({"campo": "desafio_id", "problema": "es obligatorio"})
    if not isinstance(codigo, str) or not _CODIGO_RE.match(codigo.strip()):
        problemas.append({"campo": "codigo", "problema": "debe tener 6 dígitos"})
    if problemas:
        raise validation_error(problemas)
    return desafio_id.strip(), codigo.strip()


def validar_cambio_contrasena(datos, correo: str) -> tuple[str, str]:
    datos = _cuerpo(datos)
    problemas = []
    actual, nueva = datos.get("contrasena_actual"), datos.get("contrasena_nueva")
    if not isinstance(actual, str) or actual == "":
        problemas.append({"campo": "contrasena_actual", "problema": "es obligatoria"})
    if not isinstance(nueva, str) or nueva == "":
        problemas.append({"campo": "contrasena_nueva", "problema": "es obligatoria"})
    elif len(nueva) < CONTRASENA_MIN or len(nueva) > CONTRASENA_MAX:
        problemas.append({"campo": "contrasena_nueva", "problema": f"debe tener entre {CONTRASENA_MIN} y {CONTRASENA_MAX} caracteres"})
    elif nueva == actual:
        problemas.append({"campo": "contrasena_nueva", "problema": "debe ser distinta de la actual"})
    elif nueva.strip().lower() == correo.strip().lower():
        problemas.append({"campo": "contrasena_nueva", "problema": "no puede ser igual al correo"})
    if problemas:
        raise validation_error(problemas)
    return actual, nueva


# --------------------------------------------------------------------------- registro de usuarios
ROLES_REGISTRABLES = (RolUsuario.medico, RolUsuario.gerente_medico, RolUsuario.administrativo, RolUsuario.bioinformatico)
ROLES_CON_MATRICULA = (RolUsuario.medico, RolUsuario.gerente_medico)
MAX_ESPECIALIDADES = 10
_TELEFONO_RE = re.compile(r"^\+?[0-9][0-9 ()-]{5,29}$")


@dataclass(frozen=True)
class DatosRegistro:
    """Datos del formulario de registro ya validados y limpios."""

    nombre: str
    apellido: str
    telefono: str
    correo: str  # en minúsculas
    contrasena: str
    rol: RolUsuario
    matricula: str | None = None  # solo médico y gerente médico
    especialidad_ids: tuple[uuid.UUID, ...] = ()  # solo médico y gerente médico


def _texto_obligatorio(datos: dict, campo: str, maximo: int, problemas: list) -> str | None:
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        problemas.append({"campo": campo, "problema": "es obligatorio"})
        return None
    valor = valor.strip()
    if len(valor) > maximo:
        problemas.append({"campo": campo, "problema": f"admite como máximo {maximo} caracteres"})
        return None
    return valor


def _validar_contacto(datos: dict, problemas: list) -> tuple[str | None, str | None, str | None, str | None]:
    """Nombre, apellido, teléfono y correo: los datos que piden el registro y el alta de transportista."""
    nombre = _texto_obligatorio(datos, "nombre", 100, problemas)
    apellido = _texto_obligatorio(datos, "apellido", 100, problemas)
    telefono = _texto_obligatorio(datos, "telefono", 30, problemas)
    if telefono is not None and not _TELEFONO_RE.match(telefono):
        problemas.append({"campo": "telefono", "problema": "no tiene un formato de teléfono válido"})
    correo = _texto_obligatorio(datos, "correo", 254, problemas)
    if correo is not None and not _EMAIL_RE.match(correo):
        problemas.append({"campo": "correo", "problema": "no tiene un formato de correo válido"})
    return nombre, apellido, telefono, correo


def _validar_especialidades(valor, problemas: list) -> tuple[uuid.UUID, ...]:
    if not isinstance(valor, list) or not valor:
        problemas.append({"campo": "especialidades", "problema": "debe incluir al menos una"})
        return ()
    if len(valor) > MAX_ESPECIALIDADES:
        problemas.append({"campo": "especialidades", "problema": f"admite como máximo {MAX_ESPECIALIDADES}"})
        return ()
    ids = []
    for i, item in enumerate(valor):
        if isinstance(item, str) and validar_uuid(item):
            ids.append(uuid.UUID(item))
        else:
            problemas.append({"campo": f"especialidades[{i}]", "problema": "no es un identificador válido"})
    return tuple(dict.fromkeys(ids))  # sin repetidas, conservando el orden


def validar_registro(datos) -> DatosRegistro:
    """Registro de médico, gerente médico, administrativo o bioinformático (formulario único con selector de rol).

    Matrícula y especialidades solo se piden (y se leen) para médico y gerente médico: en los otros
    dos roles, si llegan, se ignoran.
    """
    datos = _cuerpo(datos)
    problemas: list[dict] = []

    nombre, apellido, telefono, correo = _validar_contacto(datos, problemas)

    contrasena = datos.get("contrasena")
    if not isinstance(contrasena, str) or contrasena == "":
        problemas.append({"campo": "contrasena", "problema": "es obligatoria"})
    elif len(contrasena) < CONTRASENA_MIN or len(contrasena) > CONTRASENA_MAX:
        problemas.append({"campo": "contrasena", "problema": f"debe tener entre {CONTRASENA_MIN} y {CONTRASENA_MAX} caracteres"})
    elif correo is not None and contrasena.strip().lower() == correo.lower():
        problemas.append({"campo": "contrasena", "problema": "no puede ser igual al correo"})

    rol_valor = datos.get("rol")
    rol = next((r for r in ROLES_REGISTRABLES if r.value == rol_valor), None)
    if rol is None:
        opciones = ", ".join(r.value for r in ROLES_REGISTRABLES)
        problemas.append({"campo": "rol", "problema": f"debe ser uno de: {opciones}"})

    matricula, especialidad_ids = None, ()
    if rol in ROLES_CON_MATRICULA:
        matricula = _texto_obligatorio(datos, "matricula", 30, problemas)
        especialidad_ids = _validar_especialidades(datos.get("especialidades"), problemas)

    if problemas:
        raise validation_error(problemas)
    return DatosRegistro(nombre, apellido, telefono, correo.lower(), contrasena, rol, matricula, especialidad_ids)


@dataclass(frozen=True)
class DatosTransportista:
    nombre: str
    apellido: str
    telefono: str
    correo: str  # en minúsculas
    provincia_id: uuid.UUID


def validar_alta_transportista(datos) -> DatosTransportista:
    datos = _cuerpo(datos)
    problemas: list[dict] = []
    nombre, apellido, telefono, correo = _validar_contacto(datos, problemas)

    provincia = datos.get("provincia_id")
    provincia_id = None
    if not isinstance(provincia, str) or not provincia.strip():
        problemas.append({"campo": "provincia_id", "problema": "es obligatoria"})
    elif not validar_uuid(provincia.strip()):
        problemas.append({"campo": "provincia_id", "problema": "no es un identificador válido"})
    else:
        provincia_id = uuid.UUID(provincia.strip())

    if problemas:
        raise validation_error(problemas)
    return DatosTransportista(nombre, apellido, telefono, correo.lower(), provincia_id)


def validar_uuid(valor: str) -> bool:
    return bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", valor or ""))


__all__ = ["ApiError"]
