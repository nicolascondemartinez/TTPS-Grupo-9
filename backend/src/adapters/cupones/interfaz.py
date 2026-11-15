from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Protocol

from src.core.common.errors import ApiError, validation_error

# La API admite un solo gerente por grupo y fija el primero que genera cupones. Se manda siempre este id
# (no el UUID local del gerente, que cambia en la base de cada integrante).
GERENTE_ID = "gerente-grupo9"
CANTIDAD_MAXIMA = 1000


class EstadoCupon(str, Enum):
    disponible = "disponible"  # generado, todavía del gerente
    medico = "medico"  # asignado a un médico
    paciente = "paciente"  # asignado a un paciente (todavía no consumido)
    usado = "usado"  # canjeado


@dataclass(frozen=True)
class InfoCupon:
    codigo: str  # se guarda en cupon.codigo_externo
    descuento_porcentaje: Decimal | None
    estado: EstadoCupon
    gerente_id: str | None = None
    medico_id: str | None = None
    paciente_id: str | None = None
    fecha_vencimiento: date | None = None  # vence al terminar ese día
    fecha_uso: datetime | None = None

    @property
    def vencido(self) -> bool:
        return self.fecha_vencimiento is not None and self.fecha_vencimiento < date.today()


class CuponInexistente(ApiError):
    def __init__(self, codigo: str, mensaje: str = "El cupón no existe o no corresponde."):
        super().__init__(404, "CUPON_INEXISTENTE", mensaje, {"codigo": codigo})


class CuponNoDisponible(ApiError):
    """Ya canjeado, o el paciente ya tuvo un cupón."""

    def __init__(self, codigo: str, mensaje: str = "El cupón ya no se puede usar."):
        super().__init__(409, "CUPON_NO_DISPONIBLE", mensaje, {"codigo": codigo})


class CuponNoHabilitado(ApiError):
    """Vencido, o en un estado que no permite la operación."""

    def __init__(self, codigo: str, mensaje: str = "El cupón no está habilitado para esta operación."):
        super().__init__(400, "CUPON_NO_HABILITADO", mensaje, {"codigo": codigo})


class CuponesDeOtroGerente(ApiError):
    def __init__(self, mensaje: str = "El grupo ya está administrado por otro gerente."):
        super().__init__(409, "CUPONES_OTRO_GERENTE", mensaje)


class Cupones(Protocol):
    def generar_cupones(self, descuento_porcentaje, cantidad: int = 1) -> list[InfoCupon]: ...

    def asignar_a_medico(self, medico_id, codigo: str) -> None: ...

    def asignar_a_paciente(self, medico_id, paciente_id, codigo: str) -> None:
        """409 si el paciente ya tuvo un cupón en el grupo (aunque esté usado)."""
        ...

    def canjear_cupon(self, paciente_id, codigo: str) -> None:
        """Marca el cupón como usado. No cobra nada. 409 si ya estaba canjeado."""
        ...

    def validar_cupon(self, paciente_id, codigo: str) -> InfoCupon:
        """Sin escribir nada: el cupón si se puede canjear para ese paciente; si no, el mismo error que
        daría el canje (404, 409 o 400)."""
        ...

    def consultar_cupon(self, codigo: str) -> InfoCupon | None: ...

    def listar_cupones(self, estado: EstadoCupon | None = None, medico_id=None) -> list[InfoCupon]: ...


def normalizar_codigo(codigo: str) -> str:
    """Acepta el código con espacios o guiones: "2ded-2dc3" -> "2ded2dc3"."""
    return "".join(c for c in (codigo or "") if c not in " -")


def validar_descuento(descuento_porcentaje) -> Decimal:
    try:
        descuento = Decimal(str(descuento_porcentaje))
    except InvalidOperation:
        descuento = Decimal("0")
    if not (Decimal("0") < descuento <= Decimal("100")):
        raise validation_error([{"campo": "descuento_porcentaje", "problema": "debe ser mayor que 0 y hasta 100"}])
    return descuento


def validar_cantidad(cantidad) -> int:
    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or not 1 <= cantidad <= CANTIDAD_MAXIMA:
        raise validation_error([{"campo": "cantidad", "problema": f"debe ser un entero de 1 a {CANTIDAD_MAXIMA}"}])
    return cantidad


def verificar_canjeable(info: InfoCupon | None, paciente_id: str, codigo: str) -> InfoCupon:
    if info is None or info.paciente_id != paciente_id:
        raise CuponInexistente(codigo, "Cupón no encontrado para este paciente.")
    if info.estado == EstadoCupon.usado:
        raise CuponNoDisponible(codigo, "Cupón ya canjeado.")
    if info.estado != EstadoCupon.paciente or info.vencido:
        raise CuponNoHabilitado(codigo, "El cupón está vencido." if info.vencido else "El cupón no está asignado al paciente.")
    return info
