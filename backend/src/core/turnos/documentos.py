"""PDF de la orden de extracción y del consentimiento informado (escenario "Sacar el turno").

El cliente dijo que tiene plantillas propias para los dos documentos y que nos las va a pasar.
Mientras tanto, el texto es provisorio. El consentimiento se imprime, se firma y se entrega en el
centro de extracción: no vuelve al sistema. Si el paciente es menor de edad, firma el padre, la madre
o el tutor.
"""
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.core.turnos.calendario import ZONA_ARGENTINA

VIOLETA = colors.HexColor("#6D28D9")
TINTA = colors.HexColor("#160F2E")
GRIS = colors.HexColor("#5B5373")
LINEA = colors.HexColor("#E4DEF2")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]

_TITULO = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=TINTA)
_MARCA = ParagraphStyle("marca", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=VIOLETA)
_SECCION = ParagraphStyle("seccion", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=VIOLETA,
                          spaceBefore=10, spaceAfter=4)
_TEXTO = ParagraphStyle("texto", fontName="Helvetica", fontSize=10, leading=14, textColor=TINTA)
_CHICO = ParagraphStyle("chico", fontName="Helvetica", fontSize=8, leading=10, textColor=GRIS)


@dataclass
class DatosTurno:
    """Lo que necesitan los PDF, ya sacado de la base (así se pueden probar sin base de datos)."""
    paciente: str          # "Apellido, Nombre"
    dni: str
    fecha_nacimiento: date
    estudio_id: str
    fecha_hora: datetime   # con zona horaria
    centro: str
    direccion: str


def es_menor(fecha_nacimiento: date, al_dia: date) -> bool:
    cumplidos = al_dia.year - fecha_nacimiento.year - ((al_dia.month, al_dia.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    return cumplidos < 18


def _fecha_larga(momento: datetime) -> str:
    local = momento.astimezone(ZONA_ARGENTINA)
    return f"{DIAS[local.weekday()]} {local.day} de {MESES[local.month - 1]} de {local.year}, {local:%H:%M} hs"


def _codigo(estudio_id: str) -> str:
    return f"EST-{estudio_id[:8].upper()}"


def _tabla_datos(filas: list[tuple[str, str]]) -> Table:
    tabla = Table([[Paragraph(f"<b>{k}</b>", _TEXTO), Paragraph(v, _TEXTO)] for k, v in filas], colWidths=[45 * mm, None])
    tabla.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabla


def _documento(titulo: str, contenido: list) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm, title=titulo, author="Exoma Clínico")
    encabezado = [Paragraph("EXOMA CLÍNICO · Laboratorio de genética clínica", _MARCA), Spacer(1, 2 * mm),
                  Paragraph(titulo, _TITULO), Spacer(1, 6 * mm)]
    doc.build(encabezado + contenido)
    return buffer.getvalue()


def generar_orden(datos: DatosTurno) -> bytes:
    """Orden de extracción: con qué datos se presenta el paciente en el centro."""
    contenido = [
        Paragraph("Paciente", _SECCION),
        _tabla_datos([
            ("Nombre", datos.paciente),
            ("DNI", datos.dni),
            ("Fecha de nacimiento", datos.fecha_nacimiento.strftime("%d/%m/%Y")),
        ]),
        Paragraph("Turno de extracción", _SECCION),
        _tabla_datos([
            ("Día y hora", _fecha_larga(datos.fecha_hora)),
            ("Centro", datos.centro),
            ("Dirección", datos.direccion),
            ("Estudio", f"Exoma clínico · {_codigo(datos.estudio_id)}"),
        ]),
        Paragraph("Indicaciones", _SECCION),
        Paragraph("• <b>No necesita ninguna preparación especial</b> (no hace falta ayuno).", _TEXTO),
        Paragraph("• Presentarse con DNI, esta orden y el consentimiento informado firmado.", _TEXTO),
        Paragraph("• Se extrae una muestra de sangre. El turno dura 15 minutos.", _TEXTO),
        Paragraph("• Si no puede asistir, cancele el turno desde el sistema y saque otro. "
                  "Con 5 inasistencias se pierde el pago del estudio.", _TEXTO),
        Spacer(1, 10 * mm),
        Paragraph(f"Código del estudio: {_codigo(datos.estudio_id)} · Documento generado por el sistema.", _CHICO),
    ]
    return _documento("Orden de extracción", contenido)


def generar_consentimiento(datos: DatosTurno) -> bytes:
    """Consentimiento informado para imprimir y firmar. Si el paciente es menor, firma su responsable."""
    menor = es_menor(datos.fecha_nacimiento, datos.fecha_hora.astimezone(ZONA_ARGENTINA).date())
    firmante = "Firma del padre, madre o tutor" if menor else "Firma del paciente"
    contenido = [
        _tabla_datos([
            ("Paciente", datos.paciente),
            ("DNI", datos.dni),
            ("Estudio", f"Exoma clínico · {_codigo(datos.estudio_id)}"),
        ]),
        Spacer(1, 4 * mm),
        Paragraph(
            ("Quien firma, en su carácter de padre, madre o tutor del paciente, declara" if menor else "Declaro")
            + " haber sido informado/a sobre el estudio de exoma clínico: un análisis del ADN obtenido a partir "
            "de una muestra de sangre, para buscar variantes genéticas relacionadas con la sospecha diagnóstica "
            "indicada por el médico tratante.", _TEXTO),
        Spacer(1, 2 * mm),
        Paragraph("Entiendo que:", _TEXTO),
        Paragraph("• La muestra se envía al exterior para su lectura, con la autorización del Ministerio de Salud.", _TEXTO),
        Paragraph("• El resultado puede ser positivo, negativo o mostrar variantes de significado incierto.", _TEXTO),
        Paragraph("• Si la muestra no es suficiente, puede ser necesario repetir la extracción sin costo.", _TEXTO),
        Paragraph("• Mis datos genéticos son confidenciales y solo los ven el médico tratante y el laboratorio.", _TEXTO),
        Spacer(1, 2 * mm),
        Paragraph("Habiendo comprendido la información, presto mi consentimiento para la realización del estudio.", _TEXTO),
        Spacer(1, 22 * mm),
        _firmas(firmante),
        Spacer(1, 10 * mm),
        Paragraph("Texto provisorio: se reemplaza por la plantilla del laboratorio. "
                  "Este documento se entrega firmado en el centro de extracción.", _CHICO),
    ]
    return _documento("Consentimiento informado", contenido)


def _firmas(firmante: str) -> Table:
    """Tres líneas para firmar, con un espacio entre cada una (las columnas 1 y 3 quedan vacías)."""
    tabla = Table([["", "", "", "", ""], [firmante, "", "Aclaración y DNI", "", "Fecha"]],
                  colWidths=[58 * mm, 8 * mm, 58 * mm, 8 * mm, 38 * mm])
    tabla.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.8, TINTA),
        ("LINEABOVE", (2, 1), (2, 1), 0.8, TINTA),
        ("LINEABOVE", (4, 1), (4, 1), 0.8, TINTA),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("TEXTCOLOR", (0, 1), (-1, 1), GRIS),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tabla
