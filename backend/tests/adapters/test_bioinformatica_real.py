import json

import pytest
import requests

from src.adapters import HttpClient, RespuestaInvalida, SolicitudRechazada
from src.adapters.bioinformatica import get_bioinformatica
from src.adapters.bioinformatica.real import TAMANO_PAGINA, BioinformaticaReal
from src.core.enums import ClasificacionVariante


class Apigen(requests.Session):
    """Sesión falsa: `responder(method, path, kwargs)` devuelve (status, cuerpo)."""

    def __init__(self, responder):
        super().__init__()
        self.responder = responder
        self.pedidos = []

    def request(self, method, url, **kwargs):
        path = url.removeprefix("https://apigen.test/rest/v1")
        self.pedidos.append((method, path, kwargs))
        status, cuerpo = self.responder(method, path, kwargs)
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(cuerpo).encode()
        return response


def real(responder) -> tuple[BioinformaticaReal, Apigen]:
    sesion = Apigen(responder)
    return BioinformaticaReal(HttpClient("BIOINFORMATICA", "https://apigen.test/rest/v1", "k", session=sesion)), sesion


def test_get_bioinformatica_real_manda_la_key_en_el_header_apikey(monkeypatch):
    monkeypatch.setenv("BIOINFORMATICA_MODE", "real")
    monkeypatch.setenv("BIOINFORMATICA_API_URL", "https://apigen.test/rest/v1")
    monkeypatch.setenv("BIOINFORMATICA_API_KEY", "clave")
    bio = get_bioinformatica()
    assert isinstance(bio, BioinformaticaReal)
    assert bio.http.session.headers["apikey"] == "clave"


@pytest.mark.parametrize("nombre, codigo", [
    ("Fabry", "FABRY"), ("Pompe", "POMPE"), ("Mucopolisacaridosis 1", "MPS1"), ("Gaucher", "GAUCHER"), ("ASMD", "ASMD"),
])
def test_genes_por_patologia_traduce_el_nombre_al_codigo(nombre, codigo):
    bio, sesion = real(lambda *_: (200, ["GEN1"]))

    assert bio.genes_por_patologia(nombre) == ["GEN1"]

    method, path, kwargs = sesion.pedidos[0]
    assert (method, path) == ("POST", "/rpc/genes_por_patologia")
    assert kwargs["json"] == {"p_patologia": codigo, "p_grupo_id": "grupo9"}


def test_patologia_inexistente_devuelve_lista_vacia():
    bio, _ = real(lambda *_: (400, {"code": "P0001", "message": "Patología inexistente: XYZ"}))
    assert bio.genes_por_patologia("XYZ") == []


def test_otro_400_no_se_oculta():
    bio, _ = real(lambda *_: (400, {"message": "Otro error"}))
    with pytest.raises(SolicitudRechazada):
        bio.genes_por_patologia("Fabry")


def test_genes_hallazgos_secundarios():
    bio, sesion = real(lambda *_: (200, [{"gen": "ACTA2"}, {"gen": "BRCA1"}]))
    assert bio.genes_hallazgos_secundarios() == ["ACTA2", "BRCA1"]
    assert sesion.pedidos[0][1] == "/genes_hallazgos_secundarios"


def test_variantes_traduce_clasificaciones_y_arma_el_nombre():
    filas = [
        {"id": "GAA:c.-32-13T>G", "hgvs_c": "c.-32-13T>G", "proteina": None, "clasificacion": "patogenica"},
        {"id": "GAA:c.1012G>T", "hgvs_c": "c.1012G>T", "proteina": "p.Asp338Tyr", "clasificacion": "probablemente_patogenica"},
        {"id": "GAA:c.1013A>T", "hgvs_c": "c.1013A>T", "proteina": "p.Asp338Val", "clasificacion": "vus"},
        {"id": "GAA:c.1011G>T", "hgvs_c": "c.1011G>T", "proteina": "p.Leu337=", "clasificacion": "benigna"},
    ]
    bio, sesion = real(lambda *_: (200, filas))

    variantes = bio.variantes_por_gen("gaa")

    assert [(v.codigo, v.nombre, v.clasificacion) for v in variantes] == [
        ("GAA:c.-32-13T>G", "c.-32-13T>G", ClasificacionVariante.patogenica),
        ("GAA:c.1012G>T", "c.1012G>T (p.Asp338Tyr)", ClasificacionVariante.vus),
        ("GAA:c.1013A>T", "c.1013A>T (p.Asp338Val)", ClasificacionVariante.vus),
        ("GAA:c.1011G>T", "c.1011G>T (p.Leu337=)", ClasificacionVariante.benigna),
    ]
    assert sesion.pedidos[0][2]["params"]["gen"] == "eq.GAA"


def test_variantes_pide_todas_las_paginas():
    total = TAMANO_PAGINA * 2 + 5
    fila = {"id": "G:c.1A>G", "hgvs_c": "c.1A>G", "proteina": None, "clasificacion": "vus"}

    def responder(_method, _path, kwargs):
        offset = kwargs["params"]["offset"]
        return 200, [fila] * min(TAMANO_PAGINA, total - offset)

    bio, sesion = real(responder)

    assert len(bio.variantes_por_gen("G")) == total
    assert [p[2]["params"]["offset"] for p in sesion.pedidos] == [0, TAMANO_PAGINA, TAMANO_PAGINA * 2]


def test_gen_sin_variantes():
    bio, _ = real(lambda *_: (200, []))
    assert bio.variantes_por_gen("NOEXISTE") == []


@pytest.mark.parametrize("fila", [
    {"id": "G:c.1A>G", "hgvs_c": "c.1A>G", "proteina": None, "clasificacion": "rara"},
    {"id": "G:c.1A>G", "proteina": None, "clasificacion": "vus"},
])
def test_variante_con_formato_inesperado(fila):
    bio, _ = real(lambda *_: (200, [fila]))
    with pytest.raises(RespuestaInvalida):
        bio.variantes_por_gen("G")
