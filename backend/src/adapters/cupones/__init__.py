"""Módulo 3 (Cupones). Recorrido: generar (disponible) -> asignar al médico (medico) -> asignar al
paciente (paciente) -> canjear (usado). Vencen a los 30 días. Sin PDF ni QR: alcanza con el código.

    from src.adapters.cupones import get_cupones

    cupones = get_cupones()
    [cupon] = cupones.generar_cupones(15)                     # gerente
    cupones.asignar_a_medico(medico_id, cupon.codigo)         # gerente
    cupones.asignar_a_paciente(medico_id, paciente_id, cupon.codigo)  # médico
    cupones.validar_cupon(paciente_id, codigo)                # antes de cobrar: 404/409/400 si no sirve
    cupones.canjear_cupon(paciente_id, codigo)                # al registrar el pago
"""
from src.adapters import crear_adaptador
from src.adapters.cupones.interfaz import (CuponesDeOtroGerente, CuponInexistente, CuponNoDisponible,
                                           CuponNoHabilitado, Cupones, EstadoCupon, InfoCupon)
from src.adapters.cupones.mock import CuponesMock
from src.adapters.cupones.real import CuponesReal


def get_cupones() -> Cupones:
    return crear_adaptador("CUPONES", mock=CuponesMock, real=CuponesReal)


__all__ = ["CuponesDeOtroGerente", "CuponInexistente", "CuponNoDisponible", "CuponNoHabilitado", "Cupones",
           "EstadoCupon", "InfoCupon", "get_cupones"]
