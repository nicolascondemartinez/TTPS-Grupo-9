"""Genera el DER en Mermaid a partir de los modelos (siempre coincide con el código).

    python tools/generar_der.py backend               > docs/der_core.md
    python tools/generar_der.py obras_sociales_api   > docs/der_obras_sociales.md
"""
import importlib
import os
import sys

proyecto = sys.argv[1]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", proyecto))
importlib.import_module("app.db.models")
from app.db.base import Base  # noqa: E402

TIPOS = {"UUID": "uuid", "VARCHAR": "string", "TEXT": "text", "BOOLEAN": "bool", "INTEGER": "int", "NUMERIC": "decimal",
         "DATE": "date", "TIMESTAMP": "timestamptz", "ENUM": "enum"}


def tipo(col):
    n = col.type.__class__.__name__.upper()
    return TIPOS.get(n, n.lower())


def tabla(t):
    return t.name


out = ["```mermaid", "erDiagram"]
for t in sorted(Base.metadata.tables.values(), key=tabla):
    out.append(f"    {tabla(t)} {{")
    fks = {c.name for fk in t.foreign_key_constraints for c in fk.columns}
    for c in t.columns:
        marcas = [m for m, cond in (("PK", c.primary_key), ("FK", c.name in fks), ("UK", bool(c.unique))) if cond]
        out.append(f"        {tipo(c)} {c.name} {','.join(marcas)}".rstrip())
    out.append("    }")
for t in sorted(Base.metadata.tables.values(), key=tabla):
    pk = {c.name for c in t.primary_key.columns}
    for fk in t.foreign_key_constraints:
        padre = tabla(fk.referred_table)
        cols = list(fk.columns)
        nombres = {c.name for c in cols}
        opcional = any(c.nullable for c in cols)
        uno_a_uno = nombres == pk or (len(cols) == 1 and bool(cols[0].unique))
        if uno_a_uno:
            rel = "|o--o|" if opcional else "||--o|"
        else:
            rel = "|o--o{" if opcional else "||--o{"
        out.append(f'    {padre} {rel} {tabla(t)} : "{",".join(sorted(nombres))}"')
out.append("```")
print("\n".join(out))
