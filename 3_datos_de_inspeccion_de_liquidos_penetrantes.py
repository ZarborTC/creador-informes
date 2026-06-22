import streamlit as st
import pandas as pd
import os
import uuid
from utils import (
    cargar_kits, get_norma_global, get_material_base,
    get_kits_disponibles, get_componentes_kit, materiales_base,
    get_proceso_soldadura, get_tipo_soldadura,
    get_materiales_base_seleccionados, get_procesos_soldadura_seleccionados,
    get_tipos_soldadura_seleccionados, procesos_soldadura, tipos_soldadura,
    get_esquema_elementos_global
)
from save_state import persist_session_state

st.title("💧 3 Datos de Inspección de Líquidos Penetrantes")

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

# Sección 1: Información General
st.subheader("Información General")

# Procedimiento editable para Líquidos Penetrantes
procedimiento_default = "TLPR0026 - Inspección de Líquidos Penetrantes - Rev. 1"

# Inicializar procedimiento en session_state si no existe
if "procedimiento_pt" not in st.session_state:
    st.session_state.procedimiento_pt = procedimiento_default

procedimiento = st.text_input("PROCEDIMIENTO:", value=st.session_state.procedimiento_pt, help="Procedimiento utilizado para la inspección de líquidos penetrantes")

# Actualizar session_state cuando cambie
st.session_state.procedimiento_pt = procedimiento

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
kits_disponibles = get_kits_disponibles("PT")
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

# Sección 2: Materiales Utilizados
st.subheader("Materiales Utilizados")

# Define material data (could be moved to a config file later)
materiales_pt_data = {
    "PENETRANTE": {
        "Met-L-Company": ["Met-L-Chek VP-30", "Met-L-Chek FP-95A(M)"],
        "Sherwin": ["SKL-SP2"],
    },
    "EMULSIFICANTE": {
        "Met-L-Company": ["Met-L-Chek E-59A"],
        "N.A.": ["N.A."]
    },
    "LIMPIADOR": {
        "Met-L-Company": ["Met-L-Chek E-59A"],
        "Sherwin": ["SKC-S"],
    },
    "REVELADOR": {
        "Met-L-Company": ["Met-L-Chek D-70"],
        "Sherwin": ["SKD-S2"],
    }
}

# Initialize session state for materials
if "materiales_utilizados_pt" not in st.session_state:
    st.session_state.materiales_utilizados_pt = {
        "PENETRANTE": {"fabricante": "Met-L-Company", "referencia": "Met-L-Chek VP-30", "lote": ""},
        "EMULSIFICANTE": {"fabricante": "N.A.", "referencia": "N.A.", "lote": "N.A."},
        "LIMPIADOR": {"fabricante": "Met-L-Company", "referencia": "Met-L-Chek E-59A", "lote": ""},
        "REVELADOR": {"fabricante": "Met-L-Company", "referencia": "Met-L-Chek D-70", "lote": ""},
    }

materiales_values = st.session_state.materiales_utilizados_pt

# Create header
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**DETALLES**")
with col2:
    st.markdown("**FABRICANTE**")
with col3:
    st.markdown("**REFERENCIA COMERCIAL**")
with col4:
    st.markdown("**LOTE N°**")

# Create rows for each material
for detalle in ["PENETRANTE", "EMULSIFICANTE", "LIMPIADOR", "REVELADOR"]:
    
    current_material = materiales_values[detalle]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write(f"**{detalle}**")

    with col2:
        fabricantes = list(materiales_pt_data[detalle].keys())
        try:
            fabricante_idx = fabricantes.index(current_material["fabricante"])
        except ValueError:
            fabricante_idx = 0
        
        selected_fabricante = st.selectbox(
            f"fabricante_{detalle}",
            options=fabricantes,
            index=fabricante_idx,
            label_visibility="collapsed"
        )
        current_material["fabricante"] = selected_fabricante

    with col3:
        referencias = materiales_pt_data[detalle].get(current_material["fabricante"], [])
        
        if current_material["referencia"] not in referencias:
            current_material["referencia"] = referencias[0] if referencias else ""

        try:
            referencia_idx = referencias.index(current_material["referencia"])
        except (ValueError, IndexError):
            referencia_idx = 0

        selected_referencia = st.selectbox(
            f"referencia_{detalle}",
            options=referencias,
            index=referencia_idx,
            label_visibility="collapsed"
        )
        current_material["referencia"] = selected_referencia

    with col4:
        lote_val = st.text_input(f"lote_{detalle}", value=current_material["lote"], label_visibility="collapsed")
        current_material["lote"] = lote_val

# Sección 3: Normas para Procedimientos y Métodos de Aplicación
st.subheader("Normas para Procedimientos y Métodos de Aplicación")

# Inicializar estándares ASTM en session_state si no existen
if "estandares_astm_pt" not in st.session_state:
    st.session_state.estandares_astm_pt = [
        "ASTM E 165: Standard Test Method for Liquid Penetrant Examination",
        "ASTM E 1417: Standard Practice for Liquid Penetrant Examination"
    ]

# Campo para estándares ASTM
st.markdown("**ESTÁNDARES ASTM:**")
astm_e165 = st.text_input(
    "ASTM E 165:",
    value=st.session_state.estandares_astm_pt[0] if len(st.session_state.estandares_astm_pt) > 0 else "ASTM E 165: Standard Test Method for Liquid Penetrant Examination",
    key="astm_e165_pt"
)
astm_e1417 = st.text_input(
    "ASTM E 1417:",
    value=st.session_state.estandares_astm_pt[1] if len(st.session_state.estandares_astm_pt) > 1 else "ASTM E 1417: Standard Practice for Liquid Penetrant Examination",
    key="astm_e1417_pt"
)

# Actualizar session_state
st.session_state.estandares_astm_pt = [astm_e165, astm_e1417]

st.markdown("---")

# Opciones para el tipo de líquidos penetrantes
opciones_tipo = ["Visibles", "Fluorescentes"]
tipo_seleccionado = st.selectbox("TIPO:", options=opciones_tipo, index=0)
tipo = f"II - Líquidos Penetrantes {tipo_seleccionado}"

# Opciones para el método de líquidos penetrantes
opciones_metodo = [
    "A: Lavables con agua",
    "B: Postemulsificantes", 
    "C: Eliminables con Disolvente"
]
metodo = st.selectbox("MÉTODO:", options=opciones_metodo, index=2)

pasos_procedimiento = st.text_area(
    "PASOS DEL PROCEDIMIENTO:",
    """1. Limpieza de la superficie con método manual (con paño).
2. Aplicación de limpiador.
3. Aplicación del líquido penetrante (tiempo de penetración: 10:00 min).
4. Limpieza del líquido penetrante.
5. Aplicación de revelador (tiempo de revelado: 10:00 min).
6. Limpieza final."""
)

# Sección 4: Parámetros de Operación
st.subheader("Parámetros de Operación")

# Initialize session state for operation parameters
if "parametros_operacion_pt" not in st.session_state:
    st.session_state.parametros_operacion_pt = [
        {"actividad": "LIMPIEZA", "tiempo": 5, "temperatura": "26° C", "aplicacion": "Spray", "iluminacion": "Luz Natural"},
        {"actividad": "PENETRANTE", "tiempo": 12, "temperatura": "26° C", "aplicacion": "Spray", "iluminacion": "Luz Natural"},
        {"actividad": "LIMPIEZA", "tiempo": 3, "temperatura": "26° C", "aplicacion": "Spray", "iluminacion": "Luz Natural"},
        {"actividad": "REVELADOR", "tiempo": 10, "temperatura": "26° C", "aplicacion": "Spray", "iluminacion": "Luz Natural"},
    ]

# Header
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown("**ACTIVIDAD**")
c2.markdown("**TIEMPO DE PERMANENCIA (min)**")
c3.markdown("**TEMPERATURA**")
c4.markdown("**APLICACIÓN**")
c5.markdown("**ILUMINACIÓN**")

# Rows
for i, param in enumerate(st.session_state.parametros_operacion_pt):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.write(param["actividad"])
    with c2:
        param["tiempo"] = st.number_input(f"tiempo_{i}", min_value=0, max_value=999, value=param["tiempo"], step=1, label_visibility="collapsed", key=f"tiempo_pt_{i}", help="Tiempo en minutos")
    with c3:
        param["temperatura"] = st.text_input(f"temperatura_{i}", value=param["temperatura"], label_visibility="collapsed", key=f"temperatura_pt_{i}")
    with c4:
        aplicacion_options = ["Spray", "Brocha", "Inmersión"]
        aplicacion_idx = aplicacion_options.index(param["aplicacion"]) if param["aplicacion"] in aplicacion_options else 0
        param["aplicacion"] = st.selectbox(f"aplicacion_{i}", options=aplicacion_options, index=aplicacion_idx, label_visibility="collapsed", key=f"aplicacion_pt_{i}")
    with c5:
        iluminacion_options = ["Luz Natural", "Luz Artificial", "Luz UV"]
        iluminacion_idx = iluminacion_options.index(param["iluminacion"]) if param["iluminacion"] in iluminacion_options else 0
        param["iluminacion"] = st.selectbox(f"iluminacion_{i}", options=iluminacion_options, index=iluminacion_idx, label_visibility="collapsed", key=f"iluminacion_pt_{i}")

# Sección 5: Interpretación y Evaluación de Resultados
st.subheader("Interpretación y Evaluación de Resultados")

# --- Elementos Inspeccionados Heredados Automáticamente ---

st.write("---")
st.subheader("Elementos Inspeccionados")

# Heredar elementos de inspección visual automáticamente (solo nuevos elementos)
elementos_key = "tabla_elementos_3_1"

# Inicializar si no existe
if elementos_key not in st.session_state:
    st.session_state[elementos_key] = []

bulk_col_1, bulk_col_2 = st.columns([2, 1.5])
with bulk_col_1:
    if st.button("Marcar toda la sección como Fuera de Alcance", key="bulk_fda_pt"):
        for idx in range(len(st.session_state[elementos_key])):
            st.session_state[elementos_key][idx]["calificacion"] = "Fuera de Alcance"
        st.rerun()
with bulk_col_2:
    if st.button("Restablecer sección", key="bulk_reset_pt"):
        for idx in range(len(st.session_state[elementos_key])):
            st.session_state[elementos_key][idx]["calificacion"] = "Satisfactorio"
        st.rerun()

# Clave para rastrear los IDs de elementos ya heredados
elementos_heredados_key = "elementos_heredados_ids_3_1"
if elementos_heredados_key not in st.session_state:
    st.session_state[elementos_heredados_key] = set()

# Función para mapear calificaciones de visual a líquidos penetrantes
def mapear_calificacion_visual_a_liquidos(calificacion_visual):
    """Mapea la calificación de inspección visual al formato de líquidos penetrantes"""
    cal_upper = str(calificacion_visual).upper().strip()
    
    # Mapeo de calificaciones
    if "(C)" in cal_upper or "CONFORME" in cal_upper:
        if "(R)" in cal_upper or "REPARACION" in cal_upper or "REPARACIÓN" in cal_upper:
            # Conforme después de reparación -> Satisfactorio (ya que no hay equivalente exacto)
            return "Satisfactorio"
        else:
            return "Satisfactorio"
    elif "(NC)" in cal_upper or "NO CONFORME" in cal_upper:
        return "No Satisfactorio"
    elif "(RI)" in cal_upper or "REINSPECCIONAR" in cal_upper or "RE INSPECCIONAR" in cal_upper:
        return "Fuera de Alcance"  # O podría ser "Satisfactorio" dependiendo de la lógica
    else:
        # Por defecto, mapear a Satisfactorio
        return "Satisfactorio"

# Sincronizar solo nuevos elementos de inspección visual
if "tabla_elementos_2_1" in st.session_state and st.session_state.tabla_elementos_2_1:
    elementos_nuevos = 0
    for elemento in st.session_state.tabla_elementos_2_1:
        # Crear un ID único para cada elemento basado en su número y descripción
        elemento_id = f"{elemento['numero']}_{elemento['descripcion']}"
        
        # Solo agregar si no ha sido heredado antes
        if elemento_id not in st.session_state[elementos_heredados_key]:
            # Mapear la calificación de visual a líquidos penetrantes
            calificacion_mapeada = mapear_calificacion_visual_a_liquidos(elemento.get("calificacion", "(C) Conforme"))
            
            # Crear una copia independiente del elemento
            elemento_copia = {
                "id": uuid.uuid4().hex,
                "numero": elemento["numero"],
                "descripcion": elemento["descripcion"],
                "indicacion": elemento["indicacion"],
                "calificacion": calificacion_mapeada,  # Mapear la calificación original
                "observacion": elemento["observacion"]
            }
            st.session_state[elementos_key].append(elemento_copia)
            st.session_state[elementos_heredados_key].add(elemento_id)
            elementos_nuevos += 1
    
    if elementos_nuevos > 0:
        st.success(f"✅ {elementos_nuevos} elemento(s) nuevo(s) heredado(s) de Inspección Visual")
    elif len(st.session_state[elementos_key]) > 0:
        st.info(f"📋 Elementos actuales: {len(st.session_state[elementos_key])} (editables de forma independiente)")
else:
    if len(st.session_state[elementos_key]) == 0:
        st.info("💡 No hay elementos en Inspección Visual para heredar. Los elementos aparecerán automáticamente cuando se agreguen en el módulo de Inspección Visual.")

# Función para agregar una nueva fila
def agregar_fila_elemento_pt():
    nuevo_numero = len(st.session_state[elementos_key]) + 1
    nueva_fila = {
        "id": uuid.uuid4().hex,
        "numero": str(nuevo_numero),
        "descripcion": "",
        "indicacion": "",
        "calificacion": "Satisfactorio",
        "observacion": ""
    }
    st.session_state[elementos_key].append(nueva_fila)

# Opciones para la calificación
opciones_calificacion = ["Satisfactorio", "No Satisfactorio", "Fuera de Alcance"]

# Crear la tabla de elementos
if st.session_state[elementos_key]:
    # Encabezados de la tabla
    col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 3])
    col1.markdown("**No.**")
    col2.markdown("**Descripción del Elemento**")
    col3.markdown("**Indicación**")
    col4.markdown("**Calificación**")
    col5.markdown("**Observación**")

    # Filas de la tabla
    for i, elemento in enumerate(st.session_state[elementos_key]):
        if "id" not in elemento:
            elemento["id"] = uuid.uuid4().hex
        c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 3])
        
        # Número (solo lectura)
        c1.write(elemento["numero"])
        
        # Descripción (editable)
        st.session_state[elementos_key][i]["descripcion"] = c2.text_input(
            f"Descripción del elemento {elemento['numero']}",
            value=elemento["descripcion"],
            key=f"elem_desc_3_1_{elemento['id']}",
            label_visibility="collapsed"
        )
        
        # Indicación (editable)
        indicacion_val = c3.text_input(
            f"Indicación del elemento {elemento['numero']}",
            value=elemento["indicacion"],
            key=f"elem_ind_3_1_{elemento['id']}",
            label_visibility="collapsed"
        )
        st.session_state[elementos_key][i]["indicacion"] = indicacion_val
        indicacion_tiene_texto = bool(indicacion_val.strip())
        if indicacion_tiene_texto:
            st.session_state[elementos_key][i]["calificacion"] = "No Satisfactorio"
 
        # Calificación (editable)
        calificacion_seleccionada = c4.selectbox(
            f"Calificación del elemento {elemento['numero']}",
            options=opciones_calificacion,
            index=opciones_calificacion.index(elemento["calificacion"]),
            key=f"elem_cal_3_1_{elemento['id']}",
            label_visibility="collapsed",
            disabled=indicacion_tiene_texto,
            help="Se fuerza a No Satisfactorio cuando hay texto en Indicación." if indicacion_tiene_texto else None
        )
        if not indicacion_tiene_texto:
            st.session_state[elementos_key][i]["calificacion"] = calificacion_seleccionada
        
        # Observación (editable)
        st.session_state[elementos_key][i]["observacion"] = c5.text_area(
            f"Observación del elemento {elemento['numero']}",
            value=elemento["observacion"],
            key=f"elem_obs_3_1_{elemento['id']}",
            height=70,
            label_visibility="collapsed"
        )
        
        # Botones para eliminar y duplicar fila
        col_elim, col_dupl = c5.columns(2)
        if col_elim.button("Eliminar", key=f"elem_eliminar_3_1_{elemento['id']}", use_container_width=True):
            st.session_state[elementos_key].pop(i)
            # Re-enumerar secuencialmente
            for idx, elem in enumerate(st.session_state[elementos_key]):
                elem["numero"] = str(idx + 1)
            st.rerun()
        if col_dupl.button("Duplicar", key=f"elem_duplicar_3_1_{elemento['id']}", use_container_width=True):
            nuevo_elemento = st.session_state[elementos_key][i].copy()
            nuevo_elemento["id"] = uuid.uuid4().hex
            st.session_state[elementos_key].insert(i + 1, nuevo_elemento)
            # Re-enumerar secuencialmente
            for idx, elem in enumerate(st.session_state[elementos_key]):
                elem["numero"] = str(idx + 1)
            st.rerun()
else:
    st.info("No hay elementos inspeccionados. Use el botón 'Agregar Elemento' para comenzar.")

if st.button("Agregar Elemento", key="agregar_elemento_pt"):
    agregar_fila_elemento_pt()
    st.rerun()

# Inicializar resultados_pt para compatibilidad
if "resultados_pt" not in st.session_state:
    st.session_state.resultados_pt = []

# Sección 6: Esquema y Detalles
st.subheader("Esquema y Detalles")

# Inicializar esquema del módulo actual
esquema_key = "esquema_3_1"
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
    key="upload_esquema_pt",
    accept_multiple_files=True
)

if uploaded_files_esquema:
    if st.button("Agregar Imágenes al Esquema", key="agregar_esquema_pt"):
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
    if st.button("Re-heredar de Inspección Visual", key="reheredar_esquema_pt"):
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
    if st.button("Limpiar Esquema", key="limpiar_esquema_pt"):
        st.session_state[esquema_key] = []
        st.success("✅ Esquema limpiado")
        st.rerun()

# Mostrar las imágenes del esquema
if len(st.session_state[esquema_key]) == 0:
    st.info("No hay esquema cargado todavía. Sube imágenes o hereda desde Inspección Visual.")
else:
    st.success(f"✅ Esquema de Líquidos Penetrantes: {len(st.session_state[esquema_key])} imágenes cargadas")
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
                key=f"comentario_esquema_pt_{i}"
            )
            st.session_state[esquema_key][i]["comentario"] = nuevo_comentario
            
            if st.button("Eliminar imagen", key=f"eliminar_esquema_pt_{i}"):
                st.session_state[esquema_key].pop(i)
                st.rerun()

detalle_resultados = st.text_area("DETALLE DE ELEMENTOS INSPECCIONADOS Y RESULTADOS:", "")

# Sección 7: Observaciones y Registros
st.subheader("Observaciones y Registros")
observaciones_generales = st.text_area("OBSERVACIONES GENERALES:", "")

# Sección 8: Registros Fotográficos
st.subheader("Registros Fotográficos")

if "imagenes_3_1" not in st.session_state:
    st.session_state.imagenes_3_1 = []

if "delete_idx_3_1" not in st.session_state:
    st.session_state.delete_idx_3_1 = None

st.subheader("Cargar nuevas imágenes")
uploaded_files = st.file_uploader(
    "Selecciona una o varias imágenes",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if st.button("Agregar Imágenes", key="agregar_imagenes_pt"):
    if uploaded_files:
        for file in uploaded_files:
            nueva_imagen = {
                "archivo": file,
                "nombre": file.name,
                "comentario": ""
            }
            st.session_state.imagenes_3_1.append(nueva_imagen)
    else:
        st.warning("No has seleccionado ningún archivo.")

st.write("---")

st.subheader("Imágenes cargadas")
if len(st.session_state.imagenes_3_1) == 0:
    st.info("No hay imágenes cargadas todavía.")
else:
    for i, img_info in enumerate(st.session_state.imagenes_3_1):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(img_info["archivo"], use_container_width=True)
        
        with col2:
            st.write(f"**Archivo:** {img_info['nombre']}")
            nuevo_comentario = st.text_area(
                "Comentario",
                value=img_info["comentario"],
                key=f"comentario_3_1_{i}"
            )
            st.session_state.imagenes_3_1[i]["comentario"] = nuevo_comentario
            
            if st.button("Eliminar esta imagen", key=f"eliminar_3_1_{i}"):
                st.session_state.delete_idx_3_1 = i

    if st.session_state.delete_idx_3_1 is not None:
        st.session_state.imagenes_3_1.pop(st.session_state.delete_idx_3_1)
        st.session_state.delete_idx_3_1 = None
        st.rerun()

st.write("---")

st.subheader("Datos finales (diccionario)")
datos_finales = {
    "imagenes": st.session_state.imagenes_3_1,  # Incluir el objeto completo con archivo, nombre y comentario
    "resultados": st.session_state.resultados_pt,
    "esquema_elementos": [],  # Lista vacía por defecto
    "detalle_resultados": detalle_resultados,
    "observaciones_generales": observaciones_generales
}

saved_key = "saved_3_1"
if saved_key not in st.session_state:
    st.session_state[saved_key] = "bloque_3_1" in st.session_state

if st.button("Guardar Datos", key="guardar_datos_pt", type="primary"):
    st.write("### Datos guardados correctamente")
    
    st.session_state.bloque_3_1 = {
        "norma": norma_global,
        "especificacion": materiales_editados,
        "proceso": procesos_editados,
        "equipos": kit_seleccionado,
        "materiales": st.session_state.materiales_utilizados_pt,
        "estandares_astm": st.session_state.estandares_astm_pt,
        "tipo": tipo,
        "metodo": metodo,
        "procedimiento": procedimiento,
        "pasos_procedimiento": pasos_procedimiento,
        "parametros": st.session_state.parametros_operacion_pt,
        "resultados": st.session_state.resultados_pt,
        "elementos_inspeccionados": st.session_state[elementos_key],  # Agregar elementos inspeccionados
        "esquema_elementos": st.session_state[esquema_key],  # Usar esquema independiente
        "detalle_resultados": detalle_resultados,
        "observaciones_generales": observaciones_generales,
        "registros_fotograficos": datos_finales["imagenes"]
    }
    persist_session_state()
    st.session_state[saved_key] = True
    st.rerun()

if st.session_state.get(saved_key, False):
    if st.button("Siguiente sección", key="siguiente_seccion_3_1", type="primary"):
        st.switch_page("4_datos_de_inspeccion_de_particulas_magneticas.py")
