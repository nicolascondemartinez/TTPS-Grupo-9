"""Vistas en JSOn de: orden del día, paradas y ubicación de muestras."""
from src.core.models import OrdenDelDia, OrdenParada


def orden_generada_view(ordenes: list[OrdenDelDia]) -> dict:
    """Devuelve el resumen de las órdenes del día generadas."""
    return {
        "ordenes": [
            {
                "id": str(o.id),
                "fecha": o.fecha.isoformat(),
                "transportista_id": str(o.transportista_id),
            }
            for o in ordenes
        ]
    }


def orden_del_dia_view(data: dict | None) -> dict:
    """Devuelve la orden del día del transportista con sus paradas para la vista móvil y el mapa."""
    if data is None:
        return {"orden": None}

    orden: OrdenDelDia = data["orden"]
    return {
        "orden": {
            "id": str(orden.id),
            "fecha": orden.fecha.isoformat(),
            "llegada_central_at": orden.llegada_central_at.isoformat() if orden.llegada_central_at else None,
            "paradas": [
                {
                    "id": str(p["id"]),
                    "posicion": p["posicion"],
                    "recogido": p["recogido"],
                    "recogida_at": p["recogida_at"].isoformat() if p["recogida_at"] else None,
                    "cantidad_muestras": p["cantidad_muestras"],
                    "centro": {
                        "id": str(p["centro"].id),
                        "nombre": p["centro"].nombre,
                        "direccion": p["centro"].direccion,
                        "latitud": float(p["centro"].latitud),
                        "longitud": float(p["centro"].longitud),
                    },
                }
                for p in data["paradas"]
            ],
        }
    }


def parada_recogida_view(parada: OrdenParada) -> dict:
    """Devuelve la confirmación de una parada marcada como recogida."""
    return {
        "parada": {
            "id": str(parada.id),
            "posicion": parada.posicion,
            "recogida_at": parada.recogida_at.isoformat() if parada.recogida_at else None,
        }
    }


def orden_entregada_view(orden: OrdenDelDia) -> dict:
    """Devuelve la confirmación de llegada de la orden al laboratorio central."""
    return {
        "orden": {
            "id": str(orden.id),
            "llegada_central_at": orden.llegada_central_at.isoformat() if orden.llegada_central_at else None,
        }
    }


def ubicacion_muestra_view(data: dict) -> dict:
    """Devuelve la ubicación simulada del transportista y las paradas del recorrido para <Mapa />."""
    return {
        "estudio_id": str(data["estudio_id"]),
        "transportista": data["transportista"],
        "paradas": [
            {
                "id": str(p["id"]),
                "posicion": p["posicion"],
                "nombre": p["nombre"],
                "direccion": p["direccion"],
                "latitud": p["latitud"],
                "longitud": p["longitud"],
                "recogido": p["recogido"],
            }
            for p in data["paradas"]
        ],
    }