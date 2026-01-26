"""
Importador Batch Local
Importa múltiples archivos Excel desde carpetas locales a MySQL
Procesa todos los archivos .xlsx encontrados recursivamente
"""

import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import logging

# ================== CONFIGURACIÓN ==================

# 📁 Carpeta donde están tus archivos Excel descargados
BASE_FOLDER = r"E:\Users\franco.insfran\Desktop\Dashboard_DB\datos_descargados\extracciones\2023"

# 🧪 MODO DE PRUEBA
TEST_MODE = False  # True = solo 3 archivos | False = todos los archivos
MAX_FILES_TEST = 3

# Configuración de MySQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'analytics_datos',
    'user': 'root',
    'password': ''
}

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('importacion_batch.log'),
        logging.StreamHandler()
    ]
)

# ================== FUNCIONES DE IMPORTACIÓN ==================

def create_connection():
    """Crear conexión a MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        logging.error(f"Error conectando a MySQL: {e}")
        return None

def insert_metricas_generales(connection, df, fecha):
    """Insertar métricas generales (OPTIMIZADO - BATCH INSERT)"""
    if df.empty:
        return
    
    cursor = connection.cursor()
    query = """INSERT IGNORE INTO metricas_generales 
        (fecha, activeUsers, sessions, screenPageViews, bounceRate, averageSessionDuration)
        VALUES (%s, %s, %s, %s, %s, %s)"""
    
    # Preparar todos los valores en batch
    values_list = []
    for _, row in df.iterrows():
        values = (
            fecha,
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            int(row['sessions']) if pd.notna(row['sessions']) else 0,
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
            float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
            float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
        )
        values_list.append(values)
    
    try:
        # Inserción en batch (mucho más rápido)
        cursor.executemany(query, values_list)
        connection.commit()
    except Exception as e:
        logging.error(f"Error en metricas_generales: {e}")
    finally:
        cursor.close()

def insert_dispositivos(connection, df, fecha):
    """Insertar dispositivos (OPTIMIZADO - BATCH INSERT)"""
    if df.empty:
        return
    
    cursor = connection.cursor()
    query = """INSERT IGNORE INTO dispositivos 
        (fecha, deviceCategory, operatingSystem, browser, activeUsers, sessions, screenPageViews, averageSessionDuration)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    
    values_list = []
    for _, row in df.iterrows():
        values = (
            fecha,
            str(row['deviceCategory']) if pd.notna(row['deviceCategory']) else '',
            str(row['operatingSystem']) if pd.notna(row['operatingSystem']) else '',
            str(row['browser']) if pd.notna(row['browser']) else '',
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            int(row['sessions']) if pd.notna(row['sessions']) else 0,
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
            float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
        )
        values_list.append(values)
    
    try:
        cursor.executemany(query, values_list)
        connection.commit()
    except Exception as e:
        logging.error(f"Error en dispositivos: {e}")
    finally:
        cursor.close()

def insert_geografia(connection, df, fecha):
    """Insertar geografía"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO geografia 
                (fecha, country, city, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s, %s)"""
            values = (
                fecha,
                str(row['country']) if pd.notna(row['country']) else '',
                str(row['city']) if pd.notna(row['city']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en geografía: {e}")
    connection.commit()
    cursor.close()

def insert_paginas_top(connection, df, fecha):
    """Insertar páginas top (OPTIMIZADO - BATCH INSERT)"""
    if df.empty:
        return
    
    cursor = connection.cursor()
    query = """INSERT IGNORE INTO paginas_top 
        (fecha, pagePath, pageTitle, screenPageViews, activeUsers, sessions, bounceRate, averageSessionDuration)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    
    values_list = []
    for _, row in df.iterrows():
        values = (
            fecha,
            str(row['pagePath']) if pd.notna(row['pagePath']) else '',
            str(row['pageTitle']) if pd.notna(row['pageTitle']) else '',
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            0,  # sessions no disponible en Excel
            0.0,  # bounceRate no disponible en Excel
            float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
        )
        values_list.append(values)
    
    try:
        cursor.executemany(query, values_list)
        connection.commit()
    except Exception as e:
        logging.error(f"Error en paginas_top: {e}")
    finally:
        cursor.close()

def insert_datos_horarios(connection, df, fecha):
    """Insertar datos horarios (OPTIMIZADO - BATCH INSERT)"""
    if df.empty:
        return
    
    cursor = connection.cursor()
    query = """INSERT IGNORE INTO datos_horarios 
        (fecha, hour, activeUsers, sessions, screenPageViews)
        VALUES (%s, %s, %s, %s, %s)"""
    
    values_list = []
    for _, row in df.iterrows():
        values = (
            fecha,
            int(row['hour']) if pd.notna(row['hour']) else 0,
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            int(row['sessions']) if pd.notna(row['sessions']) else 0,
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0
        )
        values_list.append(values)
    
    try:
        cursor.executemany(query, values_list)
        connection.commit()
    except Exception as e:
        logging.error(f"Error en datos_horarios: {e}")
    finally:
        cursor.close()

def insert_busqueda_interna(connection, df, fecha):
    """Insertar búsqueda interna (OPTIMIZADO - BATCH INSERT)"""
    if df.empty:
        return
    
    cursor = connection.cursor()
    query = """INSERT IGNORE INTO busqueda_interna 
        (fecha, searchTerm, pagePath, sessions, activeUsers, screenPageViews, bounceRate)
        VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    
    values_list = []
    for _, row in df.iterrows():
        # Limitar searchTerm a 100 caracteres
        search_term = str(row['searchTerm']) if pd.notna(row['searchTerm']) else ''
        if len(search_term) > 100:
            search_term = search_term[:97] + '...'
        
        values = (
            fecha,
            search_term,
            str(row['pagePath']) if pd.notna(row['pagePath']) else '',
            int(row['sessions']) if pd.notna(row['sessions']) else 0,
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
            float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0
        )
        values_list.append(values)
    
    try:
        cursor.executemany(query, values_list)
        connection.commit()
    except Exception as e:
        logging.error(f"Error en busqueda_interna: {e}")
    finally:
        cursor.close()

def insert_fuentes_trafico(connection, df, fecha):
    """Insertar fuentes de tráfico (OPTIMIZADO - BATCH INSERT)"""
    if df.empty:
        return
    
    cursor = connection.cursor()
    query = """INSERT IGNORE INTO fuentes_trafico 
        (fecha, sourceMedium, sessionSource, sessionMedium, activeUsers, sessions, 
         screenPageViews, bounceRate, averageSessionDuration)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    
    values_list = []
    for _, row in df.iterrows():
        values = (
            fecha,
            str(row['sourceMedium']) if pd.notna(row['sourceMedium']) else '',
            str(row['sessionSource']) if pd.notna(row['sessionSource']) else '',
            str(row['sessionMedium']) if pd.notna(row['sessionMedium']) else '',
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            int(row['sessions']) if pd.notna(row['sessions']) else 0,
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
            float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
            float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
        )
        values_list.append(values)
    
    try:
        cursor.executemany(query, values_list)
        connection.commit()
    except Exception as e:
        logging.error(f"Error en fuentes_trafico: {e}")
    finally:
        cursor.close()
    connection.commit()
    cursor.close()

def insert_utm_tracking(connection, df, fecha):
    """Insertar UTM tracking (OPTIMIZADO - BATCH INSERT)"""
    if df.empty:
        return
    
    cursor = connection.cursor()
    query = """INSERT IGNORE INTO utm_tracking 
        (fecha, sessionSource, sessionMedium, sessionCampaignName, 
         sessions, activeUsers, screenPageViews, bounceRate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    
    values_list = []
    for _, row in df.iterrows():
        values = (
            fecha,
            str(row['sessionSource']) if pd.notna(row['sessionSource']) else '',
            str(row['sessionMedium']) if pd.notna(row['sessionMedium']) else '',
            str(row['sessionCampaignName']) if pd.notna(row['sessionCampaignName']) else '',
            int(row['sessions']) if pd.notna(row['sessions']) else 0,
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
            float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0
        )
        values_list.append(values)
    
    try:
        cursor.executemany(query, values_list)
        connection.commit()
    except Exception as e:
        logging.error(f"Error en utm_tracking: {e}")
    finally:
        cursor.close()

# ================== PROCESADOR DE ARCHIVOS ==================

def process_excel_file(file_path, fecha):
    """Procesar un archivo Excel e importar a MySQL"""
    
    filename = os.path.basename(file_path)
    logging.info(f"Procesando: {filename}")
    
    # Mapeo de hojas a funciones de importación (SOLO 6 TABLAS ACTIVAS)
    sheet_mapping = {
        'metricas_generales': ('metricas_generales', insert_metricas_generales),
        'dispositivos': ('dispositivos', insert_dispositivos),
        'paginas_top': ('paginas_top', insert_paginas_top),
        'datos_horarios': ('datos_horarios', insert_datos_horarios),
        'fuentes_trafico': ('fuentes_trafico', insert_fuentes_trafico),
        'utm_tracking': ('utm_tracking', insert_utm_tracking)
    }
    
    try:
        # Leer todas las hojas
        logging.info(f"  > Leyendo Excel...")
        excel_data = pd.read_excel(file_path, sheet_name=None)
        logging.info(f"  > Excel leido. Hojas encontradas: {len(excel_data)}")
        
        # Conectar a MySQL
        logging.info(f"  > Conectando a MySQL...")
        connection = create_connection()
        if not connection:
            return False, "Error de conexion a MySQL"
        logging.info(f"  > Conectado a MySQL")
        
        imported_sheets = 0
        
        # Procesar cada hoja
        for sheet_name, (table_name, insert_func) in sheet_mapping.items():
            if sheet_name in excel_data:
                df = excel_data[sheet_name]
                if not df.empty:
                    logging.info(f"  > Insertando {sheet_name}: {len(df)} filas")
                    insert_func(connection, df, fecha)
                    imported_sheets += 1
                    logging.info(f"  OK {sheet_name} completado")
        
        connection.close()
        logging.info(f"OK {filename} completado: {imported_sheets} tablas")
        return True, f"{imported_sheets} tablas importadas"
        
    except Exception as e:
        logging.error(f"ERROR en {filename}: {str(e)}")
        return False, str(e)

# ================== BÚSQUEDA DE ARCHIVOS ==================

def find_excel_files(base_folder):
    """Buscar todos los archivos .xlsx recursivamente"""
    excel_files = []
    
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith('.xlsx') and not file.startswith('~$'):
                full_path = os.path.join(root, file)
                excel_files.append(full_path)
    
    return sorted(excel_files)

def extract_date_from_filename(filename):
    """Extraer fecha del nombre del archivo"""
    # Intenta extraer fecha del formato: ga4_data_YYYY-MM-DD.xlsx
    try:
        if 'ga4_data_' in filename:
            date_part = filename.split('ga4_data_')[1].replace('.xlsx', '')
            fecha = datetime.strptime(date_part, '%Y-%m-%d').date()
            return fecha
    except:
        pass
    
    # Si no tiene el formato esperado, usar fecha actual
    return datetime.now().date()

# ================== FUNCIÓN PRINCIPAL ==================

def main():
    """Función principal del importador batch"""
    
    print("=" * 70)
    print("IMPORTADOR BATCH LOCAL")
    print("=" * 70)
    print()
    
    # Verificar que existe la carpeta
    if not os.path.exists(BASE_FOLDER):
        print(f"ERROR: La carpeta no existe")
        print(f"Ruta esperada: {BASE_FOLDER}")
        print(f"\nCrea la carpeta y coloca tus archivos Excel alli")
        return
    
    # Buscar archivos Excel
    print(f"Buscando archivos Excel en: {BASE_FOLDER}")
    excel_files = find_excel_files(BASE_FOLDER)
    
    if not excel_files:
        print("No se encontraron archivos .xlsx")
        print(f"\nAsegurate de descargar los archivos a: {BASE_FOLDER}")
        return
    
    print(f"Encontrados {len(excel_files)} archivos Excel\n")
    
    # Mostrar ejemplos
    print("Ejemplos de archivos encontrados:")
    for file in excel_files[:5]:
        rel_path = os.path.relpath(file, BASE_FOLDER)
        print(f"   - {rel_path}")
    if len(excel_files) > 5:
        print(f"   ... y {len(excel_files) - 5} mas\n")
    
    # Aplicar modo de prueba
    files_to_process = excel_files
    if TEST_MODE:
        print(f"\nMODO DE PRUEBA ACTIVADO")
        print(f"Solo se procesaran {MAX_FILES_TEST} archivos")
        files_to_process = excel_files[:MAX_FILES_TEST]
        print(f"Archivos seleccionados: {len(files_to_process)}\n")
    
    # Confirmar inicio
    print("=" * 70)
    response = input("Deseas comenzar la importacion? (s/n): ")
    if response.lower() != 's':
        print("Importacion cancelada")
        return
    
    print("\nIniciando importacion...\n")
    
    # Estadísticas
    success_count = 0
    error_count = 0
    errors_log = []
    total_files = len(files_to_process)
    
    # Procesar cada archivo con progreso visible
    print(f"\nProcesando {total_files} archivos...")
    print("=" * 70)
    
    for idx, file_path in enumerate(files_to_process, 1):
        try:
            filename = os.path.basename(file_path)
            fecha = extract_date_from_filename(filename)
            
            # Mostrar progreso en consola
            percent = (idx / total_files) * 100
            print(f"[{idx}/{total_files}] ({percent:.1f}%) - {filename}")
            
            success, message = process_excel_file(file_path, fecha)
            
            if success:
                success_count += 1
                print(f"    OK: {message}")
                logging.info(f"OK {filename}: {message}")
            else:
                error_count += 1
                error_msg = f"{filename}: {message}"
                errors_log.append(error_msg)
                print(f"    ERROR: {message}")
                logging.error(f"ERROR {error_msg}")
        
        except Exception as e:
            error_count += 1
            error_msg = f"{os.path.basename(file_path)}: {str(e)}"
            errors_log.append(error_msg)
            print(f"    ERROR: {str(e)}")
            logging.error(f"ERROR {error_msg}")
    
    # Reporte final
    print("\n" + "=" * 70)
    print("IMPORTACION COMPLETADA")
    print("=" * 70)
    print(f"Archivos importados exitosamente: {success_count}")
    print(f"Archivos con errores: {error_count}")
    print(f"Total procesados: {len(files_to_process)}")
    
    if errors_log:
        print(f"\nErrores encontrados (primeros 10):")
        for error in errors_log[:10]:
            print(f"   - {error}")
        if len(errors_log) > 10:
            print(f"   ... y {len(errors_log) - 10} mas (ver importacion_batch.log)")
    
    print(f"\nLog completo guardado en: importacion_batch.log")
    print("=" * 70)

if __name__ == "__main__":
    main()
