import streamlit as st
import os
from reportes import (
    ReporteInspeccionVisual,
    ReporteLiquidosPenetrantes,
    ReporteParticulasMagneticas,
    ReporteUltrasonido
)
from utils import build_unique_report_filename

st.title("📄 Generación de Reportes")

# Modo de prueba: restringe la generación exclusivamente a Inspección Visual
SOLO_REPORTE_VISUAL = True

# Definir tipos de reportes disponibles
tipos_reportes = {
    "visual": {
        "nombre": "Inspección Visual",
        "modulo": "2_datos_de_inspeccion_visual.py",
        "icono": "👁️",
        "descripcion": "Inspección visual de superficies y estructuras",
        "clase": ReporteInspeccionVisual
    },
    "liquidos_penetrantes": {
        "nombre": "Líquidos Penetrantes", 
        "modulo": "3_datos_de_inspeccion_de_liquidos_penetrantes.py",
        "icono": "💧",
        "descripcion": "Inspección mediante líquidos penetrantes",
        "clase": ReporteLiquidosPenetrantes
    },
    "particulas_magneticas": {
        "nombre": "Partículas Magnéticas",
        "modulo": "4_datos_de_inspeccion_de_particulas_magneticas.py", 
        "icono": "🧲",
        "descripcion": "Inspección mediante partículas magnéticas",
        "clase": ReporteParticulasMagneticas
    },
    "ultrasonido": {
        "nombre": "Ultrasonido",
        "modulo": "5_datos_de_inspeccion_de_ultrasonido.py",
        "icono": "🔊", 
        "descripcion": "Inspección mediante ultrasonido",
        "clase": ReporteUltrasonido
    }
}

# Mostrar selector de tipo de reporte
st.subheader("📋 Seleccionar Tipo de Reporte")

# Verificar qué tipos están disponibles
tipos_disponibles = []
for tipo, info in tipos_reportes.items():
    # Crear instancia temporal para verificar disponibilidad
    reporte_temp = info["clase"]()
    if reporte_temp.verificar_datos_disponibles():
        tipos_disponibles.append(tipo)

# Aplicar restricción global para corridas de prueba
if SOLO_REPORTE_VISUAL:
    tipos_disponibles = [tipo for tipo in tipos_disponibles if tipo == "visual"]

if not tipos_disponibles:
    st.warning("⚠️ No hay datos disponibles para generar reportes.")
    if SOLO_REPORTE_VISUAL:
        st.info("💡 En modo de prueba, solo se permite generar Inspección Visual. Complete ese módulo para continuar.")
    else:
        st.info("💡 Complete los datos en los módulos correspondientes antes de generar un reporte.")
else:
    if SOLO_REPORTE_VISUAL:
        st.info("🧪 Modo de prueba activo: solo está habilitado el informe de Inspección Visual.")

    # Crear selector de tipo de reporte
    tipo_seleccionado = st.selectbox(
        "Seleccione el tipo de reporte a generar:",
        options=tipos_disponibles,
        format_func=lambda x: f"{tipos_reportes[x]['icono']} {tipos_reportes[x]['nombre']}",
        help="Seleccione el tipo de inspección para el cual desea generar el reporte"
    )
    
    if tipo_seleccionado:
        info_tipo = tipos_reportes[tipo_seleccionado]
        
        # Mostrar información del tipo seleccionado
        st.info(f"""
        **{info_tipo['icono']} {info_tipo['nombre']}**
        
        {info_tipo['descripcion']}
        
        Módulo de datos: `{info_tipo['modulo']}`
        """)
        
        # Generación y previsualización automática del reporte
        with st.spinner(f"Preparando previsualización en tiempo real del reporte..."):
            try:
                # Salvaguarda extra en caso de manipulación manual del estado
                if SOLO_REPORTE_VISUAL and tipo_seleccionado != "visual":
                    st.error("❌ En modo de prueba solo se puede generar el reporte de Inspección Visual.")
                    st.stop()

                # Crear instancia del reporte específico
                reporte = info_tipo["clase"]()
                
                # Generar el reporte
                output_filename = build_unique_report_filename(tipo_seleccionado)
                output_path = reporte.generar_reporte(output_filename)
                
                # Leer el archivo generado
                try:
                    with open(output_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                finally:
                    try:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    except OSError:
                        pass
                
                # Construir el nombre base del reporte
                from utils import generar_numero_informe, obtener_consecutivo_por_tipo
                num_informe_base = "Informe"
                if "datos_proyecto" in st.session_state:
                    dp = st.session_state.datos_proyecto
                    num_ord = dp.get("numero_orden", "")
                    cons = dp.get("consecutivo_inicial", "")
                    fecha = dp.get("fecha_obj", None) or dp.get("fecha", None)
                    year = None
                    if hasattr(fecha, 'year'):
                        year = fecha.year
                    elif isinstance(fecha, str):
                        try:
                            year = int(fecha.split("-")[0])
                        except Exception:
                            pass
                    offset = obtener_consecutivo_por_tipo(tipo_seleccionado)
                    if num_ord and cons:
                        num_informe_base = generar_numero_informe(num_ord, cons, year=year, offset=offset)
                
                pdf_download_name = f"{num_informe_base}.pdf"
                zip_download_name = f"{num_informe_base}.zip"

                # Generar el ZIP que contiene el PDF + los datos del estado e imágenes
                from persistencia import generar_zip_completo
                zip_bytes = generar_zip_completo(pdf_bytes, pdf_download_name)
                
                # Mostrar botones de acción y la previsualización
                col_acc1, col_acc2 = st.columns([1, 1])
                with col_acc1:
                    st.download_button(
                        label=f"📥 Descargar Informe Completo (ZIP + PDF)",
                        data=zip_bytes,
                        file_name=zip_download_name,
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
                with col_acc2:
                    if st.button("🔄 Actualizar Vista Previa", use_container_width=True):
                        st.rerun()

                st.subheader("👀 Previsualización del PDF")
                
                # Renderizar páginas del PDF como imágenes de alta resolución usando PyMuPDF
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    for i, page in enumerate(doc):
                        # Matrix zoom = 2.0x para que la resolución del texto sea muy nítida
                        zoom = 2.0
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat)
                        img_bytes = pix.tobytes("png")
                        
                        st.markdown(f"**Página {i+1} de {len(doc)}**")
                        st.image(img_bytes, use_container_width=True)
                except Exception as img_err:
                    # Fallback alternativo al iframe base64 en caso de fallar PyMuPDF
                    import base64
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" style="border: none; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ Error al generar la previsualización del reporte: {str(e)}")
                st.write("**Posibles causas:**")
                st.write("- Falta de datos en los módulos correspondientes")
                st.write("- Error en la estructura de datos")
                st.write("- Problema con las dependencias")

# Información adicional
with st.expander("ℹ️ Información sobre los Reportes", expanded=False):
    st.write("""
    **Tipos de Reportes Disponibles:**
    
    - **👁️ Inspección Visual:** Para inspección visual de superficies y estructuras
    - **💧 Líquidos Penetrantes:** Para detectar discontinuidades superficiales
    - **🧲 Partículas Magnéticas:** Para detectar discontinuidades en materiales ferromagnéticos
    - **🔊 Ultrasonido:** Para detectar discontinuidades internas
    
    **Nota:** Solo se muestran los tipos de reportes para los cuales hay datos disponibles.
    """)

# Debug opcional
if st.checkbox("🔧 Modo Debug (Mostrar información técnica)", False):
    st.write("**Información Técnica:**")
    st.write(f"- Tipos disponibles: {tipos_disponibles}")
    st.write("- Módulos de reportes específicos:")
    for tipo, info in tipos_reportes.items():
        reporte_temp = info["clase"]()
        disponible = reporte_temp.verificar_datos_disponibles()
        st.write(f"  - {info['nombre']}: {'✅' if disponible else '❌'}")
    st.write("- Módulo de reportes: `reportes/`")
