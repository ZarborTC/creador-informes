import streamlit as st
from save_state import get_saved_at, restore_session_state

st.set_page_config(
    page_title="Joint and Welding Form",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Modo de prueba: mostrar solo el módulo de inspección visual en la navegación
SOLO_REPORTE_VISUAL = True
MODULO_VISUAL = "2_datos_de_inspeccion_visual.py"

# Restaurar estado persistido en disco (solo datos guardados manualmente).
restored_from_disk = restore_session_state()
saved_at = get_saved_at()
if restored_from_disk and saved_at:
    st.sidebar.success(f"Datos restaurados desde ultimo guardado ({saved_at})")
if saved_at:
    st.sidebar.caption(f"Ultimo guardado: {saved_at}")

# Configuración inicial de páginas
modulos_sidebar_titles = {
    "1_datos_del_proyecto.py": "Datos del Proyecto",
    "2_datos_de_inspeccion_visual.py": "Datos de Inspección Visual",
    "3_datos_de_inspeccion_de_liquidos_penetrantes.py": "Datos de Inspección de Líquidos Penetrantes",
    "4_datos_de_inspeccion_de_particulas_magneticas.py": "Datos de Inspección de Partículas Magnéticas",
    "5_datos_de_inspeccion_de_ultrasonido.py": "Datos de Inspección de Ultrasonido"
}

def get_sidebar_title(archivo):
    return modulos_sidebar_titles.get(archivo, archivo)

default_pages = {
    "Encabezado y Firmas": [
        st.Page("1_datos_del_proyecto.py", title="Datos del Proyecto"),
    ],
    "Módulos": [
        st.Page("2_datos_de_inspeccion_visual.py", title=get_sidebar_title("2_datos_de_inspeccion_visual.py")),
        st.Page("3_datos_de_inspeccion_de_liquidos_penetrantes.py", title=get_sidebar_title("3_datos_de_inspeccion_de_liquidos_penetrantes.py")),
    ],
    "Reports": [
        st.Page("bloque_reportes.py", title="Generación de reportes"),
    ],
}

if SOLO_REPORTE_VISUAL:
    default_pages["Módulos"] = [
        st.Page(MODULO_VISUAL, title=get_sidebar_title(MODULO_VISUAL)),
    ]

# Inicializar la configuración de páginas si no existe
if "pages_config" not in st.session_state:
    modulos_iniciales = [
        st.Page("2_datos_de_inspeccion_visual.py", title=get_sidebar_title("2_datos_de_inspeccion_visual.py")),
        st.Page("3_datos_de_inspeccion_de_liquidos_penetrantes.py", title=get_sidebar_title("3_datos_de_inspeccion_de_liquidos_penetrantes.py")),
    ]
    if SOLO_REPORTE_VISUAL:
        modulos_iniciales = [
            st.Page(MODULO_VISUAL, title=get_sidebar_title(MODULO_VISUAL)),
        ]
    st.session_state.pages_config = {"modulos": modulos_iniciales}
elif SOLO_REPORTE_VISUAL:
    # Salvaguarda: forzar navegación visual-only incluso si la sesión tenía otros módulos
    st.session_state.pages_config["modulos"] = [
        st.Page(MODULO_VISUAL, title=get_sidebar_title(MODULO_VISUAL)),
    ]

# Obtener la configuración de páginas del session_state si existe
if "pages_config" in st.session_state and "modulos" in st.session_state.pages_config:
    # Crear una copia de las páginas por defecto
    pages = default_pages.copy()
    # Actualizar la sección de módulos con la configuración dinámica
    pages["Módulos"] = st.session_state.pages_config["modulos"]
else:
    pages = default_pages

pg = st.navigation(pages)
pg.run()

# --- AUTO-GUARDADO AUTOMÁTICO Y BOTÓN FLOTANTE ---
import time
import uuid
from persistencia import guardar_informe

# 1. Definir el nombre del informe para guardar
nombre_guardar = "AutoGuardado_General"
if "datos_proyecto" in st.session_state:
    dp = st.session_state.datos_proyecto
    num_ord = dp.get("numero_orden", "")
    cons = dp.get("consecutivo_inicial", "")
    cliente = dp.get("cliente", "")
    if num_ord and cons:
        cliente_clean = "".join(c for c in cliente if c.isalnum() or c in "._- ") if cliente else ""
        nombre_guardar = f"AutoGuardado_T{num_ord}I{cons}_{cliente_clean}".strip("_")

# 2. Lógica de Auto-guardado Automático (cooldown de 30 segundos)
ahora = time.time()
if "ultimo_autoguardado" not in st.session_state:
    st.session_state.ultimo_autoguardado = ahora

if ahora - st.session_state.ultimo_autoguardado >= 30:
    st.session_state.ultimo_autoguardado = ahora
    try:
        guardar_informe(nombre_guardar)
    except Exception:
        pass

# 3. Renderizar Estilos y Botón Flotante de Guardado Manual
st.markdown(
    """
    <style>
    /* Estilo del contenedor del botón flotante */
    .stApp div[data-testid="stVerticalBlock"] > div:has(#btn-guardar-flotante-marker) + div {
        position: fixed !important;
        bottom: 25px !important;
        right: 25px !important;
        width: auto !important;
        z-index: 999999 !important;
        background: transparent !important;
    }
    /* Estilo del botón propiamente dicho */
    .stApp div[data-testid="stVerticalBlock"] > div:has(#btn-guardar-flotante-marker) + div button {
        width: auto !important;
        background-color: #2e7d32 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 30px !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35) !important;
        border: 2px solid #1b5e20 !important;
        font-size: 16px !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stApp div[data-testid="stVerticalBlock"] > div:has(#btn-guardar-flotante-marker) + div button:hover {
        background-color: #1b5e20 !important;
        transform: scale(1.08) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45) !important;
    }
    </style>
    <div id="btn-guardar-flotante-marker"></div>
    """,
    unsafe_allow_html=True
)

if st.button("💾 Guardar", key="btn_guardar_flotante_click"):
    if guardar_informe(nombre_guardar):
        st.toast(f"💾 ¡Informe guardado con éxito como '{nombre_guardar}'!", icon="✅")
        st.session_state.ultimo_autoguardado = time.time()

# Guardar automáticamente el estado de la sesión en el disco para evitar pérdidas en F5
from save_state import persist_session_state
persist_session_state()

