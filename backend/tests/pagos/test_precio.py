"""Precio del estudio: USD 500 hasta 5 genes y USD 30 por cada gen adicional (no usa la base)."""
from decimal import Decimal

import pytest

from src.core.pagos.service import precio


@pytest.mark.parametrize("genes, esperado", [(1, "500"), (5, "500"), (6, "530"), (8, "590"), (20, "950")])
def test_precio(genes, esperado):
    assert precio(genes) == Decimal(esperado)


def test_un_estudio_sin_genes_no_tiene_precio():
    with pytest.raises(ValueError):
        precio(0)
