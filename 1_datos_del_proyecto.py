import streamlit as st
from datetime import datetime
from utils import cargar_inspectores, cargar_normas, generar_numero_informe
from save_state import persist_session_state, clear_persisted_state
from signature_registry import get_signature_for_person


def formatear_fecha_para_display(fecha):
    """Convierte un objeto date a formato DD/MMM/YYYY"""
    if hasattr(fecha, 'strftime'):
        meses_abrev = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN',
                      'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
        return f"{fecha.day:02d}/{meses_abrev[fecha.month-1]}/{fecha.year}"
    return str(fecha)

# Estilo personalizado restaurado
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        border-bottom: none !important;
        box-shadow: none !important;
    }
    .stTabs {
        border-bottom: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stTabs"] > div {
        border-bottom: none !important;
        box-shadow: none !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 4rem;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        gap: 1rem;
        padding-top: 10px;
        padding-bottom: 10px;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border: none;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background: none !important;
        height: 0px !important;
    }
    .stProgress > div > div > div {
        background-color: #4CAF50;
    }
    .module-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #e9ecef;
    }
    .module-card:hover {
        border-color: #4CAF50;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stTabs div, .stTabs [data-baseweb="tab-list"], .stTabs, div[data-testid="stTabs"], div[data-testid="stTabs"] > div {
        border-bottom: none !important;
        box-shadow: none !important;
    }
    
    </style>
""", unsafe_allow_html=True)

# Título principal con icono y descripción
st.title("📋 Datos del Proyecto")
st.markdown("Configure los detalles de su informe y seleccione los módulos necesarios para su inspección.")

# Modo de prueba: restringe la interfaz y configuración al módulo de Inspección Visual
SOLO_REPORTE_VISUAL = True

# Barra de progreso
if "bloque_1" in st.session_state:
    progress = 100
else:
    progress = 0
st.progress(progress/100)

# Crear pestañas para organizar la información
tab1, tab2, tab3 = st.tabs(["📝 Datos del Proyecto", "⚙️ Configuración de Módulos", "📂 Guardar/Cargar Informe"])

# Definir módulos disponibles
modulos_disponibles = {
    "Inspección Visual": {
        "archivo": "2_datos_de_inspeccion_visual.py",
        "descripcion": "Inspección visual detallada de superficies y estructuras",
        "icono": "👁️",
        "titulo_sidebar": "Datos de Inspección Visual"
    },
    "Líquidos Penetrantes": {
        "archivo": "3_datos_de_inspeccion_de_liquidos_penetrantes.py",
        "descripcion": "Inspección mediante líquidos penetrantes para detectar discontinuidades superficiales",
        "icono": "💧",
        "titulo_sidebar": "Inspección de Líquidos Penetrantes"
    },
    "Partículas Magnéticas": {
        "archivo": "4_datos_de_inspeccion_de_particulas_magneticas.py",
        "descripcion": "Inspección mediante partículas magnéticas para detectar discontinuidades en materiales ferromagnéticos",
        "icono": "🧲",
        "titulo_sidebar": "Inspección de Partículas Magnéticas"
    },
    "Ultrasonido": {
        "archivo": "5_datos_de_inspeccion_de_ultrasonido.py",
        "descripcion": "Inspección mediante ondas ultrasónicas para detectar discontinuidades internas",
        "icono": "📡",
        "titulo_sidebar": "Inspección de Ultrasonido"
    }
}

# Módulos seleccionados por defecto
modulos_default = ["Inspección Visual", "Líquidos Penetrantes"]
if SOLO_REPORTE_VISUAL:
    modulos_default = ["Inspección Visual"]

with tab1:
    # Usar valores guardados si existen, si no usar por defecto
    def_valores = {
        "cliente": "",
        "proyecto": "",
        "subproyecto": "",
        "contratista": "",
        "numero_orden": "",
        "consecutivo_inicial": "",
        "elaboro": "",
        "norma_global": "",
        "fecha": datetime.now().date(),
        "lugar": "",
        "firma_1": "",
        "firma_2": "",
        "modulos_seleccionados": modulos_default
    }

    if "bloque_1" in st.session_state:
        valores = st.session_state.bloque_1.copy()
        if "firmas" in valores:
            valores["firma_1"] = valores["firmas"].get("firma_1", valores.get("elaboro", def_valores["firma_1"]))
            valores["firma_2"] = valores["firmas"].get("firma_2", def_valores["firma_2"])
    else:
        valores = def_valores.copy()
        # Inicializar la configuración de páginas
        st.session_state.pages_config = {
            "modulos": [
                st.Page(modulos_disponibles[modulo]["archivo"], title=modulos_disponibles[modulo]["titulo_sidebar"])
                for modulo in modulos_default
            ]
        }

    # Crear columnas para los campos del formulario
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📌 Información General")
        with st.container():
            cliente = st.text_input("Cliente", valores["cliente"], help="Nombre del cliente o empresa")
            proyecto = st.text_input("Proyecto", valores["proyecto"], help="Nombre del proyecto")
            subproyecto = st.text_input("Subproyecto", valores["subproyecto"], help="Nombre del subproyecto o área específica")
            contratista = st.text_input("Contratista", valores["contratista"], help="Nombre de la empresa contratista")
            
            # Numeración de informes
            st.markdown("---")
            st.markdown("**📋 Numeración de Informes**")
            col_orden, col_consec = st.columns(2)
            with col_orden:
                numero_orden = st.text_input(
                    "Número de Orden", 
                    valores.get("numero_orden", ""), 
                    help="Número de orden. Ej: 209"
                )
            with col_consec:
                consecutivo_inicial = st.text_input(
                    "Consecutivo Inicial", 
                    valores.get("consecutivo_inicial", ""), 
                    help="Consecutivo del informe visual (3 dígitos). Ej: 462"
                )
            
            # Mostrar vista previa de los números de informe
            if numero_orden and consecutivo_inicial:
                try:
                    year = datetime.now().year
                    st.info(
                        f"**Vista previa de números de informe:**\n\n"
                        f"- 👁️ Visual: `{generar_numero_informe(numero_orden, consecutivo_inicial, year, 0)}`\n"
                        f"- 💧 Líquidos: `{generar_numero_informe(numero_orden, consecutivo_inicial, year, 1)}`\n"
                        f"- 🧲 Partículas: `{generar_numero_informe(numero_orden, consecutivo_inicial, year, 2)}`\n"
                        f"- 📡 Ultrasonido: `{generar_numero_informe(numero_orden, consecutivo_inicial, year, 3)}`"
                    )
                except (ValueError, TypeError):
                    st.warning("⚠️ Por favor ingrese números válidos")

    with col2:
        st.subheader("📋 Detalles del Informe")
        with st.container():
            # Cargar lista de inspectores desde CSV
            inspectores = cargar_inspectores()
            opciones_inspectores = [""] + inspectores
            elaboro_actual = valores.get("elaboro", "")
            elaboro_index = opciones_inspectores.index(elaboro_actual) if elaboro_actual in opciones_inspectores else 0
            elaboro = st.selectbox("Elaboró", options=opciones_inspectores, index=elaboro_index, help="Nombre del inspector que elabora el informe")
            # Cargar lista de normas desde CSV
            normas = cargar_normas()
            opciones_normas = [""] + normas
            norma_actual = valores.get("norma_global", "")
            norma_index = opciones_normas.index(norma_actual) if norma_actual in opciones_normas else 0
            norma_global = st.selectbox("Norma global", options=opciones_normas, index=norma_index, help="Norma de referencia para la inspección")
            st.session_state["norma_global"] = norma_global
            fecha = st.date_input("Fecha", value=valores["fecha"] if hasattr(valores["fecha"], 'strftime') else datetime.now().date(), help="Fecha de la inspección")
            lugar = st.text_input("Lugar", valores["lugar"], help="Ubicación donde se realiza la inspección")

    # Sección de firmas en un contenedor expandible
    with st.expander("👥 Firmas", expanded=True):
        st.markdown("Configure las firmas necesarias para el informe")
        col1, col2 = st.columns(2)
        firma_1 = elaboro
        with col1:
            st.text_input(
                "Elaboró (Firma 1)",
                value=firma_1,
                help="Siempre coincide con el inspector seleccionado en 'Elaboró'",
                disabled=True,
            )
        with col2:
            firma_2_default = valores.get("firma_2", elaboro)
            firma_2 = st.selectbox(
                "Revisó",
                options=opciones_inspectores,
                index=opciones_inspectores.index(firma_2_default) if firma_2_default in opciones_inspectores else opciones_inspectores.index(elaboro) if elaboro in opciones_inspectores else 0,
                help="Inspector que revisa el informe",
            )

        st.caption("Las firmas automáticas se gestionan en código desde `config/signature_map.py`.")

with tab2:
    st.subheader("🎯 Selección de Módulos")
    st.markdown("Seleccione los módulos que desea incluir en el informe:")
    if SOLO_REPORTE_VISUAL:
        st.info("🧪 Modo de prueba activo: solo está habilitado el módulo de Inspección Visual.")

    modulos_disponibles_ui = modulos_disponibles
    if SOLO_REPORTE_VISUAL:
        modulos_disponibles_ui = {
            nombre: info
            for nombre, info in modulos_disponibles.items()
            if nombre == "Inspección Visual"
        }

    # Crear columnas para los módulos
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Módulos Disponibles")
        modulos_seleccionados = []
        
        for nombre, info in modulos_disponibles_ui.items():
            with st.container():
                st.markdown(f"""
                <div class="module-card">
                    <h4>{info['icono']} {nombre}</h4>
                    <p>{info['descripcion']}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.checkbox(f"Incluir {nombre}", 
                             value=nombre in valores.get("modulos_seleccionados", modulos_default),
                             key=f"modulo_{nombre}"):
                    modulos_seleccionados.append(nombre)

    with col2:
        st.markdown("### ℹ️ Información")
        st.info("""
        **Instrucciones:**
        1. Seleccione los módulos que necesita para su inspección
        2. Cada módulo contiene formularios específicos
        3. Los módulos seleccionados aparecerán en la barra lateral
        4. Puede modificar su selección en cualquier momento
        """)
        
        if modulos_seleccionados:
            st.success(f"✅ {len(modulos_seleccionados)} módulos seleccionados")
        else:
            st.warning("⚠️ No hay módulos seleccionados")

with tab3:
    st.subheader("📂 Guardar o Cargar Estado del Informe")
    st.markdown(
        "Esta sección permite guardar toda la información actual ingresada en el formulario "
        "para que pueda ser cargada y re-editada en el futuro."
    )
    
    col_g, col_c = st.columns(2)
    
    with col_g:
        with st.container(border=True):
            st.markdown("### 💾 Guardar Informe")
            default_name = ""
            if "datos_proyecto" in st.session_state:
                dp = st.session_state.datos_proyecto
                num_ord = dp.get("numero_orden", "")
                cons = dp.get("consecutivo_inicial", "")
                cli = dp.get("cliente", "")
                default_name = f"Informe_T{num_ord}I{cons}_{cli}".strip("_")
            
            nombre_guardar = st.text_input(
                "Nombre del informe para guardar:",
                value=default_name,
                help="Ingresa un nombre para identificar este informe en el servidor local"
            )
            
            if st.button("💾 Guardar localmente", type="primary", use_container_width=True):
                if not nombre_guardar:
                    st.error("⚠️ Debes ingresar un nombre para el informe.")
                else:
                    from persistencia import guardar_informe
                    if guardar_informe(nombre_guardar):
                        st.success(f"✅ Informe '{nombre_guardar}' guardado exitosamente en el servidor.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Ocurrió un error al guardar el informe.")
                    
    with col_c:
        with st.container(border=True):
            st.markdown("### 📂 Cargar Informe Guardado")
            from persistencia import listar_informes_guardados, cargar_informe, eliminar_informe
            informes_guardados = listar_informes_guardados()
            
            if not informes_guardados:
                st.info("No hay informes guardados localmente en el servidor.")
            else:
                informe_seleccionado = st.selectbox(
                    "Selecciona un informe para cargar:",
                    options=informes_guardados,
                    help="Selecciona de la lista de informes persistidos localmente"
                )
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("📂 Cargar Seleccionado", type="primary", use_container_width=True):
                        if cargar_informe(informe_seleccionado):
                            st.success(f"✅ Informe '{informe_seleccionado}' cargado correctamente.")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Error al cargar el informe.")
                with col_b2:
                    if st.button("🗑️ Eliminar Seleccionado", type="secondary", use_container_width=True):
                        if eliminar_informe(informe_seleccionado):
                            st.success(f"🗑️ Informe '{informe_seleccionado}' eliminado.")
                            st.rerun()
                        else:
                            st.error("❌ Error al eliminar el informe.")
                        
    st.markdown("---")
    with st.container(border=True):
        st.markdown("### 📥 Exportar / Importar desde Archivo ZIP (Navegador)")
        col_exp, col_imp = st.columns(2)
        
        with col_exp:
            st.markdown("**Descargar Copia de Respaldo**")
            st.write("Descarga todo el estado actual e imágenes en un archivo ZIP para usar en otra computadora o guardarlo como respaldo.")
            
            # Guardamos temporalmente para generar el ZIP de descarga
            nombre_temporal = "_temp_backup"
            from persistencia import guardar_informe, exportar_zip, eliminar_informe
            guardar_informe(nombre_temporal)
            zip_bytes = exportar_zip(nombre_temporal)
            eliminar_informe(nombre_temporal)
            
            if zip_bytes:
                filename_download = f"Respaldo_Informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                if "datos_proyecto" in st.session_state:
                    dp = st.session_state.datos_proyecto
                    num_ord = dp.get("numero_orden", "")
                    cons = dp.get("consecutivo_inicial", "")
                    filename_download = f"Respaldo_T{num_ord}I{cons}.zip"
                    
                st.download_button(
                    label="📥 Descargar Archivo ZIP",
                    data=zip_bytes,
                    file_name=filename_download,
                    mime="application/zip",
                    use_container_width=True
                )
            else:
                st.warning("No hay datos suficientes para generar un archivo de respaldo.")
                
        with col_imp:
            st.markdown("**Subir Copia de Respaldo**")
            st.write("Sube un archivo ZIP previamente descargado para restaurar su información completa en esta aplicación.")
            
            uploaded_backup = st.file_uploader(
                "Selecciona el archivo ZIP de respaldo:",
                type=["zip"],
                help="Sube el archivo .zip exportado de la aplicación"
            )
            
            if uploaded_backup:
                if st.button("📂 Restaurar Respaldo Subido", type="primary", use_container_width=True):
                    from persistencia import importar_desde_zip, cargar_informe
                    nombre_importado = importar_desde_zip(uploaded_backup)
                    if nombre_importado:
                        if cargar_informe(nombre_importado):
                            st.success(f"✅ Respaldo '{nombre_importado}' cargado exitosamente.")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Error al cargar la información importada.")
                    else:
                        st.error("❌ El archivo subido no es válido o está dañado.")

# Botones de acción en la parte inferior
saved_key = "saved_1_0"
if saved_key not in st.session_state:
    st.session_state[saved_key] = "bloque_1" in st.session_state

col1, col2, col3 = st.columns([1,1,1])
with col2:
    if st.button("💾 Guardar Configuración", type="primary", use_container_width=True):
        if SOLO_REPORTE_VISUAL:
            modulos_seleccionados = ["Inspección Visual"]

        if not modulos_seleccionados:
            st.error("⚠️ Debe seleccionar al menos un módulo")
        elif not numero_orden or not consecutivo_inicial:
            st.error("⚠️ Debe ingresar el número de orden y el consecutivo inicial")
        else:
            # Generar número de informe base (visual)
            numero_informe_base = generar_numero_informe(numero_orden, consecutivo_inicial, fecha.year if hasattr(fecha, 'year') else datetime.now().year, 0)
            
            # Guardar datos del proyecto en formato para reporte
            st.session_state.datos_proyecto = {
                "numero_orden": numero_orden,
                "consecutivo_inicial": consecutivo_inicial,
                "numero_informe": numero_informe_base,  # Para compatibilidad
                "fecha": formatear_fecha_para_display(fecha) if hasattr(fecha, 'strftime') else str(fecha),
                "fecha_obj": fecha,  # Guardar objeto fecha también
                "cliente": cliente,
                "proyecto": proyecto,
                "ubicacion": lugar,
                "inspector": elaboro,
                "contratista": contratista,
                "subproyecto": subproyecto,
                "norma_global": norma_global,
                "firmas": {
                    "firma_1": firma_1,
                    "firma_2": firma_2,
                    "firma_1_path": get_signature_for_person(firma_1),
                    "firma_2_path": get_signature_for_person(firma_2),
                }
            }
            
            # También guardar en bloque_1 para compatibilidad
            st.session_state.bloque_1 = {
                "cliente": cliente,
                "proyecto": proyecto,
                "subproyecto": subproyecto,
                "contratista": contratista,
                "numero_orden": numero_orden,
                "consecutivo_inicial": consecutivo_inicial,
                "reporte_no": numero_informe_base,  # Para compatibilidad
                "elaboro": elaboro,
                "norma_global": norma_global,
                "fecha": fecha,
                "lugar": lugar,
                "firmas": {
                    "firma_1": firma_1,
                    "firma_2": firma_2,
                    "firma_1_path": get_signature_for_person(firma_1),
                    "firma_2_path": get_signature_for_person(firma_2),
                },
                "modulos_seleccionados": modulos_seleccionados
            }
            
            # Actualizar la configuración de páginas en session_state
            if "pages_config" not in st.session_state:
                st.session_state.pages_config = {}
            
            # Actualizar la configuración de módulos
            st.session_state.pages_config["modulos"] = [
                st.Page(modulos_disponibles[modulo]["archivo"], title=modulos_disponibles[modulo]["titulo_sidebar"])
                for modulo in modulos_seleccionados
            ]

            persist_session_state()
            st.session_state[saved_key] = True
            st.success("✅ Configuración guardada correctamente")
            st.balloons()
            st.rerun() 

with col3:
    if st.button("🧹 Limpiar formulario", type="secondary", use_container_width=True):
        clear_persisted_state()
        st.session_state.pages_config = {
            "modulos": [
                st.Page(modulos_disponibles[modulo]["archivo"], title=modulos_disponibles[modulo]["titulo_sidebar"])
                for modulo in modulos_default
            ]
        }
        st.success("✅ Formulario limpiado y datos guardados eliminados")
        st.rerun()

if st.session_state.get(saved_key, False):
    col_next_1, col_next_2, col_next_3 = st.columns([1, 1, 1])
    with col_next_2:
        if st.button("Siguiente sección", key="siguiente_seccion_1_0", type="primary", use_container_width=True):
            modulos_activos = st.session_state.get("pages_config", {}).get("modulos", [])
            if modulos_activos:
                pagina_objetivo = getattr(modulos_activos[0], "_page", None)
                if pagina_objetivo:
                    st.switch_page(pagina_objetivo)
                    st.stop()
            st.switch_page("2_datos_de_inspeccion_visual.py")
