import streamlit as st
import pandas as pd
import os
from datetime import datetime
from uuid import uuid4

materiales_base = [
    "No Especificado",
    "ASTM A36",
    "ASTM A283 Gr A",
    "ASTM A283 Gr B",
    "ASTM A283 Gr C",
    "ASTM A283 Gr D",
    "ASTM A285",
    "ASTM A306",
    "ASTM A529",
    "ASTM A573",
    "ASTM A572 Gr 42",
    "ASTM A572 Gr 50",
    "ASTM A572 Gr 55",
    "ASTM A572 Gr 60",
    "ASTM A572 Gr 65",
    "ASTM A656",
    "ASTM A709",
    "ASTM A852",
    "ASTM A992",
    "ASTM A913",
    "ASTM A1043",
    "ASTM A1085",
    "ASTM A242",
    "ASTM A588",
    "ASTM A690",
    "ASTM A606",
    "ASTM A514",
    "ASTM A517",
    "ASTM A633",
    "ASTM A737",
    "ASTM A500 Gr C",
    "ASTM A501",
    "ASTM A847",
    "ASTM A1065",
    "ASTM A618",
    "ASTM A131 Gr A",
    "ASTM A131 Gr B",
    "ASTM A131 Gr D",
    "ASTM A131 Gr E",
    "ASTM A131 AH36",
    "ASTM A131 DH36",
    "ASTM A131 EH36",
    "ASTM A934",
    "ASTM A307",
    "ASTM A325",
    "ASTM A490",
    "ASTM F3125",
    "ASTM A354",
    "ASTM A709 HPS 50W",
    "ASTM A709 HPS 70W",
    "ASTM A913 Gr 50",
    "ASTM A913 Gr 65",
    "ASTM A913 Gr 70",
    "ASTM A913 Gr 80",
    "ASTM A36M",
    "ASTM A572M",
    "ASTM A992M",
    "ASTM A588M",
    "ASTM A1085M",
    "ASTM A715",
    "ASTM A441",
    "ASTM A618M",
    "ASTM A852M",
    "ASTM A992 HSS"]

procesos_soldadura = ["SMAW", "GMAW", "GTAW", "FCAW", "SAW", "TIG", "Otro"]
tipos_soldadura = ["Manual", "Semiautomático", "Automático", "Robotizado", "Otro"]

mapeo_tipos_inspeccion = {
    "TLPR0025": "VT",
    "TLPR0026": "PT",
    "TLPR0027": "MT",
    "TLPR0028": "UT"
}

def cargar_kits():
    """Carga la configuración de kits desde el archivo CSV."""
    try:
        df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'config', 'kits_inspeccion.csv'))
        df['componentes'] = df['componentes'].apply(lambda x: x.split('|'))
        df['tipo_inspeccion'] = df['tipo_inspeccion'].apply(lambda x: x.split('|'))
        return df.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error al cargar la configuración de kits: {str(e)}")
        return []

def cargar_procedimientos():
    """Carga la configuración de procedimientos desde el archivo CSV."""
    try:
        df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'config', 'procedimientos.csv'))
        return df.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error al cargar procedimientos: {str(e)}")
        return []

def cargar_materiales():
    """Carga la configuración de materiales desde el archivo CSV."""
    try:
        df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'config', 'materiales_base.csv'))
        return df.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error al cargar materiales: {str(e)}")
        return []

def get_norma_global():
    """Obtiene la norma global del proyecto desde el estado de la sesión."""
    if "bloque_1" in st.session_state and "norma_global" in st.session_state.bloque_1:
        return st.session_state.bloque_1["norma_global"]
    return "AWS D1.1 2020"

def get_materiales_base_seleccionados():
    """Obtiene los materiales base seleccionados desde el estado de la sesión."""
    if "materiales_base_seleccionados" not in st.session_state:
        st.session_state.materiales_base_seleccionados = ["ASTM A500 Gr C"]
    return st.session_state.materiales_base_seleccionados

def get_procesos_soldadura_seleccionados():
    """Obtiene los procesos de soldadura seleccionados desde el estado de la sesión."""
    if "procesos_soldadura_seleccionados" not in st.session_state:
        st.session_state.procesos_soldadura_seleccionados = ["SMAW"]
    return st.session_state.procesos_soldadura_seleccionados

def get_tipos_soldadura_seleccionados():
    """Obtiene los tipos de soldadura seleccionados desde el estado de la sesión."""
    if "tipos_soldadura_seleccionados" not in st.session_state:
        st.session_state.tipos_soldadura_seleccionados = ["Manual"]
    return st.session_state.tipos_soldadura_seleccionados

def get_proceso_soldadura():
    """Obtiene el proceso de soldadura seleccionado desde el estado de la sesión (compatibilidad)."""
    procesos = get_procesos_soldadura_seleccionados()
    return ", ".join(procesos) if procesos else "No especificado"

def get_tipo_soldadura():
    """Obtiene el tipo de soldadura seleccionado desde el estado de la sesión (compatibilidad)."""
    tipos = get_tipos_soldadura_seleccionados()
    return ", ".join(tipos) if tipos else "No especificado"

def get_material_base():
    """Obtiene el material base seleccionado desde el estado de la sesión (compatibilidad)."""
    materiales = get_materiales_base_seleccionados()
    return ", ".join(materiales) if materiales else "ASTM A500 Gr C"

def get_kits_disponibles(tipo_inspeccion):
    """Obtiene los kits disponibles para un tipo de inspección específico."""
    kits = cargar_kits()
    kits_disponibles = [kit for kit in kits if tipo_inspeccion in kit['tipo_inspeccion']]
    kits_disponibles.extend([kit for kit in kits if kit['id'] == 'kit_foto'])
    return kits_disponibles

def get_componentes_kit(kit_seleccionado, kits_disponibles):
    """Obtiene los componentes de un kit seleccionado."""
    if kit_seleccionado:
        kit = next((k for k in kits_disponibles if f"{k['nombre']} - {k['descripcion']}" == kit_seleccionado), None)
        if kit:
            return kit['componentes']
    return []

def get_tipo_inspeccion(procedimiento):
    """Obtiene el tipo de inspección basado en el código del procedimiento."""
    if procedimiento:
        codigo = procedimiento.split(" - ")[0]
        return mapeo_tipos_inspeccion.get(codigo)
    return None

def cargar_inspectores():
    """Carga la lista de inspectores desde el archivo CSV, ordenados por roles (Ingeniero, Auxiliar) y alfabéticamente."""
    try:
        df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'config', 'inspectores.csv'))
        inspectores = df['nombre'].dropna().tolist()
        
        # Agregar a Jorge Uribe si no estuviera en el CSV
        if "Jorge Uribe" not in inspectores:
            inspectores.append("Jorge Uribe")
            
        def obtener_rol(nombre):
            n = nombre.lower()
            import unicodedata
            n_clean = "".join(c for c in unicodedata.normalize('NFD', n) if not unicodedata.combining(c))
            if "juan jose" in n_clean or "miguel" in n_clean or "juan pablo" in n_clean:
                return "Auxiliar"
            return "Ingeniero"
            
        ingenieros = sorted([i for i in inspectores if obtener_rol(i) == "Ingeniero"])
        auxiliares = sorted([i for i in inspectores if obtener_rol(i) == "Auxiliar"])
        
        return ingenieros + auxiliares
    except Exception as e:
        st.error(f"Error al cargar la lista de inspectores: {str(e)}")
        return ["Ing. Inspector"]  # Valor por defecto en caso de error

def cargar_normas():
    """Carga la lista de normas desde el archivo CSV."""
    try:
        df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'config', 'normas.csv'))
        return df['norma'].tolist()
    except Exception as e:
        st.error(f"Error al cargar la lista de normas: {str(e)}")
        return ["AWS D1.1 2020"]  # Valor por defecto en caso de error

def cargar_palpadores():
    """Carga la configuración de palpadores desde el archivo CSV."""
    try:
        df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'config', 'palpadores.csv'))
        return df.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error al cargar la configuración de palpadores: {str(e)}")
        return []

def get_palpador_seleccionado():
    """Obtiene el palpador seleccionado desde el estado de la sesión."""
    if "palpador_seleccionado" not in st.session_state:
        st.session_state.palpador_seleccionado = None
    return st.session_state.palpador_seleccionado

def get_frecuencias_palpadores():
    """Obtiene las frecuencias editables de cada palpador desde el estado de la sesión."""
    if "frecuencias_palpadores" not in st.session_state:
        st.session_state.frecuencias_palpadores = {}
    return st.session_state.frecuencias_palpadores

def get_esquema_elementos_global():
    """Obtiene el esquema de elementos inspeccionados global desde el estado de la sesión."""
    if "esquema_elementos_global" not in st.session_state:
        st.session_state.esquema_elementos_global = []
    return st.session_state.esquema_elementos_global

def get_datos_palpador(kit_seleccionado, kits_disponibles):
    """Obtiene los datos del palpador desde el kit seleccionado."""
    if kit_seleccionado:
        kit = next((k for k in kits_disponibles if f"{k['nombre']} - {k['descripcion']}" == kit_seleccionado), None)
        if kit and kit.get('palpador_tipo'):
            return {
                'tipo': kit.get('palpador_tipo', ''),
                'angulo': kit.get('palpador_angulo', ''),
                'frecuencia': kit.get('palpador_frecuencia', ''),
                'dimension': kit.get('palpador_dimension', '')
            }
    return None

def generar_numero_informe(orden, consecutivo, year=None, offset=0):
    """
    Genera un número de informe según el formato:
    T+orden+I+consecutivo(3 dígitos)+último dígito del año
    
    Args:
        orden: Número de orden (sin padding)
        consecutivo: Número consecutivo base (se convertirá a 3 dígitos)
        year: Año (opcional, por defecto usa el año actual)
        offset: Incremento al consecutivo (0 para visual, 1 para líquidos, 2 para partículas, 3 para UT)
    
    Returns:
        str: Número de informe formateado. Ejemplo: T209I4625
    """
    from datetime import datetime
    
    if year is None:
        year = datetime.now().year
    
    # Convertir a enteros y validar
    try:
        orden_int = int(orden)
        consecutivo_int = int(consecutivo) + offset
    except (ValueError, TypeError):
        st.error(f"Error: orden y consecutivo deben ser números válidos")
        return ""
    
    # Formatear: orden sin padding, consecutivo con 3 dígitos
    orden_str = str(orden_int)
    consecutivo_str = str(consecutivo_int).zfill(3)
    year_digit = str(year)[-1]
    
    return f"T{orden_str}I{consecutivo_str}{year_digit}"

def get_report_output_dir():
    """Retorna la carpeta de salida de reportes y la crea si no existe."""
    base_dir = os.path.dirname(__file__)
    configured_dir = os.getenv("JW_REPORTS_DIR", "generated_reports").strip()

    if not configured_dir:
        configured_dir = "generated_reports"

    if os.path.isabs(configured_dir):
        output_dir = configured_dir
    else:
        output_dir = os.path.join(base_dir, configured_dir)

    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def get_report_output_path(output_filename):
    """Construye la ruta completa para un archivo de reporte."""
    return os.path.join(get_report_output_dir(), output_filename)

def build_unique_report_filename(report_type):
    """Genera un nombre de archivo único y seguro para reportes PDF."""
    safe_type = "".join(c if c.isalnum() or c in {"_", "-"} else "_" for c in report_type.upper())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique_suffix = uuid4().hex[:8]
    return f"INFORME_{safe_type}_{timestamp}_{unique_suffix}.pdf"

def obtener_consecutivo_por_tipo(tipo_inspeccion):
    """
    Obtiene el offset del consecutivo según el tipo de inspección.
    
    Args:
        tipo_inspeccion: Tipo de inspección ('visual', 'liquidos', 'particulas', 'ultrasonido')
    
    Returns:
        int: Offset para el consecutivo
    """
    offsets = {
        'visual': 0,
        'liquidos_penetrantes': 1,
        'particulas_magneticas': 2,
        'ultrasonido': 3
    }
    return offsets.get(tipo_inspeccion, 0)

 
