"""JSON del registro de usuarios."""


def especialidades_view(especialidades) -> dict:
    return {"especialidades": [{"id": str(e.id), "nombre": e.nombre} for e in especialidades]}