"""
Importador Automático desde Google Drive
Descarga archivos desde Drive e importa directo a MySQL
Sin necesidad de descargar todo manualmente
"""

import os
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path
import pandas as pd
import mysql.connector
from mysql.connector import Error
from tqdm import tqdm
import logging

# ================== INSTALACIÓN AUTOMÁTICA DE DEPENDENCIAS ==================
def install_required_packages():
    """Instalar paquetes necesarios si no están disponibles"""
    packages = {
        'google-auth': 'google-auth',
        'google-auth-oauthlib': 'google-auth-oauthlib',
        'google-auth-httplib2': 'google-auth-httplib2',
        'google-api-python-client': 'google-api-python-client',
        'tqdm': 'tqdm'
    }
    
    missing_packages = []
    
    for package_name, install_name in packages.items():
        try:
            __import__(package_name.replace('-', '_'))
        except ImportError:
            missing_packages.append(install_name)
    
    if missing_packages:
        print("📦 Instalando dependencias necesarias...")
        import subprocess
        for package in missing_packages:
            print(f"   Instalando {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
        print("✅ Todas las dependencias instaladas\n")

install_required_packages()

# Importar después de la instalación
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# ================== CONFIGURACIÓN ==================

# 🔧 ACTUALIZA ESTAS RUTAS CON TUS DATOS
CREDENTIALS_PATH = r"C:\ruta\a\tu\archivo\credenciales.json"  # Ruta a tu archivo JSON de credenciales
DRIVE_FOLDER_ID = None  # Se detectará automáticamente buscando "extracciones"
BASE_FOLDER_NAME = "extracciones"  # Nombre de la carpeta en Drive

# Configuración de MySQL (usa la misma que tu Importador.py)
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
        logging.FileHandler('importacion_drive.log'),
        logging.StreamHandler()
    ]
)

# ================== CONEXIÓN A GOOGLE DRIVE ==================

class DriveDownloader:
    """Clase para manejar descargas desde Google Drive"""
    
    def __init__(self, credentials_path):
        self.credentials_path = credentials_path
        self.service = None
        
    def connect(self):
        """Conectar a Google Drive API"""
        try:
            print("🔄 Conectando a Google Drive...")
            
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(f"Archivo de credenciales no encontrado: {self.credentials_path}")
            
            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            print("✅ Conectado a Google Drive\n")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando a Drive: {e}")
            return False
    
    def find_folder(self, folder_name, parent_id=None):
        """Buscar una carpeta por nombre"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            return items[0]['id'] if items else None
            
        except Exception as e:
            print(f"❌ Error buscando carpeta: {e}")
            return None
    
    def list_files_recursive(self, folder_id, path=""):
        """Listar todos los archivos .xlsx recursivamente"""
        try:
            all_files = []
            
            # Listar contenido de la carpeta
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)',
                pageSize=1000
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Recursivamente entrar en subcarpetas
                    subfolder_path = f"{path}/{item['name']}" if path else item['name']
                    all_files.extend(self.list_files_recursive(item['id'], subfolder_path))
                elif item['name'].endswith('.xlsx'):
                    # Es un archivo Excel
                    file_path = f"{path}/{item['name']}" if path else item['name']
                    all_files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'path': file_path
                    })
            
            return all_files
            
        except Exception as e:
            print(f"❌ Error listando archivos: {e}")
            return []
    
    def download_file(self, file_id, destination_path):
        """Descargar un archivo de Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Guardar archivo
            fh.seek(0)
            with open(destination_path, 'wb') as f:
                f.write(fh.read())
            
            return True
            
        except Exception as e:
            print(f"❌ Error descargando archivo: {e}")
            return False

# ================== FUNCIONES DE IMPORTACIÓN A MYSQL ==================
# Reutilizamos la lógica del Importador.py existente

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
    """Insertar métricas generales"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO metricas_generales 
                (fecha, activeUsers, sessions, screenPageViews, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s)"""
            values = (
                fecha,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en metricas_generales: {e}")
    connection.commit()
    cursor.close()

def insert_dispositivos(connection, df, fecha):
    """Insertar dispositivos"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO dispositivos 
                (fecha, deviceCategory, operatingSystem, browser, activeUsers, sessions, screenPageViews, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
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
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en dispositivos: {e}")
    connection.commit()
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
    """Insertar páginas top"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO paginas_top 
                (fecha, pagePath, pageTitle, screenPageViews, activeUsers, sessions, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            values = (
                fecha,
                str(row['pagePath']) if pd.notna(row['pagePath']) else '',
                str(row['pageTitle']) if pd.notna(row['pageTitle']) else '',
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en paginas_top: {e}")
    connection.commit()
    cursor.close()

def insert_datos_horarios(connection, df, fecha):
    """Insertar datos horarios"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO datos_horarios 
                (fecha, hour, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s)"""
            values = (
                fecha,
                int(row['hour']) if pd.notna(row['hour']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en datos_horarios: {e}")
    connection.commit()
    cursor.close()

def insert_terminos_busqueda(connection, df, fecha):
    """Insertar términos de búsqueda"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO terminos_busqueda 
                (fecha, searchTerm, sessions, activeUsers, screenPageViews, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s)"""
            values = (
                fecha,
                str(row['searchTerm']) if pd.notna(row['searchTerm']) else '',
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en terminos_busqueda: {e}")
    connection.commit()
    cursor.close()

def insert_busqueda_interna(connection, df, fecha):
    """Insertar búsqueda interna"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO busqueda_interna 
                (fecha, searchTerm, pagePath, sessions, activeUsers, screenPageViews, bounceRate)
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            values = (
                fecha,
                str(row['searchTerm']) if pd.notna(row['searchTerm']) else '',
                str(row['pagePath']) if pd.notna(row['pagePath']) else '',
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en busqueda_interna: {e}")
    connection.commit()
    cursor.close()

def insert_fuentes_trafico(connection, df, fecha):
    """Insertar fuentes de tráfico"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO fuentes_trafico 
                (fecha, sourceMedium, sessionSource, sessionMedium, activeUsers, sessions, 
                 screenPageViews, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
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
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en fuentes_trafico: {e}")
    connection.commit()
    cursor.close()

def insert_utm_tracking(connection, df, fecha):
    """Insertar UTM tracking"""
    cursor = connection.cursor()
    for _, row in df.iterrows():
        try:
            query = """INSERT IGNORE INTO utm_tracking 
                (fecha, sessionSource, sessionMedium, sessionCampaignName, 
                 sessions, activeUsers, screenPageViews, bounceRate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
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
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error en utm_tracking: {e}")
    connection.commit()
    cursor.close()

# ================== PROCESADOR DE ARCHIVOS ==================

def process_excel_file(file_path, fecha):
    """Procesar un archivo Excel e importar a MySQL"""
    
    # Mapeo de hojas a funciones de importación
    sheet_mapping = {
        'Métricas Básicas': ('metricas_generales', insert_metricas_generales),
        'Usuarios por Dispositivo': ('dispositivos', insert_dispositivos),
        'Fuentes de Tráfico': ('fuentes_trafico', insert_fuentes_trafico),
        'Datos Geográficos': ('geografia', insert_geografia),
        'Rendimiento de Páginas': ('paginas_top', insert_paginas_top),
        'Términos de Búsqueda': ('terminos_busqueda', insert_terminos_busqueda),
        'Búsqueda Interna': ('busqueda_interna', insert_busqueda_interna),
        'Datos por Hora': ('datos_horarios', insert_datos_horarios),
        'Seguimiento UTM': ('utm_tracking', insert_utm_tracking)
    }
    
    try:
        # Leer todas las hojas
        excel_data = pd.read_excel(file_path, sheet_name=None)
        
        # Conectar a MySQL
        connection = create_connection()
        if not connection:
            return False, "Error de conexión a MySQL"
        
        imported_sheets = 0
        
        # Procesar cada hoja
        for sheet_name, (table_name, insert_func) in sheet_mapping.items():
            if sheet_name in excel_data:
                df = excel_data[sheet_name]
                if not df.empty:
                    insert_func(connection, df, fecha)
                    imported_sheets += 1
        
        connection.close()
        return True, f"{imported_sheets} tablas importadas"
        
    except Exception as e:
        return False, str(e)

# ================== FUNCIÓN PRINCIPAL ==================

def main():
    """Función principal del importador automático"""
    
    print("=" * 70)
    print("🚀 IMPORTADOR AUTOMÁTICO DESDE GOOGLE DRIVE")
    print("=" * 70)
    print()
    
    # Validar credenciales
    if not os.path.exists(CREDENTIALS_PATH):
        print("❌ ERROR: Archivo de credenciales no encontrado")
        print(f"📁 Ruta esperada: {CREDENTIALS_PATH}")
        print("\n💡 Actualiza la variable CREDENTIALS_PATH en la línea 46 del script")
        return
    
    # Conectar a Drive
    downloader = DriveDownloader(CREDENTIALS_PATH)
    if not downloader.connect():
        return
    
    # Buscar carpeta de extracciones
    print(f"🔍 Buscando carpeta '{BASE_FOLDER_NAME}'...")
    folder_id = downloader.find_folder(BASE_FOLDER_NAME)
    
    if not folder_id:
        print(f"❌ No se encontró la carpeta '{BASE_FOLDER_NAME}' en tu Drive")
        return
    
    print(f"✅ Carpeta encontrada (ID: {folder_id})\n")
    
    # Listar todos los archivos Excel
    print("📋 Listando archivos Excel...")
    files = downloader.list_files_recursive(folder_id)
    
    if not files:
        print("❌ No se encontraron archivos .xlsx")
        return
    
    print(f"✅ Encontrados {len(files)} archivos Excel\n")
    
    # Mostrar algunos ejemplos
    print("📄 Ejemplos de archivos encontrados:")
    for file in files[:5]:
        print(f"   - {file['path']}")
    if len(files) > 5:
        print(f"   ... y {len(files) - 5} más\n")
    
    # Confirmar inicio
    print("=" * 70)
    response = input("¿Deseas comenzar la importación? (s/n): ")
    if response.lower() != 's':
        print("❌ Importación cancelada")
        return
    
    print("\n🏁 Iniciando importación automática...\n")
    
    # Crear carpeta temporal
    temp_dir = tempfile.mkdtemp()
    
    # Estadísticas
    success_count = 0
    error_count = 0
    errors_log = []
    
    # Procesar cada archivo con barra de progreso
    for file in tqdm(files, desc="📥 Importando archivos", unit="archivo", ncols=100):
        try:
            # Extraer fecha del nombre del archivo (ga4_data_YYYY-MM-DD.xlsx)
            filename = file['name']
            if 'ga4_data_' in filename:
                date_str = filename.replace('ga4_data_', '').replace('.xlsx', '')
                fecha = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                # Si no tiene el formato esperado, usar fecha actual
                fecha = datetime.now().date()
            
            # Descargar archivo temporalmente
            temp_file = os.path.join(temp_dir, filename)
            
            if downloader.download_file(file['id'], temp_file):
                # Procesar e importar
                success, message = process_excel_file(temp_file, fecha)
                
                if success:
                    success_count += 1
                    logging.info(f"✅ {filename}: {message}")
                else:
                    error_count += 1
                    error_msg = f"{filename}: {message}"
                    errors_log.append(error_msg)
                    logging.error(f"❌ {error_msg}")
                
                # Eliminar archivo temporal
                os.remove(temp_file)
            else:
                error_count += 1
                error_msg = f"{filename}: Error en descarga"
                errors_log.append(error_msg)
                logging.error(f"❌ {error_msg}")
        
        except Exception as e:
            error_count += 1
            error_msg = f"{file['name']}: {str(e)}"
            errors_log.append(error_msg)
            logging.error(f"❌ {error_msg}")
    
    # Limpiar carpeta temporal
    try:
        os.rmdir(temp_dir)
    except:
        pass
    
    # Reporte final
    print("\n" + "=" * 70)
    print("🎉 IMPORTACIÓN COMPLETADA")
    print("=" * 70)
    print(f"✅ Archivos importados exitosamente: {success_count}")
    print(f"❌ Archivos con errores: {error_count}")
    print(f"📊 Total procesados: {len(files)}")
    
    if errors_log:
        print(f"\n⚠️ Errores encontrados (primeros 10):")
        for error in errors_log[:10]:
            print(f"   - {error}")
        if len(errors_log) > 10:
            print(f"   ... y {len(errors_log) - 10} más (ver importacion_drive.log)")
    
    print(f"\n📝 Log completo guardado en: importacion_drive.log")
    print("=" * 70)

if __name__ == "__main__":
    main()
