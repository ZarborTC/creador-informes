import streamlit as st
import pandas as pd
import os
import uuid
from utils import (
    cargar_kits, get_norma_global, get_material_base,
    get_kits_disponibles, get_componentes_kit, materiales_base,
    get_proceso_soldadura, get_tipo_soldadura, get_tipo_inspeccion,
    get_materiales_base_seleccionados, get_procesos_soldadura_seleccionados,
    get_tipos_soldadura_seleccionados, procesos_soldadura, tipos_soldadura,
    get_esquema_elementos_global, cargar_palpadores, get_frecuencias_palpadores
)
from save_state import persist_session_state

st.title("🔊 5 Datos de Inspección de Ultrasonido")

# Obtener la norma global
norma_global = get_norma_global()
st.markdown(f"**Norma global:** {norma_global}")

# Mostrar información heredada del módulo de inspección visual
st.subheader("📋 Información Heredada del Módulo de Inspección Visual")

# Obtener materiales base seleccionados
materiales_seleccionados = get_materiales_base_seleccionados()
procesos_seleccionados = get_procesos_soldadura_seleccionados()
tipos_seleccionados = get_tipos_soldadura_seleccionados()

# Mostrar información heredada
if materiales_seleccionados:
    st.success(f"**Materiales Base:** {', '.join(materiales_seleccionados)}")
else:
    st.warning("No hay materiales base seleccionados en el módulo de inspección visual")

if procesos_seleccionados:
    st.success(f"**Procesos de Soldadura:** {', '.join(procesos_seleccionados)}")
else:
    st.warning("No hay procesos de soldadura seleccionados en el módulo de inspección visual")

if tipos_seleccionados:
    st.success(f"**Tipos de Soldadura:** {', '.join(tipos_seleccionados)}")
else:
    st.warning("No hay tipos de soldadura seleccionados en el módulo de inspección visual")

st.markdown("---")

# Selector múltiple de material base (heredado pero editable)
st.subheader("Especificación de Material Base")
st.markdown("Los materiales base se heredan del módulo de inspección visual. Puede modificarlos si es necesario:")

materiales_editados = st.multiselect(
    "ESPECIFICACIÓN MATERIAL BASE:",
    options=materiales_base,
    default=materiales_seleccionados,
    help="Selecciona una o más especificaciones del material base"
)

# Guardar en session_state
st.session_state.materiales_base_seleccionados = materiales_editados

# Mostrar materiales seleccionados
if materiales_editados:
    st.success(f"Materiales seleccionados: {', '.join(materiales_editados)}")
else:
    st.warning("No se han seleccionado materiales base")

# Procedimiento editable para Ultrasonido
procedimiento_default = "TLPR0028 - Inspección de Ultrasonido - Rev. 1"

# Inicializar procedimiento en session_state si no existe
if "procedimiento_ut" not in st.session_state:
    st.session_state.procedimiento_ut = procedimiento_default

procedimiento = st.text_input("PROCEDIMIENTO:", value=st.session_state.procedimiento_ut, help="Procedimiento utilizado para la inspección de ultrasonido")

# Actualizar session_state cuando cambie
st.session_state.procedimiento_ut = procedimiento

# Determinar el tipo de inspección basado en el procedimiento
tipo_inspeccion = get_tipo_inspeccion(procedimiento)

# Mostrar procesos de soldadura heredados
st.markdown("**Procesos de Soldadura Heredados:**")
if procesos_seleccionados:
    st.success(f"{', '.join(procesos_seleccionados)}")
else:
    st.warning("No hay procesos de soldadura seleccionados")

st.markdown("**Tipos de Soldadura Heredados:**")
if tipos_seleccionados:
    st.success(f"{', '.join(tipos_seleccionados)}")
else:
    st.warning("No hay tipos de soldadura seleccionados")

# Opción para editar procesos de soldadura si es necesario
with st.expander("✏️ Editar Procesos de Soldadura (opcional)"):
    st.markdown("Puede modificar los procesos de soldadura si es necesario:")
    
    col_proc, col_tipo = st.columns(2)
    with col_proc:
        procesos_editados = st.multiselect(
            "Procesos de soldadura:",
            options=procesos_soldadura,
            default=procesos_seleccionados,
            help="Selecciona uno o más procesos de soldadura"
        )
        st.session_state.procesos_soldadura_seleccionados = procesos_editados

    with col_tipo:
        tipos_editados = st.multiselect(
            "Tipos de soldadura:",
            options=tipos_soldadura,
            default=tipos_seleccionados,
            help="Selecciona uno o más tipos de soldadura"
        )
        st.session_state.tipos_soldadura_seleccionados = tipos_editados

    # Mostrar selecciones editadas
    if procesos_editados:
        st.success(f"Procesos seleccionados: {', '.join(procesos_editados)}")
    if tipos_editados:
        st.success(f"Tipos seleccionados: {', '.join(tipos_editados)}")

# Cargar y filtrar kits
kits = cargar_kits()
kits_disponibles = get_kits_disponibles(tipo_inspeccion) if tipo_inspeccion else []
opciones_kits = [f"{kit['nombre']} - {kit['descripcion']}" for kit in kits_disponibles]

kit_seleccionado = st.selectbox(
    "EQUIPOS UTILIZADOS:",
    options=opciones_kits,
    help="Selecciona el kit necesario para la inspección"
)

if kit_seleccionado:
    componentes = get_componentes_kit(kit_seleccionado, kits_disponibles)
    if componentes:
        componentes_texto = ", ".join(componentes)
        kit = next((k for k in kits_disponibles if f"{k['nombre']} - {k['descripcion']}" == kit_seleccionado), None)
        if kit:
            st.write(f"**{kit['nombre']}:** {componentes_texto}")
            
            # Mostrar información específica del equipo de ultrasonido
            if kit['id'] == 'kit_ut' and kit.get('marca'):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Marca:** {kit.get('marca', 'N/A')}")
                    st.write(f"**Modelo:** {kit.get('modelo', 'N/A')}")
                with col2:
                    st.write(f"**Escala:** {kit.get('escala', 'N/A')}")
                    st.write(f"**Grado Calibración (dB):** {kit.get('grado_calibracion', 'N/A')}")

# --- PALPADOR ---
st.markdown("##### Palpador, Tipo y Método de Inspección")

# Cargar palpadores disponibles desde CSV
palpadores_disponibles = cargar_palpadores()
frecuencias_palpadores = get_frecuencias_palpadores()

# Crear opciones para el selector con toda la información visible
opciones_palpadores = [
    f"{p['nombre']} | Tipo: {p['tipo']} | Ángulo: {p['angulo']}° | Dimensión: {p['dimension']} | Frecuencia: {p['frecuencia_default']} MHz | Calibración: {p['calibracion']}" 
    for p in palpadores_disponibles
]

# Inicializar palpador seleccionado si no existe
if "palpador_seleccionado_id" not in st.session_state:
    st.session_state.palpador_seleccionado_id = palpadores_disponibles[0]['id'] if palpadores_disponibles else None

# Selector de palpador
if opciones_palpadores:
    # Encontrar el índice del palpador actual
    palpador_actual = next((p for p in palpadores_disponibles if p['id'] == st.session_state.palpador_seleccionado_id), palpadores_disponibles[0])
    index_actual = next((i for i, p in enumerate(palpadores_disponibles) if p['id'] == st.session_state.palpador_seleccionado_id), 0)
    
    palpador_seleccionado_display = st.selectbox(
        "**Seleccionar Palpador:**",
        options=opciones_palpadores,
        index=index_actual,
        help="Selecciona el palpador a utilizar en la inspección"
    )
    
    # Extraer el nombre del palpador de la opción seleccionada (antes del primer "|")
    palpador_seleccionado_nombre = palpador_seleccionado_display.split(" | ")[0]
    
    # Obtener el palpador completo seleccionado
    palpador_seleccionado = next((p for p in palpadores_disponibles if p['nombre'] == palpador_seleccionado_nombre), None)
    
    if palpador_seleccionado:
        st.session_state.palpador_seleccionado_id = palpador_seleccionado['id']
        
        # Mostrar información del palpador en columnas
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.info(f"**Tipo:** {palpador_seleccionado['tipo']}")
        
        with col2:
            st.info(f"**Ángulo:** {palpador_seleccionado['angulo']}°")
        
        with col3:
            st.info(f"**Dimensión:** {palpador_seleccionado['dimension']}")
        
        with col4:
            st.info(f"**Calibración:** {palpador_seleccionado['calibracion']}")
        
        with col5:
            # Frecuencia editable por palpador
            palpador_id = palpador_seleccionado['id']
            
            # Inicializar frecuencia para este palpador si no existe
            if palpador_id not in frecuencias_palpadores:
                frecuencias_palpadores[palpador_id] = float(palpador_seleccionado['frecuencia_default'])
            
            opciones_frecuencia = [1.0, 1.5, 2.0, 2.25, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
            
            # Asegurar que la frecuencia actual esté en las opciones
            frecuencia_actual = frecuencias_palpadores[palpador_id]
            if frecuencia_actual not in opciones_frecuencia:
                frecuencia_actual = float(palpador_seleccionado['frecuencia_default'])
            
            try:
                index_frecuencia = opciones_frecuencia.index(frecuencia_actual)
            except ValueError:
                index_frecuencia = 3  # Default a 2.25 MHz
            
            frecuencia_seleccionada = st.selectbox(
                "**Frecuencia (MHz):**",
                options=opciones_frecuencia,
                index=index_frecuencia,
                key=f"frecuencia_{palpador_id}",
                help="Frecuencia del palpador (editable para cada palpador)"
            )
            
            # Guardar la frecuencia editada
            frecuencias_palpadores[palpador_id] = frecuencia_seleccionada
        
        # Construir string para guardar con toda la información
        palpador = (
            f"Nombre: {palpador_seleccionado['nombre']}\n"
            f"Tipo: {palpador_seleccionado['tipo']}\n"
            f"Ángulo: {palpador_seleccionado['angulo']}°\n"
            f"Frecuencia: {frecuencia_seleccionada} MHz\n"
            f"Dimensión: {palpador_seleccionado['dimension']}\n"
            f"Calibración: {palpador_seleccionado['calibracion']}"
        )
    else:
        st.error("⚠️ No se pudo cargar la información del palpador seleccionado.")
        palpador = "Error al cargar datos del palpador"
else:
    st.warning("⚠️ No hay palpadores disponibles. Verifica el archivo config/palpadores.csv")
    palpador = "No hay palpadores disponibles"

# Sección 2: Materiales y Procedimientos
st.subheader("Materiales y Procedimientos")

# 2.1 Tipo de inspección por ultrasonido
tipo_opciones = ["Haz recto (Solo para palpador recto)", "Haz angular (Solo para palpador angular)"]
tipo = st.selectbox("TIPO DE INSPECCIÓN POR ULTRASONIDO:", tipo_opciones, help="Selecciona el tipo de inspección según el palpador utilizado")

# 2.2 Método
metodo_opciones = ["A-scan", "B-scan"]
metodo = st.selectbox("MÉTODO:", metodo_opciones, help="Selecciona el método de inspección")

# 2.3 Soldadura
soldadura = st.text_area(
    "SOLDADURA:",
    """Proceso: SMAW
Paso 4xe: 4.0
Medio paso P/2: 2.0
11xe rango 111: 11.0""",
    help="Datos de la soldadura: proceso, paso 4xe, medio paso P/2, 11xe rango 111"
)

# 2.4 Materiales
materiales = st.text_area(
    "MATERIALES:",
    """Material base: A36
Espesor de m. base 11: 12.7 mm
Material de aporte: E7018
Acoplante: CMC""",
    help="Materiales utilizados: material base, espesor, material de aporte, acoplante"
)

procedimiento = st.text_area(
    "PROCEDIMIENTO:",
    """1. Limpieza de la superficie con método manual (con paño).
2. Aplicación de limpiador.
3. Aplicación de acoplante (tiempo de exposición: 10:00 min).
4. Limpieza de acoplante.
5. Aplicación de revelador (tiempo de revelado: 10:00 min).
6. Limpieza final."""
)

# Sección 3: Parámetros de Operación
st.subheader("Parámetros de Operación")
parametros = st.text_area(
    "PARÁMETROS DE OPERACIÓN:",
    """LIMPIEZA: 5:00 min
ACOPLANTE: 12:00 min
REVELADOR: 3:00 min
TEMPERATURA: 26° C
APLICACIÓN: Spray
ILUMINACIÓN: Luz Natural"""
)

# Sección 4: Elementos Inspeccionados
st.subheader("Elementos Inspeccionados")

# Inicializar elementos del módulo actual
elementos_key = "tabla_elementos_5_1"
if elementos_key not in st.session_state:
    st.session_state[elementos_key] = []

bulk_col_1, bulk_col_2 = st.columns([2, 1.5])
with bulk_col_1:
    if st.button("Marcar toda la sección como Fuera de Alcance", key="bulk_fda_ut"):
        for idx in range(len(st.session_state[elementos_key])):
            st.session_state[elementos_key][idx]["evaluacion_junta"] = "Fuera de Alcance"
        st.rerun()
with bulk_col_2:
    if st.button("Restablecer sección", key="bulk_reset_ut"):
        for idx in range(len(st.session_state[elementos_key])):
            st.session_state[elementos_key][idx]["evaluacion_junta"] = "Satisfactorio"
        st.rerun()

# Función para agregar una nueva fila
def agregar_fila_elemento_ut():
    nuevo_numero = len(st.session_state[elementos_key]) + 1
    nueva_fila = {
        "id": uuid.uuid4().hex,
        "numero": str(nuevo_numero),
        "descripcion_junta": "",
        "numero_junta": "",
        "ubicacion_junta": "",
        "estampe": "",
        "decibeles_a": "",
        "decibeles_b": "",
        "decibeles_c": "",
        "decibeles_d": "",
        "discontinuidad_distancia_angular": "",
        "discontinuidad_profundidad": "",
        "discontinuidad_distancia_eje_y": "",
        "discontinuidad_distancia_eje_x": "",
        "evaluacion_junta": "Satisfactorio"
    }
    st.session_state[elementos_key].append(nueva_fila)

# Opciones para la evaluación de la junta
opciones_evaluacion = ["Satisfactorio", "No Satisfactorio", "Fuera de Alcance"]

# Crear la tabla de elementos
if st.session_state[elementos_key]:
    st.markdown("### Tabla de Elementos Inspeccionados por Ultrasonido")
    
    # Filas de la tabla - cada elemento es una sección completa
    for i, elemento in enumerate(st.session_state[elementos_key]):
        if "id" not in elemento:
            elemento["id"] = uuid.uuid4().hex
        # Contenedor para cada elemento con borde visual
        with st.container():
            st.markdown(f"#### 🔍 Elemento #{elemento['numero']}")
            
            # Información básica de la junta
            st.markdown("**📋 Información Básica de la Junta**")
            col1, col2, col3, col4 = st.columns([2, 1, 2, 2])
            
            with col1:
                st.session_state[elementos_key][i]["descripcion_junta"] = st.text_input(
                    "Descripción de la Junta",
                    value=elemento["descripcion_junta"],
                    key=f"elem_desc_junta_5_1_{elemento['id']}",
                    help="Descripción detallada de la junta inspeccionada"
                )
            
            with col2:
                st.session_state[elementos_key][i]["numero_junta"] = st.text_input(
                    "# de Junta",
                    value=elemento["numero_junta"],
                    key=f"elem_num_junta_5_1_{elemento['id']}",
                    help="Número identificador de la junta"
                )
            
            with col3:
                st.session_state[elementos_key][i]["ubicacion_junta"] = st.text_input(
                    "Ubicación de la Junta",
                    value=elemento["ubicacion_junta"],
                    key=f"elem_ubic_junta_5_1_{elemento['id']}",
                    help="Ubicación física de la junta en el componente"
                )
            
            with col4:
                st.session_state[elementos_key][i]["estampe"] = st.text_input(
                    "Estampe",
                    value=elemento["estampe"],
                    key=f"elem_estampe_5_1_{elemento['id']}",
                    help="Estampe o marca identificadora"
                )
            
            # Calificación de decibeles
            st.markdown("**🔊 Calificación de Decibeles**")
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                st.session_state[elementos_key][i]["decibeles_a"] = st.text_input(
                    "Decibeles A",
                    value=elemento["decibeles_a"],
                    key=f"elem_db_a_5_1_{elemento['id']}",
                    help="Valor en decibeles para calificación A"
                )
            
            with col6:
                st.session_state[elementos_key][i]["decibeles_b"] = st.text_input(
                    "Decibeles B",
                    value=elemento["decibeles_b"],
                    key=f"elem_db_b_5_1_{elemento['id']}",
                    help="Valor en decibeles para calificación B"
                )
            
            with col7:
                st.session_state[elementos_key][i]["decibeles_c"] = st.text_input(
                    "Decibeles C",
                    value=elemento["decibeles_c"],
                    key=f"elem_db_c_5_1_{elemento['id']}",
                    help="Valor en decibeles para calificación C"
                )
            
            with col8:
                st.session_state[elementos_key][i]["decibeles_d"] = st.text_input(
                    "Decibeles D",
                    value=elemento["decibeles_d"],
                    key=f"elem_db_d_5_1_{elemento['id']}",
                    help="Valor en decibeles para calificación D"
                )
            
            # Discontinuidad
            st.markdown("**📏 Discontinuidad**")
            col9, col10, col11, col12 = st.columns(4)
            
            with col9:
                st.session_state[elementos_key][i]["discontinuidad_distancia_angular"] = st.text_input(
                    "Distancia Angular",
                    value=elemento["discontinuidad_distancia_angular"],
                    key=f"elem_dist_ang_5_1_{elemento['id']}",
                    help="Distancia angular de la discontinuidad"
                )
            
            with col10:
                st.session_state[elementos_key][i]["discontinuidad_profundidad"] = st.text_input(
                    "Profundidad",
                    value=elemento["discontinuidad_profundidad"],
                    key=f"elem_prof_5_1_{elemento['id']}",
                    help="Profundidad de la discontinuidad"
                )
            
            with col11:
                st.session_state[elementos_key][i]["discontinuidad_distancia_eje_y"] = st.text_input(
                    "Distancia Eje Y",
                    value=elemento["discontinuidad_distancia_eje_y"],
                    key=f"elem_dist_y_5_1_{elemento['id']}",
                    help="Distancia sobre el eje Y"
                )
            
            with col12:
                st.session_state[elementos_key][i]["discontinuidad_distancia_eje_x"] = st.text_input(
                    "Distancia Eje X",
                    value=elemento["discontinuidad_distancia_eje_x"],
                    key=f"elem_dist_x_5_1_{elemento['id']}",
                    help="Distancia sobre el eje X"
                )
            
            # Evaluación y acción
            st.markdown("**✅ Evaluación**")
            col13, col14 = st.columns([3, 1])
            
            with col13:
                st.session_state[elementos_key][i]["evaluacion_junta"] = st.selectbox(
                    "Evaluación de la Junta",
                    options=opciones_evaluacion,
                    index=opciones_evaluacion.index(elemento["evaluacion_junta"]),
                    key=f"elem_eval_5_1_{elemento['id']}",
                    help="Resultado de la evaluación de la junta"
                )
            
            with col14:
                st.markdown("")  # Espacio en blanco para alineación
                col_elim, col_dupl = st.columns(2)
                if col_elim.button("🗑️ Eliminar", key=f"elem_eliminar_5_1_{elemento['id']}", type="secondary", use_container_width=True):
                    st.session_state[elementos_key].pop(i)
                    # Re-enumerar secuencialmente
                    for idx, elem in enumerate(st.session_state[elementos_key]):
                        elem["numero"] = str(idx + 1)
                    st.rerun()
                if col_dupl.button("👯 Duplicar", key=f"elem_duplicar_5_1_{elemento['id']}", type="primary", use_container_width=True):
                    nuevo_elemento = st.session_state[elementos_key][i].copy()
                    nuevo_elemento["id"] = uuid.uuid4().hex
                    st.session_state[elementos_key].insert(i + 1, nuevo_elemento)
                    # Re-enumerar secuencialmente
                    for idx, elem in enumerate(st.session_state[elementos_key]):
                        elem["numero"] = str(idx + 1)
                    st.rerun()
            
            # Separador visual entre elementos
            st.markdown("---")
else:
    st.info("No hay elementos inspeccionados. Use el botón 'Agregar Elemento' para comenzar.")

if st.button("Agregar Elemento", key="agregar_elemento_ut"):
    agregar_fila_elemento_ut()
    st.rerun()

juntas = st.number_input(
    "JUNTAS:",
    min_value=0,
    value=1,
    step=1,
    help="Cantidad de juntas en la inspección"
)

# Sección 5: Detalles y Esquema
st.subheader("Detalles y Esquema")

# Inicializar esquema del módulo actual
esquema_key = "esquema_5_1"
if esquema_key not in st.session_state:
    # Heredar esquema de inspección visual si existe
    esquema_global_original = get_esquema_elementos_global()
    if esquema_global_original:
        # Copiar esquema de inspección visual (herencia inicial)
        st.session_state[esquema_key] = []
        for img_info in esquema_global_original:
            # Crear una copia independiente de la imagen
            img_copia = {
                "archivo": img_info["archivo"],
                "nombre": img_info["nombre"],
                "comentario": img_info["comentario"]
            }
            st.session_state[esquema_key].append(img_copia)
        st.success(f"✅ Esquema heredado de Inspección Visual: {len(st.session_state[esquema_key])} imágenes")
    else:
        # Si no hay esquema en inspección visual, inicializar lista vacía
        st.session_state[esquema_key] = []
        st.info("💡 No hay esquema en Inspección Visual para heredar. Puedes agregar imágenes manualmente.")

# Cargar nuevas imágenes del esquema
uploaded_files_esquema = st.file_uploader(
    "Selecciona las imágenes del esquema de inspección (puedes subir múltiples)",
    type=["png", "jpg", "jpeg"],
    key="upload_esquema_ut",
    accept_multiple_files=True
)

if uploaded_files_esquema:
    if st.button("Agregar Imágenes al Esquema", key="agregar_esquema_ut"):
        for file in uploaded_files_esquema:
            nueva_imagen = {
                "archivo": file,
                "nombre": file.name,
                "comentario": ""
            }
            st.session_state[esquema_key].append(nueva_imagen)
        st.success(f"Se agregaron {len(uploaded_files_esquema)} imágenes al esquema")
        st.rerun()

# Botones para gestionar esquema
col1, col2 = st.columns(2)
with col1:
    if st.button("Re-heredar de Inspección Visual", key="reheredar_esquema_ut"):
        esquema_global_original = get_esquema_elementos_global()
        if esquema_global_original:
            # Limpiar esquema actual y re-heredar
            st.session_state[esquema_key] = []
            for img_info in esquema_global_original:
                img_copia = {
                    "archivo": img_info["archivo"],
                    "nombre": img_info["nombre"],
                    "comentario": img_info["comentario"]
                }
                st.session_state[esquema_key].append(img_copia)
            st.success(f"✅ Esquema actualizado desde Inspección Visual: {len(st.session_state[esquema_key])} imágenes")
            st.rerun()
        else:
            st.warning("⚠️ No hay esquema en Inspección Visual para heredar.")

with col2:
    if st.button("Limpiar Esquema", key="limpiar_esquema_ut"):
        st.session_state[esquema_key] = []
        st.success("✅ Esquema limpiado")
        st.rerun()

# Mostrar las imágenes del esquema
if len(st.session_state[esquema_key]) == 0:
    st.info("No hay esquema cargado todavía. Sube imágenes o hereda desde Inspección Visual.")
else:
    st.success(f"✅ Esquema de Ultrasonido: {len(st.session_state[esquema_key])} imágenes cargadas")
    st.info("💡 Este esquema es independiente del módulo de Inspección Visual.")
    
    for i, img_info in enumerate(st.session_state[esquema_key]):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(img_info["archivo"], use_container_width=True)
        
        with col2:
            st.write(f"**Archivo:** {img_info['nombre']}")
            nuevo_comentario = st.text_area(
                "Comentario",
                value=img_info["comentario"],
                key=f"comentario_esquema_ut_{i}"
            )
            st.session_state[esquema_key][i]["comentario"] = nuevo_comentario
            
            if st.button("Eliminar imagen", key=f"eliminar_esquema_ut_{i}"):
                st.session_state[esquema_key].pop(i)
                st.rerun()

detalle_resultados = st.text_area("DETALLE DE ELEMENTOS INSPECCIONADOS Y RESULTADOS:", "")

# Sección 6: Observaciones
st.subheader("Observaciones")
observaciones_generales = st.text_area("OBSERVACIONES GENERALES:", "")

# Sección 7: Registros Fotográficos
st.subheader("Registros Fotográficos")

if "imagenes" not in st.session_state:
    st.session_state.imagenes = []

if "delete_idx" not in st.session_state:
    st.session_state.delete_idx = None

st.subheader("Cargar nuevas imágenes")
uploaded_files = st.file_uploader(
    "Selecciona una o varias imágenes",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if st.button("Agregar Imágenes", key="agregar_imagenes_ut"):
    if uploaded_files:
        for file in uploaded_files:
            nueva_imagen = {
                "archivo": file,
                "nombre": file.name,
                "comentario": ""
            }
            st.session_state.imagenes.append(nueva_imagen)
    else:
        st.warning("No has seleccionado ningún archivo.")

st.write("---")

st.subheader("Imágenes cargadas")
if len(st.session_state.imagenes) == 0:
    st.info("No hay imágenes cargadas todavía.")
else:
    for i, img_info in enumerate(st.session_state.imagenes):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(img_info["archivo"], use_container_width=True)
        
        with col2:
            st.write(f"**Archivo:** {img_info['nombre']}")
            nuevo_comentario = st.text_area(
                "Comentario",
                value=img_info["comentario"],
                key=f"comentario_{i}"
            )
            st.session_state.imagenes[i]["comentario"] = nuevo_comentario
            
            if st.button("Eliminar esta imagen", key=f"eliminar_{i}"):
                st.session_state.delete_idx = i

    if st.session_state.delete_idx is not None:
        st.session_state.imagenes.pop(st.session_state.delete_idx)
        st.session_state.delete_idx = None
        st.rerun()

st.write("---")

st.subheader("Datos finales (diccionario)")
datos_finales = {
    "imagenes": [
        {
            "nombre": img["nombre"],
            "comentario": img["comentario"]
        }
        for img in st.session_state.imagenes
    ]
}

saved_key = "saved_5_1"
if saved_key not in st.session_state:
    st.session_state[saved_key] = "bloque_5_1" in st.session_state

if st.button("Guardar Datos", key="guardar_datos_ut", type="primary"):
    st.write("### Datos guardados correctamente")
    
    st.session_state.bloque_5_1 = {
        "equipo": kit_seleccionado,
        "palpador": palpador,
        "tipo_inspeccion": tipo,
        "metodo": metodo,
        "soldadura": soldadura,
        "materiales": materiales,
        "norma": norma_global,
        "procedimiento": procedimiento,
        "elementos_inspeccionados": st.session_state[elementos_key],
        "juntas": juntas,
        "detalle_resultados": detalle_resultados,
        "esquema_inspeccion": st.session_state[esquema_key],  # Usar esquema independiente
        "observaciones_generales": observaciones_generales,
        "registros_fotograficos": datos_finales["imagenes"]
    }
    persist_session_state()
    st.session_state[saved_key] = True

if st.session_state.get(saved_key, False):
    if st.button("Siguiente sección", key="siguiente_seccion_5_1", type="primary"):
        st.switch_page("bloque_reportes.py")
