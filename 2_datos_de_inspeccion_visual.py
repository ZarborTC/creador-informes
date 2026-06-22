import streamlit as st
import pandas as pd
import os
import uuid
from utils import (
    cargar_kits, cargar_procedimientos, cargar_materiales,
    get_norma_global, get_material_base, get_kits_disponibles,
    get_componentes_kit, get_tipo_inspeccion, materiales_base,
    get_materiales_base_seleccionados, get_procesos_soldadura_seleccionados,
    get_tipos_soldadura_seleccionados, procesos_soldadura, tipos_soldadura,
    get_esquema_elementos_global
)
from save_state import persist_session_state

# Obtener listas de configuración
procedimientos = cargar_procedimientos()
kits = cargar_kits()
materiales = cargar_materiales()

# Preparar opciones para los selectores
opciones_procedimientos = [f"{p['codigo']} - {p['nombre']} {p['revision']}" for p in procedimientos]

# Agrupar materiales por tipo
materiales_por_tipo = {}
for material in materiales:
    tipo = material['tipo']
    if tipo not in materiales_por_tipo:
        materiales_por_tipo[tipo] = []
    materiales_por_tipo[tipo].append(material)

st.title("👁️ 2 Datos de Inspección Visual")

# Sección 1: Información General
st.subheader("Información General")

# Obtener la norma global
norma_global = get_norma_global()
st.write(f"**Norma Global del Proyecto:** {norma_global}")

# Procedimiento editable para Inspección Visual
procedimiento_default = "TLPR0025 - Inspección Visual - Rev. 1"

# Inicializar procedimiento en session_state si no existe
if "procedimiento_visual" not in st.session_state:
    st.session_state.procedimiento_visual = procedimiento_default

procedimiento = st.text_input("PROCEDIMIENTO:", value=st.session_state.procedimiento_visual, help="Procedimiento utilizado para la inspección visual")

# Actualizar session_state cuando cambie
st.session_state.procedimiento_visual = procedimiento

# Determinar el tipo de inspección basado en el procedimiento predefinido
tipo_inspeccion = get_tipo_inspeccion(procedimiento)

# Filtrar kits disponibles según el tipo de inspección
kits_disponibles = get_kits_disponibles(tipo_inspeccion) if tipo_inspeccion else []
opciones_kits = [f"{kit['nombre']} - {kit['descripcion']}" for kit in kits_disponibles]

# Selector único de kit
kit_seleccionado = st.selectbox(
    "EQUIPOS UTILIZADOS:",
    options=opciones_kits,
    help="Selecciona el kit necesario para la inspección"
)

# Mostrar componentes del kit seleccionado
if kit_seleccionado:
    componentes = get_componentes_kit(kit_seleccionado, kits_disponibles)
    if componentes:
        componentes_texto = ", ".join(componentes)
        kit = next((k for k in kits_disponibles if f"{k['nombre']} - {k['descripcion']}" == kit_seleccionado), None)
        if kit:
            st.write(f"**{kit['nombre']}:** {componentes_texto}")

st.write("---")

# Selector múltiple de material base
st.subheader("Especificación de Material Base")
st.markdown("Seleccione una o más especificaciones de material base:")

materiales_seleccionados = st.multiselect(
    "ESPECIFICACIÓN MATERIAL BASE:",
    options=materiales_base,
    default=get_materiales_base_seleccionados(),
    help="Selecciona una o más especificaciones del material base"
)

# Guardar en session_state
st.session_state.materiales_base_seleccionados = materiales_seleccionados

# Mostrar materiales seleccionados
if materiales_seleccionados:
    st.success(f"Materiales seleccionados: {', '.join(materiales_seleccionados)}")
else:
    st.warning("No se han seleccionado materiales base")

st.write("---")

# --- NUEVO BLOQUE: Proceso de soldadura y Tipo con selección múltiple ---
st.subheader("Proceso de Soldadura")
st.markdown("Seleccione uno o más procesos y tipos de soldadura:")

col_proc, col_tipo = st.columns(2)
with col_proc:
    procesos_seleccionados = st.multiselect(
        "Procesos de soldadura:",
        options=procesos_soldadura,
        default=get_procesos_soldadura_seleccionados(),
        help="Selecciona uno o más procesos de soldadura"
    )
    st.session_state.procesos_soldadura_seleccionados = procesos_seleccionados

with col_tipo:
    tipos_seleccionados = st.multiselect(
        "Tipos de soldadura:",
        options=tipos_soldadura,
        default=get_tipos_soldadura_seleccionados(),
        help="Selecciona uno o más tipos de soldadura"
    )
    st.session_state.tipos_soldadura_seleccionados = tipos_seleccionados

# Mostrar selecciones
if procesos_seleccionados:
    st.success(f"Procesos seleccionados: {', '.join(procesos_seleccionados)}")
if tipos_seleccionados:
    st.success(f"Tipos seleccionados: {', '.join(tipos_seleccionados)}")

if not procesos_seleccionados:
    st.warning("No se han seleccionado procesos de soldadura")
if not tipos_seleccionados:
    st.warning("No se han seleccionado tipos de soldadura")
# --- NUEVO BLOQUE: Proceso de soldadura y Tipo con selección múltiple ---

# Sección 2: Fases de Inspección
st.subheader("Fases de Inspección")

# Definir los ítems por fase
fases_items = [
    {
        "fase": "ANTES DE INICIAR EL PROCESO DE SOLDADURA",
        "items": [
            "Chequear la calificación del personal",
            "Chequear el tipo del material base y el de aporte",
            "Chequear si hay algún tipo discontinuidad en el metal base",
            "Chequear el alineamiento de la junta de soldadura",
            "Chequear condiciones de precalentamiento"
        ]
    },
    {
        "fase": "INICIO DE LA SOLDADURA",
        "items": [
            "Ángulo de chaflán",
            "Hombro de raíz",
            "Alineamiento de la junta",
            "Respaldo con soldadura o platina",
            "Limpieza de la junta",
            "Puntos de soldadura (si se punteo)",
            "Precalentamiento"
        ]
    },
    {
        "fase": "DESPUÉS DE LA SOLDADURA",
        "items": [
            "Apariencia final de la soldadura",
            "Tamaño final de la soldadura",
            "Longitud de la soldadura",
            "Cantidad de distorsión (en la pieza)",
            "Tratamiento Térmico después de la soldadura"
        ]
    }
]

# Inicializar el estado de la tabla de fases si no existe
if "tabla_fases_2_1" not in st.session_state:
    st.session_state.tabla_fases_2_1 = []
    for fase in fases_items:
        for item in fase["items"]:
            st.session_state.tabla_fases_2_1.append({
                "fase": fase["fase"],
                "item": item,
                "aplica": "Aplica",
                "resultado": "Satisfactorio",
                "observacion": ""
            })
else:
    # Migrar etiquetas de fase antiguas a nombres canónicos para mantener compatibilidad
    fase_canonica = {
        "ANTES DE INICIAR EL PROCESO DE SOLDADURA": "ANTES DE INICIAR EL PROCESO DE SOLDADURA",
        "INICIO DE LA SOLDADURA": "INICIO DE LA SOLDADURA",
        "DESPUÉS DE LA SOLDADURA": "DESPUÉS DE LA SOLDADURA",
    }

    for idx, fila in enumerate(st.session_state.tabla_fases_2_1):
        nombre = str(fila.get("fase", "")).upper().strip()
        if "ANTES DE INICIAR" in nombre:
            st.session_state.tabla_fases_2_1[idx]["fase"] = fase_canonica["ANTES DE INICIAR EL PROCESO DE SOLDADURA"]
        elif "INICIO" in nombre:
            st.session_state.tabla_fases_2_1[idx]["fase"] = fase_canonica["INICIO DE LA SOLDADURA"]
        elif "DESPUÉS" in nombre or "DESPUES" in nombre:
            st.session_state.tabla_fases_2_1[idx]["fase"] = fase_canonica["DESPUÉS DE LA SOLDADURA"]

    # Asegurar que existan todos los ítems esperados en cada fase
    existentes = {
        (f.get("fase", ""), f.get("item", ""))
        for f in st.session_state.tabla_fases_2_1
    }
    for fase in fases_items:
        for item in fase["items"]:
            key = (fase["fase"], item)
            if key not in existentes:
                st.session_state.tabla_fases_2_1.append({
                    "fase": fase["fase"],
                    "item": item,
                    "aplica": "Aplica",
                    "resultado": "Satisfactorio",
                    "observacion": ""
                })

opciones_aplica = ["Aplica", "No Aplica", "Fuera de Alcance"]
opciones_resultado = ["Satisfactorio", "No satisfactorio"]

# Mostrar la tabla de fases con ítems
for fase in fases_items:
    phase_indices = [
        idx for idx, fila in enumerate(st.session_state.tabla_fases_2_1)
        if fila["fase"] == fase["fase"]
    ]

    st.markdown(f"**{fase['fase']}**")
    action_col_1, action_col_2, action_col_3 = st.columns([2, 2, 1.5])
    with action_col_1:
        if st.button("Marcar sección como No Aplica", key=f"fase_no_aplica_{fase['fase']}"):
            for idx in phase_indices:
                st.session_state.tabla_fases_2_1[idx]["aplica"] = "No Aplica"
                st.session_state.tabla_fases_2_1[idx]["resultado"] = "No Aplica"
                st.session_state[f"fase_aplica_2_1_{idx}"] = "No Aplica"
                st.session_state[f"fase_resultado_2_1_{idx}"] = "No Aplica"
            st.rerun()
    with action_col_2:
        if st.button("Marcar sección como Fuera de Alcance", key=f"fase_fuera_{fase['fase']}"):
            for idx in phase_indices:
                st.session_state.tabla_fases_2_1[idx]["aplica"] = "Fuera de Alcance"
                st.session_state.tabla_fases_2_1[idx]["resultado"] = "Fuera de Alcance"
                st.session_state[f"fase_aplica_2_1_{idx}"] = "Fuera de Alcance"
                st.session_state[f"fase_resultado_2_1_{idx}"] = "Fuera de Alcance"
            st.rerun()
    with action_col_3:
        if st.button("Restablecer sección", key=f"fase_reset_{fase['fase']}"):
            for idx in phase_indices:
                st.session_state.tabla_fases_2_1[idx]["aplica"] = "Aplica"
                st.session_state.tabla_fases_2_1[idx]["resultado"] = "Satisfactorio"
                st.session_state[f"fase_aplica_2_1_{idx}"] = "Aplica"
                st.session_state[f"fase_resultado_2_1_{idx}"] = "Satisfactorio"
            st.rerun()

    # Encabezados
    col1, col2, col3, col4 = st.columns([3, 2, 2, 5])
    col1.markdown("**Ítem**")
    col2.markdown("**¿Aplica?**")
    col3.markdown("**Resultado**")
    col4.markdown("**Observaciones**")
    # Filas
    for i, idx in enumerate(phase_indices):
        fila = st.session_state.tabla_fases_2_1[idx]
        c1, c2, c3, c4 = st.columns([3, 2, 2, 5])
        c1.write(fila["item"])
        aplica_key = f"fase_aplica_2_1_{idx}"
        resultado_key = f"fase_resultado_2_1_{idx}"

        aplica_sel = c2.selectbox(
            f"Aplica para {fila['item']}",
            options=opciones_aplica,
            index=opciones_aplica.index(fila["aplica"]),
            key=aplica_key,
            label_visibility="collapsed"
        )
        st.session_state.tabla_fases_2_1[idx]["aplica"] = aplica_sel
        aplica_val = aplica_sel
        if aplica_val == "Aplica":
            # Obtener el resultado actual y validar que esté en las opciones disponibles
            resultado_actual = st.session_state.tabla_fases_2_1[idx].get("resultado", "Satisfactorio")
            if resultado_actual not in opciones_resultado:
                resultado_actual = "Satisfactorio"

            resultado_sel = c3.selectbox(
                f"Resultado para {fila['item']}",
                options=opciones_resultado,
                index=opciones_resultado.index(resultado_actual),
                key=resultado_key,
                label_visibility="collapsed"
            )
            st.session_state.tabla_fases_2_1[idx]["resultado"] = resultado_sel
        else:
            # Si no aplica o está fuera de alcance, el resultado es igual al valor de aplica
            st.session_state.tabla_fases_2_1[idx]["resultado"] = aplica_val
            st.session_state[resultado_key] = aplica_val
            c3.write(aplica_val)
        st.session_state.tabla_fases_2_1[idx]["observacion"] = c4.text_area(
            f"Observación para {fila['item']}",
            value=fila["observacion"],
            key=f"fase_obs_2_1_{idx}",
            height=70,
            label_visibility="collapsed"
        )
    st.write("")

st.write("---")

# Sección 3: Elementos Inspeccionados
st.subheader("Elementos Inspeccionados")

# Mensaje informativo sobre la herencia
st.info("💡 **Nota importante:** Los elementos que agregues aquí serán heredados automáticamente por los módulos de Líquidos Penetrantes y Partículas Magnéticas. Cada módulo podrá editar sus propios elementos de forma independiente.")

# Inicializar el estado de la tabla de elementos si no existe
if "tabla_elementos_2_1" not in st.session_state:
    st.session_state.tabla_elementos_2_1 = []

# Función para agregar una nueva fila
def agregar_fila_elemento():
    nuevo_numero = len(st.session_state.tabla_elementos_2_1) + 1
    nueva_fila = {
        "id": uuid.uuid4().hex,
        "numero": str(nuevo_numero),
        "descripcion": "",
        "indicacion": "",
        "calificacion": "(C) Conforme",
        "observacion": ""
    }
    st.session_state.tabla_elementos_2_1.append(nueva_fila)


# Opciones para la calificación
opciones_calificacion = ["(C) Conforme", "(NC) No conforme", "(RI) Reinspeccionar", "(C(R)) Conforme después de reparación"]


# Crear la tabla de elementos
if st.session_state.tabla_elementos_2_1:
    # Encabezados de la tabla
    col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 3])
    col1.markdown("**No.**")
    col2.markdown("**Descripción del Elemento**")
    col3.markdown("**Indicación**")
    col4.markdown("**Calificación**")
    col5.markdown("**Observación**")

    # Filas de la tabla
    for i, elemento in enumerate(st.session_state.tabla_elementos_2_1):
        if "id" not in elemento:
            elemento["id"] = uuid.uuid4().hex
        c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 3])
        
        # Número (solo lectura)
        c1.write(elemento["numero"])
        
        # Descripción
        st.session_state.tabla_elementos_2_1[i]["descripcion"] = c2.text_input(
            f"Descripción del elemento {elemento['numero']}",
            value=elemento["descripcion"],
            key=f"elem_desc_2_1_{elemento['id']}",
            label_visibility="collapsed"
        )
        
        # Indicación
        indicacion_val = c3.text_input(
            f"Indicación del elemento {elemento['numero']}",
            value=elemento["indicacion"],
            key=f"elem_ind_2_1_{elemento['id']}",
            label_visibility="collapsed"
        )
        st.session_state.tabla_elementos_2_1[i]["indicacion"] = indicacion_val
        indicacion_tiene_texto = bool(indicacion_val.strip())
        if indicacion_tiene_texto:
            st.session_state.tabla_elementos_2_1[i]["calificacion"] = "(NC) No conforme"
        
        # Calificación
        calificacion_actual = elemento["calificacion"]
        try:
            index_calificacion = opciones_calificacion.index(calificacion_actual)
        except ValueError:
            # Si el valor no está en la lista, usar el primer valor por defecto
            index_calificacion = 0
            calificacion_actual = opciones_calificacion[0]
        
        calificacion_seleccionada = c4.selectbox(
            f"Calificación del elemento {elemento['numero']}",
            options=opciones_calificacion,
            index=index_calificacion,
            key=f"elem_cal_2_1_{elemento['id']}",
            label_visibility="collapsed",
            disabled=indicacion_tiene_texto,
            help="Se fuerza a No conforme cuando hay texto en Indicación." if indicacion_tiene_texto else None
        )
        if not indicacion_tiene_texto:
            st.session_state.tabla_elementos_2_1[i]["calificacion"] = calificacion_seleccionada
        
        # Observación
        st.session_state.tabla_elementos_2_1[i]["observacion"] = c5.text_area(
            f"Observación del elemento {elemento['numero']}",
            value=elemento["observacion"],
            key=f"elem_obs_2_1_{elemento['id']}",
            height=100,
            label_visibility="collapsed"
        )
        
        # Botones para eliminar y duplicar fila
        col_elim, col_dupl = c5.columns(2)
        if col_elim.button("Eliminar", key=f"elem_eliminar_2_1_{elemento['id']}", use_container_width=True):
            st.session_state.tabla_elementos_2_1.pop(i)
            # Re-enumerar secuencialmente
            for idx, elem in enumerate(st.session_state.tabla_elementos_2_1):
                elem["numero"] = str(idx + 1)
            st.rerun()
        if col_dupl.button("Duplicar", key=f"elem_duplicar_2_1_{elemento['id']}", use_container_width=True):
            nuevo_elemento = st.session_state.tabla_elementos_2_1[i].copy()
            nuevo_elemento["id"] = uuid.uuid4().hex
            st.session_state.tabla_elementos_2_1.insert(i + 1, nuevo_elemento)
            # Re-enumerar secuencialmente
            for idx, elem in enumerate(st.session_state.tabla_elementos_2_1):
                elem["numero"] = str(idx + 1)
            st.rerun()
else:
    st.info("No hay elementos inspeccionados. Use el botón 'Agregar Elemento' para comenzar.")

# Opciones para agregar elementos
col_cant, col_btn = st.columns([1, 2])
with col_cant:
    cantidad_a_agregar = st.number_input(
        "Cantidad a agregar:",
        min_value=1,
        max_value=100,
        value=1,
        step=1,
        key="cant_elementos_agregar_2_1"
    )
with col_btn:
    st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Agregar Elemento(s)", key="agregar_elemento_2_1", use_container_width=True):
        for _ in range(cantidad_a_agregar):
            agregar_fila_elemento()
        st.rerun()

st.write("---")

# Sección 4: Esquema y Detalles
st.subheader("Esquema y Detalles")

# Mensaje informativo sobre la herencia
st.info("💡 **Nota importante:** El esquema que subas aquí será heredado automáticamente por los otros módulos de inspección (Líquidos Penetrantes, Partículas Magnéticas y Ultrasonido). Cada módulo recibirá una copia independiente que podrá modificar sin afectar al esquema original ni a los esquemas de otros módulos.")

# Inicializar el estado global del esquema
esquema_global = get_esquema_elementos_global()

# Cargar nuevas imágenes del esquema
uploaded_files_esquema = st.file_uploader(
    "Selecciona las imágenes del esquema de inspección (puedes subir múltiples)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

def agregar_archivos_esquema(archivos):
    """Agrega archivos al esquema global evitando duplicados por nombre."""
    if not archivos:
        return 0

    nombres_actuales = {
        img.get("nombre")
        for img in esquema_global
        if isinstance(img, dict) and img.get("nombre")
    }

    agregadas = 0
    for file in archivos:
        if file.name in nombres_actuales:
            continue
        nueva_imagen = {
            "archivo": file,
            "nombre": file.name,
            "comentario": ""
        }
        esquema_global.append(nueva_imagen)
        nombres_actuales.add(file.name)
        agregadas += 1

    return agregadas

if st.button("Agregar Imágenes al Esquema", key="agregar_esquema_2_1"):
    if uploaded_files_esquema:
        agregadas = agregar_archivos_esquema(uploaded_files_esquema)
        if agregadas > 0:
            st.success(f"Se agregaron {agregadas} imágenes al esquema global")
        else:
            st.info("Las imágenes seleccionadas ya estaban en el esquema global.")
        st.rerun()
    else:
        st.warning("No has seleccionado ningún archivo.")

# Mostrar las imágenes del esquema global
if len(esquema_global) == 0:
    st.info("No hay esquema cargado todavía. Sube imágenes para crear el esquema global.")
else:
    st.success(f"✅ Esquema Global: {len(esquema_global)} imágenes cargadas")
    st.info("💡 Este esquema se compartirá automáticamente con todos los módulos de inspección.")
    
    for i, img_info in enumerate(esquema_global):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(img_info["archivo"], use_container_width=True)
        
        with col2:
            st.write(f"**Archivo:** {img_info['nombre']}")
            nuevo_comentario = st.text_area(
                "Comentario",
                value=img_info["comentario"],
                key=f"comentario_esquema_global_{i}"
            )
            esquema_global[i]["comentario"] = nuevo_comentario
            
            if st.button("Eliminar imagen", key=f"eliminar_esquema_global_{i}"):
                esquema_global.pop(i)
                st.rerun()

detalle_guardado = st.session_state.get("bloque_2_1", {}).get("detalle_resultados", "")
if "detalle_resultados_2_1" not in st.session_state:
    st.session_state.detalle_resultados_2_1 = detalle_guardado
detalle_resultados = st.text_area(
    "DETALLE DE ELEMENTOS INSPECCIONADOS Y RESULTADOS:",
    key="detalle_resultados_2_1"
)

st.write("---")

# Sección 5: Observaciones y Registros
st.subheader("Observaciones y Registros")
observaciones_guardadas = st.session_state.get("bloque_2_1", {}).get("observaciones_generales", "")
if "observaciones_generales_2_1" not in st.session_state:
    st.session_state.observaciones_generales_2_1 = observaciones_guardadas
observaciones_generales = st.text_area(
    "OBSERVACIONES GENERALES:",
    key="observaciones_generales_2_1"
)

# Sección 6: Registros Fotográficos
st.subheader("Registros Fotográficos")

if "imagenes_2_1" not in st.session_state:
    st.session_state.imagenes_2_1 = []

if "delete_idx_2_1" not in st.session_state:
    st.session_state.delete_idx_2_1 = None

uploaded_files = st.file_uploader(
    "Selecciona una o varias imágenes",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if st.button("Agregar Imágenes"):
    if uploaded_files:
        for file in uploaded_files:
            nueva_imagen = {
                "archivo": file,
                "nombre": file.name,
                "comentario": ""
            }
            st.session_state.imagenes_2_1.append(nueva_imagen)
    else:
        st.warning("No has seleccionado ningún archivo.")

st.write("---")

st.subheader("Imágenes cargadas")
if len(st.session_state.imagenes_2_1) == 0:
    st.info("No hay imágenes cargadas todavía.")
else:
    for i, img_info in enumerate(st.session_state.imagenes_2_1):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(img_info["archivo"], use_container_width=True)
        
        with col2:
            st.write(f"**Archivo:** {img_info['nombre']}")
            nuevo_comentario = st.text_area(
                "Comentario",
                value=img_info["comentario"],
                key=f"comentario_2_1_{i}"
            )
            st.session_state.imagenes_2_1[i]["comentario"] = nuevo_comentario
            
            if st.button("Eliminar esta imagen", key=f"eliminar_2_1_{i}"):
                st.session_state.delete_idx_2_1 = i

    if st.session_state.delete_idx_2_1 is not None:
        st.session_state.imagenes_2_1.pop(st.session_state.delete_idx_2_1)
        st.session_state.delete_idx_2_1 = None
        st.rerun()

st.write("---")

st.subheader("Datos finales (diccionario)")
datos_finales = {
    "imagenes": [
        {
            "nombre": img["nombre"],
            "comentario": img["comentario"]
        }
        for img in st.session_state.imagenes_2_1
    ]
}

saved_key = "saved_2_1"
if saved_key not in st.session_state:
    st.session_state[saved_key] = "bloque_2_1" in st.session_state

if st.button("Guardar Datos", key="guardar_datos_2_1", type="primary"):
    st.write("### Datos guardados correctamente")

    # Si el usuario seleccionó archivos pero no pulsó "Agregar Imágenes al Esquema",
    # incluirlos automáticamente al guardar para evitar perderlos.
    agregadas_guardado = agregar_archivos_esquema(uploaded_files_esquema)
    if agregadas_guardado > 0:
        st.info(f"Se agregaron automáticamente {agregadas_guardado} imágenes del esquema al guardar.")
    
    # Obtener los componentes del kit seleccionado
    componentes_seleccionados = []
    if kit_seleccionado:
        kit = next((k for k in kits_disponibles if f"{k['nombre']} - {k['descripcion']}" == kit_seleccionado), None)
        if kit:
            componentes_seleccionados = kit['componentes']
    
    # Guardar datos de inspección visual en formato para reporte
    # SOLO usar bloque_2_1 para evitar duplicación
    # NOTA: Se eliminó datos_inspeccion_visual para evitar conflictos de datos
    st.session_state.bloque_2_1 = {
        "norma": norma_global,
        "procedimiento": procedimiento,
        "equipos_utilizados": {
            "kit_seleccionado": kit_seleccionado,
            "componentes": componentes_seleccionados
        },
        "materiales_base": materiales_seleccionados,
        "procesos_soldadura": procesos_seleccionados,
        "tipos_soldadura": tipos_seleccionados,
        "fases_inspeccion": st.session_state.tabla_fases_2_1,
        "elementos_inspeccionados": st.session_state.tabla_elementos_2_1,
        "esquema": [
            {
                "archivo": img["archivo"],
                "nombre": img["nombre"],
                "comentario": img["comentario"]
            }
            for img in get_esquema_elementos_global()
        ],
        "detalle_resultados": detalle_resultados,
        "observaciones_generales": observaciones_generales,
        "registros_fotograficos": [
            {
                "archivo": img["archivo"],
                "nombre": img["nombre"],
                "comentario": img["comentario"]
            }
            for img in st.session_state.imagenes_2_1
        ]
    }
    persist_session_state()
    st.session_state[saved_key] = True

if st.session_state.get(saved_key, False):
    if st.button("Siguiente sección", key="siguiente_seccion_2_1", type="primary"):
        modulos_activos = st.session_state.get("pages_config", {}).get("modulos", [])
        if len(modulos_activos) <= 1:
            st.switch_page("bloque_reportes.py")
        else:
            st.switch_page("3_datos_de_inspeccion_de_liquidos_penetrantes.py")
