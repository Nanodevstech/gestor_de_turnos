# ==============================================================================
# 📄 MÓDULO DE REPORTES - GENERADOR DE PDFs (REPORTLAB) - MEDIDOC 2.0
# ==============================================================================

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from tkinter import messagebox 
import html
import os

# ==============================================================================
# 🖨️ FUNCIÓN: GENERAR HISTORIA CLÍNICA PDF
# ==============================================================================

def generar_pdf_historia(paciente, historial, ruta_guardado):
    """
    Crea un archivo PDF profesional con los datos del paciente y su historial.
    Retorna True si salió bien, False si hubo error.
    """
    try:
        doc = SimpleDocTemplate(ruta_guardado, pagesize=A4)
        elements = [] 
        styles = getSampleStyleSheet() 

        # 1. ENCABEZADO Y TÍTULOS
        titulo = Paragraph("<b>Historia Clínica Digital</b>", styles['Title'])
        elements.append(titulo)
        elements.append(Spacer(1, 12))
        
        fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
        info_pie = Paragraph(f"Reporte generado el: {fecha_hoy} | MEDIDOC 2.0 Soft", styles['Normal'])
        elements.append(info_pie)
        elements.append(Spacer(1, 20))

        # 2. DATOS DEL PACIENTE
        datos = [
            ["Paciente:", str(paciente.get('nombre', '')), "DNI:", str(paciente.get('dni', ''))],
            ["Fecha Nac:", str(paciente.get('fecha_nac', '')), "Teléfono:", str(paciente.get('telefono', ''))],
            ["Obra Social:", str(paciente.get('obra_social', '')), "Grupo Sanguíneo:", str(paciente.get('grupo_sanguineo', ''))]
        ]

        t_datos = Table(datos, colWidths=[85, 170, 100, 100])
        t_datos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.aliceblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.white)
        ]))
        
        elements.append(t_datos)
        elements.append(Spacer(1, 20))

        # 3. TABLA DE HISTORIAL MÉDICO
        elements.append(Paragraph("<b>Registro de Visitas y Observaciones</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))

        if not historial:
            elements.append(Paragraph("No hay registros médicos para este paciente.", styles['Normal']))
        else:
            data_historia = [["Fecha", "Hora", "Observación Médica"]]
            estilo_celda = ParagraphStyle('Celda', parent=styles['Normal'], fontSize=9, leading=11)

            for h in historial:
                raw_obs = str(h['observacion']) if h.get('observacion') else "-"
                texto_obs_escapado = html.escape(raw_obs)
                obs_parrafo = Paragraph(texto_obs_escapado, estilo_celda)
                data_historia.append([str(h.get('fecha', '')), str(h.get('hora', '')), obs_parrafo])

            t_historia = Table(data_historia, colWidths=[70, 50, 320])
            t_historia.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(t_historia)

        doc.build(elements)
        return True

    except Exception as e:
        messagebox.showerror("Error Interno PDF", f"Hubo un fallo creando el reporte:\n{e}")
        print(f"Error PDF detallado: {e}")
        return False

# ==============================================================================
# 💊 FUNCIÓN: GENERAR RECETA / ORDEN MÉDICA DIGITAL (MEDIDOC 2.0)
# ==============================================================================

def generar_pdf_receta(paciente, medico_dict, indicacion, diagnostico, ruta_guardado):
    """
    Crea una receta o solicitud de estudio profesional en PDF.
    """
    try:
        doc = SimpleDocTemplate(ruta_guardado, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # 1. CABECERA MÉDICA DE RECETA
        encabezado_texto = f"<b>RECETA Y ORDEN MÉDICA DIGITAL</b>"
        titulo = Paragraph(encabezado_texto, styles['Title'])
        elements.append(titulo)
        elements.append(Spacer(1, 10))

        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        medico_nombre = html.escape(str(medico_dict.get('nombre', 'Dr/a. Profesional')))
        medico_esp = html.escape(str(medico_dict.get('especialidad', 'Medicina General')))
        medico_mat = html.escape(str(medico_dict.get('matricula', 'N/A')))

        info_medico = Paragraph(f"<b>Profesional:</b> {medico_nombre} | <b>Esp:</b> {medico_esp} | <b>M.N./M.P.:</b> {medico_mat}", styles['Normal'])
        elements.append(info_medico)
        elements.append(Spacer(1, 15))

        # 2. DATOS DEL PACIENTE
        datos_pac = [
            ["Paciente:", html.escape(str(paciente.get('nombre', ''))), "DNI:", str(paciente.get('dni', ''))],
            ["Obra Social:", html.escape(str(paciente.get('obra_social', 'Particular'))), "Nº Afiliado:", html.escape(str(paciente.get('num_afiliado', '-')))],
            ["Fecha de Emisión:", fecha_hoy, "Diagnóstico / Motivo:", html.escape(str(diagnostico))]
        ]

        t_pac = Table(datos_pac, colWidths=[100, 180, 80, 120])
        t_pac.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightskyblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.darkblue),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.white)
        ]))
        elements.append(t_pac)
        elements.append(Spacer(1, 25))

        # 3. CUERPO DE PRESCRIPCIÓN / TRATAMIENTO
        elements.append(Paragraph("<b>Prescripción Médica / Tratamiento Indicado:</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))

        estilo_cuerpo = ParagraphStyle('RecetaCuerpo', parent=styles['Normal'], fontSize=11, leading=16)
        texto_indicaciones = html.escape(indicacion).replace('\n', '<br/>')
        elements.append(Paragraph(texto_indicaciones, estilo_cuerpo))
        elements.append(Spacer(1, 40))

        # 4. PIE Y FIRMA DIGITALIZADA
        datos_firma = [
            ["", "___________________________________"],
            ["", f"Firma y Sello: {medico_nombre}"],
            ["", f"Matrícula: {medico_mat}"]
        ]
        t_firma = Table(datos_firma, colWidths=[250, 230])
        t_firma.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, -1), 9),
        ]))
        elements.append(t_firma)

        doc.build(elements)
        return True
    except Exception as e:
        messagebox.showerror("Error Receta PDF", f"No se pudo generar la receta:\n{e}")
        print(f"Error Receta PDF: {e}")
        return False