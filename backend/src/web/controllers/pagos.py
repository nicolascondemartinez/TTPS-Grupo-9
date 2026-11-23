"""Presupuesto y pago particular. El administrativo emite el presupuesto; el paciente lo ve y lo paga."""
from flask import Blueprint, g

from src.core.avisos.mail_service import get_mail_sender
from src.core.database import get_db
from src.core.pagos import service as pagos_service
from src.web.security import require_permission
from src.web.views.pago_view import (estudios_del_paciente_view, pago_view, pendientes_de_presupuesto_view,
                                    presupuesto_view)

bp = Blueprint("pagos", __name__)


@bp.get("/presupuestos/pendientes")
@require_permission("presupuesto_emitir")
def pendientes():
    pendientes = pagos_service.listar_pendientes_de_presupuesto(get_db())
    return pendientes_de_presupuesto_view(pendientes, pagos_service.precio)


@bp.get("/presupuestos/mios")
@require_permission("presupuesto_ver")
def mios():
    """Para la pantalla "Presupuesto y pago" del paciente: sus estudios con su situación de pago."""
    return estudios_del_paciente_view(pagos_service.listar_estudios_del_paciente(get_db(), g.usuario))


@bp.post("/estudios/<estudio_id>/presupuesto")
@require_permission("presupuesto_emitir")
def emitir(estudio_id):
    presupuesto = pagos_service.emitir_presupuesto(get_db(), estudio_id, g.usuario, get_mail_sender())
    return presupuesto_view(presupuesto), 201


@bp.get("/estudios/<estudio_id>/presupuesto")
@require_permission("presupuesto_ver")
def ver(estudio_id):
    return presupuesto_view(pagos_service.obtener_presupuesto(get_db(), estudio_id, g.usuario))


@bp.post("/estudios/<estudio_id>/pagos")
@require_permission("pago_realizar")
def pagar(estudio_id):
    movimiento, estudio = pagos_service.pagar_particular(get_db(), estudio_id, g.usuario, get_mail_sender())
    return pago_view(movimiento, estudio), 201
