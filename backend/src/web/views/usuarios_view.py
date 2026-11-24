"""JSON del registro de usuarios."""


from src.web.views.auth_view import usuario_view


def especialidades_view(especialidades) -> dict:
    return {"especialidades": [{"id": str(e.id), "nombre": e.nombre} for e in especialidades]}


def registro_view(usuario) -> dict:
    return {"usuario": usuario_view(usuario)}


def provincias_view(provincias) -> dict:
    return {
        "provincias": [
            {"id": str(p.id), "nombre": p.nombre, "tiene_transportista": ocupada} for p, ocupada in provincias
        ]
    }


def transportista_view(transportista) -> dict:
    usuario = transportista.usuario
    return {
        "id": str(usuario.id),
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "correo": usuario.email,
        "telefono": usuario.telefono,
        "activo": usuario.activo,
        "provincia": {"id": str(transportista.provincia.id), "nombre": transportista.provincia.nombre},
    }


def transportistas_view(transportistas) -> dict:
    return {"transportistas": [transportista_view(t) for t in transportistas]}