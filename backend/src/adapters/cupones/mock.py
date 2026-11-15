"""Cupones simulados con estado EN MEMORIA, con las mismas reglas que la API real (estados en orden,
vencimiento a 30 días, un cupón por paciente, canje único). El estado se comparte entre instancias
(cada pedido llama a get_cupones()) pero se pierde al reiniciar el backend."""
import secrets
import threading
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from src.adapters.cupones.interfaz import (GERENTE_ID, CuponInexistente, CuponNoDisponible, CuponNoHabilitado,
                                           EstadoCupon, InfoCupon, normalizar_codigo, validar_cantidad,
                                           validar_descuento, verificar_canjeable)

DIAS_DE_VIGENCIA = 30

_cupones: dict[str, InfoCupon] = {}
_lock = threading.Lock()


def reiniciar() -> None:
    """Borra todos los cupones simulados (para los tests)."""
    with _lock:
        _cupones.clear()


class CuponesMock:
    def generar_cupones(self, descuento_porcentaje, cantidad: int = 1) -> list[InfoCupon]:
        descuento = validar_descuento(descuento_porcentaje)
        validar_cantidad(cantidad)
        vencimiento = date.today() + timedelta(days=DIAS_DE_VIGENCIA)
        nuevos = []
        with _lock:
            for _ in range(cantidad):
                codigo = _codigo_nuevo()
                _cupones[codigo] = InfoCupon(codigo, descuento, EstadoCupon.disponible, gerente_id=GERENTE_ID,
                                             fecha_vencimiento=vencimiento)
                nuevos.append(_cupones[codigo])
        return nuevos

    def asignar_a_medico(self, medico_id, codigo: str) -> None:
        codigo = normalizar_codigo(codigo)
        with _lock:
            cupon = _cupones.get(codigo)
            if cupon is None or cupon.gerente_id != GERENTE_ID:
                raise CuponInexistente(codigo)
            _habilitado(cupon, EstadoCupon.disponible)
            _cupones[codigo] = replace(cupon, estado=EstadoCupon.medico, medico_id=str(medico_id))

    def asignar_a_paciente(self, medico_id, paciente_id, codigo: str) -> None:
        codigo, paciente_id = normalizar_codigo(codigo), str(paciente_id)
        with _lock:
            if any(c.paciente_id == paciente_id for c in _cupones.values()):
                raise CuponNoDisponible(codigo, "El paciente ya tiene un cupón.")
            cupon = _cupones.get(codigo)
            if cupon is None or cupon.medico_id != str(medico_id):
                raise CuponInexistente(codigo)
            _habilitado(cupon, EstadoCupon.medico)
            _cupones[codigo] = replace(cupon, estado=EstadoCupon.paciente, paciente_id=paciente_id)

    def canjear_cupon(self, paciente_id, codigo: str) -> None:
        codigo = normalizar_codigo(codigo)
        with _lock:
            cupon = verificar_canjeable(_cupones.get(codigo), str(paciente_id), codigo)
            _cupones[codigo] = replace(cupon, estado=EstadoCupon.usado, fecha_uso=datetime.now(timezone.utc))

    def validar_cupon(self, paciente_id, codigo: str) -> InfoCupon:
        codigo = normalizar_codigo(codigo)
        return verificar_canjeable(self.consultar_cupon(codigo), str(paciente_id), codigo)

    def consultar_cupon(self, codigo: str) -> InfoCupon | None:
        with _lock:
            return _cupones.get(normalizar_codigo(codigo))

    def listar_cupones(self, estado: EstadoCupon | None = None, medico_id=None) -> list[InfoCupon]:
        with _lock:
            return [c for c in _cupones.values()
                    if (estado is None or c.estado == estado) and (medico_id is None or c.medico_id == str(medico_id))]


def _habilitado(cupon: InfoCupon, estado_esperado: EstadoCupon) -> None:
    if cupon.estado != estado_esperado or cupon.vencido:
        raise CuponNoHabilitado(cupon.codigo)


def _codigo_nuevo() -> str:
    while True:
        codigo = secrets.token_hex(4)  # 8 caracteres, como los de la API
        if codigo not in _cupones:
            return codigo
