"""JSON del registro de usuarios."""


from src.web.views.auth_view import usuario_view


def especialidades_view(especialidades) -> dict:
    return {"especialidades": [{"id": str(e.id), "nombre": e.nombre} for e in especialidades]}


def registro_view(usuario) -> dict:
    return {"usuario": usuario_view(usuario)}