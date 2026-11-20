"""Adaptador real del módulo 1 (familiograma del Laboratorio): devuelve un SVG."""
import base64
import binascii
import re

from src.adapters import HttpClient, RespuestaInvalida, SolicitudRechazada
from src.adapters.bioinformatica.real import CODIGOS_PATOLOGIA
from src.adapters.familiograma.interfaz import (ArchivoFamiliograma, FamiliarFamiliograma, PacienteFamiliograma,
                                                Parentesco, validar_familiares)
from src.core.common.errors import validation_error

PARENTESCO_PACIENTE = 0
# La API dibuja rayado (sospecha) a quien cumple esta regla según sus síntomas. Con la regla activa la API tarda
# bastante más (más de 10 s en las pruebas): por eso el módulo tiene un timeout más largo (ver __init__.py).
REGLA_SOSPECHA = "un_cardinal_o_dos_secundarios"
SEXO_DESCONOCIDO = "no_identificado"  # el paciente no tiene sexo cargado (la API no lo necesita)


class FamiliogramaReal:
    def __init__(self, http: HttpClient):
        self.http = http

    def parentescos(self) -> list[Parentesco]:
        filas = self.http.get("/parentescos")
        try:
            return [Parentesco(int(f["id"]), f["parentesco"]) for f in filas if int(f["id"]) != PARENTESCO_PACIENTE]
        except (KeyError, TypeError, ValueError):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "parentescos"})

    def generar_familiograma(self, paciente: PacienteFamiliograma,
                             familiares: list[FamiliarFamiliograma]) -> ArchivoFamiliograma | None:
        if not familiares:
            return None
        validados = validar_familiares(familiares, self.parentescos())
        personas = [_persona(PARENTESCO_PACIENTE, paciente.nombre, paciente.apellido, paciente.sintomas,
                             edad=paciente.edad)]
        personas += [_persona(v.parentesco_id, v.nombre, v.apellido, v.familiar.sintomas,
                              edad=v.familiar.edad, diagnostico=v.familiar.diagnostico_previo, sexo=v.familiar.sexo,
                              fallecido=v.familiar.fallecido) for v in validados]
        try:
            datos = self.http.post("", {"personas": personas, "opciones": {"reglaSospecha": REGLA_SOSPECHA}})
        except SolicitudRechazada as e:
            if e.status_externo == 422:
                raise validation_error(_campos_invalidos(e.cuerpo))
            raise
        try:
            imagen = datos["imagen"]
            return ArchivoFamiliograma(base64.b64decode(imagen["base64"], validate=True), imagen["tipo"],
                                       list(datos.get("advertencias") or []))
        except (KeyError, TypeError, binascii.Error):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "imagen"})


def _persona(parentesco: int, nombre: str, apellido: str, sintomas, edad=None, diagnostico=None,
             sexo: str = SEXO_DESCONOCIDO, fallecido: bool = False) -> dict:
    persona = {
        "parentesco": parentesco, "nombre": nombre, "apellido": apellido, "sexo": sexo,
        "sintomas": [{"codigo": s.snomed_code, "nombre": s.termino} for s in sintomas],
    }
    if edad is not None:
        persona["edad"] = edad
    if fallecido:
        persona["fallecido"] = True
    if diagnostico:
        codigo = CODIGOS_PATOLOGIA.get(diagnostico.strip().lower(), diagnostico.strip().upper())
        persona["diagnosticos"] = [{"codigo": codigo, "nombre": diagnostico}]
    return persona


def _campos_invalidos(cuerpo) -> list[dict]:
    error = cuerpo.get("error", {}) if isinstance(cuerpo, dict) else {}
    detalles = error.get("detalles") or []
    campos = [{"campo": _campo(d.get("ruta", "")), "problema": _mensaje_legible(d.get("mensaje", ""))}
              for d in detalles if isinstance(d, dict)]
    return campos or [{"campo": "familiares", "problema": error.get("mensaje", "datos inválidos")}]


def _mensaje_legible(mensaje: str) -> str:
    """Saca el código técnico y los números de parentesco para mostrárselo al médico:
    'FALTA_PERSONA_DE_REFERENCIA: "Ana" (tío/a materno/a) necesita un abuelo/a materno/a (parentesco 3) en la lista.'
    -> '"Ana" (tío/a materno/a) necesita un abuelo/a materno/a en la lista.'"""
    mensaje = re.sub(r"^[A-Z_]+:\s+", "", mensaje)
    return re.sub(r"\s*\(parentesco \d+\)", "", mensaje)


def _campo(ruta: str) -> str:
    """La API numera `personas` con el paciente en el 0: "personas.2.nombre" -> "familiares[1].nombre"."""
    coincidencia = re.fullmatch(r"personas\.(\d+)(\..+)?", ruta)
    if not coincidencia:
        return ruta
    indice, resto = int(coincidencia.group(1)), coincidencia.group(2) or ""
    return f"paciente{resto}" if indice == 0 else f"familiares[{indice - 1}]{resto}"
