"""Datos fijos de ejemplo para desarrollo y tests: no son una referencia clínica.
Mismo formato que Apigen: código "GEN:c.…" y nombre "c.… (p.…)"."""
from src.adapters.bioinformatica.interfaz import Variante
from src.core.enums import ClasificacionVariante as C

GENES_POR_PATOLOGIA = {
    "fabry": ("GLA",),
    "pompe": ("GAA",),
    "mucopolisacaridosis 1": ("IDUA",),
    "gaucher": ("GBA1",),
    "asmd": ("SMPD1",),
}

GENES_HALLAZGOS_SECUNDARIOS = ("BRCA1", "BRCA2", "MLH1", "MSH2", "TP53", "LDLR", "MYBPC3", "KCNQ1", "RYR1", "TTR")


def _v(gen: str, hgvs_c: str, proteina: str | None, clasificacion: C) -> Variante:
    return Variante(f"{gen}:{hgvs_c}", hgvs_c + (f" ({proteina})" if proteina else ""), clasificacion)


VARIANTES_POR_GEN = {
    "GLA": (
        _v("GLA", "c.644A>G", "p.Asn215Ser", C.patogenica),
        _v("GLA", "c.427G>A", "p.Ala143Thr", C.vus),
        _v("GLA", "c.937G>T", "p.Asp313Tyr", C.benigna),
    ),
    "GAA": (
        _v("GAA", "c.-32-13T>G", None, C.patogenica),
        _v("GAA", "c.1726G>A", "p.Gly576Ser", C.benigna),
        _v("GAA", "c.324T>C", "p.Cys108=", C.inocua),
    ),
    "IDUA": (
        _v("IDUA", "c.1205G>A", "p.Trp402Ter", C.patogenica),
        _v("IDUA", "c.208C>T", "p.Gln70Ter", C.patogenica),
        _v("IDUA", "c.1081G>A", "p.Ala361Thr", C.vus),
    ),
    "GBA1": (
        _v("GBA1", "c.1226A>G", "p.Asn409Ser", C.patogenica),
        _v("GBA1", "c.1448T>C", "p.Leu483Pro", C.patogenica),
        _v("GBA1", "c.1093G>A", "p.Glu365Lys", C.vus),
    ),
    "SMPD1": (
        _v("SMPD1", "c.1829_1831del", "p.Arg610del", C.patogenica),
        _v("SMPD1", "c.107T>C", "p.Val36Ala", C.benigna),
    ),
    "BRCA1": (
        _v("BRCA1", "c.68_69del", "p.Glu23ValfsTer17", C.patogenica),
        _v("BRCA1", "c.2612C>T", "p.Pro871Leu", C.benigna),
    ),
    "BRCA2": (
        _v("BRCA2", "c.5946del", "p.Ser1982ArgfsTer22", C.patogenica),
        _v("BRCA2", "c.7397T>C", "p.Val2466Ala", C.inocua),
    ),
    "MLH1": (_v("MLH1", "c.655A>G", "p.Ile219Val", C.benigna),),
    "MSH2": (_v("MSH2", "c.942+3A>T", None, C.patogenica),),
    "TP53": (_v("TP53", "c.215C>G", "p.Pro72Arg", C.benigna),),
    "LDLR": (_v("LDLR", "c.1060+10G>C", None, C.vus),),
    "MYBPC3": (_v("MYBPC3", "c.1504C>T", "p.Arg502Trp", C.patogenica),),
    "KCNQ1": (_v("KCNQ1", "c.1343C>G", "p.Pro448Arg", C.inocua),),
    "RYR1": (_v("RYR1", "c.1840C>T", "p.Arg614Cys", C.patogenica),),
    "TTR": (_v("TTR", "c.424G>A", "p.Val142Ile", C.patogenica),),
}


class BioinformaticaMock:
    def genes_por_patologia(self, patologia: str) -> list[str]:
        return list(GENES_POR_PATOLOGIA.get(patologia.strip().lower(), ()))

    def genes_hallazgos_secundarios(self) -> list[str]:
        return list(GENES_HALLAZGOS_SECUNDARIOS)

    def variantes_por_gen(self, gen: str) -> list[Variante]:
        return list(VARIANTES_POR_GEN.get(gen.strip().upper(), ()))
