import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
import requests

from src.adapters import AdaptadorNoAutorizado, HttpClient, RespuestaInvalida
from src.adapters.cupones import (CuponesDeOtroGerente, CuponInexistente, CuponNoDisponible, CuponNoHabilitado,
                                  EstadoCupon, get_cupones)
from src.adapters.cupones.real import TAMANO_PAGINA, CuponesReal

BASE = "https://cupones.test/functions/v1/cupones-api"
MANANA = (date.today() + timedelta(days=1)).isoformat()


def item(codigo="2ded2dc3", estado="paciente", paciente_id="p-1", vencimiento=MANANA, **kwargs):
    return {"id": "00000000-0000-0000-0000-000000000000", "codigo": codigo, "estado": estado,
            "gerente_id": "gerente-grupo9", "medico_id": "m-1", "paciente_id": paciente_id,
            "porcentaje_descuento": 20, "fecha_vencimiento": vencimiento, "fecha_uso": None, **kwargs}


class Api(requests.Session):
    """`respuestas` mapea la ruta a (status, cuerpo); GET /cupones pagina sobre `items`."""

    def __init__(self, respuestas=None, items=()):
        super().__init__()
        self.respuestas, self.items, self.pedidos = respuestas or {}, list(items), []

    def request(self, method, url, **kwargs):
        ruta = url.removeprefix(BASE)
        self.pedidos.append((method, ruta, kwargs))
        if ruta == "/cupones":
            p = kwargs["params"]
            status, cuerpo = 200, {"items": self.items[p["offset"]:p["offset"] + p["limit"]],
                                   "total": len(self.items), "limit": p["limit"], "offset": p["offset"]}
        else:
            status, cuerpo = self.respuestas.get(ruta, (200, True))
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(cuerpo).encode()
        return response


def real(**kwargs) -> tuple[CuponesReal, Api]:
    sesion = Api(**kwargs)
    return CuponesReal(HttpClient("CUPONES", BASE, "clave", session=sesion)), sesion


def error(status, mensaje):
    return status, {"code": f"PT{status}", "message": mensaje, "details": None, "hint": None}


def test_get_cupones_real(monkeypatch):
    monkeypatch.setenv("CUPONES_MODE", "real")
    monkeypatch.setenv("CUPONES_API_URL", BASE)
    monkeypatch.setenv("CUPONES_API_KEY", "ecg_clave")
    cupones = get_cupones()
    assert isinstance(cupones, CuponesReal)
    assert cupones.http.session.headers["X-API-Key"] == "ecg_clave"


def test_generar_manda_el_gerente_fijo():
    cupones, sesion = real(respuestas={"/generar_cupones_gerencia": (200, [
        {"codigo_cupon": "53399388", "porcentaje": 20}, {"codigo_cupon": "2ded2dc3", "porcentaje": 20}])})

    nuevos = cupones.generar_cupones(20, cantidad=2)

    assert [(c.codigo, c.descuento_porcentaje, c.estado) for c in nuevos] == [
        ("53399388", Decimal("20"), EstadoCupon.disponible), ("2ded2dc3", Decimal("20"), EstadoCupon.disponible)]
    assert sesion.pedidos[0][2]["json"] == {"p_gerente_id": "gerente-grupo9", "p_cantidad": 2,
                                            "p_porcentaje_descuento": 20.0}


def test_generar_con_otro_gerente():
    cupones, _ = real(respuestas={"/generar_cupones_gerencia": error(403, "El grupo ya está administrado por otro gerente")})
    with pytest.raises(CuponesDeOtroGerente) as e:
        cupones.generar_cupones(20)
    assert e.value.status == 409 and e.value.mensaje == "El grupo ya está administrado por otro gerente"


def test_401_sigue_siendo_no_autorizado():
    cupones, _ = real(respuestas={"/generar_cupones_gerencia": error(401, "Clave ausente, inválida o revocada")})
    with pytest.raises(AdaptadorNoAutorizado):
        cupones.generar_cupones(20)


def test_asignaciones_y_canje_mandan_los_ids_como_texto():
    cupones, sesion = real()
    cupones.asignar_a_medico(123, "2ded-2dc3")
    cupones.asignar_a_paciente(123, 456, "2ded2dc3")
    cupones.canjear_cupon(456, "2ded2dc3")

    assert [(r, k["json"]) for _, r, k in sesion.pedidos] == [
        ("/asignar_cupon_a_medico", {"p_gerente_id": "gerente-grupo9", "p_medico_id": "123", "p_codigo": "2ded2dc3"}),
        ("/asignar_cupon_a_paciente", {"p_medico_id": "123", "p_paciente_id": "456", "p_codigo": "2ded2dc3"}),
        ("/canjear_cupon", {"p_paciente_id": "456", "p_codigo": "2ded2dc3"}),
    ]


@pytest.mark.parametrize("status, error_esperado", [
    (404, CuponInexistente), (409, CuponNoDisponible), (400, CuponNoHabilitado)])
def test_errores_de_negocio_con_el_mensaje_de_la_api(status, error_esperado):
    cupones, _ = real(respuestas={"/canjear_cupon": error(status, "mensaje de la API")})
    with pytest.raises(error_esperado) as e:
        cupones.canjear_cupon("p-1", "2ded2dc3")
    assert e.value.mensaje == "mensaje de la API" and e.value.detalle == {"codigo": "2ded2dc3"}


def test_respuesta_distinta_de_true():
    cupones, _ = real(respuestas={"/canjear_cupon": (200, {"ok": True})})
    with pytest.raises(RespuestaInvalida):
        cupones.canjear_cupon("p-1", "2ded2dc3")


def test_listar_recorre_todas_las_paginas_y_traduce_los_campos():
    items = [item(codigo=f"c{i:07d}") for i in range(TAMANO_PAGINA + 5)]
    items[0] = item(codigo="c0000000", estado="usado", fecha_uso="2026-11-15T13:00:00+00:00")
    cupones, sesion = real(items=items)

    todos = cupones.listar_cupones(estado=EstadoCupon.paciente, medico_id="m-1")

    assert len(todos) == TAMANO_PAGINA + 5 and len(sesion.pedidos) == 2
    assert sesion.pedidos[0][2]["params"] == {"estado": "paciente", "medico_id": "m-1", "limit": 100, "offset": 0}
    primero = todos[0]
    assert primero.estado == EstadoCupon.usado and primero.fecha_uso.year == 2026
    assert primero.descuento_porcentaje == Decimal("20") and primero.fecha_vencimiento.isoformat() == MANANA


def test_consultar_busca_el_codigo():
    cupones, _ = real(items=[item(codigo="aaaa1111"), item(codigo="2ded2dc3")])
    assert cupones.consultar_cupon("2ded-2dc3").codigo == "2ded2dc3"
    assert cupones.consultar_cupon("noexiste") is None


def test_validar_no_escribe_nada():
    cupones, sesion = real(items=[item()])
    assert cupones.validar_cupon("p-1", "2ded2dc3").codigo == "2ded2dc3"
    assert all(m == "GET" for m, _, _ in sesion.pedidos)


@pytest.mark.parametrize("cupon, paciente, error_esperado", [
    (item(), "otro", CuponInexistente),
    (item(estado="usado"), "p-1", CuponNoDisponible),
    (item(vencimiento=(date.today() - timedelta(days=1)).isoformat()), "p-1", CuponNoHabilitado),
    (item(estado="medico", paciente_id=None), "p-1", CuponInexistente),  # todavía no es de ningún paciente
])
def test_validar_rechaza(cupon, paciente, error_esperado):
    cupones, _ = real(items=[cupon])
    with pytest.raises(error_esperado):
        cupones.validar_cupon(paciente, "2ded2dc3")


def test_vence_al_terminar_el_dia():
    cupones, _ = real(items=[item(vencimiento=date.today().isoformat())])
    assert cupones.validar_cupon("p-1", "2ded2dc3")


def test_item_con_formato_inesperado():
    cupones, _ = real(items=[{"codigo": "x"}])
    with pytest.raises(RespuestaInvalida):
        cupones.listar_cupones()
