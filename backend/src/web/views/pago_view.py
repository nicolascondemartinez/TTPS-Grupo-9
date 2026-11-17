"""JSON de presupuestos y pagos que va a recibir
el front. Los montos van como texto ("590.00") para no perder precisión."""
from src.core.pagos.service import GENES_INCLUIDOS, PRECIO_BASE, PRECIO_GEN_ADICIONAL


def presupuesto_view(presupuesto) -> dict:
    return {
        "id": str(presupuesto.id),
        "estudio_id": str(presupuesto.estudio_id),
        "cantidad_genes": presupuesto.cantidad_genes,
        "genes_incluidos": GENES_INCLUIDOS,
        "genes_adicionales": max(0, presupuesto.cantidad_genes - GENES_INCLUIDOS),
        "precio_base": str(PRECIO_BASE),
        "precio_gen_adicional": str(PRECIO_GEN_ADICIONAL),
        "monto_total": str(presupuesto.monto_total),
        "moneda": presupuesto.moneda,
        "emitido_at": presupuesto.emitido_at.isoformat(),
    }


def pago_view(movimiento, estudio) -> dict:
    return {
        "id": str(movimiento.id),
        "estudio_id": str(estudio.id),
        "monto": str(movimiento.monto),
        "moneda": movimiento.moneda,
        "concepto": movimiento.concepto.value,
        "fecha": movimiento.created_at.isoformat(),
        "estado_estudio": estudio.estado.value,
    }


def pendientes_de_presupuesto_view(pendientes, precio) -> dict:
    """pendientes: [(estudio, cantidad_de_genes)]. precio: la función que calcula el monto."""
    return {
        "estudios": [
            {
                "estudio_id": str(estudio.id),
                "paciente": f"{estudio.paciente.usuario.apellido}, {estudio.paciente.usuario.nombre}",
                "dni": estudio.paciente.dni,
                "cantidad_genes": genes,
                "monto_estimado": str(precio(genes)) if genes else None,
                "creado_at": estudio.created_at.isoformat(),
            }
            for estudio, genes in pendientes
        ]
    }



def estudios_del_paciente_view(estudios) -> dict:
    """estudios: [(estudio, presupuesto o None)]."""
    return {
        "estudios": [
            {
                "estudio_id": str(estudio.id),
                "estado": estudio.estado.value,
                "creado_at": estudio.created_at.isoformat(),
                "presupuesto": presupuesto_view(presupuesto) if presupuesto else None,
            }
            for estudio, presupuesto in estudios
        ]
    }
