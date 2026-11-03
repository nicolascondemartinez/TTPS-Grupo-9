"""Contraseñas con Argon2id (librería argon2-cffi). Nunca se guarda ni se loguea la contraseña en claro."""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id con los parámetros recomendados por la librería

# Hash de una contraseña inexistente: se usa cuando el correo no existe, para que el login tarde
# lo mismo y no permita descubrir qué correos están registrados.
HASH_FICTICIO = _hasher.hash("contrasena-ficticia-para-igualar-tiempos")


def hash_contrasena(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar_contrasena(hash_guardado: str, contrasena: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except (VerificationError, InvalidHashError):
        return False


def requiere_rehash(hash_guardado: str) -> bool:
    """True si el hash se hizo con parámetros viejos y conviene regenerarlo al ingresar."""
    return _hasher.check_needs_rehash(hash_guardado)
