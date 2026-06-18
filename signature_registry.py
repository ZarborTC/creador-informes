import os
import unicodedata

# Directorio de firmas dentro de config
DIR_FIRMAS = os.path.join(os.path.dirname(__file__), "config", "firmas")

def normalizar_nombre(nombre):
    """
    Normaliza un nombre de inspector:
    - Convierte a minúsculas.
    - Remueve tildes y diéresis.
    - Reemplaza espacios y caracteres especiales por guión bajo.
    - Elimina puntos y caracteres no alfanuméricos.
    """
    if not nombre:
        return ""
    
    # Decodificar caracteres Unicode a formato normalizado NFD para separar letras de acentos
    nombre_normalized = unicodedata.normalize('NFD', nombre)
    # Filtrar solo caracteres que no sean marcas de combinación (acentos)
    solo_letras = "".join(c for c in nombre_normalized if not unicodedata.combining(c))
    
    # Convertir a minúsculas y reemplazar espacios
    nombre_clean = solo_letras.lower().strip()
    nombre_clean = nombre_clean.replace(" ", "_")
    
    # Remover caracteres no alfanuméricos excepto guión bajo y guión
    nombre_clean = "".join(c for c in nombre_clean if c.isalnum() or c in "_-")
    
    return nombre_clean

def obtener_ruta_firma(nombre_inspector):
    """
    Busca si existe la firma PNG del inspector seleccionado y retorna su ruta absoluta.
    Retorna None si no se encuentra.
    """
    if not nombre_inspector:
        return None
        
    nombre_normalizado = normalizar_nombre(nombre_inspector)
    if not nombre_normalizado:
        return None
        
    # Verificar si el directorio existe, si no, crearlo
    if not os.path.exists(DIR_FIRMAS):
        os.makedirs(DIR_FIRMAS)
        
    # Buscar el archivo PNG en la carpeta
    ruta_archivo = os.path.join(DIR_FIRMAS, f"{nombre_normalizado}.png")
    
    if os.path.exists(ruta_archivo):
        return ruta_archivo
        
    return None

get_signature_for_person = obtener_ruta_firma

