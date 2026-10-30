"""    DATABASE_URL=postgresql+psycopg2://... python -m tests.smoke_test   (se revierte al final)"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.db.models import Consumidor, EstadoSolicitud, ObraSocial, SolicitudEstudio
from app.db.session import SessionLocal

ok = 0


def chk(s, desc, fn, falla):
    global ok
    try:
        with s.begin_nested():
            fn()
            s.flush()
        if falla:
            raise AssertionError(f"NO se rechazó: {desc}")
    except IntegrityError:
        if not falla:
            raise
    ok += 1
    print(f"  OK  {'rechaza' if falla else 'acepta '}: {desc}")


with SessionLocal() as s:
    c1, c2 = Consumidor(nombre="grupo-test-1", api_key_hash="h1"), Consumidor(nombre="grupo-test-2", api_key_hash="h2")
    os_ = ObraSocial(rnos_codigo="TEST-1", nombre="OS de prueba", porcentaje_cobertura=Decimal("70"))
    s.add_all([c1, c2, os_])
    s.flush()
    nueva = lambda **kw: SolicitudEstudio(consumidor_id=c1.id, obra_social_id=os_.id, paciente_nombre="Ana", fecha=date.today(), **kw)
    chk(s, "obra social con 150%", lambda: s.add(ObraSocial(rnos_codigo="T2", nombre="x", porcentaje_cobertura=Decimal("150"))), True)
    chk(s, "solicitud pendiente", lambda: s.add(nueva()), False)
    chk(s, "solicitud rechazada sin motivo", lambda: s.add(nueva(estado=EstadoSolicitud.rechazada, resuelta_at=datetime.now(timezone.utc))), True)
    chk(s, "solicitud autorizada sin fecha de resolución", lambda: s.add(nueva(estado=EstadoSolicitud.autorizada)), True)
    chk(s, "solicitud rechazada con motivo y fecha", lambda: s.add(nueva(estado=EstadoSolicitud.rechazada, motivo_rechazo="sin evidencia", resuelta_at=datetime.now(timezone.utc))), False)
    s.rollback()
    print(f"\n{ok} verificaciones correctas")
