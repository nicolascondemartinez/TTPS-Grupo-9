"""Adaptador real del módulo 3 (API de cupones de Exoma Care, v2).

Ojo: las escrituras no se pueden deshacer ni reintentar a ciegas (no son idempotentes): ante un
timeout, consultar el estado antes de repetir."""
from datetime import date, datetime
from decimal import Decimal

from src.adapters import AdaptadorNoAutorizado, HttpClient, RespuestaInvalida, SolicitudRechazada
from src.adapters.cupones.interfaz import (GERENTE_ID, CuponesDeOtroGerente, CuponInexistente, CuponNoDisponible,
                                           CuponNoHabilitado, EstadoCupon, InfoCupon, normalizar_codigo,
                                           validar_cantidad, validar_descuento, verificar_canjeable)

TAMANO_PAGINA = 100  # máximo de la API


class CuponesReal:
    def __init__(self, http: HttpClient):
        self.http = http

    def generar_cupones(self, descuento_porcentaje, cantidad: int = 1) -> list[InfoCupon]:
        descuento = validar_descuento(descuento_porcentaje)
        validar_cantidad(cantidad)
        filas = self._escribir("/generar_cupones_gerencia", {
            "p_gerente_id": GERENTE_ID, "p_cantidad": cantidad, "p_porcentaje_descuento": float(descuento),
        }, codigo="")
        try:
            # La fecha de vencimiento la fija la API (30 días); se ve al consultar el cupón.
            return [InfoCupon(f["codigo_cupon"], Decimal(str(f["porcentaje"])), EstadoCupon.disponible,
                              gerente_id=GERENTE_ID) for f in filas]
        except (KeyError, TypeError):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "generar_cupones"})

    def asignar_a_medico(self, medico_id, codigo: str) -> None:
        codigo = normalizar_codigo(codigo)
        self._confirmar(self._escribir("/asignar_cupon_a_medico", {
            "p_gerente_id": GERENTE_ID, "p_medico_id": str(medico_id), "p_codigo": codigo}, codigo))

    def asignar_a_paciente(self, medico_id, paciente_id, codigo: str) -> None:
        codigo = normalizar_codigo(codigo)
        self._confirmar(self._escribir("/asignar_cupon_a_paciente", {
            "p_medico_id": str(medico_id), "p_paciente_id": str(paciente_id), "p_codigo": codigo}, codigo))

    def canjear_cupon(self, paciente_id, codigo: str) -> None:
        codigo = normalizar_codigo(codigo)
        self._confirmar(self._escribir("/canjear_cupon", {"p_paciente_id": str(paciente_id), "p_codigo": codigo}, codigo))

    def validar_cupon(self, paciente_id, codigo: str) -> InfoCupon:
        codigo = normalizar_codigo(codigo)
        return verificar_canjeable(self.consultar_cupon(codigo), str(paciente_id), codigo)

    def consultar_cupon(self, codigo: str) -> InfoCupon | None:
        # La API no filtra por código: se recorren las páginas del grupo.
        codigo = normalizar_codigo(codigo)
        return next((c for c in self.listar_cupones() if c.codigo == codigo), None)

    def listar_cupones(self, estado: EstadoCupon | None = None, medico_id=None) -> list[InfoCupon]:
        filtros = {}
        if estado is not None:
            filtros["estado"] = EstadoCupon(estado).value
        if medico_id is not None:
            filtros["medico_id"] = str(medico_id)
        cupones: list[InfoCupon] = []
        while True:
            pagina = self.http.get("/cupones", params={**filtros, "limit": TAMANO_PAGINA, "offset": len(cupones)})
            try:
                items, total = pagina["items"], int(pagina["total"])
                cupones.extend(_info(item) for item in items)
            except (KeyError, TypeError, ValueError):
                raise RespuestaInvalida(self.http.modulo, {"motivo": "cupones"})
            if not items or len(cupones) >= total:
                return cupones

    def _escribir(self, ruta: str, cuerpo: dict, codigo: str):
        try:
            return self.http.post(ruta, cuerpo)
        except SolicitudRechazada as e:
            mensaje = e.cuerpo.get("message") if isinstance(e.cuerpo, dict) else None
            if e.status_externo == 404:
                raise CuponInexistente(codigo, mensaje or "El cupón no existe o no corresponde.")
            if e.status_externo == 409:
                raise CuponNoDisponible(codigo, mensaje or "El cupón ya no se puede usar.")
            if e.status_externo == 400:
                raise CuponNoHabilitado(codigo, mensaje or "El cupón no está habilitado para esta operación.")
            raise
        except AdaptadorNoAutorizado as e:
            if e.status_externo == 403:  # el grupo ya tiene otro gerente (solo al generar)
                mensaje = e.cuerpo.get("message") if isinstance(e.cuerpo, dict) else None
                raise CuponesDeOtroGerente(mensaje or "El grupo ya está administrado por otro gerente.")
            raise

    def _confirmar(self, respuesta) -> None:
        if respuesta is not True:
            raise RespuestaInvalida(self.http.modulo, {"motivo": "se esperaba true"})


def _info(item: dict) -> InfoCupon:
    porcentaje = item["porcentaje_descuento"]
    return InfoCupon(
        codigo=item["codigo"],
        descuento_porcentaje=Decimal(str(porcentaje)) if porcentaje is not None else None,
        estado=EstadoCupon(item["estado"]),
        gerente_id=item["gerente_id"],
        medico_id=item["medico_id"],
        paciente_id=item["paciente_id"],
        fecha_vencimiento=date.fromisoformat(item["fecha_vencimiento"]) if item["fecha_vencimiento"] else None,
        fecha_uso=datetime.fromisoformat(item["fecha_uso"]) if item["fecha_uso"] else None,
    )
