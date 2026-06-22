# -*- coding: utf-8 -*-
"""
Generador de PDF para reportes de inspección
Contiene toda la lógica de generación de PDF usando reportlab
"""

import os
from datetime import datetime
from typing import Dict, Any
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, Flowable, HRFlowable, KeepInFrame, KeepTogether, CondPageBreak
)
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

SIGNATURE_BLOCK_MIN_SPACE = 52 * mm

class NumberedCanvas(canvas.Canvas):
    """Canvas personalizado para numeración de páginas"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        # Guardar el estado actual antes de avanzar a la siguiente página
        self._saved_page_states.append(dict(self.__dict__))
        # Usar _startPage() para iniciar una nueva página sin emitirla todavía
        # Esto evita la duplicación cuando se guarda el PDF
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        # Restaurar cada estado y dibujar el número de página
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(total)
            # Emitir la página usando el método del canvas base
            canvas.Canvas.showPage(self)
        # Guardar el PDF
        canvas.Canvas.save(self)

    def draw_page_number(self, total):
        self.setFont("Helvetica", 9)
        self.drawRightString(200*mm, 10*mm, f"Página {self._pageNumber} de {total}")

class Box(Flowable):
    """Caja placeholder para fotos"""
    
    def __init__(self, width, height, label=""):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.label = label

    def draw(self):
        c = self.canv
        c.saveState()
        c.rect(0, 0, self.width, self.height)
        if self.label:
            c.setFont("Helvetica", 8)
            c.drawCentredString(self.width/2, self.height/2 - 4, self.label)
        c.restoreState()

class EspacioFirma(Flowable):
    """Flowable que crea un espacio para firma sin bordes"""
    def __init__(self, width, height):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def draw(self):
        # No dibujar nada, solo ocupar espacio
        pass


class LegendWithNextPageNote(Flowable):
    """Muestra leyenda inmediatamente o inserta aviso si debe pasar a la pagina siguiente."""

    NOTE_TEXT = "Tabla de convenciones en la página siguiente."

    def __init__(self, legend, note_style, spacer_h=3 * mm):
        super().__init__()
        self.legend = legend
        self.note_style = note_style
        self.spacer_h = spacer_h
        self._legend_h = 0

    def wrap(self, availW, availH):
        _, self._legend_h = self.legend.wrap(availW, 10000 * mm)
        return availW, self._legend_h + self.spacer_h

    def draw(self):
        self.legend.wrapOn(self.canv, self.width, self._legend_h)
        self.legend.drawOn(self.canv, 0, 0)

    def split(self, availW, availH):
        note = Paragraph(self.NOTE_TEXT, self.note_style)
        return [note, PageBreak(), Spacer(0, self.spacer_h), self.legend]

class GeneradorPDF:
    """Clase principal para generar PDFs de reportes de inspección"""
    
    def __init__(self):
        self.data = {}
        self.output_path = ""

    def _resolver_ruta_salida(self, output_filename: str) -> str:
        from utils import get_report_output_path
        return get_report_output_path(output_filename)
    
    def generar_inspeccion_visual(self, datos_proyecto: Dict[str, Any], 
                                 datos_inspeccion: Dict[str, Any], 
                                 output_filename: str) -> str:
        """
        Genera un PDF de inspección visual
        
        Args:
            datos_proyecto: Datos del proyecto
            datos_inspeccion: Datos de la inspección filtrados por imagen
            output_filename: Nombre del archivo de salida
            
        Returns:
            str: Ruta del archivo PDF generado
        """
        # Formatear datos directamente desde los datos filtrados
        self.data = self._formatear_datos_inspeccion_visual(datos_proyecto, datos_inspeccion)
        
        # Generar PDF
        self.output_path = self._resolver_ruta_salida(output_filename)
        self._generar_pdf(self.output_path)
        
        return self.output_path
    
    def generar_liquidos_penetrantes(self, datos_proyecto: Dict[str, Any], 
                                    datos_inspeccion: Dict[str, Any], 
                                    output_filename: str) -> str:
        """Genera un PDF de inspección de líquidos penetrantes"""
        # Formatear datos específicos para líquidos penetrantes
        self.data = self._formatear_datos_liquidos_penetrantes(datos_proyecto, datos_inspeccion)
        
        # Generar PDF
        self.output_path = self._resolver_ruta_salida(output_filename)
        self._generar_pdf(self.output_path, "liquidos_penetrantes")
        
        return self.output_path
    
    def generar_particulas_magneticas(self, datos_proyecto: Dict[str, Any], 
                                     datos_inspeccion: Dict[str, Any], 
                                     output_filename: str) -> str:
        """Genera un PDF de inspección de partículas magnéticas"""
        self.data = self._formatear_datos_particulas_magneticas(datos_proyecto, datos_inspeccion)
        self.output_path = self._resolver_ruta_salida(output_filename)
        self._generar_pdf(self.output_path, report_type="particulas_magneticas")
        return self.output_path
    
    def generar_ultrasonido(self, datos_proyecto: Dict[str, Any], 
                           datos_inspeccion: Dict[str, Any], 
                           output_filename: str) -> str:
        """Genera un PDF de inspección de ultrasonido"""
        self.data = self._formatear_datos_ultrasonido(datos_proyecto, datos_inspeccion)
        self.output_path = self._resolver_ruta_salida(output_filename)
        self._generar_pdf(self.output_path, report_type="ultrasonido")
        return self.output_path
    
    def _generar_pdf(self, out_path: str, report_type: str = "visual"):
        """Genera el PDF usando reportlab"""
        enc = self.data["encabezado"]
        doc = BaseDocTemplate(
            out_path, pagesize=letter,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=35*mm, bottomMargin=45*mm
        )

        # Configurar frames
        header_bottom_y = 220*mm
        padding = 6*mm
        first_top_y = header_bottom_y - padding
        first_height = first_top_y - doc.bottomMargin

        frame_first = Frame(doc.leftMargin, doc.bottomMargin, doc.width, first_height, id="first")
        frame_rest = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="rest")

        # Configurar templates
        template_first = PageTemplate(
            id="tpl_first",
            frames=[frame_first],
            onPage=lambda c, d: self._draw_header(c, d, enc, report_type),
            onPageEnd=lambda c, d: self._draw_footer(c, d, enc),
        )

        template_rest = PageTemplate(
            id="tpl_rest",
            frames=[frame_rest],
            onPage=lambda c, d: self._draw_header(c, d, enc, report_type),
            onPageEnd=lambda c, d: self._draw_footer(c, d, enc),
        )

        doc.addPageTemplates([template_first, template_rest])

        # Construir contenido según el tipo de reporte
        if report_type == "liquidos_penetrantes":
            story = self._build_story_liquidos_penetrantes(doc.width)
        elif report_type == "particulas_magneticas":
            story = self._build_story_particulas_magneticas(doc.width)
        elif report_type == "ultrasonido":
            story = self._build_story_ultrasonido(doc.width)
        else:
            story = self._build_story(doc.width)

        title_by_type = {
            "visual": "INFORME_INSPECCION_VISUAL",
            "liquidos_penetrantes": "INFORME_INSPECCION_LIQUIDOS_PENETRANTES",
            "particulas_magneticas": "INFORME_INSPECCION_PARTICULAS_MAGNETICAS",
            "ultrasonido": "INFORME_INSPECCION_ULTRASONIDO",
        }
        pdf_title = title_by_type.get(report_type, "INFORME_INSPECCION")
        numero = enc.get("rep", "") or enc.get("numero_informe", "")
        if numero:
            pdf_title = f"{pdf_title}_{numero}"
        pdf_author = "Joint and Welding Ingenieros S.A.S."
        pdf_subject = f"Informe de inspeccion - {enc.get('cliente', 'Cliente')}"
        pdf_creator = "Joint and Welding Reporteador"
        doc.title = pdf_title
        doc.author = pdf_author
        doc.subject = pdf_subject
        doc.creator = pdf_creator

        doc.build(story, canvasmaker=NumberedCanvas)
    
    def _draw_header(self, canv, doc, enc, report_type="visual"):
        """Dibuja el encabezado de cada página"""
        canv.saveState()

        # Títulos centrados (todas las páginas)
        canv.setFont("Helvetica-Bold", 13)
        
        # Determinar el título según el tipo de reporte
        if report_type == "liquidos_penetrantes":
            title = "INFORME INSPECCIÓN LÍQUIDOS PENETRANTES"
        elif report_type == "particulas_magneticas":
            title = "INFORME INSPECCIÓN PARTÍCULAS MAGNÉTICAS"
        elif report_type == "ultrasonido":
            title = "INFORME INSPECCIÓN ULTRASONIDO"
        else:
            title = "INFORME INSPECCIÓN VISUAL"
            
        # Logo en la parte superior izquierda (alineado con el margen izquierdo del reporte)
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo.jpeg")
            if os.path.exists(logo_path):
                # Tamaño más pequeño para que no se corte
                logo_img = Image(logo_path, width=30*mm, height=15*mm)
                # Posicionar alineado con el margen izquierdo del reporte
                logo_x = doc.leftMargin
                logo_y = 260*mm
                logo_img.drawOn(canv, logo_x, logo_y)
        except Exception:
            pass

        canv.drawCentredString(105*mm, 267*mm, title)
        canv.setFont("Helvetica-Bold", 11)
        canv.drawCentredString(105*mm, 260*mm, enc.get("norma", "AWS D1.1 2020"))

        # Bloque de metadatos (todas las páginas)
        x0, y0, w, h = doc.leftMargin, 220*mm, doc.width, 38*mm
        canv.setLineWidth(1)
        canv.rect(x0, y0, w, h)

        # Preparar datos con Paragraph para permitir wrap de texto
        from reportlab.lib.styles import ParagraphStyle
        # Leading más compacto para que el texto esté más cerca de la línea
        styles_meta = ParagraphStyle(
            name="MetaValue",
            fontName="Helvetica",
            fontSize=9,
            leading=8,  # Leading más compacto
            leftIndent=0,
            rightIndent=0,
            spaceBefore=0,
            spaceAfter=0
        )
        
        # Crear tabla izquierda con Paragraph para valores largos
        left_data = [
            ["Cliente:", Paragraph(enc.get("cliente",""), styles_meta)],
            ["Proyecto:", Paragraph(enc.get("proyecto",""), styles_meta)],
            ["Subproyecto:", Paragraph(enc.get("subproyecto",""), styles_meta)],
            ["Contratista:", Paragraph(enc.get("contratista",""), styles_meta)],
            ["Elaboró:", Paragraph(enc.get("elaboro",""), styles_meta)],
        ]
        
        # Crear tabla derecha con Paragraph
        right_data = [
            ["Rep N°:", Paragraph(enc.get("rep",""), styles_meta)],
            ["Fecha:", Paragraph(enc.get("fecha",""), styles_meta)],
            ["Lugar:", Paragraph(enc.get("lugar",""), styles_meta)],
            ["Proceso de soldadura:", Paragraph(enc.get("proceso_soldadura",""), styles_meta)],
            ["Tipo:", Paragraph(enc.get("tipo_proceso",""), styles_meta)],
        ]

        def draw_meta_left(tbl, x, y):
            # Columna izquierda: etiquetas más estrechas, línea más larga (casi hasta la columna derecha)
            # Permitir altura variable para texto de dos líneas de forma compacta
            col_widths = [24*mm, 88*mm]
            cliente_text = str(enc.get("cliente",""))
            is_long = len(cliente_text) > 60
            
            # Alturas más compactas - asegurar que todo quepa en 38mm
            # 5 filas: si una tiene 2 líneas (10mm) + 4 filas normales (6mm cada una) = 10 + 24 = 34mm, con padding = ~36mm
            row_heights = [6*mm] * len(tbl)  # Reducido de 7mm a 6mm para que quepa todo
            if is_long:
                row_heights[0] = 9*mm  # Altura moderada para dos líneas sin romper estructura
            
            t = Table(tbl, colWidths=col_widths, rowHeights=row_heights)
            
            # Estilo con alineación MIDDLE para que etiquetas y valores queden a la misma altura
            style_list = [
                ("FONT", (0,0), (0,-1), "Helvetica", 9),  # Solo etiquetas
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),  # Alineación central para etiquetas
                ("VALIGN", (1,0), (1,-1), "MIDDLE"),  # Alineación central para valores (misma altura)
                ("LINEBELOW", (1,0), (1,-1), 0.6, colors.black),
                ("RIGHTPADDING", (0,0), (0,-1), 0),
                ("LEFTPADDING", (1,0), (1,-1), 0),
            ]
            
            # Padding para controlar distancia entre texto y línea
            # BOTTOMPADDING controla la distancia entre el texto y la línea debajo
            if is_long:
                style_list.extend([
                    ("TOPPADDING", (0,0), (-1,0), 0.5),  # Padding mínimo superior
                    ("BOTTOMPADDING", (0,0), (-1,0), 4.2),  # Espacio moderado cuando cliente es de 2 líneas (balanceado)
                    ("TOPPADDING", (0,1), (-1,-1), 1),  # Padding reducido para el resto
                    ("BOTTOMPADDING", (0,1), (-1,-1), 2.5),  # Ajustar aquí: distancia texto-línea (0.5-3mm)
                ])
            else:
                style_list.extend([
                    ("TOPPADDING", (0,0), (-1,-1), 1),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),  # Ajustar aquí: distancia texto-línea (0.5-3mm)
                ])
            
            t.setStyle(TableStyle(style_list))
            _, h_ = t.wrapOn(canv, 0, 0)
            t.drawOn(canv, x, y - h_)

        def draw_meta_right(tbl, x, y):
            # Columna derecha: etiquetas más anchas para "Proceso de soldadura", líneas más cortas
            # Verificar si el campo "Tipo" tiene texto largo que necesita más espacio
            tipo_text = str(enc.get("tipo_proceso", ""))
            is_tipo_long = len(tipo_text) > 30  # Si el texto es muy largo
            
            # Ajustar ancho de columnas si el tipo es largo
            if is_tipo_long:
                # Reducir un poco el ancho de etiquetas y aumentar el de valores para acomodar texto largo
                col_widths = [36*mm, 30*mm]  # Etiquetas ligeramente más estrechas, valores más anchos
            else:
                col_widths = [38*mm, 28*mm]  # Etiquetas más anchas, valores más estrechos pero suficientes
            
            # Ajustar altura de filas si el tipo es largo
            row_heights = [6*mm] * len(tbl)
            if is_tipo_long:
                # La última fila (Tipo) necesita más altura para dos líneas
                row_heights[-1] = 9*mm
            
            t = Table(tbl, colWidths=col_widths, rowHeights=row_heights)
            
            style_list = [
                ("FONT", (0,0), (0,-1), "Helvetica", 9),  # Solo etiquetas
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),  # Alineación central para etiquetas
                ("VALIGN", (1,0), (1,-1), "MIDDLE"),  # Alineación central para valores (misma altura)
                ("LINEBELOW", (1,0), (1,-1), 0.6, colors.black),
                ("RIGHTPADDING", (0,0), (0,-1), 0),
                ("LEFTPADDING", (1,0), (1,-1), 0),
            ]
            
            # Ajustar padding según si el tipo es largo
            if is_tipo_long:
                style_list.extend([
                    ("TOPPADDING", (0,0), (-1,-2), 1),  # Padding normal para las primeras filas
                    ("BOTTOMPADDING", (0,0), (-1,-2), 2.5),
                    ("TOPPADDING", (0,-1), (-1,-1), 0.5),  # Padding mínimo superior para la última fila
                    ("BOTTOMPADDING", (0,-1), (-1,-1), 4.2),  # Más espacio debajo para que el texto no toque la línea
                ])
            else:
                style_list.extend([
                    ("TOPPADDING", (0,0), (-1,-1), 1),  # Padding reducido
                    ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),  # Ajustar aquí: distancia texto-línea (0.5-3mm)
                ])
            
            t.setStyle(TableStyle(style_list))
            _, h_ = t.wrapOn(canv, 0, 0)
            t.drawOn(canv, x, y - h_)

        inner = 0.5*mm
        inner_right = 2*mm  # Margen interno derecho para que las líneas no toquen el borde
        left_tbl_w = (24+88)*mm
        
        # Calcular ancho de tabla derecha dinámicamente según si el tipo es largo
        tipo_text = str(enc.get("tipo_proceso", ""))
        is_tipo_long = len(tipo_text) > 30
        if is_tipo_long:
            right_tbl_w = (36+30)*mm  # Ancho ajustado para texto largo
        else:
            right_tbl_w = (38+28)*mm  # Ancho normal
        
        left_x  = x0 + inner
        # Columna derecha separada del margen derecho
        right_x = x0 + w - inner_right - right_tbl_w
        top_y = y0 + h - 3*mm

        draw_meta_left(left_data,  left_x,  top_y)
        draw_meta_right(right_data, right_x, top_y)

        # Texto vertical margen izquierdo
        canv.setFont("Helvetica", 7)
        canv.saveState()
        canv.translate(10*mm, 140*mm)
        canv.rotate(90)
        canv.drawString(0, 0, "© Joint and Welding Ingenieros S.A.S. 2024 - Versión 7.0")
        canv.restoreState()

        canv.restoreState()

    def _draw_footer(self, canv, doc, enc):
        """Dibuja el pie de página"""
        from reportlab.platypus import Paragraph, Table, TableStyle
        from reportlab.lib.styles import ParagraphStyle

        x0, w = doc.leftMargin, doc.width

        st_small   = ParagraphStyle("small",   fontName="Helvetica",       fontSize=7, leading=8)
        st_small_b = ParagraphStyle("small_b", parent=st_small,            fontName="Helvetica-Bold", alignment=1)
        st_small_r = ParagraphStyle("small_r", parent=st_small,            alignment=2)

        abrev_txt = ("Abreviaciones:  A: Aplica   N.A: No aplica   S: Satisfactorio   "
                     "N.S: No Satisfactorio   F.A: Fuera de Alcance")

        data = [[
            Paragraph(abrev_txt, st_small),
            Paragraph("Joint and Welding Ingenieros S.A.S.", st_small_b),
            Paragraph("Cliente", st_small_r),
        ]]

        col_left  = w - (55*mm + 25*mm)
        col_mid   = 55*mm
        col_right = 25*mm
        col_widths = [col_left, col_mid, col_right]

        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.8, colors.black),
            ("INNERGRID", (0,0), (-1,-1), 0.8, colors.black),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("ALIGN", (1,0), (1,0), "CENTER"),
            ("ALIGN", (2,0), (2,0), "LEFT"),
        ]))

        tw, th = t.wrapOn(canv, w, 0)
        by = 15*mm
        t.drawOn(canv, x0, by)

    def _section_box(self, title, rows, with_obs, total_w):
        """Crea una tabla de sección"""
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="SectionTitle",
            parent=styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            leading=12
        )
        
        # Convert title to Paragraph if it's a string
        if isinstance(title, str):
            title_para = Paragraph(title, title_style)
        else:
            title_para = title
            
        cols = [total_w*0.7, total_w*0.3] if with_obs else [total_w]
        data = [[title_para, "OBSERVACIONES"]] if with_obs else [[title_para]]
        for r in rows:
            data.append([r, ""] if with_obs else [r])

        allow_split = len(data) > 2
        row_split_range = (2, len(data) - 1) if allow_split else None
        t = Table(
            data,
            colWidths=cols,
            repeatRows=1 if allow_split else 0,
            splitByRow=1 if allow_split else 0,
            rowSplitRange=row_split_range
        )
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.6, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        return t

    def _section_text_box(self, title, text, total_w):
        """Crea una caja de texto para sección"""
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            name="BodyText",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            leftIndent=0,
            rightIndent=0
        )
        
        if isinstance(text, str):
            # Convert text to Paragraph for proper text wrapping and line breaks
            text_html = text.replace('\r\n', '<br/>').replace('\n', '<br/>').replace('\r', '<br/>')
            rows = [Paragraph(text_html, body_style)]
        else:
            # Handle list of strings
            rows = [Paragraph(str(item), body_style) for item in text]
        
        return self._section_box(title, rows, False, total_w)
    
    def _esquema_cell_liquidos(self, esquema_item: Dict[str, Any], idx: int, col_w: float, styles) -> Table:
        """Crea una celda para mostrar una imagen del esquema en el informe de líquidos penetrantes"""
        inner_w = col_w - 8*mm
        max_img_h = 45*mm
        try:
            archivo = esquema_item.get("archivo")
            # Si es un objeto UploadedFile de Streamlit, convertir a BytesIO
            if hasattr(archivo, 'read'):
                # Es un objeto de archivo de Streamlit
                archivo.seek(0)  # Asegurar que estamos al inicio del archivo
                img_bytes = archivo.read()
                img = Image(BytesIO(img_bytes))
            elif isinstance(archivo, (str, bytes)):
                # Es una ruta de archivo o bytes
                img = Image(archivo)
            else:
                # Intentar usar directamente
                img = Image(archivo)
            img.hAlign = "CENTER"
            img._restrictSize(inner_w, max_img_h)
        except Exception as e:
            img = Box(inner_w, max_img_h, f"ESQUEMA {idx}")
        titulo = Paragraph(f"<b>Esquema {idx}</b>", styles["Body"])
        comentario = Paragraph(esquema_item.get("comentario", ""), styles["Body"])
        col = KeepInFrame(maxWidth=inner_w, maxHeight=70*mm,
                          content=[img, Spacer(0,2*mm), titulo, comentario],
                          mode="shrink")
        cell = Table([[col]], colWidths=[col_w])
        cell.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING",(0,0), (-1,-1), 4),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]))
        cell.splitByRow = 0
        cell.splitInRow = 0
        return cell
    
    def _foto_cell_liquidos(self, registro: Dict[str, Any], idx: int, col_w: float, styles) -> Table:
        """Crea una celda para mostrar una foto en el informe de líquidos penetrantes"""
        inner_w = col_w - 8*mm
        max_img_h = 45*mm
        try:
            archivo = registro.get("archivo")
            # Si es un objeto UploadedFile de Streamlit, convertir a BytesIO
            if hasattr(archivo, 'read'):
                # Es un objeto de archivo de Streamlit
                archivo.seek(0)  # Asegurar que estamos al inicio del archivo
                img_bytes = archivo.read()
                img = Image(BytesIO(img_bytes))
            elif isinstance(archivo, (str, bytes)):
                # Es una ruta de archivo o bytes
                img = Image(archivo)
            else:
                # Intentar usar directamente
                img = Image(archivo)
            img.hAlign = "CENTER"
            img._restrictSize(inner_w, max_img_h)
        except Exception as e:
            img = Box(inner_w, max_img_h, f"FOTO {idx}")
        titulo = Paragraph(f"<b>Registro Fotográfico N° {idx}</b>", styles["Body"])
        comentario = Paragraph(registro.get("comentario", ""), styles["Body"])
        col = KeepInFrame(maxWidth=inner_w, maxHeight=70*mm,
                          content=[img, Spacer(0,2*mm), titulo, comentario],
                          mode="shrink")
        cell = Table([[col]], colWidths=[col_w])
        cell.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING",(0,0), (-1,-1), 4),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]))
        return cell
    
    def _abreviar_calificacion(self, calificacion: str) -> str:
        """
        Abrevia la calificación a solo las siglas (C, C(xR), NC, RI).
        """
        import re
        cal_upper = str(calificacion).upper().strip()
        
        # Detectar el tipo de calificación y retornar solo las siglas
        # Orden importante: primero las más específicas
        if ('C(' in cal_upper and 'R)' in cal_upper) or 'CX' in cal_upper or 'CONFORME LUEGO' in cal_upper or 'CONFORME DESPUES' in cal_upper:
            # Extraer el número si existe (ej: C(2R) -> C(2R), C(1R) -> C(1R))
            match = re.search(r'C\((\d+)R\)', cal_upper)
            if match:
                return f"C({match.group(1)}R)"
            else:
                return "C(xR)"
        elif cal_upper.startswith('NC') or 'NO CONFORME' in cal_upper or 'NO SATISFACTORIO' in cal_upper:
            return 'NC'
        elif cal_upper.startswith('RI') or 'RE INSPECCIONAR' in cal_upper or 'REINSPECCIONAR' in cal_upper:
            return 'RI'
        elif cal_upper.startswith('C') or 'CONFORME' in cal_upper or 'SATISFACTORIO' in cal_upper:
            return 'C'
        else:
            # Por defecto, si no coincide, usar C
            return 'C'
    
    def _obtener_color_calificacion(self, calificacion: str):
        """
        Retorna el color de fondo correspondiente a la calificación.
        """
        cal_upper = str(calificacion).upper().strip()
        
        # Colores para calificaciones (mismos que en la leyenda)
        color_conforme = colors.HexColor('#4CAF50')  # Verde más oscuro
        color_conforme_reparacion = colors.HexColor('#98FB98')  # Verde más claro
        color_no_conforme = colors.HexColor('#FF6B6B')  # Rojo
        color_re_inspeccionar = colors.HexColor('#FFD700')  # Amarillo
        
        # Detectar el tipo de calificación
        # Orden importante: primero las más específicas
        if ('C(' in cal_upper and 'R)' in cal_upper) or 'CX' in cal_upper or 'CONFORME LUEGO' in cal_upper or 'CONFORME DESPUES' in cal_upper:
            return color_conforme_reparacion
        elif cal_upper.startswith('NC') or 'NO CONFORME' in cal_upper or 'NO SATISFACTORIO' in cal_upper:
            return color_no_conforme
        elif cal_upper.startswith('RI') or 'RE INSPECCIONAR' in cal_upper or 'REINSPECCIONAR' in cal_upper:
            return color_re_inspeccionar
        elif cal_upper.startswith('C') or 'CONFORME' in cal_upper or 'SATISFACTORIO' in cal_upper:
            return color_conforme
        else:
            # Por defecto, si no coincide, usar color conforme
            return color_conforme
    
    def _crear_leyenda_disconformidades(self, total_w):
        """
        Crea la leyenda de disconformidades y calificaciones según la imagen proporcionada.
        Retorna una tabla con dos secciones: Convención de DISCONTINUIDAD y Calificación (CAL).
        """
        # Primera sección: Convención de DISCONTINUIDAD
        # Organizada en 3 columnas
        disconformidades = [
            ["Cir:", "Cordón Irregular"],
            ["EC:", "Exceso de Concavidad"],
            ["ER:", "Exceso de Refuerzo"],
            ["EP:", "Exceso de Penetración"],
            ["FF:", "Falta de Fusión"],
            ["FP:", "Falta de Penetración"],
            ["G:", "Grieta"],
            ["FMA:", "Falta de Material de aporte"],
            ["P:", "Porosidad"],
            ["SE:", "Socavado Externo"],
            ["SI:", "Socavado Interno"],
            ["DMB:", "Daño Material Base"],
        ]
        
        # Dividir en 3 columnas (4 elementos por columna)
        col1 = disconformidades[:4]
        col2 = disconformidades[4:8]
        col3 = disconformidades[8:]
        
        # Asegurar que todas las columnas tengan el mismo número de filas
        max_rows = max(len(col1), len(col2), len(col3))
        while len(col1) < max_rows:
            col1.append(["", ""])
        while len(col2) < max_rows:
            col2.append(["", ""])
        while len(col3) < max_rows:
            col3.append(["", ""])
        
        # Crear filas combinando las 3 columnas
        disconformidades_data = []
        for i in range(max_rows):
            row = [col1[i][0] + " " + col1[i][1], 
                   col2[i][0] + " " + col2[i][1], 
                   col3[i][0] + " " + col3[i][1]]
            disconformidades_data.append(row)
        
        # Segunda sección: Calificación (CAL)
        calificaciones_data = [
            ["C:", "Conforme"],
            ["C(xR):", "Conforme luego x Reparación"],
            ["NC:", "No Conforme"],
            ["RI:", "Re Inspeccionar"],
        ]
        
        # Colores para calificaciones
        color_conforme = colors.HexColor('#4CAF50')  # Verde más oscuro
        color_conforme_reparacion = colors.HexColor('#98FB98')  # Verde más claro
        color_no_conforme = colors.HexColor('#FF6B6B')  # Rojo
        color_re_inspeccionar = colors.HexColor('#FFD700')  # Amarillo
        
        # Calcular número máximo de filas para alinear ambas secciones
        max_filas = max(len(disconformidades_data) + 1, len(calificaciones_data) + 1)  # +1 por encabezado
        
        # Crear tabla con 4 columnas: CAL (izquierda) + 3 columnas de DISCONTINUIDAD
        # Anchos: CAL ocupa ~30%, las otras 3 columnas se dividen el resto
        cal_width = total_w * 0.3
        discon_width = (total_w - cal_width) / 3.0
        col_widths = [cal_width, discon_width, discon_width, discon_width]
        
        # Construir datos de la tabla
        leyenda_data = []
        
        # Primera fila: encabezados
        # "Convención de DISCONTINUIDAD:" ocupará las columnas 1, 2, 3 (SPAN)
        leyenda_data.append(["Calificación (CAL)", "Convención de DISCONTINUIDAD:", "", ""])
        
        # Llenar filas combinando ambas secciones
        for i in range(max_filas - 1):  # -1 porque ya tenemos el encabezado
            cal_row = ""
            if i < len(calificaciones_data):
                cal_row = calificaciones_data[i][0] + " " + calificaciones_data[i][1]
            
            discon_row1 = ""
            discon_row2 = ""
            discon_row3 = ""
            if i < len(disconformidades_data):
                discon_row1 = disconformidades_data[i][0]
                discon_row2 = disconformidades_data[i][1]
                discon_row3 = disconformidades_data[i][2]
            
            leyenda_data.append([cal_row, discon_row1, discon_row2, discon_row3])
        
        # Crear tabla
        t = Table(leyenda_data, colWidths=col_widths)
        
        # Estilos
        style_list = [
            ("GRID", (0,0), (-1,-1), 0.6, colors.black),
            ("FONT", (0,0), (-1,-1), "Helvetica", 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 7),
            # SPAN para "Convención de DISCONTINUIDAD:" en la primera fila
            ("SPAN", (1,0), (3,0)),
        ]
        
        # Aplicar colores a la columna de calificación (columna 0)
        for i, cal in enumerate(calificaciones_data, start=1):
            cal_text = cal[0].upper()
            if 'C(' in cal_text or 'CX' in cal_text:
                color = color_conforme_reparacion
            elif cal_text.startswith('NC'):
                color = color_no_conforme
            elif cal_text.startswith('RI'):
                color = color_re_inspeccionar
            else:
                color = color_conforme
            style_list.append(("BACKGROUND", (0, i), (0, i), color))
        
        t.setStyle(TableStyle(style_list))
        return t
    
    def _crear_seccion_firmas(self, total_w, encabezado):
        """
        Crea la sección de firmas y sello al final del informe.
        Basado en el diseño del informe de inspección visual.
        Incluye espacios para Elaboró, Revisó, sello/logo, nombre de empresa y cliente.
        """
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        
        # Estilos compactos (iguales al informe de inspección visual)
        style_label = ParagraphStyle(
            name="FirmaLabel",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10
        )
        style_name = ParagraphStyle(
            name="FirmaName",
            fontName="Helvetica",
            fontSize=8,
            leading=9
        )
        style_name_center = ParagraphStyle(
            name="FirmaNameCenter",
            parent=style_name,
            alignment=1
        )
        style_company = ParagraphStyle(
            name="CompanyName",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=1  # CENTER
        )
        style_client = ParagraphStyle(
            name="ClientName",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,
            alignment=1  # CENTER
        )
        
        # Obtener datos del encabezado
        elaboro_nombre = encabezado.get("elaboro", "")
        reviso_nombre = encabezado.get("reviso", "")
        firma_elaboro_path = encabezado.get("firma_elaboro_path", "")
        firma_reviso_path = encabezado.get("firma_reviso_path", "")
        cliente_nombre = encabezado.get("cliente", "Concreacero")
        
        # Altura reducida para las secciones de firma
        altura_firma = 12*mm
        
        # Anchos de columnas
        col_elaboro = total_w * 0.35
        col_reviso = total_w * 0.35
        col_cliente = total_w * 0.30
        
        # Fila 1: Etiquetas
        fila1 = [
            Paragraph("Elaboró:", style_label),
            Paragraph("Revisó:", style_label),
            Paragraph(cliente_nombre, style_client)
        ]
        
        # Fila 2: Contenido de las secciones
        # Columna Elaboró: solo espacio para firma (sin nombre, sin bordes)
        espacio_firma_elaboro = self._firma_flowable(firma_elaboro_path, 45.5*mm, 13*mm)
        celda_elaboro = Table([
            [espacio_firma_elaboro],
        ], colWidths=[col_elaboro - 8*mm], splitByRow=0, splitInRow=0)
        celda_elaboro.setStyle(TableStyle([
            ("LEFTPADDING", (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ("ALIGN", (0,0), (0,0), "CENTER"),  # Centrar la firma
        ]))
        
        # Columna Revisó: espacio para sello a la izquierda, espacio para firma a la derecha
        # Espacio para sello (sin cuadro)
        espacio_sello = EspacioFirma(22*mm, 12*mm)
        # Espacio para firma sin caja
        espacio_firma_reviso = self._firma_flowable(firma_reviso_path, 45.5*mm, 13*mm)
        # Espacio para NIT (sin texto)
        espacio_nit = EspacioFirma(22*mm, 4*mm)
        
        # Tabla interna para Revisó: espacio para sello a la izquierda, espacio para firma a la derecha
        # Agregar padding izquierdo para mover todo el contenido más a la derecha
        celda_reviso_superior = Table([
            [espacio_sello, espacio_firma_reviso],  # Espacio para sello y espacio para firma (sin cajas)
            [espacio_nit, Paragraph("", style_name)],  # Espacio para NIT (sin texto)
        ], colWidths=[22*mm, col_reviso - 22*mm], splitByRow=0, splitInRow=0)
        celda_reviso_superior.setStyle(TableStyle([
            ("LEFTPADDING", (0,0), (-1,-1), 5),  # Padding izquierdo para mover contenido a la derecha
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        
        # Nombre del revisor (vacío)
        nombre_revisor = Paragraph("", style_name)
        
        # Contenedor completo de Revisó
        celda_reviso_completa = Table([
            [celda_reviso_superior],
            [Spacer(0, 0.5*mm)],
            [nombre_revisor],  # Nombre del revisor (vacío)
        ], colWidths=[col_reviso - 4*mm], splitByRow=0, splitInRow=0)
        celda_reviso_completa.setStyle(TableStyle([
            ("LEFTPADDING", (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ]))
        
        fila2 = [celda_elaboro, celda_reviso_completa, Paragraph("", style_name)]

        # Fila 3: Nombres centrados
        fila3 = [
            Paragraph(elaboro_nombre, style_name_center),
            Paragraph(reviso_nombre, style_name_center),
            Paragraph("", style_name),
        ]

        # Fila 4: Nombre empresa (spanning columnas Elaboró y Revisó)
        empresa_text = Paragraph("Joint and Welding Ingenieros S.A.S.", style_company)
        fila4 = [empresa_text, Paragraph("", style_name), Paragraph("", style_name)]

        # Crear tabla principal
        data = [fila1, fila2, fila3, fila4]
        row_heights = [6*mm, altura_firma + 5*mm, 6*mm, 5*mm]
        t = Table(
            data,
            colWidths=[col_elaboro, col_reviso, col_cliente],
            rowHeights=row_heights,
            splitByRow=0,
            splitInRow=0,
        )
        
        # Estilos de la tabla (iguales al informe de inspección visual)
        t.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 1.0, colors.black),
            ("LINEAFTER", (1,0), (1,-1), 1.0, colors.black),
            ("LINEABOVE", (0,3), (1,3), 1.0, colors.black),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("SPAN", (2,0), (2,2)),
            ("ALIGN", (2,0), (2,2), "CENTER"),
            ("VALIGN", (2,0), (2,2), "MIDDLE"),
            ("SPAN", (0,3), (1,3)),
            ("ALIGN", (0,3), (1,3), "CENTER"),
            ("ALIGN", (0,2), (1,2), "CENTER"),
        ]))
        
        return t

    def _resolver_reviso(self, datos_proyecto: Dict[str, Any]) -> str:
        firmas = datos_proyecto.get("firmas", {})
        if isinstance(firmas, dict):
            reviso = firmas.get("firma_2", "")
            if reviso:
                return reviso
        reviso = datos_proyecto.get("reviso", "")
        if reviso:
            return reviso
        return datos_proyecto.get("inspector", "Inspector")

    def _resolver_firma_path(self, datos_proyecto: Dict[str, Any], person_name: str, firma_key: str) -> str:
        firmas = datos_proyecto.get("firmas", {})
        if isinstance(firmas, dict):
            saved = firmas.get(firma_key, "")
            if saved and os.path.exists(saved):
                return saved
        try:
            from signature_registry import get_signature_for_person
            return get_signature_for_person(person_name) or ""
        except Exception:
            return ""

    def _firma_flowable(self, firma_path, width, height):
        if firma_path and isinstance(firma_path, str) and os.path.exists(firma_path):
            try:
                img = Image(firma_path)
                img.hAlign = "CENTER"
                img._restrictSize(width, height)
                return img
            except Exception:
                pass
        return EspacioFirma(width, height)

    def _formatear_datos_particulas_magneticas(self, datos_proyecto: Dict[str, Any],
                                              datos_inspeccion: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea los datos de inspección de partículas magnéticas para el PDF"""
        
        data = {
            "encabezado": {
                "cliente": datos_proyecto.get('cliente', 'Cliente'),
                "proyecto": datos_proyecto.get('proyecto', 'Proyecto'),
                "subproyecto": datos_proyecto.get('subproyecto', 'Subproyecto'),
                "contratista": datos_proyecto.get('contratista', 'Contratista'),
                "elaboro": datos_proyecto.get('inspector', 'Inspector'),
                "reviso": self._resolver_reviso(datos_proyecto),
                "firma_elaboro_path": self._resolver_firma_path(datos_proyecto, datos_proyecto.get('inspector', 'Inspector'), "firma_1_path"),
                "firma_reviso_path": self._resolver_firma_path(datos_proyecto, self._resolver_reviso(datos_proyecto), "firma_2_path"),
                "rep": datos_proyecto.get('numero_informe', 'T1234I1025'),
                "fecha": datos_proyecto.get('fecha', 'DD/MMM/YYYY'),
                "lugar": datos_proyecto.get('ubicacion', 'Ubicación'),
                "proceso_soldadura": ', '.join(datos_inspeccion.get('proceso_soldadura', ['SMAW'])) if isinstance(datos_inspeccion.get('proceso_soldadura'), list) else datos_inspeccion.get('proceso_soldadura', 'SMAW'),
                "tipo_proceso": "III - Partículas Magnéticas",
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020'),
                "procedimiento": datos_inspeccion.get('procedimiento', 'TLPR0027 - Inspección de Partículas Magnéticas - Rev. 1')
            },
            "seccion_1_procedimiento": {
                "procedimiento": datos_inspeccion.get('procedimiento', 'TLPR0027 - Inspección de Partículas Magnéticas - Rev. 1')
            },
            "seccion_2_normas": {
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020')
            },
            "seccion_3_equipos": {
                "equipos": datos_inspeccion.get('equipos', 'Kit de Partículas Magnéticas')
            },
            "seccion_4_material_base": {
                "material_base": ', '.join(datos_inspeccion.get('material_base', ['No especificado'])) if isinstance(datos_inspeccion.get('material_base'), list) else datos_inspeccion.get('material_base', 'No especificado')
            },
            "seccion_5_materiales": {
                "materiales": datos_inspeccion.get('materiales_utilizados', [])
            },
            "seccion_6_tipo_metodo": {
                "tipo_metodo": datos_inspeccion.get('tipo_y_metodo', [])
            },
            "seccion_7_parametros": {
                "parametros": datos_inspeccion.get('parametros_operacion', [])
            },
            "seccion_8_proceso_corriente": {
                "proceso_corriente": datos_inspeccion.get('proceso_y_corriente', [])
            },
            "seccion_9_elementos": {
                "elementos": datos_inspeccion.get('elementos', [])
            },
            "seccion_10_detalle": {
                "detalle_resultados": datos_inspeccion.get('detalle_resultados', ''),
                "observaciones_generales": datos_inspeccion.get('observaciones_generales', '')
            },
            "registros_fotograficos": datos_inspeccion.get('registros_fotograficos', [])
        }
        return data

    def _formatear_datos_ultrasonido(self, datos_proyecto: Dict[str, Any],
                                    datos_inspeccion: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea los datos de inspección de ultrasonido para el PDF"""
        
        data = {
            "encabezado": {
                "cliente": datos_proyecto.get('cliente', 'Cliente'),
                "proyecto": datos_proyecto.get('proyecto', 'Proyecto'),
                "subproyecto": datos_proyecto.get('subproyecto', 'Subproyecto'),
                "contratista": datos_proyecto.get('contratista', 'Contratista'),
                "elaboro": datos_proyecto.get('inspector', 'Inspector'),
                "reviso": self._resolver_reviso(datos_proyecto),
                "firma_elaboro_path": self._resolver_firma_path(datos_proyecto, datos_proyecto.get('inspector', 'Inspector'), "firma_1_path"),
                "firma_reviso_path": self._resolver_firma_path(datos_proyecto, self._resolver_reviso(datos_proyecto), "firma_2_path"),
                "rep": datos_proyecto.get('numero_informe', 'T1234I1035'),
                "fecha": datos_proyecto.get('fecha', 'DD/MMM/YYYY'),
                "lugar": datos_proyecto.get('ubicacion', 'Ubicación'),
                "proceso_soldadura": ', '.join(datos_inspeccion.get('soldadura', ['SMAW'])) if isinstance(datos_inspeccion.get('soldadura'), list) else datos_inspeccion.get('soldadura', 'SMAW'),
                "tipo_proceso": "IV - Ultrasonido",
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020'),
                "procedimiento": datos_inspeccion.get('procedimiento', 'TLPR0028 - Inspección de Ultrasonido - Rev. 1')
            },
            "seccion_1_procedimiento": {
                "procedimiento": datos_inspeccion.get('procedimiento', 'TLPR0028 - Inspección de Ultrasonido - Rev. 1')
            },
            "seccion_2_normas": {
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020')
            },
            "seccion_3_equipos": {
                "equipos": datos_inspeccion.get('equipo', 'Equipo de Ultrasonido'),
                "palpador": datos_inspeccion.get('palpador', 'Palpador')
            },
            "seccion_4_material_base": {
                "material_base": ', '.join(datos_inspeccion.get('material_base', ['No especificado'])) if isinstance(datos_inspeccion.get('material_base'), list) else datos_inspeccion.get('material_base', 'No especificado')
            },
            "seccion_5_juntas": {
                "juntas": datos_inspeccion.get('juntas', [])
            },
            "seccion_6_elementos": {
                "elementos": datos_inspeccion.get('elementos_inspeccionados', [])
            },
            "seccion_7_detalle": {
                "detalle_resultados": datos_inspeccion.get('detalle_resultados', ''),
                "observaciones_generales": datos_inspeccion.get('observaciones_generales', '')
            },
            "registros_fotograficos": datos_inspeccion.get('registros_fotograficos', [])
        }
        return data

    def _build_story(self, total_w):
        """Construye el contenido del PDF"""
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="HSection", fontName="Helvetica-Bold", fontSize=10, spaceBefore=6, spaceAfter=4))
        styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=9, leading=12))
        styles.add(ParagraphStyle(name="Legend", fontName="Helvetica", fontSize=8))
        styles.add(ParagraphStyle(name="LegendNextPageNote", fontName="Helvetica-Bold", fontSize=9, alignment=1, spaceAfter=2))

        story = []

        # CONTENIDO ESTÁTICO COMENTADO PARA EVITAR DUPLICACIÓN
        # Este método se usa solo para otros tipos de inspección, no para inspección visual
        # La inspección visual usa ReporteInspeccionVisual que tiene su propio _build_story dinámico
        
        # story.append(self._section_text_box("1. NORMAS PARA EL CRITERIO DE EVALUACIÓN:", self.data["seccion_1_normas"]["norma"], total_w))
        # story.append(Spacer(0, 3*mm))
        # story.append(self._section_text_box("2. EQUIPOS UTILIZADOS", self.data["seccion_2_equipos"]["equipos"], total_w))
        # story.append(Spacer(0, 3*mm))
        # story.append(self._section_text_box("3. MATERIAL BASE:", self.data["seccion_3_material_base"]["material_base"], total_w))
        # story.append(Spacer(0, 3*mm))
        # story.append(self._section_box("4. ANTES DE INICIAR EL PROCESO DE SOLDADURA", self.data["seccion_4_antes_soldadura"]["items"], True, total_w))
        # story.append(Spacer(0, 3*mm))
        # story.append(self._section_box("5. INICIO DE LA JUNTA", self.data["seccion_5_inicio_junta"]["items"], True, total_w))
        # story.append(Spacer(0, 3*mm))
        # story.append(self._section_box("6. DESPUÉS DE LA SOLDADURA", self.data["seccion_6_despues_soldadura"]["items"], True, total_w))

        # Página 2
        story.append(PageBreak())
        story.append(Spacer(0, 70*mm))
        story.append(Paragraph("ESQUEMA DE ELEMENTOS INSPECCIONADOS", styles["HSection"]))

        legend_rows = [[k, v] for k, v in self.data["seccion_7_elementos_inspeccionados"]["leyenda"].items()]
        legend_tbl = Table(legend_rows, colWidths=[20*mm, 60*mm])
        legend_tbl.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.25, colors.black),
                                        ('FONT', (0,0), (-1,-1), 'Helvetica', 8),
                                        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke)]))
        conv_txt = ", ".join(self.data["seccion_7_elementos_inspeccionados"]["convencion_discontinuidades"])
        story.append(legend_tbl)
        story.append(Spacer(0, 3*mm))
        story.append(Paragraph(f"Convención de DISCONTINUIDAD: {conv_txt}", styles["Legend"]))

        ids = self.data["seccion_7_elementos_inspeccionados"]["items_esquema"]
        if ids:
            grid_data = [["ID", "Cal."]] + [[str(x["id"]), x["estado"]] for x in ids]
            grid = Table(grid_data, colWidths=[25*mm, 25*mm])
            grid.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.25, colors.black),
                                      ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
                                      ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke)]))
            story.append(Spacer(0, 3*mm))
            story.append(grid)

        # Página 3
        story.append(PageBreak())
        story.append(Spacer(0, 60*mm))
        story.append(Paragraph("8. DETALLE ELEMENTOS INSPECCIONADOS", styles["HSection"]))

        detalle_data = [["ITEM", "ELEMENTO", "INDICACIÓN", "CAL"]]
        for r in self.data["seccion_8_detalle_elementos"]:
            detalle_data.append([r["item"], r["elemento"], r["indicacion"], r["cal"]])
        
        if len(detalle_data) > 1:
            detalle = Table(detalle_data, colWidths=[15*mm, 75*mm, 65*mm, 15*mm])
            detalle.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.25, colors.black),
                                         ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
                                         ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                                         ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(detalle)
        else:
            story.append(Paragraph("No hay elementos inspeccionados registrados.", styles["Body"]))

        story.append(Spacer(0, 4*mm))
        story.append(Paragraph("10. OBSERVACIONES", styles["HSection"]))
        obs_rows = [[f"• {x}"] for x in self.data["seccion_10_observaciones"]]
        
        # Verificar que hay observaciones antes de crear la tabla
        if obs_rows:
            obs_tbl = Table(obs_rows, colWidths=[total_w])
            obs_tbl.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Helvetica', 9),
                                         ('LEADING', (0,0), (-1,-1), 12),
                                         ('LEFTPADDING', (0,0), (-1,-1), 2),
                                         ('RIGHTPADDING', (0,0), (-1,-1), 2)]))
            story.append(obs_tbl)
        else:
            # Si no hay observaciones, agregar un mensaje
            story.append(Paragraph("No hay observaciones registradas.", styles["Body"]))

        # Página 4
        story.append(PageBreak())
        story.append(Spacer(0, 60*mm))
        story.append(Paragraph("11. REGISTRO FOTOGRÁFICO", styles["HSection"]))

        fotos = self.data["seccion_11_registro_fotografico"]
        foto_cells = []
        for f in fotos:
            if f.get("imagen"):
                try:
                    img = Image(f["imagen"], width=75*mm, height=45*mm)
                except Exception:
                    img = Box(75*mm, 45*mm, "FOTO")
            else:
                img = Box(75*mm, 45*mm, "FOTO")
            caption = Paragraph(f"<b>{f['titulo']}</b><br/>{f['descripcion']}", styles['Body'])
            cell = Table([[img],[caption]], colWidths=[75*mm])
            cell.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),
                                      ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
            foto_cells.append(cell)

        if len(foto_cells) >= 6:
            grid_fotos = Table([
                [foto_cells[0], foto_cells[1]],
                [foto_cells[2], foto_cells[3]],
                [foto_cells[4], foto_cells[5]],
            ], colWidths=[(total_w/2)-5*mm, (total_w/2)-5*mm], rowHeights=[60*mm, 60*mm, 60*mm])
        elif len(foto_cells) > 0:
            grid_fotos = Table([foto_cells], colWidths=[(total_w/2)-5*mm, (total_w/2)-5*mm], rowHeights=[60*mm])
            grid_fotos.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                                            ('ALIGN',(0,0),(-1,-1),'CENTER')]))
            story.append(grid_fotos)
        else:
            # Si no hay fotos, agregar un mensaje
            story.append(Paragraph("No hay registros fotográficos.", styles["Body"]))

        # Sección de firmas y sello al final: no dividir entre páginas.
        firma = self._crear_seccion_firmas(total_w, self.data["encabezado"])
        story.append(CondPageBreak(SIGNATURE_BLOCK_MIN_SPACE))
        story.append(KeepTogether([Spacer(0, 5*mm), firma]))

        return story 
    
    def _build_story_liquidos_penetrantes(self, total_w):
        """Construye el contenido del PDF específico para líquidos penetrantes"""
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="HSection", fontName="Helvetica-Bold", fontSize=10, spaceBefore=6, spaceAfter=4))
        styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=9, leading=12))
        styles.add(ParagraphStyle(name="Legend", fontName="Helvetica", fontSize=8))

        story = []

        # 1. NORMAS PARA EL CRITERIO DE EVALUACIÓN
        norma_text = f"Norma: {self.data['seccion_2_normas']['norma']}"
        story.append(self._section_text_box("1. NORMAS PARA EL CRITERIO DE EVALUACIÓN:", norma_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 2. PROCEDIMIENTO (Información General)
        procedimiento_value = self.data.get('seccion_1_procedimiento', {}).get('procedimiento', 'TLPR0026 - Inspección de Líquidos Penetrantes - Rev. 1')
        procedimiento_text = f"Procedimiento: {procedimiento_value}"
        story.append(self._section_text_box("2. PROCEDIMIENTO:", procedimiento_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 3. EQUIPOS UTILIZADOS
        story.append(self._section_text_box("3. EQUIPOS UTILIZADOS", self.data["seccion_2_equipos"]["equipos"], total_w))
        story.append(Spacer(0, 6*mm))

        # 4. MATERIAL BASE
        story.append(self._section_text_box("4. MATERIAL BASE:", self.data["seccion_3_material_base"]["material_base"], total_w))
        story.append(Spacer(0, 6*mm))

        # 6. MATERIALES UTILIZADOS
        story.append(CondPageBreak(24 * mm))
        story.append(Paragraph("6. MATERIALES UTILIZADOS", styles["HSection"]))
        story.append(Spacer(0, 3*mm))
        
        # Crear tabla de materiales
        materiales_data = self.data.get("seccion_4_materiales", {}).get("materiales", {})
        
        # Definir el orden de los materiales
        orden_materiales = ["PENETRANTE", "EMULSIFICANTE", "LIMPIADOR", "REVELADOR"]
        
        # Crear encabezados de la tabla
        tabla_data = [
            ["DETALLES", "FABRICANTE", "REFERENCIA COMERCIAL", "LOTE N°"]
        ]
        
        # Agregar filas de datos
        for detalle in orden_materiales:
            material = materiales_data.get(detalle, {})
            fabricante = material.get("fabricante", "")
            referencia = material.get("referencia", "")
            lote = material.get("lote", "")
            
            tabla_data.append([
                detalle,
                fabricante,
                referencia,
                lote
            ])
        
        # Crear la tabla
        col_widths = [total_w * 0.25, total_w * 0.25, total_w * 0.30, total_w * 0.20]
        row_split_range = (2, len(tabla_data) - 1) if len(tabla_data) > 2 else None
        materiales_tabla = Table(
            tabla_data,
            colWidths=col_widths,
            repeatRows=1 if len(tabla_data) > 1 else 0,
            splitByRow=1,
            rowSplitRange=row_split_range
        )
        materiales_tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        
        story.append(materiales_tabla)
        story.append(Spacer(0, 6*mm))

        # 7. NORMAS PARA LOS PROCEDIMIENTOS Y MÉTODOS DE APLICACIÓN
        story.append(CondPageBreak(18 * mm))
        story.append(Paragraph("7. NORMAS PARA LOS PROCEDIMIENTOS Y MÉTODOS DE APLICACIÓN:", styles["HSection"]))
        story.append(Spacer(0, 3*mm))
        
        # Estándares ASTM (leídos del formulario)
        astm_style = ParagraphStyle(
            name="ASTM",
            fontName="Helvetica",
            fontSize=9,
            leading=12
        )
        estandares_astm = self.data['seccion_5_tipo_metodo'].get('estandares_astm', [
            'ASTM E 165: Standard Test Method for Liquid Penetrant Examination',
            'ASTM E 1417: Standard Practice for Liquid Penetrant Examination'
        ])
        for estandar in estandares_astm:
            if estandar:  # Solo agregar si el estándar no está vacío
                story.append(Paragraph(estandar, astm_style))
        story.append(Spacer(0, 3*mm))
        
        # Línea horizontal
        story.append(HRFlowable(width=total_w, thickness=0.5, lineCap='round', color=colors.black))
        story.append(Spacer(0, 3*mm))
        
        # 7.1 TIPO Y MÉTODO
        story.append(CondPageBreak(16 * mm))
        tipo_metodo_style = ParagraphStyle(
            name="TipoMetodo",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            spaceBefore=0,
            spaceAfter=0
        )
        story.append(Paragraph("7.1 TIPO Y MÉTODO", tipo_metodo_style))
        story.append(Spacer(0, 3*mm))
        
        # Obtener datos de tipo y método
        tipo_valor = self.data['seccion_5_tipo_metodo'].get('tipo', 'II - Líquidos Penetrantes Visibles')
        metodo_valor = self.data['seccion_5_tipo_metodo'].get('metodo', 'C - Removible con Solvente')
        
        # Crear tabla para TIPO y MÉTODO en horizontal (misma fila)
        tipo_metodo_data = [
            [
                Paragraph("<b>TIPO :</b>", astm_style), 
                Paragraph(f"<u>{tipo_valor}</u>", astm_style),
                Paragraph("<b>MÉTODO:</b>", astm_style), 
                Paragraph(f"<u>{metodo_valor}</u>", astm_style)
            ]
        ]
        tipo_metodo_tabla = Table(tipo_metodo_data, colWidths=[total_w * 0.15, total_w * 0.35, total_w * 0.15, total_w * 0.35])
        tipo_metodo_tabla.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tipo_metodo_tabla)
        story.append(Spacer(0, 3*mm))
        
        # Línea horizontal
        story.append(HRFlowable(width=total_w, thickness=0.5, lineCap='round', color=colors.black))
        story.append(Spacer(0, 3*mm))
        
        # 7.2 PROCEDIMIENTO
        story.append(CondPageBreak(16 * mm))
        story.append(Paragraph("7.2 PROCEDIMIENTO", tipo_metodo_style))
        story.append(Spacer(0, 2*mm))
        
        # Obtener pasos del procedimiento
        pasos_text = self.data['seccion_5_tipo_metodo'].get('pasos_procedimiento', '')
        
        # Procesar los pasos del procedimiento (pueden venir como texto con saltos de línea o lista)
        if pasos_text:
            # Dividir por líneas y crear párrafos numerados
            pasos_lines = pasos_text.split('\n')
            pasos_paragraphs = []
            for linea in pasos_lines:
                if linea.strip():
                    # Mantener el formato original de la línea (puede tener números, símbolos, etc.)
                    pasos_paragraphs.append(Paragraph(linea.strip(), astm_style))
        else:
            pasos_paragraphs = [Paragraph("No se especificaron pasos del procedimiento.", astm_style)]
        
        # Crear caja de texto con borde para los pasos
        procedimiento_data = [[p] for p in pasos_paragraphs]
        procedimiento_tabla = Table(procedimiento_data, colWidths=[total_w])
        procedimiento_tabla.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(procedimiento_tabla)
        story.append(Spacer(0, 6*mm))

        # 8. PARÁMETROS DE OPERACIÓN
        story.append(CondPageBreak(24 * mm))
        story.append(Paragraph("8. PARÁMETROS DE OPERACIÓN", styles["HSection"]))
        story.append(Spacer(0, 3*mm))
        
        # Crear tabla de parámetros de operación
        parametros_data = self.data.get("seccion_6_parametros", {}).get("parametros", [])
        
        # Crear encabezados de la tabla
        tabla_parametros_data = [
            ["ACTIVIDAD", "TIEMPO DE PERMANENCIA", "TEMPERATURA", "APLICACIÓN", "ILUMINACIÓN"]
        ]
        
        # Agregar filas de datos
        for param in parametros_data:
            actividad = param.get("actividad", "")
            tiempo = param.get("tiempo", 0)
            # Formatear tiempo como "5:00 min"
            tiempo_formateado = f"{tiempo}:00 min" if isinstance(tiempo, (int, float)) else str(tiempo)
            temperatura = param.get("temperatura", "")
            aplicacion = param.get("aplicacion", "")
            iluminacion = param.get("iluminacion", "")
            
            tabla_parametros_data.append([
                actividad,
                tiempo_formateado,
                temperatura,
                aplicacion,
                iluminacion
            ])
        
        # Crear la tabla con anchos ajustados
        # ACTIVIDAD: 18%, TIEMPO DE PERMANENCIA: 25%, TEMPERATURA: 15% (ampliada), APLICACIÓN: 18% (reducida), ILUMINACIÓN: 24% (reducida)
        col_widths = [
            total_w * 0.18,  # ACTIVIDAD
            total_w * 0.25,  # TIEMPO DE PERMANENCIA
            total_w * 0.15,  # TEMPERATURA (ampliada para evitar solapamiento)
            total_w * 0.18,  # APLICACIÓN (reducida)
            total_w * 0.24   # ILUMINACIÓN (reducida)
        ]
        row_split_range = (2, len(tabla_parametros_data) - 1) if len(tabla_parametros_data) > 2 else None
        parametros_tabla = Table(
            tabla_parametros_data,
            colWidths=col_widths,
            repeatRows=1 if len(tabla_parametros_data) > 1 else 0,
            splitByRow=1,
            rowSplitRange=row_split_range
        )
        parametros_tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            # Permitir que el texto se ajuste dentro de las celdas
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        
        story.append(parametros_tabla)
        story.append(Spacer(0, 6*mm))

        # 9. ESQUEMA ESTRUCTURA INSPECCIONADA
        esquema = self.data.get("seccion_9_esquema", {}).get("esquema", [])
        esquema_imgs = [e for e in esquema if isinstance(e, dict) and e.get("archivo")]
        if esquema_imgs:
            story.append(Paragraph(f"{seccion}. ESQUEMA ESTRUCTURA INSPECCIONADA:", styles["HSection"]))
            col_w = total_w
            for idx, esquema_item in enumerate(esquema_imgs, start=1):
                # Una imagen por fila con ancho completo.
                # La celda mantiene junta imagen + título + comentario.
                cell = self._esquema_cell_liquidos(esquema_item, idx, col_w, styles)
                story.append(cell)

            story.append(Spacer(0, 6 * mm))
            seccion += 1

        # 10. ELEMENTOS INSPECCIONADOS
        elementos_inspeccionados = self.data.get("seccion_7_elementos_inspeccionados", {}).get(
            "elementos_inspeccionados", [])
        if elementos_inspeccionados:
            story.append(CondPageBreak(26 * mm))
            story.append(Paragraph("10. ELEMENTOS INSPECCIONADOS:", styles["HSection"]))

            body_table = ParagraphStyle(
                name="ElemTable",
                parent=styles["Body"],
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                spaceBefore=0,
                spaceAfter=0,
            )

            tabla = [["No.", "Descripción del Elemento", "Indicación", "CAL", "Observación"]]
            calificaciones = []
            for e in elementos_inspeccionados:
                cal_completa = e.get('calificacion', 'Satisfactorio')
                cal_abreviada = self._abreviar_calificacion(cal_completa)
                calificaciones.append(cal_completa)

                desc = e.get('descripcion', '') or ''
                ind = e.get('indicacion', '') or ''
                obs = e.get('observacion', '') or ''

                desc_p = Paragraph(desc, body_table) if desc else ""
                ind_p = Paragraph(ind, body_table) if ind else ""
                obs_p = Paragraph(obs, body_table) if obs else ""

                tabla.append([
                    e.get('numero', ''),
                    desc_p,
                    ind_p,
                    cal_abreviada,
                    obs_p,
                ])

            col_widths = [
                total_w * 0.079,  # No.
                total_w * 0.330,  # Descripción
                total_w * 0.211,  # Indicación
                total_w * 0.080,  # CAL
                total_w * 0.300,  # Observación
            ]

            row_split_range = (2, len(tabla) - 1) if len(tabla) > 2 else None
            t = Table(
                tabla,
                colWidths=col_widths,
                repeatRows=1 if len(tabla) > 1 else 0,
                splitByRow=1,
                rowSplitRange=row_split_range
            )

            style_list = [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("WORDWRAP", (0, 0), (-1, -1), True),
            ]

            for idx, cal in enumerate(calificaciones, start=1):
                color = self._obtener_color_calificacion(cal)
                style_list.append(("BACKGROUND", (3, idx), (3, idx), color))

            t.setStyle(TableStyle(style_list))
            story.append(t)

            leyenda = self._crear_leyenda_disconformidades(total_w)
            story.append(LegendWithNextPageNote(leyenda, styles["LegendNextPageNote"], spacer_h=3 * mm))
            story.append(Spacer(0, 6 * mm))

        # 11. DETALLE DE RESULTADOS
        detalle_text = self.data["seccion_8_detalle"]["detalle_resultados"] or "Sin detalles específicos"
        story.append(self._section_text_box("11. DETALLE DE ELEMENTOS INSPECCIONADOS Y RESULTADOS:", detalle_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 12. OBSERVACIONES GENERALES
        obs_text = self.data["seccion_8_detalle"]["observaciones_generales"] or "Sin observaciones"
        story.append(self._section_text_box("12. OBSERVACIONES GENERALES:", obs_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 13. REGISTROS FOTOGRÁFICOS
        regs = self.data.get("registros_fotograficos", [])
        imgs = [r for r in regs if isinstance(r, dict) and r.get("archivo")]

        story.append(CondPageBreak(24 * mm))
        story.append(Paragraph("13. REGISTROS FOTOGRÁFICOS", styles["HSection"]))

        if imgs:
            col_w = total_w / 2.0
            rows = []
            odd_last_row = False
            idx = 1
            for i in range(0, len(imgs), 2):
                left = self._foto_cell_liquidos(imgs[i], idx, col_w, styles)
                idx += 1
                if i + 1 < len(imgs):
                    right = self._foto_cell_liquidos(imgs[i+1], idx, col_w, styles)
                    idx += 1
                    rows.append([left, right])
                else:
                    odd_last_row = True
                    rows.append([left, ""])

            grid = Table(rows, colWidths=[col_w, col_w])
            style_list = [
                ("GRID", (0,0), (-1,-1), 0.8, colors.black),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
            ]
            if odd_last_row and rows:
                last_row = len(rows) - 1
                style_list.extend([
                    ("SPAN", (0, last_row), (1, last_row)),
                    ("ALIGN", (0, last_row), (1, last_row), "CENTER"),
                ])
            grid.setStyle(TableStyle(style_list))
            story.append(grid)
        else:
            story.append(Paragraph("No se registraron fotografías en este informe.", styles["Body"]))

        # Sección de firmas y sello al final: no dividir entre páginas.
        firma = self._crear_seccion_firmas(total_w, self.data["encabezado"])
        story.append(CondPageBreak(SIGNATURE_BLOCK_MIN_SPACE))
        story.append(KeepTogether([Spacer(0, 5*mm), firma]))

        return story

    def _build_story_particulas_magneticas(self, total_w):
        """Construye el contenido del PDF para partículas magnéticas"""
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="HSection", fontName="Helvetica-Bold", fontSize=10, spaceBefore=6, spaceAfter=4))
        styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=9, leading=12))
        styles.add(ParagraphStyle(name="Legend", fontName="Helvetica", fontSize=8))

        story = []

        # 1. PROCEDIMIENTO (Información General)
        procedimiento_value = self.data.get('seccion_1_procedimiento', {}).get('procedimiento', 'TLPR0027 - Inspección de Partículas Magnéticas - Rev. 1')
        procedimiento_text = f"Procedimiento: {procedimiento_value}"
        story.append(self._section_text_box("1. PROCEDIMIENTO:", procedimiento_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 2. NORMAS PARA EL CRITERIO DE EVALUACIÓN
        norma_text = f"Norma: {self.data['seccion_2_normas']['norma']}"
        story.append(self._section_text_box("2. NORMAS PARA EL CRITERIO DE EVALUACIÓN:", norma_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 3. EQUIPOS UTILIZADOS
        story.append(self._section_text_box("3. EQUIPOS UTILIZADOS", self.data["seccion_3_equipos"]["equipos"], total_w))
        story.append(Spacer(0, 6*mm))

        # 4. MATERIAL BASE
        story.append(self._section_text_box("4. MATERIAL BASE:", self.data["seccion_4_material_base"]["material_base"], total_w))
        story.append(Spacer(0, 6*mm))

        # 5. MATERIALES UTILIZADOS
        materiales_text = "Materiales utilizados en la inspección de partículas magnéticas"
        story.append(self._section_text_box("5. MATERIALES UTILIZADOS:", materiales_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 6. TIPO Y MÉTODO
        tipo_metodo_text = "Tipo y método de partículas magnéticas"
        story.append(self._section_text_box("6. TIPO Y MÉTODO:", tipo_metodo_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 7. PARÁMETROS DE OPERACIÓN
        parametros_text = "Parámetros de operación para la inspección"
        story.append(self._section_text_box("7. PARÁMETROS DE OPERACIÓN:", parametros_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 8. PROCESO Y CORRIENTE
        proceso_corriente_text = "Proceso y corriente utilizados"
        story.append(self._section_text_box("8. PROCESO Y CORRIENTE:", proceso_corriente_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 9. ELEMENTOS INSPECCIONADOS
        elementos_text = "Elementos inspeccionados durante la prueba"
        story.append(self._section_text_box("9. ELEMENTOS INSPECCIONADOS:", elementos_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 10. DETALLE DE RESULTADOS
        detalle_text = self.data["seccion_10_detalle"]["detalle_resultados"] or "Sin detalles específicos"
        story.append(self._section_text_box("10. DETALLE DE ELEMENTOS INSPECCIONADOS Y RESULTADOS:", detalle_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 11. OBSERVACIONES GENERALES
        obs_text = self.data["seccion_10_detalle"]["observaciones_generales"] or "Sin observaciones"
        story.append(self._section_text_box("11. OBSERVACIONES GENERALES:", obs_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 12. REGISTROS FOTOGRÁFICOS
        story.append(CondPageBreak(24 * mm))
        story.append(Paragraph("12. REGISTROS FOTOGRÁFICOS", styles["HSection"]))
        story.append(Spacer(0, 3*mm))
        
        # Manejar registros fotográficos
        if self.data.get("registros_fotograficos"):
            for i, foto in enumerate(self.data["registros_fotograficos"]):
                if foto and foto.get("imagen"):
                    try:
                        img = Image(foto["imagen"], width=120, height=90)
                        story.append(img)
                        story.append(Paragraph(f"Foto {i+1}: {foto.get('descripcion', 'Sin descripción')}", styles["Legend"]))
                        story.append(Spacer(0, 3*mm))
                    except Exception as e:
                        story.append(Paragraph(f"Error al cargar foto {i+1}: {str(e)}", styles["Body"]))
        else:
            # Si no hay fotos, agregar un mensaje
            story.append(Paragraph("No hay registros fotográficos.", styles["Body"]))

        # Sección de firmas y sello al final: no dividir entre páginas.
        firma = self._crear_seccion_firmas(total_w, self.data["encabezado"])
        story.append(CondPageBreak(SIGNATURE_BLOCK_MIN_SPACE))
        story.append(KeepTogether([Spacer(0, 5*mm), firma]))

        return story

    def _build_story_ultrasonido(self, total_w):
        """Construye el contenido del PDF para ultrasonido"""
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="HSection", fontName="Helvetica-Bold", fontSize=10, spaceBefore=6, spaceAfter=4))
        styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=9, leading=12))
        styles.add(ParagraphStyle(name="Legend", fontName="Helvetica", fontSize=8))

        story = []

        # 1. PROCEDIMIENTO (Información General)
        procedimiento_value = self.data.get('seccion_1_procedimiento', {}).get('procedimiento', 'TLPR0028 - Inspección de Ultrasonido - Rev. 1')
        procedimiento_text = f"Procedimiento: {procedimiento_value}"
        story.append(self._section_text_box("1. PROCEDIMIENTO:", procedimiento_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 2. NORMAS PARA EL CRITERIO DE EVALUACIÓN
        norma_text = f"Norma: {self.data['seccion_2_normas']['norma']}"
        story.append(self._section_text_box("2. NORMAS PARA EL CRITERIO DE EVALUACIÓN:", norma_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 3. EQUIPOS UTILIZADOS
        equipos_text = f"Equipo: {self.data['seccion_3_equipos']['equipos']}\nPalpador: {self.data['seccion_3_equipos']['palpador']}"
        story.append(self._section_text_box("3. EQUIPOS UTILIZADOS", equipos_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 4. MATERIAL BASE
        story.append(self._section_text_box("4. MATERIAL BASE:", self.data["seccion_4_material_base"]["material_base"], total_w))
        story.append(Spacer(0, 6*mm))

        # 5. JUNTAS
        juntas_text = "Juntas inspeccionadas"
        story.append(self._section_text_box("5. JUNTAS:", juntas_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 6. ELEMENTOS INSPECCIONADOS
        elementos_text = "Elementos inspeccionados durante la prueba"
        story.append(self._section_text_box("6. ELEMENTOS INSPECCIONADOS:", elementos_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 7. DETALLE DE RESULTADOS
        detalle_text = self.data["seccion_7_detalle"]["detalle_resultados"] or "Sin detalles específicos"
        story.append(self._section_text_box("7. DETALLE DE ELEMENTOS INSPECCIONADOS Y RESULTADOS:", detalle_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 8. OBSERVACIONES GENERALES
        obs_text = self.data["seccion_7_detalle"]["observaciones_generales"] or "Sin observaciones"
        story.append(self._section_text_box("8. OBSERVACIONES GENERALES:", obs_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 9. REGISTROS FOTOGRÁFICOS
        story.append(CondPageBreak(24 * mm))
        story.append(Paragraph("9. REGISTROS FOTOGRÁFICOS", styles["HSection"]))
        story.append(Spacer(0, 3*mm))
        
        # Manejar registros fotográficos
        if self.data.get("registros_fotograficos"):
            for i, foto in enumerate(self.data["registros_fotograficos"]):
                if foto and foto.get("imagen"):
                    try:
                        img = Image(foto["imagen"], width=120, height=90)
                        story.append(img)
                        story.append(Paragraph(f"Foto {i+1}: {foto.get('descripcion', 'Sin descripción')}", styles["Legend"]))
                        story.append(Spacer(0, 3*mm))
                    except Exception as e:
                        story.append(Paragraph(f"Error al cargar foto {i+1}: {str(e)}", styles["Body"]))
        else:
            # Si no hay fotos, agregar un mensaje
            story.append(Paragraph("No hay registros fotográficos.", styles["Body"]))

        # Sección de firmas y sello al final: no dividir entre páginas.
        firma = self._crear_seccion_firmas(total_w, self.data["encabezado"])
        story.append(CondPageBreak(SIGNATURE_BLOCK_MIN_SPACE))
        story.append(KeepTogether([Spacer(0, 5*mm), firma]))

        return story

    def _formatear_datos_inspeccion_visual(self, datos_proyecto: Dict[str, Any], 
                                          datos_inspeccion: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea los datos de inspección visual para el PDF"""
        
        # Estructura de datos para el PDF basada en los datos reales
        data = {
            "encabezado": {
                "numero_informe": datos_proyecto.get('numero_informe', 'T1234I1005'),
                "fecha": datos_proyecto.get('fecha', '5-jun-24'),
                "cliente": datos_proyecto.get('cliente', 'Cliente'),
                "proyecto": datos_proyecto.get('proyecto', 'Proyecto'),
                "ubicacion": datos_proyecto.get('ubicacion', 'Lugar'),
                "inspector": datos_proyecto.get('inspector', 'Ing. Andrés López'),
                "elaboro": datos_proyecto.get('inspector', 'Ing. Andrés López'),
                "reviso": self._resolver_reviso(datos_proyecto),
                "firma_elaboro_path": self._resolver_firma_path(datos_proyecto, datos_proyecto.get('inspector', 'Ing. Andrés López'), "firma_1_path"),
                "firma_reviso_path": self._resolver_firma_path(datos_proyecto, self._resolver_reviso(datos_proyecto), "firma_2_path"),
                "contratista": datos_proyecto.get('contratista', 'Contratista'),
                "subproyecto": datos_proyecto.get('subproyecto', 'Subproyecto'),
                "proceso_soldadura": datos_inspeccion.get('proceso_soldadura', 'SMAW'),
                "tipo": datos_inspeccion.get('tipo', 'Manual'),
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020')
            },
            "seccion_1_normas": {
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020')
            },
            "seccion_2_equipos": {
                "equipos": datos_inspeccion.get('equipos', 'Flexómetro, Calibrador, galga soldadura, Cámara digital, linterna, Regla')
            },
            "seccion_3_material_base": {
                "material_base": datos_inspeccion.get('especificacion', 'No especificado')
            },
            "seccion_4_antes_soldadura": {
                "items": datos_inspeccion.get('antes_soldadura', [
                    'Chequear la calificación del personal',
                    'Chequear el tipo del material base y el de aporte',
                    'Chequear si hay algún tipo discontinuidad en el metal base',
                    'Chequear el alineamiento de la junta de soldadura',
                    'Chequear condiciones de precalentamiento'
                ])
            },
            "seccion_5_inicio_junta": {
                "items": datos_inspeccion.get('inicio_junta', [
                    'Angulo de chaflán',
                    'Hombro de raíz',
                    'Alineamiento de la junta',
                    'Respaldo con soldadura o platina',
                    'Limpieza de la junta',
                    'Puntos de soldadura (si se punteo)',
                    'Precalentamiento'
                ])
            },
            "seccion_6_despues_soldadura": {
                "items": datos_inspeccion.get('despues_soldadura', [
                    'Apariencia final de la soldadura',
                    'Tamaño final de la soldadura',
                    'Longitud de la soldadura',
                    'Cantidad de distorsión (en la pieza)',
                    'Tratamiento Térmico después de la soldadura'
                ])
            },
            "seccion_7_elementos_inspeccionados": {
                "leyenda": {
                    "A": "Aplica",
                    "N.A": "No aplica", 
                    "S": "Satisfactorio",
                    "N.S": "No Satisfactorio",
                    "F.A": "Fuera de Alcance"
                },
                "convencion_discontinuidades": ["A", "N.A", "S", "N.S", "F.A"],
                "items_esquema": []
            },
            "seccion_8_detalle_elementos": [
                {
                    "item": str(i+1),
                    "elemento": elem.get('elemento', ''),
                    "especificacion": elem.get('especificacion', ''),
                    "indicacion": elem.get('indicacion', ''),
                    "cal": elem.get('cal', 'Satisfactorio')
                }
                for i, elem in enumerate(datos_inspeccion.get('elementos_inspeccionados', []))
            ],
            "seccion_10_observaciones": [
                datos_inspeccion.get('observaciones_generales', '')
            ],
            "seccion_11_registro_fotografico": [
                {
                    "titulo": f"Foto {i+1}",
                    "descripcion": img.get('comentario', ''),
                    "imagen": None  # Las imágenes se manejan por separado
                }
                for i, img in enumerate(datos_inspeccion.get('registros_fotograficos', []))
            ]
        }
        
        return data 
    
    def _formatear_datos_liquidos_penetrantes(self, datos_proyecto: Dict[str, Any], 
                                            datos_inspeccion: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea los datos de inspección de líquidos penetrantes para el PDF"""
        
        # Estructura de datos para el PDF basada en los datos reales
        data = {
            "encabezado": {
                "rep": datos_proyecto.get('numero_informe', 'T1234I1015'),
                "fecha": datos_proyecto.get('fecha', '5-jun-24'),
                "cliente": datos_proyecto.get('cliente', 'Cliente'),
                "proyecto": datos_proyecto.get('proyecto', 'Proyecto'),
                "lugar": datos_proyecto.get('ubicacion', 'Lugar'),
                "elaboro": datos_proyecto.get('inspector', 'Ing. Andrés López'),
                "reviso": self._resolver_reviso(datos_proyecto),
                "firma_elaboro_path": self._resolver_firma_path(datos_proyecto, datos_proyecto.get('inspector', 'Ing. Andrés López'), "firma_1_path"),
                "firma_reviso_path": self._resolver_firma_path(datos_proyecto, self._resolver_reviso(datos_proyecto), "firma_2_path"),
                "contratista": datos_proyecto.get('contratista', 'Contratista'),
                "subproyecto": datos_proyecto.get('subproyecto', 'Subproyecto'),
                "proceso_soldadura": ', '.join(datos_inspeccion.get('proceso', ['SMAW'])) if isinstance(datos_inspeccion.get('proceso'), list) else datos_inspeccion.get('proceso', 'SMAW'),
                "tipo_proceso": datos_inspeccion.get('tipo', 'II - Líquidos Penetrantes Visibles'),
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020'),
                "procedimiento": datos_inspeccion.get('procedimiento', 'TLPR0026 - Inspección de Líquidos Penetrantes - Rev. 1')
            },
            "seccion_1_procedimiento": {
                "procedimiento": datos_inspeccion.get('procedimiento', 'TLPR0026 - Inspección de Líquidos Penetrantes - Rev. 1')
            },
            "seccion_2_normas": {
                "norma": datos_inspeccion.get('norma', 'AWS D1.1 2020')
            },
            "seccion_2_equipos": {
                "equipos": datos_inspeccion.get('equipos', 'Kit de Líquidos Penetrantes')
            },
            "seccion_3_material_base": {
                "material_base": ', '.join(datos_inspeccion.get('especificacion', ['No especificado'])) if isinstance(datos_inspeccion.get('especificacion'), list) else datos_inspeccion.get('especificacion', 'No especificado')
            },
            "seccion_4_materiales": {
                "materiales": datos_inspeccion.get('materiales', {})
            },
            "seccion_5_tipo_metodo": {
                "tipo": datos_inspeccion.get('tipo', 'II - Líquidos Penetrantes Visibles'),
                "metodo": datos_inspeccion.get('metodo', 'C - Eliminables con Disolvente'),
                "pasos_procedimiento": datos_inspeccion.get('pasos_procedimiento', ''),
                "estandares_astm": datos_inspeccion.get('estandares_astm', [
                    'ASTM E 165: Standard Test Method for Liquid Penetrant Examination',
                    'ASTM E 1417: Standard Practice for Liquid Penetrant Examination'
                ])
            },
            "seccion_6_parametros": {
                "parametros": datos_inspeccion.get('parametros', [])
            },
            "seccion_7_elementos": {
                "elementos": datos_inspeccion.get('elementos', [])
            },
            "seccion_7_elementos_inspeccionados": {
                "elementos_inspeccionados": datos_inspeccion.get('elementos', [])
            },
            "seccion_8_detalle": {
                "detalle_resultados": datos_inspeccion.get('detalle_resultados', ''),
                "observaciones_generales": datos_inspeccion.get('observaciones_generales', '')
            },
            "seccion_9_esquema": {
                "esquema": datos_inspeccion.get('esquema_elementos', [])
            },
            "registros_fotograficos": datos_inspeccion.get('registros_fotograficos', [])
        }
        
        return data
