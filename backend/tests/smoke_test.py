"""Prueba de humo del esquema contra un Postgres real (valida constraints e índices parciales).

    DATABASE_URL=postgresql+psycopg2://... python -m tests.smoke_test

Corre dentro de una transacción que se revierte al final: no deja datos.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.db.enums import *  # noqa: F403
from app.db.models import *  # noqa: F403
from app.db.session import SessionLocal

ok = 0


def debe_fallar(s, descripcion, fn):
    """Ejecuta fn en un savepoint y exige IntegrityError."""
    global ok
    try:
        with s.begin_nested():
            fn()
            s.flush()
    except IntegrityError:
        ok += 1
        print(f"  OK  rechaza: {descripcion}")
        return
    raise AssertionError(f"NO se rechazó: {descripcion}")


def debe_pasar(s, descripcion, fn):
    global ok
    with s.begin_nested():
        fn()
        s.flush()
    ok += 1
    print(f"  OK  acepta : {descripcion}")


def usuario(email, rol):
    return Usuario(email=email, password_hash="x", nombre="N", apellido="A", telefono="1", rol=rol)


with SessionLocal() as s:
    prov = Provincia(nombre="Provincia de prueba")
    medico_u, gerente_u, paciente_u, transp_u = (
        usuario("medico@x.com", RolUsuario.medico), usuario("gerente@x.com", RolUsuario.gerente_medico),
        usuario("paciente@x.com", RolUsuario.paciente), usuario("transp@x.com", RolUsuario.transportista),
    )
    pato, pato2 = Patologia(nombre="Fabry-test"), Patologia(nombre="Pompe-test")
    s1, s2 = Sintoma(snomed_code="1", termino="a"), Sintoma(snomed_code="2", termino="b")
    s.add_all([prov, medico_u, gerente_u, paciente_u, transp_u, pato, pato2, s1, s2])
    s.flush()
    medico = Medico(usuario_id=medico_u.id, matricula="M1")
    gerente = GerenteMedico(usuario_id=gerente_u.id, matricula="G1")
    s.add_all([medico, gerente, Transportista(usuario_id=transp_u.id, provincia_id=prov.id)])
    s.flush()  # sin relationship entre tablas, el ORM no garantiza el orden de INSERT: se fuerza con flush
    paciente = Paciente(
        usuario_id=paciente_u.id, dni="1", fecha_nacimiento=date(2026, 8, 1), medico_alta_id=medico_u.id,
        diagnostico_presuntivo_id=pato.id, tipo_sospecha=TipoSospecha.clinica, historia_clinica="resumen",
    )
    s.add(paciente)
    s.flush()
    print("Usuarios / clínico")
    debe_fallar(s, "email duplicado con otra capitalización", lambda: s.add(usuario("MEDICO@x.com", RolUsuario.medico)))
    debe_fallar(s, "segundo transportista en la misma provincia", lambda: (
        s.add(usuario("t2@x.com", RolUsuario.transportista)), s.flush(),
        s.add(Transportista(usuario_id=s.scalar(__import__("sqlalchemy").select(Usuario.id).where(Usuario.email == "t2@x.com")), provincia_id=prov.id))))
    debe_pasar(s, "un síntoma cardinal", lambda: s.add(PatologiaSintoma(patologia_id=pato.id, sintoma_id=s1.id, es_cardinal=True)))
    debe_fallar(s, "segundo síntoma cardinal en la misma patología", lambda: s.add(PatologiaSintoma(patologia_id=pato.id, sintoma_id=s2.id, es_cardinal=True)))
    debe_pasar(s, "síntoma secundario", lambda: s.add(PatologiaSintoma(patologia_id=pato.id, sintoma_id=s2.id, es_cardinal=False)))

    print("Estudio / análisis")
    est = Estudio(paciente_id=paciente.usuario_id, medico_id=medico.usuario_id)
    s.add(est)
    s.flush()
    assert est.estado == EstadoEstudio.creado
    debe_fallar(s, "inasistencias = 6", lambda: setattr(est, "inasistencias", 6))
    est.inasistencias = 0
    an = Analisis(estudio_id=est.id, numero=1)
    gen_a, gen_b = Gen(simbolo="GLA"), Gen(simbolo="GAA")
    s.add_all([an, gen_a, gen_b])
    s.flush()
    s.add(AnalisisGen(analisis_id=an.id, gen_id=gen_a.id, origen=OrigenGen.patologia))
    s.flush()
    debe_fallar(s, "análisis número 1 repetido", lambda: s.add(Analisis(estudio_id=est.id, numero=1)))
    debe_pasar(s, "variante de un gen pedido", lambda: s.add(AnalisisVariante(
        analisis_id=an.id, gen_id=gen_a.id, variante_codigo="v1", clasificacion=ClasificacionVariante.patogenica)))
    debe_fallar(s, "variante de un gen NO pedido en el análisis", lambda: s.add(AnalisisVariante(
        analisis_id=an.id, gen_id=gen_b.id, variante_codigo="v2", clasificacion=ClasificacionVariante.vus)))

    print("Turnos")
    centro = CentroExtraccion(nombre="C1", direccion="d", provincia_id=prov.id, latitud=Decimal("-34.9"), longitud=Decimal("-57.9"))
    est2 = Estudio(paciente_id=paciente.usuario_id, medico_id=medico.usuario_id)
    s.add_all([centro, est2])
    s.flush()
    hora = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
    t1 = Turno(estudio_id=est.id, centro_id=centro.id, fecha_hora=hora)
    s.add(t1)
    s.flush()
    debe_fallar(s, "dos turnos reservados en el mismo centro y horario", lambda: s.add(Turno(estudio_id=est2.id, centro_id=centro.id, fecha_hora=hora)))
    debe_fallar(s, "un estudio con dos turnos reservados", lambda: s.add(Turno(estudio_id=est.id, centro_id=centro.id, fecha_hora=hora.replace(hour=10))))
    t1.estado = EstadoTurno.cancelado
    s.flush()
    debe_pasar(s, "reservar el horario liberado por una cancelación", lambda: s.add(Turno(estudio_id=est2.id, centro_id=centro.id, fecha_hora=hora)))

    print("Pagos / cupones")
    debe_fallar(s, "cupón con descuento 0%", lambda: s.add(Cupon(codigo_externo="c0", descuento_porcentaje=Decimal("0"), gerente_id=gerente.usuario_id)))
    debe_fallar(s, "cupón asignado a paciente sin médico", lambda: s.add(Cupon(codigo_externo="c1", descuento_porcentaje=Decimal("10"), gerente_id=gerente.usuario_id, paciente_id=paciente.usuario_id)))
    debe_fallar(s, "cupón usado sin estudio", lambda: s.add(Cupon(codigo_externo="c2", descuento_porcentaje=Decimal("10"), gerente_id=gerente.usuario_id, usado_at=datetime.now(timezone.utc))))
    debe_pasar(s, "cupón válido", lambda: s.add(Cupon(codigo_externo="c3", descuento_porcentaje=Decimal("15"), gerente_id=gerente.usuario_id, medico_id=medico.usuario_id)))
    debe_fallar(s, "movimiento con monto 0", lambda: s.add(MovimientoFinanciero(estudio_id=est.id, origen=OrigenPago.paciente, concepto=ConceptoPago.estudio, monto=Decimal("0"))))
    debe_fallar(s, "cobertura con porcentaje 120", lambda: s.add(Cobertura(
        estudio_id=est.id, obra_social_externa_id=__import__("uuid").uuid4(), obra_social_nombre="OS", porcentaje_cobertura=Decimal("120"),
        monto_obra_social=Decimal("1"), monto_paciente=Decimal("1"))))

    print("Logística")
    debe_fallar(s, "lote sellado sin PDF de autorización", lambda: s.add(Lote(sellado_at=datetime.now(timezone.utc))))
    lote = Lote(sellado_at=datetime.now(timezone.utc), autorizacion_pdf_url="storage://x.pdf")
    s.add(lote)
    s.flush()
    assert lote.token_retiro is not None and lote.estado == EstadoLote.esperando_autorizacion_ministerio
    debe_pasar(s, "estudio asociado a un lote", lambda: setattr(est, "lote_id", lote.id))
    orden = OrdenDelDia(fecha=date(2026, 11, 2), transportista_id=transp_u.id)
    s.add(orden)
    s.flush()
    s.add(OrdenParada(orden_id=orden.id, centro_id=centro.id, posicion=1))
    s.flush()
    debe_fallar(s, "dos órdenes del día para el mismo transportista y fecha", lambda: s.add(OrdenDelDia(fecha=date(2026, 11, 2), transportista_id=transp_u.id)))
    debe_fallar(s, "posición repetida en la orden del día", lambda: s.add(OrdenParada(orden_id=orden.id, centro_id=centro.id, posicion=1)))

    s.rollback()
    print(f"\n{ok} verificaciones correctas")
