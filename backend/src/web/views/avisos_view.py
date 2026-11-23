"""JSON que devuelven los endpoints de avisos."""


def aviso_view(aviso) -> dict:
    return {
        "id": str(aviso.id),
        "tipo": aviso.tipo.value,
        "titulo": aviso.titulo,
        "mensaje": aviso.mensaje,
        "estudio_id": str(aviso.estudio_id) if aviso.estudio_id else None,
        "turno_id": str(aviso.turno_id) if aviso.turno_id else None,
        "leido": aviso.leido,
        "creado_en": aviso.created_at.isoformat(),
    }