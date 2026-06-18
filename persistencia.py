import os
import json
import shutil
import io
import zipfile
from datetime import datetime, date
import streamlit as st

# Directorio base para guardar los informes
DIRECTORIO_GUARDADO = os.path.join(os.getcwd(), "informes_guardados")

# Claves de st.session_state que queremos persistir
CLAVES_PERSISTENCIA = [
    "datos_proyecto", "bloque_1", "bloque_2_1", "bloque_3_1", "bloque_4_1", "bloque_5_1",
    "procedimiento_visual", "materiales_base_seleccionados",
    "procesos_soldadura_seleccionados", "tipos_soldadura_seleccionados",
    "tabla_fases_2_1", "tabla_elementos_2_1", "esquema_elementos_global",
    "procedimiento_pt", "materiales_utilizados_pt", "estandares_astm_pt",
    "parametros_operacion_pt", "tabla_elementos_3_1", "elementos_heredados_ids_3_1",
    "resultados_pt", "esquema_3_1", "imagenes_3_1",
    "procedimiento_pm", "materiales_utilizados_mt", "tipo_metodo_mt",
    "parametros_operacion_mt", "proceso_corriente_mt", "tabla_elementos_4_1",
    "elementos_heredados_ids_4_1", "esquema_4_1", "imagenes_4_1",
    "procedimiento_ut", "palpador_seleccionado_id", "frecuencias_palpadores",
    "tabla_elementos_5_1", "esquema_5_1", "imagenes",
    "imagenes_2_1"
]

class MockUploadedFile(io.BytesIO):
    """Clase para simular un archivo subido por st.file_uploader en Streamlit."""
    def __init__(self, buffer, name, type_mime=None):
        super().__init__(buffer)
        self.name = name
        self.type = type_mime or "image/jpeg"
        self.size = len(buffer)

def inicializar_directorio():
    """Asegura que el directorio de informes guardados exista."""
    if not os.path.exists(DIRECTORIO_GUARDADO):
        os.makedirs(DIRECTORIO_GUARDADO)

def listar_informes_guardados():
    """Retorna una lista de nombres de informes guardados localmente."""
    inicializar_directorio()
    informes = []
    for nombre in os.listdir(DIRECTORIO_GUARDADO):
        ruta = os.path.join(DIRECTORIO_GUARDADO, nombre)
        if os.path.isdir(ruta) and os.path.exists(os.path.join(ruta, "datos.json")):
            informes.append(nombre)
    return sorted(informes)

def _serializar_valor(val):
    """Serializa tipos especiales que JSON no soporta por defecto."""
    if isinstance(val, (date, datetime)):
        return {"__type__": "date", "value": val.isoformat()}
    if isinstance(val, set):
        return {"__type__": "set", "value": list(val)}
    return val

def _deserializar_valor(val):
    """Deserializa tipos especiales restaurados desde JSON."""
    if isinstance(val, dict) and "__type__" in val:
        if val["__type__"] == "date":
            # Intentar parsear como date o datetime
            try:
                dt = datetime.fromisoformat(val["value"])
                return dt.date() if len(val["value"]) <= 10 else dt
            except ValueError:
                return val["value"]
        if val["__type__"] == "set":
            return set(val["value"])
    return val

def _procesar_datos_para_guardar(estado, imagenes_dict, prefijo_img=""):
    """
    Recorre recursivamente los datos y extrae los archivos binarios (imágenes),
    reemplazándolos con metadatos para guardarlos físicamente en disco.
    """
    if isinstance(estado, dict):
        nuevo_dict = {}
        for k, v in estado.items():
            # Si el valor tiene una estructura de archivo (como los de cargadores de archivos)
            if k == "archivo" and hasattr(v, "read"):
                # Es un objeto de archivo. Extraer sus bytes.
                v.seek(0)
                contenido = v.read()
                # Generar una ruta única
                nombre_archivo = f"{prefijo_img}_{getattr(v, 'name', 'imagen.jpg')}"
                # Reemplazar por caracteres seguros
                nombre_archivo = "".join(c for c in nombre_archivo if c.isalnum() or c in "._-")
                imagenes_dict[nombre_archivo] = contenido
                nuevo_dict[k] = {"__type__": "image_ref", "nombre": nombre_archivo, "type": getattr(v, "type", "image/jpeg")}
            else:
                nuevo_dict[k] = _procesar_datos_para_guardar(v, imagenes_dict, f"{prefijo_img}_{k}")
        return nuevo_dict
    elif isinstance(estado, list):
        nueva_lista = []
        for i, item in enumerate(estado):
            nueva_lista.append(_procesar_datos_para_guardar(item, imagenes_dict, f"{prefijo_img}_{i}"))
        return nueva_lista
    else:
        return _serializar_valor(estado)

def _procesar_datos_al_cargar(estado, ruta_informe):
    """
    Recorre los datos restaurados del JSON y reconstruye los objetos MockUploadedFile
    a partir de las imágenes guardadas en disco.
    """
    if isinstance(estado, dict):
        if "__type__" in estado and estado["__type__"] == "image_ref":
            # Reconstruir la imagen
            nombre_img = estado["nombre"]
            ruta_img = os.path.join(ruta_informe, "imagenes", nombre_img)
            if os.path.exists(ruta_img):
                with open(ruta_img, "rb") as f:
                    contenido = f.read()
                return MockUploadedFile(contenido, nombre_img, estado.get("type", "image/jpeg"))
            else:
                return None
        
        nuevo_dict = {}
        for k, v in estado.items():
            nuevo_dict[k] = _procesar_datos_al_cargar(v, ruta_informe)
        return _deserializar_valor(nuevo_dict)
    elif isinstance(estado, list):
        return [_procesar_datos_al_cargar(item, ruta_informe) for item in estado]
    else:
        return _deserializar_valor(estado)

def guardar_informe(nombre_informe):
    """Guarda el estado actual de session_state a disco con el nombre provisto."""
    inicializar_directorio()
    
    # Sanitizar nombre de informe
    nombre_informe = "".join(c for c in nombre_informe if c.isalnum() or c in "._- ")
    ruta_informe = os.path.join(DIRECTORIO_GUARDADO, nombre_informe)
    
    if os.path.exists(ruta_informe):
        shutil.rmtree(ruta_informe)
    
    os.makedirs(ruta_informe)
    os.makedirs(os.path.join(ruta_informe, "imagenes"))
    
    # Capturar estado y extraer imágenes
    estado_copia = {}
    imagenes_dict = {}
    
    for clave in CLAVES_PERSISTENCIA:
        if clave in st.session_state:
            estado_copia[clave] = _procesar_datos_para_guardar(st.session_state[clave], imagenes_dict, clave)
    
    # Guardar archivo JSON
    with open(os.path.join(ruta_informe, "datos.json"), "w", encoding="utf-8") as f:
        json.dump(estado_copia, f, indent=4, ensure_ascii=False)
        
    # Guardar las imágenes físicamente
    for nombre_img, bytes_img in imagenes_dict.items():
        with open(os.path.join(ruta_informe, "imagenes", nombre_img), "wb") as f:
            f.write(bytes_img)
            
    return True

def cargar_informe(nombre_informe):
    """Carga los datos del informe seleccionado en el session_state."""
    ruta_informe = os.path.join(DIRECTORIO_GUARDADO, nombre_informe)
    ruta_json = os.path.join(ruta_informe, "datos.json")
    
    if not os.path.exists(ruta_json):
        return False
        
    with open(ruta_json, "r", encoding="utf-8") as f:
        estado_guardado = json.load(f)
        
    # Limpiar las claves de persistencia actuales del session_state para evitar conflictos
    for clave in CLAVES_PERSISTENCIA:
        if clave in st.session_state:
            del st.session_state[clave]
            
    # Reconstruir datos e imágenes y colocarlos en session_state
    for clave, valor in estado_guardado.items():
        st.session_state[clave] = _procesar_datos_al_cargar(valor, ruta_informe)
        
    # Sincronización post-carga: asegurar que la configuración de páginas se regenere si cambiaron los módulos seleccionados
    if "bloque_1" in st.session_state and "modulos_seleccionados" in st.session_state.bloque_1:
        modulos_seleccionados = st.session_state.bloque_1["modulos_seleccionados"]
        
        # Módulos disponibles en la app
        modulos_disponibles = {
            "Inspección Visual": "2_datos_de_inspeccion_visual.py",
            "Líquidos Penetrantes": "3_datos_de_inspeccion_de_liquidos_penetrantes.py",
            "Partículas Magnéticas": "4_datos_de_inspeccion_de_particulas_magneticas.py",
            "Ultrasonido": "5_datos_de_inspeccion_de_ultrasonido.py"
        }
        
        # Regenerar la configuración de páginas
        st.session_state.pages_config = {
            "modulos": [
                st.Page(modulos_disponibles[modulo], title=modulo)
                for modulo in modulos_seleccionados if modulo in modulos_disponibles
            ]
        }
        
    return True

def exportar_zip(nombre_informe):
    """Comprime la carpeta del informe y retorna los bytes del archivo ZIP."""
    ruta_informe = os.path.join(DIRECTORIO_GUARDADO, nombre_informe)
    if not os.path.exists(ruta_informe):
        return None
        
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(ruta_informe):
            for file in files:
                ruta_completa = os.path.join(root, file)
                # Guardar con ruta relativa dentro del zip
                ruta_relativa = os.path.relpath(ruta_completa, ruta_informe)
                zip_file.write(ruta_completa, arcname=ruta_relativa)
                
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def importar_desde_zip(archivo_zip, nombre_sugerido=None):
    """
    Importa un informe a partir de un archivo ZIP cargado por el usuario.
    Retorna el nombre del informe importado o None.
    """
    inicializar_directorio()
    
    try:
        # Leer el zip
        zip_bytes = archivo_zip.read()
        zip_buffer = io.BytesIO(zip_bytes)
        
        # Determinar nombre del informe
        if nombre_sugerido:
            nombre_informe = nombre_sugerido
        else:
            nombre_informe = os.path.splitext(archivo_zip.name)[0]
            
        nombre_informe = "".join(c for c in nombre_informe if c.isalnum() or c in "._- ")
        ruta_informe = os.path.join(DIRECTORIO_GUARDADO, nombre_informe)
        
        if os.path.exists(ruta_informe):
            # Agregar sufijo de tiempo para evitar sobreescritura accidental
            nombre_informe = f"{nombre_informe}_{datetime.now().strftime('%H%M%S')}"
            ruta_informe = os.path.join(DIRECTORIO_GUARDADO, nombre_informe)
            
        os.makedirs(ruta_informe)
        
        with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
            zip_ref.extractall(ruta_informe)
            
        # Validar que contenga datos.json
        if not os.path.exists(os.path.join(ruta_informe, "datos.json")):
            shutil.rmtree(ruta_informe)
            return None
            
        return nombre_informe
    except Exception as e:
        st.error(f"Error al importar archivo ZIP: {str(e)}")
        return None

def eliminar_informe(nombre_informe):
    """Elimina permanentemente un informe guardado localmente."""
    ruta_informe = os.path.join(DIRECTORIO_GUARDADO, nombre_informe)
    if os.path.exists(ruta_informe):
        shutil.rmtree(ruta_informe)
        return True
    return False

def generar_zip_completo(pdf_bytes, pdf_name):
    """
    Genera un archivo ZIP en memoria que contiene:
    1. El archivo PDF generado.
    2. Los datos del informe (JSON e imágenes) del estado actual.
    """
    import uuid
    # Nombre temporal único para el guardado local del estado
    temp_name = f"_temp_zip_{uuid.uuid4().hex[:8]}"
    guardar_informe(temp_name)
    
    ruta_informe = os.path.join(DIRECTORIO_GUARDADO, temp_name)
    zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Añadir el PDF en la raíz del zip
            zip_file.writestr(pdf_name, pdf_bytes)
            
            # Añadir todos los archivos de la carpeta del informe (datos.json y subcarpeta de imágenes)
            for root, dirs, files in os.walk(ruta_informe):
                for file in files:
                    # Omitir el propio PDF si por casualidad existiera ahí
                    if file == pdf_name:
                        continue
                    ruta_completa = os.path.join(root, file)
                    ruta_relativa = os.path.relpath(ruta_completa, ruta_informe)
                    zip_file.write(ruta_completa, arcname=ruta_relativa)
    finally:
        # Limpiar la carpeta temporal pase lo que pase
        eliminar_informe(temp_name)
        
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

