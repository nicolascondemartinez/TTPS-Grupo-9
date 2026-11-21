"""Almacenamiento de archivos generados o subidos (familiograma, PDF de autorización, CSV del lote, etc.).

    from src.core.almacenamiento import service as almacenamiento

    ruta = almacenamiento.guardar(session, contenido, "image/svg+xml", "familiograma.svg")  # sin commit
    paciente.familiograma_url = ruta
    archivo = almacenamiento.leer(session, ruta)  # archivo.contenido, archivo.tipo, archivo.nombre

Los modelos guardan solo la ruta que devuelve `guardar`. Por ahora los archivos van a la base (tabla `archivo`):
funciona en cualquier despliegue sin configurar nada (el disco de servicios como Render se borra en cada
reinicio) y, como usa la misma sesión, el archivo se guarda o se descarta junto con el resto de la transacción.
Los archivos de este sistema son chicos (un SVG o un PDF pesan unos KB).

Para sumar otro lugar (por ejemplo Supabase Storage, para archivos grandes): agregar una implementación que
devuelva rutas con otro prefijo ("supabase/...") y elegirla con una variable de entorno. Las rutas viejas
("db/...") se siguen leyendo de la base, y nadie tiene que cambiar su código: todos usan guardar y leer.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.almacenamiento.models import Archivo
from src.core.common.errors import ApiError

PREFIJO_BASE = "db/"


@dataclass(frozen=True)
class ArchivoLeido:
    contenido: bytes
    tipo: str
    nombre: str


def guardar(session: Session, contenido: bytes, tipo: str, nombre: str) -> str:
    """Guarda el archivo y devuelve su ruta. No hace commit: queda en la transacción de quien lo llama."""
    archivo = Archivo(nombre=nombre, tipo=tipo, tamano=len(contenido), contenido=contenido)
    session.add(archivo)
    session.flush()
    return f"{PREFIJO_BASE}{archivo.id}"


def leer(session: Session, ruta: str) -> ArchivoLeido:
    """404 ARCHIVO_NO_ENCONTRADO si la ruta no existe o no es de este almacenamiento."""
    archivo = None
    if ruta and ruta.startswith(PREFIJO_BASE):
        try:
            archivo = session.get(Archivo, uuid.UUID(ruta[len(PREFIJO_BASE):]))
        except ValueError:
            archivo = None
    if archivo is None:
        raise ApiError(404, "ARCHIVO_NO_ENCONTRADO", "El archivo no existe")
    return ArchivoLeido(archivo.contenido, archivo.tipo, archivo.nombre)


def borrar(session: Session, ruta: str) -> None:
    """Borra el archivo si existe (sin commit). Para reemplazar uno, por ejemplo, un familiograma nuevo."""
    if ruta and ruta.startswith(PREFIJO_BASE):
        try:
            archivo = session.get(Archivo, uuid.UUID(ruta[len(PREFIJO_BASE):]))
        except ValueError:
            return
        if archivo is not None:
            session.delete(archivo)
