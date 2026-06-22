# -*- coding: utf-8 -*-
"""
Módulo específico para generación de reportes de Inspección Visual
Completamente autónomo - solo usa datos del módulo 2
Estética basada en build_report.py
"""

import os
import re
from io import BytesIO
from typing import Dict, List, Any

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, Flowable, KeepInFrame, KeepTogether, CondPageBreak, PageBreak
)

SIGNATURE_BLOCK_MIN_SPACE = 52 * mm

# ---------------- Numeración real: "Página X de Y" (sin duplicar) -------------------------
class NumberedCanvas(rl_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._pages_with_abbreviations = set()  # Páginas que tienen secciones 5, 6, 7
        self._total_pages = 0
        self._last_page_number = 0  # Número de la última página

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()  # evita duplicación

    def save(self):
        self._total_pages = len(self._saved_page_states)
        # Guardar el total de páginas en cada estado para que el footer pueda acceder
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            # Guardar el total de páginas en el estado para que esté disponible cuando se dibuje el footer
            self._total_pages = len(self._saved_page_states)
            self._last_page_number = self._total_pages  # Guardar el número de la última página
            self._draw_page_number(self._total_pages)
            rl_canvas.Canvas.showPage(self)  # ahora sí, emite la página
        rl_canvas.Canvas.save(self)

    def _draw_page_number(self, total):
        self.setFont("Helvetica", 9)
        self.drawRightString(200*mm, 10*mm, f"Página {self._pageNumber} de {total}")
    
    def mark_page_with_abbreviations(self, page_num):
        """Marca una página como que contiene las secciones 5, 6, 7"""
        self._pages_with_abbreviations.add(page_num)
    
    def has_abbreviations(self, page_num):
        """Verifica si una página debe mostrar abreviaciones"""
        return page_num in self._pages_with_abbreviations
    
    def is_last_page(self, page_num):
        """Verifica si es la última página"""
        # Usar el número de la última página guardado
        return page_num == self._last_page_number if self._last_page_number > 0 else False

# ---------------- Caja placeholder para fotos ------------------------------
class Box(Flowable):
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

# ---------------- Espacio para firma sin bordes ------------------------------
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

# ---------------- Flowable para marcar páginas con abreviaciones -----------
class MarkAbbreviationPage(Flowable):
    """Flowable que marca la página actual como que contiene abreviaciones"""
    def __init__(self):
        Flowable.__init__(self)
        self.width = 0
        self.height = 0
    
    def draw(self):
        # Marcar esta página como que tiene abreviaciones
        if hasattr(self.canv, 'mark_page_with_abbreviations'):
            page_num = getattr(self.canv, '_pageNumber', 1)
            self.canv.mark_page_with_abbreviations(page_num)

class ReporteInspeccionVisual:
    """Clase específica para generar reportes de Inspección Visual - Autónoma"""
    
    def __init__(self):
        self.data = {}
        self.output_path = ""
    
    def extraer_datos_proyecto(self) -> Dict[str, Any]:
        """Extrae datos del proyecto desde el módulo 1"""
        from datetime import datetime
        from utils import generar_numero_informe
        
        if 'datos_proyecto' in st.session_state:
            dp = st.session_state['datos_proyecto']
            # Generar número de informe para visual (offset 0)
            numero_orden = dp.get('numero_orden', '1234')
            consecutivo_inicial = dp.get('consecutivo_inicial', '100')
            fecha_obj = dp.get('fecha_obj', datetime.now())
            year = fecha_obj.year if hasattr(fecha_obj, 'year') else datetime.now().year
            numero_informe = generar_numero_informe(numero_orden, consecutivo_inicial, year, 0)
            
            dp_copy = dp.copy()
            dp_copy['numero_informe'] = numero_informe
            firmas = dp_copy.get("firmas", {})
            if isinstance(firmas, dict) and firmas.get("firma_2") and not dp_copy.get("reviso"):
                dp_copy["reviso"] = firmas.get("firma_2")
            return dp_copy
            
        elif 'bloque_1' in st.session_state:
            b1 = st.session_state['bloque_1']
            numero_orden = b1.get('numero_orden', '1234')
            consecutivo_inicial = b1.get('consecutivo_inicial', '100')
            fecha = b1.get('fecha', datetime.now())
            year = fecha.year if hasattr(fecha, 'year') else datetime.now().year
            numero_informe = generar_numero_informe(numero_orden, consecutivo_inicial, year, 0)
            
            return {
                'numero_informe': numero_informe,
                'fecha': b1.get('fecha', '5-jun-24'),
                'cliente': b1.get('cliente', 'Cliente'),
                'proyecto': b1.get('proyecto', 'Proyecto'),
                'ubicacion': b1.get('lugar', 'Lugar'),
                'inspector': b1.get('elaboro', 'Ing. Andrés López'),
                'reviso': b1.get('firmas', {}).get('firma_2', b1.get('elaboro', 'Ing. Andrés López')) if isinstance(b1.get('firmas', {}), dict) else b1.get('elaboro', 'Ing. Andrés López'),
                'firmas': b1.get('firmas', {}),
                'contratista': b1.get('contratista', 'Contratista'),
                'subproyecto': b1.get('subproyecto', 'Subproyecto')
            }
        else:
            return {
                'numero_informe': 'T1234I1005',
                'fecha': '5-jun-24',
                'cliente': 'Cliente',
                'proyecto': 'Proyecto',
                'ubicacion': 'Lugar',
                'inspector': 'Ing. Andrés López',
                'contratista': 'Contratista',
                'subproyecto': 'Subproyecto'
            }
    
    def extraer_datos_inspeccion_visual(self) -> Dict[str, Any]:
        """Extrae datos específicos de inspección visual SOLO del módulo 2"""
        self._limpiar_datos_duplicados()
        if 'bloque_2_1' in st.session_state:
            return self._procesar_datos_modulo_2(st.session_state['bloque_2_1'])
        elif 'datos_inspeccion_visual' in st.session_state:
            return self._procesar_datos_modulo_2(st.session_state['datos_inspeccion_visual'])
        else:
            return self._datos_por_defecto()
    
    def _limpiar_datos_duplicados(self):
        if 'datos_inspeccion_visual' in st.session_state and 'bloque_2_1' not in st.session_state:
            st.session_state['bloque_2_1'] = st.session_state['datos_inspeccion_visual']
            del st.session_state['datos_inspeccion_visual']
        if 'datos_inspeccion_visual' in st.session_state and 'bloque_2_1' in st.session_state:
            del st.session_state['datos_inspeccion_visual']
    
    def _procesar_datos_modulo_2(self, d: Dict[str, Any]) -> Dict[str, Any]:
        # Equipos
        eq = ""
        if 'equipos_utilizados' in d:
            kit = d['equipos_utilizados']
            if isinstance(kit, dict):
                k = kit.get('kit_seleccionado', '')
                comp = kit.get('componentes', [])
                eq = (k + (" - " + ", ".join(comp) if comp else "")) if k else ""
            else:
                eq = str(kit)
        else:
            eq = d.get('equipos', 'No especificado')
        # Materiales
        mb = d.get('materiales_base', [])
        mb_txt = ', '.join(mb) if isinstance(mb, list) and mb else (str(mb) if mb else 'No especificado')
        # Procesos
        ps = d.get('procesos_soldadura', [])
        ps_txt = ', '.join(ps) if isinstance(ps, list) and ps else (str(ps) if ps else 'No especificado')
        ts = d.get('tipos_soldadura', [])
        ts_txt = ', '.join(ts) if isinstance(ts, list) and ts else (str(ts) if ts else 'No especificado')

        fases = d.get('fases_inspeccion', [])
        fases_ok = self._procesar_fases_inspeccion(fases) if fases else {}
        elems = d.get('elementos_inspeccionados', [])
        elems_ok = self._proc_elems(elems) if elems else []
        esquema = d.get('esquema', [])
        fotos = d.get('registros_fotograficos', [])

        return {
            'norma': d.get('norma', 'No especificado'),
            'procedimiento': d.get('procedimiento', 'No especificado'),
            'equipos': eq,
            'material_base': mb_txt,
            'proceso_soldadura': ps_txt,
            'tipo_soldadura': ts_txt,
            'fases_inspeccion': fases_ok,
            'esquema': esquema,
            'elementos_inspeccionados': elems_ok,
            'detalle_resultados': d.get('detalle_resultados', ''),
            'observaciones_generales': d.get('observaciones_generales', ''),
            'registros_fotograficos': fotos
        }
    
    def _procesar_fases_inspeccion(self, fases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        out = {'antes_soldadura': [], 'inicio_junta': [], 'despues_soldadura': []}
        for f in fases:
            nombre = (f.get('fase', '') or '').upper()
            item = {
                'item': f.get('item', ''),
                'aplica': f.get('aplica', 'Aplica'),
                'resultado': f.get('resultado', 'Satisfactorio'),
                'observacion': f.get('observacion', '')
            }
            if 'ANTES DE INICIAR' in nombre:
                out['antes_soldadura'].append(item)
            elif 'INICIO' in nombre:
                out['inicio_junta'].append(item)
            elif 'DESPUÉS' in nombre or 'DESPUES' in nombre:
                out['despues_soldadura'].append(item)
        return out
    
    def _proc_elems(self, elems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{
            'numero': e.get('numero', ''),
            'descripcion': e.get('descripcion', ''),
            'indicacion': e.get('indicacion', ''),
            'calificacion': e.get('calificacion', 'Satisfactorio'),
            'observacion': e.get('observacion', '')
        } for e in elems]
    
    def _datos_por_defecto(self) -> Dict[str, Any]:
        return {
            'norma': 'No especificado',
            'procedimiento': 'No especificado',
            'equipos': 'No especificado',
            'material_base': 'No especificado',
            'proceso_soldadura': 'No especificado',
            'tipo_soldadura': 'No especificado',
            'fases_inspeccion': {'antes_soldadura': [], 'inicio_junta': [], 'despues_soldadura': []},
            'esquema': [],
            'elementos_inspeccionados': [],
            'detalle_resultados': '',
            'observaciones_generales': '',
            'registros_fotograficos': []
        }
    
    def generar_reporte(self, output_filename: str) -> str:
        from utils import get_report_output_path

        dp = self.extraer_datos_proyecto()
        di = self.extraer_datos_inspeccion_visual()
        self.data = self._formatear(dp, di)
        self.output_path = get_report_output_path(output_filename)
        self._generar_pdf(self.output_path)
        return self.output_path
    
    def _formatear(self, dp: Dict[str, Any], di: Dict[str, Any]) -> Dict[str, Any]:
        firmas = dp.get("firmas", {})
        reviso = ""
        firma_elaboro_path = ""
        firma_reviso_path = ""
        if isinstance(firmas, dict):
            reviso = firmas.get("firma_2", "")
            firma_elaboro_path = firmas.get("firma_1_path", "")
            firma_reviso_path = firmas.get("firma_2_path", "")
        if not reviso:
            reviso = dp.get("reviso", "")
        if not reviso:
            reviso = dp.get("inspector", "")

        if not firma_elaboro_path:
            try:
                from signature_registry import get_signature_for_person
                firma_elaboro_path = get_signature_for_person(dp.get("inspector", "")) or ""
            except Exception:
                firma_elaboro_path = ""
        if not firma_reviso_path:
            try:
                from signature_registry import get_signature_for_person
                firma_reviso_path = get_signature_for_person(reviso) or ""
            except Exception:
                firma_reviso_path = ""

        return {
            'encabezado': {
                'norma': di.get('norma', 'AWS D1.1 2020'),
                'cliente': dp.get('cliente', ''),
                'proyecto': dp.get('proyecto', ''),
                'subproyecto': dp.get('subproyecto', ''),
                'contratista': dp.get('contratista', ''),
                'elaboro': dp.get('inspector', ''),
                'reviso': reviso,
                'firma_elaboro_path': firma_elaboro_path,
                'firma_reviso_path': firma_reviso_path,
                'rep': dp.get('numero_informe', ''),
                'fecha': dp.get('fecha', ''),
                'lugar': dp.get('ubicacion', ''),
                'proceso_soldadura': di.get('proceso_soldadura', ''),
                'tipo_proceso': di.get('tipo_soldadura', '')
            },
            'procedimiento': di.get('procedimiento', 'TLPR0025 - Inspección Visual - Rev. 1'),
            'seccion_1_normas': {'criterio': di.get('norma', 'AWS D1.1 2020')},
            'seccion_2_equipos': [di.get('equipos', 'No especificado')],
            'seccion_3_material_base': di.get('material_base', 'No especificado'),
            'fases_inspeccion': di.get('fases_inspeccion', {}),
            'esquema': di.get('esquema', []),
            'elementos_inspeccionados': di.get('elementos_inspeccionados', []),
            'detalle_resultados': di.get('detalle_resultados', ''),
            'observaciones_generales': di.get('observaciones_generales', ''),
            'registros_fotograficos': di.get('registros_fotograficos', [])
        }
    
    def _generar_pdf(self, out_path: str):
        data = self.data
        enc = data["encabezado"]
        
        # Crear canvas personalizado antes del documento
        canvas_instance = None
        
        class DocTemplateWithCanvas(BaseDocTemplate):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._canvas_instance = None
                self._last_page_marker = None
            
            def afterPage(self):
                """Se llama después de cada página"""
                super().afterPage()
                # Guardar referencia al canvas
                if self._canvas_instance is None and hasattr(self.canv, '_pageNumber'):
                    self._canvas_instance = self.canv
                # Si hay un marcador de última página, actualizar el canvas
                if self._last_page_marker and hasattr(self.canv, '_last_page_number'):
                    page_num = getattr(self.canv, '_pageNumber', 1)
                    self.canv._last_page_number = page_num
                    if hasattr(self.canv, '_saved_page_states'):
                        self.canv._total_pages = len(self.canv._saved_page_states)
        
        doc = DocTemplateWithCanvas(
            out_path, pagesize=letter,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=25*mm, bottomMargin=45*mm
        )
        # Área de contenido (respeta encabezado)
        header_bottom_y = 220*mm
        padding = 6*mm
        content_top_y = header_bottom_y - padding
        content_height = content_top_y - doc.bottomMargin
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, content_height, id="main")

        # Guardar referencia al canvas
        self._canvas_ref = None
        
        def on_page_end(c, d):
            # Guardar referencia al canvas en la primera página
            if self._canvas_ref is None:
                self._canvas_ref = c
            self._draw_footer(c, d, enc)
        
        template = PageTemplate(
            id="tpl_main",
            frames=[frame],
            onPage=lambda c, d: self._draw_header(c, d, enc),   # SIEMPRE pinta el bloque
            onPageEnd=on_page_end,
        )
        doc.addPageTemplates([template])

        story = self._build_story(data, doc.width)
        numero = enc.get("rep", "") or enc.get("numero_informe", "")
        pdf_title = "INFORME_INSPECCION_VISUAL"
        if numero:
            pdf_title = f"{pdf_title}_{numero}"
        pdf_author = "Joint and Welding Ingenieros S.A.S."
        pdf_subject = f"Informe de inspeccion visual - {enc.get('cliente', 'Cliente')}"
        pdf_creator = "Joint and Welding Reporteador"
        doc.title = pdf_title
        doc.author = pdf_author
        doc.subject = pdf_subject
        doc.creator = pdf_creator

        doc.build(story, canvasmaker=NumberedCanvas)
        
        # Después de construir, marcar la última página en el canvas si tenemos la referencia
        if self._canvas_ref:
            if hasattr(self._canvas_ref, '_total_pages') and self._canvas_ref._total_pages > 0:
                self._canvas_ref._last_page_number = self._canvas_ref._total_pages
            elif hasattr(self._canvas_ref, '_saved_page_states'):
                total = len(self._canvas_ref._saved_page_states)
                if total > 0:
                    self._canvas_ref._last_page_number = total
                    self._canvas_ref._total_pages = total
    
    def _draw_header(self, canv, doc, enc):
        """Encabezado con bloque de cliente en TODAS las páginas."""
        canv.saveState()

        # Logo en la parte superior izquierda (alineado con el margen izquierdo del reporte)
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo.jpeg")
            if os.path.exists(logo_path):
                from reportlab.platypus import Image as RLImage
                # Tamaño más pequeño para que no se corte
                logo_img = RLImage(logo_path, width=30*mm, height=15*mm)
                # Posicionar alineado con el margen izquierdo del reporte
                logo_x = doc.leftMargin
                logo_y = 260*mm
                logo_img.drawOn(canv, logo_x, logo_y)
        except Exception:
            pass

        # Títulos (ajustados para no superponerse con el logo)
        canv.setFont("Helvetica-Bold", 13)
        canv.drawCentredString(105*mm, 267*mm, "INFORME INSPECCIÓN VISUAL")
        canv.setFont("Helvetica-Bold", 11)
        canv.drawCentredString(105*mm, 260*mm, enc.get("norma", "AWS D1.1 2020"))

        # Bloque de metadatos (todas las páginas)
        x0, y0, w, h = doc.leftMargin, 220*mm, doc.width, 38*mm
        canv.setLineWidth(1)
        canv.rect(x0, y0, w, h)

        # Preparar datos con Paragraph para permitir wrap de texto
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
                row_heights[0] = 10*mm  # Altura moderada para dos líneas sin romper estructura
            
            t = Table(tbl, colWidths=col_widths, rowHeights=row_heights)
            
            # Estilo con alineación MIDDLE para que etiquetas y valores queden a la misma altura
            style_list = [
                ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),  # Solo etiquetas
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
                    ("BOTTOMPADDING", (0,0), (-1,0), 4.0),  # Espacio moderado cuando cliente es de 2 líneas (balanceado)
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
            # Aumentar más el ancho de etiquetas para que "Proceso de soldadura" no pise el valor
            col_widths = [38*mm, 28*mm]  # Etiquetas más anchas, valores más estrechos pero suficientes
            t = Table(tbl, colWidths=col_widths, rowHeights=6*mm)  # Reducido para que quepa todo
            t.setStyle(TableStyle([
                ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),  # Solo etiquetas
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),  # Alineación central para etiquetas
                ("VALIGN", (1,0), (1,-1), "MIDDLE"),  # Alineación central para valores (misma altura)
                ("LINEBELOW", (1,0), (1,-1), 0.6, colors.black),
                ("RIGHTPADDING", (0,0), (0,-1), 0),
                ("LEFTPADDING", (1,0), (1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 1),  # Padding reducido
                ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),  # Ajustar aquí: distancia texto-línea (0.5-3mm)
            ]))
            _, h_ = t.wrapOn(canv, 0, 0)
            t.drawOn(canv, x, y - h_)

        inner = 0.5*mm
        inner_right = 2*mm  # Margen interno derecho para que las líneas no toquen el borde
        left_tbl_w = (24+88)*mm
        right_tbl_w = (38+28)*mm  # Actualizado con nuevo ancho
        left_x  = x0 + inner
        # Columna derecha separada del margen derecho
        right_x = x0 + w - inner_right - right_tbl_w
        top_y = y0 + h - 3*mm

        draw_meta_left(left_data,  left_x,  top_y)
        draw_meta_right(right_data, right_x, top_y)

        # Texto vertical
        canv.setFont("Helvetica", 7)
        canv.saveState()
        canv.translate(10*mm, 140*mm)
        canv.rotate(90)
        canv.drawString(0, 0, "© Joint and Welding Ingenieros S.A.S. 2024 - Versión 6.0")
        canv.restoreState()
        canv.restoreState()

    def _draw_footer(self, canv, doc, enc):
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle

        x0, w = doc.leftMargin, doc.width
        current_page = getattr(canv, '_pageNumber', 1)

        # Obtener información del canvas si está disponible
        has_abbreviations = False
        if hasattr(canv, 'has_abbreviations'):
            has_abbreviations = canv.has_abbreviations(current_page)
        
        st_small = ParagraphStyle("small", fontName="Helvetica", fontSize=7, leading=8)
        st_small_b = ParagraphStyle("small_b", parent=st_small, fontName="Helvetica-Bold", fontSize=9, leading=10, alignment=1)
        
        cliente_nombre = enc.get("cliente", "Concreacero")
        
        # Footer normal: empresa y cliente
        data = [[
            Paragraph("Joint and Welding Ingenieros S.A.S.", st_small_b),
            Paragraph(cliente_nombre, st_small_b),
        ]]

        col_mid = w * 0.6
        col_right = w * 0.4
        t = Table(data, colWidths=[col_mid, col_right])
        t.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.8, colors.black),
            ("INNERGRID", (0,0), (-1,-1), 0.8, colors.black),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("ALIGN", (0,0), (0,0), "CENTER"),
            ("ALIGN", (1,0), (1,0), "CENTER"),
        ]))
        t.wrapOn(canv, w, 0)
        t.drawOn(canv, x0, 15*mm)

        # Si esta página tiene abreviaciones, agregarlas arriba
        if has_abbreviations:
            abrev_txt = ("Abreviaciones:  A: Aplica   N.A: No aplica   S: Satisfactorio   "
                       "N.S: No Satisfactorio   F.A: Fuera de Alcance")
            abrev_para = Paragraph(abrev_txt, st_small)
            abrev_data = [[abrev_para]]
            abrev_t = Table(abrev_data, colWidths=[w])
            abrev_t.setStyle(TableStyle([
                ("BOX", (0,0), (-1,-1), 0.8, colors.black),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("LEFTPADDING", (0,0), (-1,-1), 3),
                ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ]))
            abrev_t.wrapOn(canv, w, 0)
            abrev_t.drawOn(canv, x0, 15*mm + t._height + 0.5*mm)
    
    # ---------------- helpers de secciones ----------------
    def _section_box(self, title, rows, with_obs, total_w, row_height=None, compact_padding=False, allow_split=True):
        """
        Crea una tabla de sección.
        row_height: altura de fila personalizada (default: 7*mm)
        compact_padding: si True, usa padding reducido (default: False)
        allow_split: si True, permite dividir la tabla entre páginas (default: True)
        """
        if row_height is None:
            row_height = 7*mm
        cols = [total_w*0.7, total_w*0.3] if with_obs else [total_w]
        data = [[title, "OBSERVACIONES"]] if with_obs else [[title]]
        for r in rows:
            data.append([r, ""] if with_obs else [r])
        
        # Altura de filas: todas iguales excepto la primera (título) que puede ser un poco más alta
        row_heights = [row_height] * len(data)
        if len(data) > 1:
            row_heights[0] = row_height  # Título con misma altura para compactar
        
        # Permitir división de tabla entre páginas si allow_split es True.
        # repeatRows=1 mantiene el título cuando se divide.
        # rowSplitRange evita que se parta justo después del título: así el título
        # siempre viaja con la primera fila de contenido.
        row_split_range = None
        if allow_split and len(data) > 2:
            row_split_range = (2, len(data) - 1)

        t = Table(data, colWidths=cols, rowHeights=row_heights, 
                 repeatRows=1 if allow_split and len(data) > 1 else 0,
                 splitByRow=1 if allow_split else 0,
                 rowSplitRange=row_split_range)
        
        padding = 2 if compact_padding else 4
        # Padding vertical más reducido para bloques compactos
        top_padding = 0.5 if compact_padding else 2
        bottom_padding = 0.5 if compact_padding else 2
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.6, colors.black),
            ("FONT", (0,0), (-1,-1), "Helvetica", 9),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 9),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), padding),
            ("RIGHTPADDING", (0,0), (-1,-1), padding),
            ("TOPPADDING", (0,0), (-1,-1), top_padding),
            ("BOTTOMPADDING", (0,0), (-1,-1), bottom_padding),
        ]))
        return t

    def _section_box_with_columns(self, title, rows_data, total_w, row_height=None, compact_padding=False,
                                  allow_split=True):
        """
        Crea una tabla de sección con 4 columnas: Item, Aplica, Satisfactorio, Observaciones.
        rows_data: lista de diccionarios con 'item', 'aplica', 'resultado', 'observacion'
        """
        # Estilo para el texto de las filas
        body_style = ParagraphStyle(
            "TableBodySmall",
            fontName="Helvetica",
            fontSize=9,
            leading=11,
        )

        if row_height is None:
            row_height = 7 * mm

        # Texto: ~48%, Aplica: ~4%, Satisfactorio: ~4%, Observaciones: ~44%
        cols = [total_w * 0.48, total_w * 0.04, total_w * 0.04, total_w * 0.44]

        # Encabezado
        data = [[title, "", "", "OBSERVACIONES"]]

        # Filas de datos
        for row in rows_data:
            item = row.get('item', '')
            aplica = row.get('aplica', '')
            resultado = row.get('resultado', '')
            observacion = row.get('observacion', '')

            aplica_abrev = self._abreviar_aplica(aplica)
            resultado_abrev = self._abreviar_resultado(resultado)

            # Paragraph para permitir salto de línea y ajuste de altura
            item_cell = Paragraph(item, body_style) if item else ""
            obs_cell = Paragraph(observacion, body_style) if observacion else ""

            data.append([item_cell, aplica_abrev, resultado_abrev, obs_cell])

        # Altura de filas: encabezado fijo, resto automática
        row_heights = [row_height] + [None] * (len(data) - 1)

        row_split_range = None
        if allow_split and len(data) > 2:
            row_split_range = (2, len(data) - 1)

        t = Table(
            data,
            colWidths=cols,
            rowHeights=row_heights,
            repeatRows=1 if allow_split and len(data) > 1 else 0,
            splitByRow=1 if allow_split else 0,
            rowSplitRange=row_split_range,
        )

        padding = 2 if compact_padding else 4
        top_padding = 0.5 if compact_padding else 2
        bottom_padding = 0.5 if compact_padding else 2

        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("ALIGN", (2, 0), (2, 0), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (0, -1), padding),
            ("RIGHTPADDING", (0, 0), (0, -1), 1),
            ("LEFTPADDING", (1, 0), (2, -1), 1),
            ("RIGHTPADDING", (1, 0), (2, -1), 1),
            ("LEFTPADDING", (3, 0), (3, -1), padding),
            ("RIGHTPADDING", (3, 0), (3, -1), padding),
            ("TOPPADDING", (0, 0), (-1, -1), top_padding),
            ("BOTTOMPADDING", (0, 0), (-1, -1), bottom_padding),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        return t

    def _abreviar_aplica(self, aplica: str) -> str:
        """Abrevia el valor de aplica a siglas cortas"""
        aplica_upper = aplica.upper().strip()
        if 'NO APLICA' in aplica_upper or aplica_upper == 'N.A' or aplica_upper == 'NA':
            return 'N.A'
        elif 'APLICA' in aplica_upper or aplica_upper == 'A':
            return 'A'
        elif 'FUERA DE ALCANCE' in aplica_upper or 'F.A' in aplica_upper or aplica_upper == 'FA':
            return 'F.A'
        else:
            return aplica[:5]  # Limitar a 5 caracteres si no coincide
    
    def _abreviar_resultado(self, resultado: str) -> str:
        """Abrevia el valor de resultado a siglas cortas"""
        resultado_upper = resultado.upper().strip()
        if 'NO SATISFACTORIO' in resultado_upper or 'NO SATISFACTORIA' in resultado_upper or resultado_upper == 'N.S':
            return 'N.S'
        elif 'SATISFACTORIO' in resultado_upper or 'SATISFACTORIA' in resultado_upper or resultado_upper == 'S':
            return 'S'
        elif 'NO APLICA' in resultado_upper or resultado_upper == 'N.A' or resultado_upper == 'NA':
            return 'N.A'
        elif 'FUERA DE ALCANCE' in resultado_upper or 'F.A' in resultado_upper or resultado_upper == 'FA':
            return 'F.A'
        else:
            return resultado[:5]  # Limitar a 5 caracteres si no coincide
    
    def _abreviar_calificacion(self, calificacion: str) -> str:
        """
        Abrevia la calificación a solo las siglas (C, C(xR), NC, RI).
        """
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
        elif cal_upper.startswith('NC') or 'NO CONFORME' in cal_upper:
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
        color_conforme = colors.HexColor('#00b050')  # Verde conforme
        color_conforme_reparacion = colors.HexColor('#96ce50')  # Verde conforme luego por reparación
        color_no_conforme = colors.HexColor('#ff0400')  # Rojo no conforme
        color_re_inspeccionar = colors.HexColor('#feff01')  # Amarillo re inspeccionar
        
        # Detectar el tipo de calificación
        # Orden importante: primero las más específicas
        if ('C(' in cal_upper and 'R)' in cal_upper) or 'CX' in cal_upper or 'CONFORME LUEGO' in cal_upper or 'CONFORME DESPUES' in cal_upper:
            return color_conforme_reparacion
        elif cal_upper.startswith('NC') or 'NO CONFORME' in cal_upper:
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
        Retorna dos tablas apiladas: Convención de DISCONTINUIDAD y Calificación (CAL).
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
            ["C(xR):", "Conforme Luego de Reparación"],
            ["NC:", "No Conforme"],
            ["RI:", "Re Inspeccionar"],
        ]
        
        # Colores para calificaciones
        color_conforme = colors.HexColor('#00b050')  # Verde conforme
        color_conforme_reparacion = colors.HexColor('#96ce50')  # Verde conforme luego por reparación
        color_no_conforme = colors.HexColor('#ff0400')  # Rojo no conforme
        color_re_inspeccionar = colors.HexColor('#feff01')  # Amarillo re inspeccionar
        
        # Tabla 1: Convención de DISCONTINUIDAD
        discon_col_w = total_w / 3.0
        discon_data = [["Convención de discontinuidad:", "", ""]]
        discon_data.extend(disconformidades_data)
        discon_table = Table(discon_data, colWidths=[discon_col_w] * 3)
        discon_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.6, colors.black),
            ("FONT", (0,0), (-1,-1), "Helvetica", 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 7),
            ("SPAN", (0,0), (2,0)),
            ("ALIGN", (0,0), (2,0), "CENTER"),
        ]))

        # Tabla 2: Calificación (CAL) con una sola fila de estados
        cal_col_w = total_w / 4.0
        cal_row = [
            calificaciones_data[0][0] + " " + calificaciones_data[0][1],
            calificaciones_data[1][0] + " " + calificaciones_data[1][1],
            calificaciones_data[2][0] + " " + calificaciones_data[2][1],
            calificaciones_data[3][0] + " " + calificaciones_data[3][1],
        ]
        cal_data = [["Calificación (CAL)", "", "", ""], cal_row]
        cal_table = Table(cal_data, colWidths=[cal_col_w] * 4)
        cal_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.6, colors.black),
            ("FONT", (0,0), (-1,-1), "Helvetica", 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 7),
            ("SPAN", (0,0), (3,0)),
            ("ALIGN", (0,0), (3,0), "CENTER"),
            ("BACKGROUND", (0,1), (0,1), color_conforme),
            ("BACKGROUND", (1,1), (1,1), color_conforme_reparacion),
            ("BACKGROUND", (2,1), (2,1), color_no_conforme),
            ("BACKGROUND", (3,1), (3,1), color_re_inspeccionar),
        ]))

        # Un solo contenedor no-divisible para evitar problemas de wrap con KeepTogether
        leyenda = Table(
            [[discon_table], [cal_table]],
            colWidths=[total_w],
            splitByRow=0,
            splitInRow=0,
        )
        leyenda.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return leyenda

    def _section_text_box(self, title, text, total_w):
        rows = [text] if isinstance(text, str) else text
        return self._section_box(title, rows, False, total_w)

    def _build_reportlab_image(self, source, max_width, max_height):
        """
        Construye una imagen de ReportLab desde:
        - ruta de archivo
        - bytes/bytearray
        - UploadedFile (Streamlit) u objeto file-like
        """
        if source is None:
            raise ValueError("Fuente de imagen vacía")

        if isinstance(source, (bytes, bytearray)):
            img = Image(BytesIO(bytes(source)))
        elif hasattr(source, "getvalue"):
            # UploadedFile de Streamlit ofrece getvalue() en bytes.
            img = Image(BytesIO(source.getvalue()))
        elif hasattr(source, "read"):
            pos = None
            if hasattr(source, "tell"):
                try:
                    pos = source.tell()
                except Exception:
                    pos = None
            if hasattr(source, "seek"):
                try:
                    source.seek(0)
                except Exception:
                    pass
            img_bytes = source.read()
            if pos is not None and hasattr(source, "seek"):
                try:
                    source.seek(pos)
                except Exception:
                    pass
            img = Image(BytesIO(img_bytes))
        else:
            img = Image(source)

        img.hAlign = "CENTER"
        img._restrictSize(max_width, max_height)
        return img

    def _foto_cell(self, registro: Dict[str, Any], idx: int, col_w: float, styles) -> Table:
        inner_w = col_w - 8*mm
        max_img_h = 45*mm
        try:
            img = self._build_reportlab_image(registro.get("archivo"), inner_w, max_img_h)
        except Exception:
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

    def _esquema_cell(
            self,
            esquema_item: Dict[str, Any],
            idx: int,
            col_w: float,
            styles,
            full_page: bool = False,  # ← nuevo flag
    ) -> Table:
        """Crea una celda para mostrar una imagen del esquema"""
        inner_w = col_w - 8 * mm

        # Si es full_page, limitamos la altura al área útil real del frame.
        # Con este template (encabezado + footer), 180-200 mm excede la zona
        # disponible y provoca "Flowable ... too large" en ReportLab.
        if full_page:
            max_img_h = 120 * mm
            max_frame_h = 145 * mm
        else:
            max_img_h = 45 * mm
            max_frame_h = 70 * mm

        try:
            img = self._build_reportlab_image(esquema_item.get("archivo"), inner_w, max_img_h)
        except Exception:
            img = Box(inner_w, max_img_h, f"ESQUEMA {idx}")

        titulo = Paragraph(f"<b>Esquema {idx}</b>", styles["Body"])
        comentario = Paragraph(esquema_item.get("comentario", ""), styles["Body"])

        col = KeepInFrame(
            maxWidth=inner_w,
            maxHeight=max_frame_h,  # usamos el alto según el modo
            content=[img, Spacer(0, 2 * mm), titulo, comentario],
            mode="shrink",
        )

        cell = Table([[col]], colWidths=[col_w])
        cell.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        cell.splitByRow = 0
        cell.splitInRow = 0
        return cell

    def _build_story(self, data, total_w, bloques=None):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="HSection", fontName="Helvetica-Bold", fontSize=10, spaceBefore=6, spaceAfter=4))
        styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=9, leading=12))
        styles.add(ParagraphStyle(name="LegendNextPageNote", fontName="Helvetica-Bold", fontSize=9, alignment=1, spaceAfter=2))

        story = []

        # 1. Normas
        story.append(self._section_text_box("1. NORMAS PARA EL CRITERIO DE EVALUACIÓN:", data["seccion_1_normas"]["criterio"], total_w))
        story.append(Spacer(0, 6*mm))

        # 2. Procedimiento (Información General)
        procedimiento_text = f"Procedimiento: {data.get('procedimiento', 'TLPR0025 - Inspección Visual - Rev. 1')}"
        story.append(self._section_text_box("2. PROCEDIMIENTO:", procedimiento_text, total_w))
        story.append(Spacer(0, 6*mm))

        # 3. Equipos
        story.append(self._section_text_box("3. EQUIPOS UTILIZADOS", ", ".join(data["seccion_2_equipos"]), total_w))
        story.append(Spacer(0, 6*mm))

        # 4. Material base
        story.append(self._section_text_box("4. MATERIAL BASE:", data["seccion_3_material_base"], total_w))
        story.append(Spacer(0, 6*mm))

        # 5+. Fases de inspección (compactas, sin espacios entre ellas)
        fases = data.get("fases_inspeccion", {})
        seccion = 5

        # Configuración compacta para bloques 5, 6 y 7: filas más delgadas y padding reducido
        # Reducido a 4mm para maximizar el espacio y que quepa todo en una página
        compact_row_height = 4*mm

        # Marcar que las páginas con estas secciones necesitan abreviaciones
        has_fases = fases.get('antes_soldadura') or fases.get('inicio_junta') or fases.get('despues_soldadura')
        if has_fases:
            story.append(MarkAbbreviationPage())

        if fases.get('antes_soldadura'):
            # Usar la nueva función con 4 columnas: Item, Aplica, Satisfactorio, Observaciones
            story.append(self._section_box_with_columns(
                f"{seccion}. ANTES DE INICIAR EL PROCESO DE SOLDADURA", 
                fases['antes_soldadura'], 
                total_w,
                row_height=compact_row_height, 
                compact_padding=True
            ))
            # Sin Spacer - pegado al siguiente bloque
            seccion += 1

        if fases.get('inicio_junta'):
            # Usar la nueva función con 4 columnas: Item, Aplica, Satisfactorio, Observaciones
            story.append(self._section_box_with_columns(
                f"{seccion}. INICIO DE LA SOLDADURA", 
                fases['inicio_junta'], 
                total_w,
                row_height=compact_row_height, 
                compact_padding=True
            ))
            # Sin Spacer - pegado al siguiente bloque
            seccion += 1

        if fases.get('despues_soldadura'):
            # Usar la nueva función con 4 columnas: Item, Aplica, Satisfactorio, Observaciones
            story.append(self._section_box_with_columns(
                f"{seccion}. DESPUÉS DE LA SOLDADURA", 
                fases['despues_soldadura'], 
                total_w,
                row_height=compact_row_height, 
                compact_padding=True
            ))
            # Spacer solo después del último bloque de fases
            story.append(Spacer(0, 6*mm))
            seccion += 1

        # Esquema (antes de elementos inspeccionados)
        esquema = data.get("esquema", [])
        esquema_imgs = [e for e in esquema if isinstance(e, dict) and e.get("archivo")]
        if esquema_imgs:
            story.append(Paragraph(f"{seccion}. ESQUEMA ESTRUCTURA INSPECCIONADA:", styles["HSection"]))
            story.append(Spacer(0, 2 * mm))

            col_w = total_w
            for idx, esquema_item in enumerate(esquema_imgs, start=1):
                # Una imagen por fila con ancho completo.
                # El cell encapsula imagen + título + comentario para evitar separación.
                cell = self._esquema_cell(esquema_item, idx, col_w, styles, full_page=True)
                story.append(cell)
            story.append(Spacer(0, 6 * mm))
            seccion += 1

        # Detalle de resultados (antes de elementos inspeccionados)
        detalle = data.get("detalle_resultados", "")
        if detalle and detalle.strip():
            story.append(CondPageBreak(18 * mm))
            story.append(Paragraph(f"{seccion}. DETALLE DE ELEMENTOS INSPECCIONADOS Y RESULTADOS:", styles["HSection"]))
            detalle_formatted = detalle.replace("\r\n", "<br/>").replace("\n", "<br/>").replace("\r", "<br/>")
            story.append(Paragraph(detalle_formatted, styles["Body"]))
            story.append(Spacer(0, 6*mm))
            seccion += 1

        # Elementos inspeccionados
        elems = data.get("elementos_inspeccionados", [])
        if elems:
            # Reservar espacio para: título + encabezado + primera fila.
            story.append(CondPageBreak(26 * mm))
            story.append(Paragraph(f"{seccion}. ELEMENTOS INSPECCIONADOS:", styles["HSection"]))

            # Estilo para el texto de las celdas (con wrap)
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
            # Guardar las calificaciones completas para aplicar colores después
            # Pero mostrar solo las siglas en la tabla
            calificaciones = []
            for e in elems:
                cal_completa = e.get('calificacion', 'Satisfactorio')
                cal_abreviada = self._abreviar_calificacion(cal_completa)
                calificaciones.append(cal_completa)  # Guardar completa para el color

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

            # Usar total_w para que tenga el mismo ancho que los otros bloques
            # Calificación reducida para solo mostrar siglas (C, C(xR), NC, RI)
            col_widths = [
                total_w * 0.079,  # No. (~15/190)
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
                rowSplitRange=row_split_range,
            )

            # Estilos base
            style_list = [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),  # solo encabezado
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),  # cuerpo
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                # por si acaso
                ("WORDWRAP", (0, 0), (-1, -1), True),
            ]

            # Aplicar colores a la columna de calificación (columna índice 3)
            # La fila 0 es el encabezado, así que empezamos desde la fila 1
            for idx, cal in enumerate(calificaciones, start=1):
                color = self._obtener_color_calificacion(cal)
                style_list.append(("BACKGROUND", (3, idx), (3, idx), color))

            t.setStyle(TableStyle(style_list))
            story.append(t)
            # Agregar leyenda de disconformidades debajo de la tabla
            leyenda = self._crear_leyenda_disconformidades(total_w)
            story.append(LegendWithNextPageNote(leyenda, styles["LegendNextPageNote"], spacer_h=3 * mm))
            story.append(Spacer(0, 6 * mm))
            seccion += 1

        # Observaciones generales
        obs = data.get("observaciones_generales", "")
        if obs and obs.strip():
            story.append(CondPageBreak(18 * mm))
            story.append(Paragraph(f"{seccion}. OBSERVACIONES GENERALES:", styles["HSection"]))
            obs_formatted = obs.replace("\r\n", "<br/>").replace("\n", "<br/>").replace("\r", "<br/>")
            story.append(Paragraph(obs_formatted, styles["Body"]))
            story.append(Spacer(0, 6*mm))
            seccion += 1

        # Registro fotográfico (cuadrícula 2xN)
        regs = data.get("registros_fotograficos", [])
        imgs = [r for r in regs if isinstance(r, dict) and r.get("archivo")]

        story.append(CondPageBreak(30 * mm))
        story.append(Paragraph(f"{seccion}. REGISTRO FOTOGRÁFICO:", styles["HSection"]))

        if imgs:
            col_w = total_w / 2.0
            rows = []
            odd_last_row = False
            idx = 1
            for i in range(0, len(imgs), 2):
                left = self._foto_cell(imgs[i], idx, col_w, styles); idx += 1
                if i + 1 < len(imgs):
                    right = self._foto_cell(imgs[i+1], idx, col_w, styles); idx += 1
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

    def _crear_seccion_firmas(self, total_w, encabezado):
        """
        Crea la sección de firmas y sello al final del informe.
        Incluye espacios para Elaboró, Revisó, sello/logo, nombre de empresa y cliente.
        Versión compacta para la parte inferior de la última página.
        """
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        
        # Estilos más compactos
        style_label = ParagraphStyle(
            name="FirmaLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9
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
            fontSize=10,
            leading=11,
            alignment=1  # CENTER
        )
        style_client = ParagraphStyle(
            name="ClientName",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=1  # CENTER
        )
        
        # Obtener datos del encabezado
        elaboro_nombre = encabezado.get("elaboro", "")
        reviso_nombre = encabezado.get("reviso", "")
        firma_elaboro_path = encabezado.get("firma_elaboro_path", "")
        firma_reviso_path = encabezado.get("firma_reviso_path", "")
        cliente_nombre = encabezado.get("cliente", "Concreacero")
        
        # Altura reducida para las secciones de firma
        altura_firma = 15*mm
        
        # Crear caja para el sello/logo más pequeña
        sello_box = Box(15*mm, 12*mm, "SELLO")
        
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
        # Columna Elaboró: solo espacio para firma (sin nombre)
        espacio_firma_elaboro = self._firma_flowable(firma_elaboro_path, 45.5*mm, 13*mm)
        celda_elaboro = Table([
            [espacio_firma_elaboro],
        ], colWidths=[col_elaboro - 6*mm], splitByRow=0, splitInRow=0)
        celda_elaboro.setStyle(TableStyle([
            ("LEFTPADDING", (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ]))
        
        # Columna Revisó: espacios para sello, NIT y firma (sin cuadros ni texto)
        espacio_sello = EspacioFirma(15*mm, 12*mm)
        espacio_nit = EspacioFirma(15*mm, 4*mm)
        espacio_firma_reviso = self._firma_flowable(firma_reviso_path, 45.5*mm, 13*mm)
        
        # Tabla interna más compacta
        celda_reviso_interna = Table([
            [espacio_sello, espacio_firma_reviso],  # Espacio para sello y espacio para firma (sin cajas)
            [espacio_nit, Paragraph("", style_name)],  # Espacio para NIT (sin texto)
            [Paragraph("", style_name), Paragraph("", style_name)],  # Nombre del revisor (vacío)
        ], colWidths=[15*mm, col_reviso - 22*mm], splitByRow=0, splitInRow=0)
        celda_reviso_interna.setStyle(TableStyle([
            ("LEFTPADDING", (0,0), (-1,-1), 1),
            ("RIGHTPADDING", (0,0), (-1,-1), 1),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        
        fila2 = [
            celda_elaboro,
            celda_reviso_interna,
            Paragraph("", style_name)  # Columna cliente vacía
        ]

        # Fila 3: Nombres centrados de personas
        fila3 = [
            Paragraph(elaboro_nombre, style_name_center),
            Paragraph(reviso_nombre, style_name_center),
            Paragraph("", style_name)
        ]
        
        # Fila 4: Nombre de la empresa (spanning 2 columnas: Elaboró y Revisó)
        empresa_text = Paragraph("Joint and Welding Ingenieros S.A.S.", style_company)
        fila4 = [
            empresa_text,
            Paragraph("", style_name),  # Columna revisó vacía (será spanneada)
            Paragraph("", style_name)  # Columna cliente vacía
        ]
        
        # Crear tabla principal con alturas de fila reducidas
        data = [fila1, fila2, fila3, fila4]
        row_heights = [6*mm, altura_firma + 2*mm, 6*mm, 5*mm]
        t = Table(
            data,
            colWidths=[col_elaboro, col_reviso, col_cliente],
            rowHeights=row_heights,
            splitByRow=0,
            splitInRow=0,
        )
        
        # Estilos de la tabla más compactos
        t.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.8, colors.black),
            ("LINEAFTER", (1,0), (1,-1), 0.8, colors.black),
            ("LINEABOVE", (0,3), (1,3), 0.8, colors.black),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
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
    
    def verificar_datos_disponibles(self) -> bool:
        return 'bloque_2_1' in st.session_state
