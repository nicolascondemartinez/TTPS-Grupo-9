"""JSON de pacientes: lo que muestran el resultado del alta y el listado del médico."""


def paciente_resumen_view(paciente) -> dict:
    return {
        "id": str(paciente.usuario_id),
        "nombre": paciente.usuario.nombre,
        "apellido": paciente.usuario.apellido,
        "dni": paciente.dni,
        "fecha_nacimiento": paciente.fecha_nacimiento.isoformat(),
        "tipo_sospecha": paciente.tipo_sospecha.value,
        "patologias": sorted(p.nombre for p in paciente.diagnostico_presuntivo),
        "tiene_familiograma": paciente.familiograma_url is not None,
        "fecha_alta": paciente.created_at.isoformat() if paciente.created_at else None,
    }


def pacientes_view(pacientes) -> dict:
    return {"pacientes": [paciente_resumen_view(p) for p in pacientes]}
