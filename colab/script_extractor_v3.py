# `v3 - Extracción de Datos con Estructura de Carpetas Automatizada`

## 1️⃣ INSTALACIÓN DE DEPENDENCIAS

import subprocess
import sys

def install_packages():
    """Instalar paquetes necesarios"""
    packages = [
        'google-analytics-data',
        'pandas',
        'openpyxl',
        'plotly',
        'tqdm'
    ]

    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
            print(f"   ✅ {package} instalado")
        except subprocess.CalledProcessError:
            print(f"   ❌ Error instalando {package}")

install_packages()


## 2️⃣ IMPORTACIÓN DE LIBRERÍAS

print("\n2️⃣ Importando librerías...")

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    OrderBy
)
from google.oauth2 import service_account
from google.colab import drive, files
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import warnings
from google.analytics.data_v1beta.types import Filter, FilterExpression
from tqdm import tqdm

warnings.filterwarnings('ignore')

print("   ✅ Todas las librerías importadas correctamente")


## 3️⃣ CONFIGURACIÓN DE CREDENCIALES (¡ACTUALIZAR AQUÍ!)

print("\n3️⃣ Configuración de credenciales...")

# ⚠️ ¡IMPORTANTE! ACTUALIZA ESTAS VARIABLES CON TUS DATOS REALES:
CREDENTIALS_PATH = "/content/drive/MyDrive/analytics_datos/dashboard-mkt-466812-35e72c6c58e6.json"
PROPERTY_ID = "283583887"  # Property ID de GA4
BASE_OUTPUT_FOLDER = "/content/drive/MyDrive/analytics_datos/extracciones"  # Carpeta base para extracciones

print(f"   📁 Ruta de credenciales: {CREDENTIALS_PATH}")
print(f"   🏷️ Property ID: {PROPERTY_ID}")
print(f"   📂 Carpeta base de salida: {BASE_OUTPUT_FOLDER}")


## 4️⃣ UTILIDADES PARA ESTRUCTURA DE CARPETAS

def get_month_name_spanish(month_number):
    """Obtener nombre del mes en español"""
    months = {
        1: 'Enero',
        2: 'Febrero',
        3: 'Marzo',
        4: 'Abril',
        5: 'Mayo',
        6: 'Junio',
        7: 'Julio',
        8: 'Agosto',
        9: 'Septiembre',
        10: 'Octubre',
        11: 'Noviembre',
        12: 'Diciembre'
    }
    return months.get(month_number, f'Mes_{month_number}')

def create_folder_structure(date_str):
    """
    Crear estructura de carpetas: extracciones/YYYY/MM_NombreMes/
    
    Args:
        date_str (str): Fecha en formato 'YYYY-MM-DD'
    
    Returns:
        str: Ruta completa de la carpeta donde guardar el archivo
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        year = date_obj.strftime('%Y')
        month_num = date_obj.month
        month_name = get_month_name_spanish(month_num)
        month_folder = f"{month_num:02d}_{month_name}"
        
        # Construir ruta: extracciones/2024/11_Noviembre/
        folder_path = os.path.join(BASE_OUTPUT_FOLDER, year, month_folder)
        
        # Crear carpetas si no existen
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            print(f"   📁 Carpeta creada: {year}/{month_folder}")
        
        return folder_path
    
    except Exception as e:
        print(f"   ❌ Error creando estructura de carpetas: {str(e)}")
        return BASE_OUTPUT_FOLDER


## 5️⃣ FUNCIÓN PARA VALIDAR FECHAS

def validate_date(date_string):
    """Validar formato de fecha YYYY-MM-DD"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_date_range(start_date, end_date):
    """Validar que el rango de fechas sea lógico"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        if start > end:
            return False, "La fecha de inicio no puede ser posterior a la fecha de fin"

        if end > datetime.now():
            return False, "La fecha de fin no puede ser futura"

        # Permitir desde 2023-01-01 en adelante
        min_date = datetime(2023, 1, 1)
        if start < min_date:
            return False, "Las fechas permitidas son desde 2023-01-01"

        return True, "Rango válido"

    except ValueError:
        return False, "Formato de fecha inválido. Use YYYY-MM-DD"

def generate_date_range(start_date, end_date):
    """
    Generar lista de fechas entre start_date y end_date
    
    Args:
        start_date (str): Fecha inicio 'YYYY-MM-DD'
        end_date (str): Fecha fin 'YYYY-MM-DD'
    
    Returns:
        list: Lista de fechas en formato 'YYYY-MM-DD'
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    date_list = []
    current = start
    
    while current <= end:
        date_list.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return date_list


## 6️⃣ CLASE CONECTOR GA4

print("\n4️⃣ Configurando conector GA4...")

class GA4Connector:
    """Clase para conectar con Google Analytics 4"""

    def __init__(self):
        self.client = None
        self.credentials = None
        self.property_id = None
        self.drive_mounted = False
        print("   🔌 Conector GA4 inicializado")

    def setup_drive(self):
        """Montar Google Drive"""
        if not self.drive_mounted:
            try:
                drive.mount('/content/drive')
                self.drive_mounted = True
                print("   📂 Google Drive montado correctamente")
            except Exception as e:
                print(f"   ❌ Error montando Google Drive: {str(e)}")
                self.drive_mounted = False
        return self.drive_mounted

    def connect(self, credentials_path, property_id):
        """Conectar a GA4 con credenciales de servicio"""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/analytics.readonly']
            )
            self.client = BetaAnalyticsDataClient(credentials=self.credentials)
            self.property_id = property_id
            print(f"   ✅ Conectado exitosamente a GA4 (Property: {property_id})")
            return True
        except Exception as e:
            print(f"   ❌ Error de conexión: {str(e)}")
            return False

    def is_connected(self):
        """Verificar si hay conexión activa"""
        return self.client is not None


## 7️⃣ CLASE PARA CONSULTAS GA4 CON FECHAS

print("\n5️⃣ Configurando sistema de consultas...")

class GA4QueriesWithDate:
    """Clase para ejecutar consultas GA4 con fechas específicas"""

    def __init__(self, connector):
        self.connector = connector
        print("   📊 Sistema de consultas listo")

    def _result_to_df(self, response, date_str):
        """Convertir respuesta de GA4 a DataFrame y agregar columna de fecha"""
        if not response or not response.rows:
            return pd.DataFrame()

        # Inicializar diccionario con fecha
        result_dict = {'fecha': []}

        # Crear estructura de diccionario
        for dimension_header in response.dimension_headers:
            result_dict[dimension_header.name] = []
        for metric_header in response.metric_headers:
            result_dict[metric_header.name] = []

        # Llenar datos
        for row in response.rows:
            # Agregar fecha para cada registro
            result_dict['fecha'].append(date_str)

            # Agregar dimensiones
            for i, dimension_value in enumerate(row.dimension_values):
                dimension_name = response.dimension_headers[i].name
                result_dict[dimension_name].append(dimension_value.value)

            # Agregar métricas
            for i, metric_value in enumerate(row.metric_values):
                metric_name = response.metric_headers[i].name
                result_dict[metric_name].append(metric_value.value)

        df = pd.DataFrame(result_dict)

        # Convertir métricas a numéricas
        for metric_header in response.metric_headers:
            metric_name = metric_header.name
            if metric_name in df.columns:
                df[metric_name] = pd.to_numeric(df[metric_name], errors='coerce')

        return df
    
    def _get_all_data_with_pagination(self, request_base, date_str):
        """Obtener TODOS los datos con paginación (hasta 100,000 registros por página)"""
        all_dataframes = []
        offset = 0
        limit = 100000  # Límite máximo según GA4 API
        
        while True:
            # Crear request con offset y limit
            request = RunReportRequest(
                property=request_base.property,
                dimensions=request_base.dimensions,
                metrics=request_base.metrics,
                date_ranges=request_base.date_ranges,
                order_bys=request_base.order_bys if hasattr(request_base, 'order_bys') else None,
                dimension_filter=request_base.dimension_filter if hasattr(request_base, 'dimension_filter') else None,
                offset=offset,
                limit=limit
            )
            
            # Ejecutar request
            response = self.connector.client.run_report(request)
            
            # Verificar si hay filas
            if not response.rows:
                break
            
            # Convertir esta página a DataFrame
            df_page = self._result_to_df(response, date_str)
            if df_page is not None and not df_page.empty:
                all_dataframes.append(df_page)
            
            # Verificar si hay más datos
            if len(response.rows) < limit:
                break
            
            offset += limit
            total_rows = sum(len(df) for df in all_dataframes)
            print(f"      📄 Paginando... ({total_rows:,} registros)")
        
        # Concatenar todos los DataFrames
        if all_dataframes:
            return pd.concat(all_dataframes, ignore_index=True)
        else:
            return pd.DataFrame()

    def get_basic_metrics(self, date_str):
        """📊 Obtener métricas básicas generales para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
        )

        response = self.connector.client.run_report(request)
        return self._result_to_df(response, date_str)

    def get_users_by_device(self, date_str):
        """📱 Obtener usuarios por dispositivo para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[
                Dimension(name='deviceCategory'),
                Dimension(name='operatingSystem'),
                Dimension(name='browser')
            ],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(metric={'metric_name': 'sessions'}, desc=True)]
        )

        response = self.connector.client.run_report(request)
        return self._result_to_df(response, date_str)

    def get_traffic_sources(self, date_str):
        """🌐 Obtener TODAS las fuentes de tráfico - CORREGIDO con sessionSource + sessionMedium"""
        if not self.connector.is_connected():
            return None

        # ✅ CORRECCIÓN CRÍTICA: Usar sessionSource + sessionMedium en lugar de sourceMedium
        request_base = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[
                Dimension(name='sessionSource'),
                Dimension(name='sessionMedium')
            ],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(metric={'metric_name': 'sessions'}, desc=True)]
        )

        # Usar paginación para obtener TODOS los datos
        df = self._get_all_data_with_pagination(request_base, date_str)
        
        # Crear columna sourceMedium combinada
        if df is not None and not df.empty:
            df['sourceMedium'] = df['sessionSource'] + ' / ' + df['sessionMedium']
        
        return df

    def get_geographic_data(self, date_str):
        """🌍 Obtener datos geográficos para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[
                Dimension(name='country'),
                Dimension(name='city')
            ],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(metric={'metric_name': 'sessions'}, desc=True)]
        )

        response = self.connector.client.run_report(request)
        return self._result_to_df(response, date_str)

    def get_page_performance(self, date_str):
        """📄 Obtener rendimiento de páginas para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[
                Dimension(name='pagePath'),
                Dimension(name='pageTitle')
            ],
            metrics=[
                Metric(name='screenPageViews'),
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(metric={'metric_name': 'screenPageViews'}, desc=True)]
        )

        response = self.connector.client.run_report(request)
        return self._result_to_df(response, date_str)

    def get_hourly_data(self, date_str):
        """⏰ Obtener datos por hora para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[Dimension(name='hour')],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(dimension={'dimension_name': 'hour'}, desc=False)]
        )

        response = self.connector.client.run_report(request)
        return self._result_to_df(response, date_str)

    def get_search_terms(self, date_str):
        """🔍 TODOS los términos de búsqueda para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[
                Dimension(name='searchTerm'),
            ],
            metrics=[
                Metric(name='sessions'),
                Metric(name='activeUsers'),
                Metric(name='screenPageViews'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(metric={'metric_name': 'sessions'}, desc=True)]
        )

        try:
            response = self.connector.client.run_report(request)
            df = self._result_to_df(response, date_str)

            # Filtrar términos vacíos o "(not set)"
            if df is not None and not df.empty and 'searchTerm' in df.columns:
                df = df[
                    (df['searchTerm'] != '(not set)') &
                    (df['searchTerm'] != '') &
                    (df['searchTerm'].notna())
                ]

            return df

        except Exception as e:
            print(f"      ⚠️ Error obteniendo términos de búsqueda: {str(e)}")
            return None

    def get_internal_search_data(self, date_str):
        """🔍 TODOS los datos de búsqueda interna para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[
                Dimension(name='searchTerm'),
                Dimension(name='pagePath')
            ],
            metrics=[
                Metric(name='sessions'),
                Metric(name='activeUsers'),
                Metric(name='screenPageViews'),
                Metric(name='bounceRate')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(metric={'metric_name': 'sessions'}, desc=True)]
        )

        try:
            response = self.connector.client.run_report(request)
            df = self._result_to_df(response, date_str)

            # Filtrar términos vacíos
            if df is not None and not df.empty and 'searchTerm' in df.columns:
                df = df[
                    (df['searchTerm'] != '(not set)') &
                    (df['searchTerm'] != '') &
                    (df['searchTerm'].notna())
                ]

            return df

        except Exception as e:
            print(f"      ⚠️ Error obteniendo búsqueda interna: {str(e)}")
            return None

    def get_utm_tracking(self, date_str):
        """🎯 Obtener datos de seguimiento UTM para una fecha específica"""
        if not self.connector.is_connected():
            return None

        request = RunReportRequest(
            property=f'properties/{self.connector.property_id}',
            dimensions=[
                Dimension(name='sessionSource'),
                Dimension(name='sessionMedium'),
                Dimension(name='sessionCampaignName')
            ],
            metrics=[
                Metric(name='sessions'),
                Metric(name='activeUsers'),
                Metric(name='screenPageViews'),
                Metric(name='bounceRate')
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            order_bys=[OrderBy(metric={'metric_name': 'sessions'}, desc=True)]
        )

        try:
            response = self.connector.client.run_report(request)
            return self._result_to_df(response, date_str)
        except Exception as e:
            print(f"      ⚠️ Error obteniendo datos UTM: {str(e)}")
            return None


## 8️⃣ CLASE EXPORTADOR DIARIO CON ESTRUCTURA DE CARPETAS

print("\n6️⃣ Configurando exportador diario...")

class GA4DailyExporter:
    """Clase para exportar datos de un día específico con estructura de carpetas"""

    def __init__(self, base_folder):
        self.results = {}
        self.base_folder = base_folder
        self.date_str = None
        print("   📥 Exportador diario inicializado")

    def add_result(self, name, df, description=""):
        """Agregar resultado para exportación"""
        if df is not None and not df.empty:
            self.results[name] = {
                'data': df,
                'description': description,
                'timestamp': datetime.now()
            }

    def export_daily_file(self, date_str):
        """Exportar archivo para un día específico en su carpeta correspondiente"""
        if not self.results:
            print(f"   ⚠️ No hay resultados para exportar del {date_str}")
            return None

        # Crear estructura de carpetas y obtener ruta
        folder_path = create_folder_structure(date_str)
        
        # Crear nombre de archivo
        filename = f"ga4_data_{date_str}.xlsx"
        filepath = os.path.join(folder_path, filename)

        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Crear hoja de metadatos
                metadata = {
                    'property_id': PROPERTY_ID,
                    'extraction_date': datetime.now().isoformat(),
                    'target_date': date_str,
                    'total_datasets': len(self.results),
                    'generated_by': 'GA4 Daily Extractor v3.0'
                }

                metadata_df = pd.DataFrame([json.dumps(metadata)])
                metadata_df.to_excel(writer, sheet_name='metadata', index=False, header=False)

                # Mapeo de nombres para hojas
                sheet_names = {
                    'Métricas Básicas': 'metricas_generales',
                    'Usuarios por Dispositivo': 'dispositivos',
                    'Fuentes de Tráfico': 'fuentes_trafico',
                    'Datos Geográficos': 'geografia',
                    'Rendimiento de Páginas': 'paginas_top',
                    'Términos de Búsqueda': 'terminos_busqueda',
                    'Búsqueda Interna': 'busqueda_interna',
                    'Datos por Hora': 'datos_horarios',
                    'Seguimiento UTM': 'utm_tracking'
                }

                # Crear hoja de resumen
                summary_data = []
                total_records = 0

                for name, result in self.results.items():
                    records = len(result['data'])
                    total_records += records
                    summary_data.append({
                        'Dataset': name,
                        'Descripción': result['description'],
                        'Registros': records,
                        'Columnas': len(result['data'].columns),
                        'Fecha': date_str,
                        'Timestamp': result['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                    })

                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='resumen', index=False)

                # Exportar cada resultado en su propia hoja
                for name, result in self.results.items():
                    sheet_name = sheet_names.get(name, name.lower().replace(' ', '_'))[:31]
                    result['data'].to_excel(writer, sheet_name=sheet_name, index=False)

            # Obtener ruta relativa para mostrar
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            year = date_obj.strftime('%Y')
            month_name = get_month_name_spanish(date_obj.month)
            month_folder = f"{date_obj.month:02d}_{month_name}"
            
            print(f"   ✅ Archivo exportado:")
            print(f"      📁 {year}/{month_folder}/{filename}")
            print(f"      📊 {len(self.results)} datasets, {total_records:,} registros totales")

            return filepath

        except Exception as e:
            print(f"   ❌ Error al exportar {date_str}: {str(e)}")
            return None


## 9️⃣ FUNCIÓN PRINCIPAL - EXTRACCIÓN DIARIA

print("\n7️⃣ Configurando extracción diaria...")

def extract_single_day_data(date_str):
    """🚀 Extraer datos de un día específico"""

    print(f"\n🗓️  Procesando fecha: {date_str}")
    print("-" * 40)

    # Validar fecha
    if not validate_date(date_str):
        print(f"❌ Fecha inválida: {date_str}")
        return None

    # Inicializar sistemas
    ga4 = GA4Connector()
    if not ga4.is_connected():
        ga4.setup_drive()
        if not ga4.connect(CREDENTIALS_PATH, PROPERTY_ID):
            print("❌ Error de conexión")
            return None

    queries = GA4QueriesWithDate(ga4)
    exporter = GA4DailyExporter(BASE_OUTPUT_FOLDER)

    # Definir consultas a ejecutar
    analysis_steps = [
        ("Métricas Básicas", queries.get_basic_metrics, "Resumen general del día"),
        ("Usuarios por Dispositivo", queries.get_users_by_device, "Distribución por dispositivos"),
        ("Fuentes de Tráfico", queries.get_traffic_sources, "Fuentes de tráfico del día"),
        ("Datos Geográficos", queries.get_geographic_data, "Ubicaciones de usuarios"),
        ("Rendimiento de Páginas", queries.get_page_performance, "Páginas más visitadas"),
        ("Términos de Búsqueda", queries.get_search_terms, "Términos de búsqueda más utilizados"),
        ("Búsqueda Interna", queries.get_internal_search_data, "Búsquedas internas del sitio"),
        ("Datos por Hora", queries.get_hourly_data, "Distribución horaria"),
        ("Seguimiento UTM", queries.get_utm_tracking, "Parámetros UTM de campañas")
    ]

    completed = 0

    # Ejecutar consultas
    print(f"🔄 Ejecutando consultas para {date_str}:")
    for name, func, description in analysis_steps:
        try:
            print(f"   📊 {name}... ", end="")
            df = func(date_str)

            if df is not None and not df.empty:
                exporter.add_result(name, df, description)
                completed += 1
                print(f"✅ ({len(df):,} registros)")
            else:
                print("⚠️ Sin datos")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

    # Exportar si hay datos
    if completed > 0:
        filepath = exporter.export_daily_file(date_str)
        return filepath
    else:
        print(f"   ⚠️ Sin datos para {date_str}")
        return None


def extract_multiple_days(start_date, end_date, pause_seconds=2):
    """
    🚀 Extraer datos día por día en un rango de fechas
    
    Archivos se guardan en: extracciones/YYYY/MM_NombreMes/ga4_data_YYYY-MM-DD.xlsx

    Args:
        start_date (str): Fecha inicio 'YYYY-MM-DD'
        end_date (str): Fecha fin 'YYYY-MM-DD'
        pause_seconds (int): Pausa entre extracciones para evitar límites de API

    Returns:
        list: Lista de archivos generados exitosamente
    """

    print(f"\n{'='*60}")
    print(f"🚀 EXTRACCIÓN MÚLTIPLE - ARCHIVOS DIARIOS CON ESTRUCTURA DE CARPETAS")
    print(f"{'='*60}")
    print(f"📅 Desde: {start_date}")
    print(f"📅 Hasta: {end_date}")
    print(f"📂 Estructura: extracciones/YYYY/MM_NombreMes/ga4_data_YYYY-MM-DD.xlsx")
    print("=" * 60)

    # Validar fechas
    if not validate_date(start_date) or not validate_date(end_date):
        print("❌ Error: Formato de fecha inválido")
        return []

    is_valid, message = validate_date_range(start_date, end_date)
    if not is_valid:
        print(f"❌ Error: {message}")
        return []

    # Generar lista de fechas
    dates = generate_date_range(start_date, end_date)
    total_dates = len(dates)

    print(f"\n📊 Total de días a procesar: {total_dates}")

    # Inicializar conexión una sola vez
    print("\n🔄 Inicializando conexión...")
    ga4 = GA4Connector()
    ga4.setup_drive()

    if not ga4.connect(CREDENTIALS_PATH, PROPERTY_ID):
        print("❌ Error: No se pudo conectar a GA4")
        return []

    successful_files = []
    failed_dates = []

    # Procesar cada fecha con barra de progreso
    print(f"\n🏁 Iniciando extracción diaria...")
    for i, date_str in enumerate(tqdm(dates, desc="📥 Descargando datos", unit="día", ncols=100), 1):
        print(f"\n{'─'*60}")
        print(f"📅 [{i}/{total_dates}] Procesando {date_str}...")
        print(f"{'─'*60}")

        try:
            queries = GA4QueriesWithDate(ga4)
            exporter = GA4DailyExporter(BASE_OUTPUT_FOLDER)

            # Ejecutar consultas para esta fecha
            analysis_steps = [
                ("Métricas Básicas", queries.get_basic_metrics, "Resumen general del día"),
                ("Usuarios por Dispositivo", queries.get_users_by_device, "Distribución por dispositivos"),
                ("Fuentes de Tráfico", queries.get_traffic_sources, "Fuentes de tráfico del día"),
                ("Datos Geográficos", queries.get_geographic_data, "Ubicaciones de usuarios"),
                ("Rendimiento de Páginas", queries.get_page_performance, "Páginas más visitadas"),
                ("Términos de Búsqueda", queries.get_search_terms, "Términos de búsqueda más utilizados"),
                ("Búsqueda Interna", queries.get_internal_search_data, "Búsquedas internas del sitio"),
                ("Datos por Hora", queries.get_hourly_data, "Distribución horaria"),
                ("Seguimiento UTM", queries.get_utm_tracking, "Parámetros UTM de campañas")
            ]

            completed = 0
            for name, func, description in analysis_steps:
                try:
                    print(f"   📊 {name}... ", end="")
                    df = func(date_str)
                    if df is not None and not df.empty:
                        exporter.add_result(name, df, description)
                        completed += 1
                        print(f"✅ ({len(df):,} registros)")
                    else:
                        print("⚠️ Sin datos")
                except Exception as e:
                    print(f"❌ {str(e)[:50]}")

            # Exportar archivo del día
            if completed > 0:
                filepath = exporter.export_daily_file(date_str)
                if filepath:
                    successful_files.append(filepath)
                    print(f"   ✅ {date_str} completado ({completed} datasets)")
                else:
                    failed_dates.append(date_str)
                    print(f"   ❌ {date_str} falló en exportación")
            else:
                print(f"   ⚠️ {date_str} sin datos")
                failed_dates.append(date_str)

            # Pausa para evitar límites de API
            if i < total_dates and pause_seconds > 0:
                import time
                print(f"   ⏸️ Pausa {pause_seconds}s...")
                time.sleep(pause_seconds)

        except Exception as e:
            print(f"   ❌ Error procesando {date_str}: {str(e)}")
            failed_dates.append(date_str)

    # Reporte final
    print(f"\n{'='*60}")
    print(f"🎉 EXTRACCIÓN MÚLTIPLE COMPLETADA")
    print(f"{'='*60}")
    print(f"✅ Archivos generados exitosamente: {len(successful_files)}")
    print(f"❌ Fechas con errores: {len(failed_dates)}")

    if successful_files:
        print(f"\n📁 Resumen de archivos generados:")
        # Agrupar por mes para mejor visualización
        files_by_month = {}
        for file in successful_files:
            parts = file.split(os.sep)
            if len(parts) >= 3:
                year = parts[-3]
                month = parts[-2]
                key = f"{year}/{month}"
                if key not in files_by_month:
                    files_by_month[key] = []
                files_by_month[key].append(parts[-1])
        
        for month_key, files in sorted(files_by_month.items()):
            print(f"\n   📂 {month_key}/ ({len(files)} archivos)")
            for filename in files[:3]:  # Mostrar primeros 3
                print(f"      - {filename}")
            if len(files) > 3:
                print(f"      ... y {len(files)-3} más")

    if failed_dates:
        print(f"\n⚠️ Fechas con problemas:")
        for date in failed_dates[:10]:  # Mostrar primeras 10
            print(f"   - {date}")
        if len(failed_dates) > 10:
            print(f"   ... y {len(failed_dates)-10} más")

    print(f"\n📂 Ubicación base: {BASE_OUTPUT_FOLDER}")
    print("=" * 60)

    return successful_files


## 🔟 FUNCIONES DE CONVENIENCIA

def extract_yesterday():
    """Extraer datos de ayer"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    return extract_single_day_data(yesterday)

def extract_last_week():
    """Extraer datos de la última semana (día por día)"""
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    return extract_multiple_days(start_date, end_date)

def extract_last_month():
    """Extraer datos del último mes (día por día)"""
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    return extract_multiple_days(start_date, end_date)

def extract_year_2023():
    """Extraer todos los datos del año 2023"""
    return extract_multiple_days('2023-01-01', '2023-12-31')

def extract_year_2024():
    """Extraer todos los datos del año 2024"""
    return extract_multiple_days('2024-01-01', '2024-12-31')

def extract_year_2025():
    """Extraer todos los datos del año 2025"""
    today = datetime.now().strftime('%Y-%m-%d')
    return extract_multiple_days('2025-01-01', today)

def extract_since_2023():
    """Extraer TODOS los datos desde 2023 hasta hoy"""
    today = datetime.now().strftime('%Y-%m-%d')
    return extract_multiple_days('2023-01-01', today)


## 1️⃣1️⃣ SECCIÓN DE EJECUCIÓN

print("\n" + "="*60)
print("✅ SISTEMA DE EXTRACCIÓN LISTO")
print("="*60)
print("\n📋 OPCIONES DE EXTRACCIÓN DISPONIBLES:")
print("\n🔹 Extracción Simple:")
print("   extract_single_day_data('2024-11-01')")
print("   extract_yesterday()")
print("\n🔹 Extracción por Períodos:")
print("   extract_last_week()")
print("   extract_last_month()")
print("   extract_multiple_days('2024-01-01', '2024-01-31')")
print("\n🔹 Extracción por Año Completo:")
print("   extract_year_2023()  # Todo el 2023")
print("   extract_year_2024()  # Todo el 2024")
print("   extract_year_2025()  # Del 2025 hasta hoy")
print("\n🔹 Extracción Completa desde 2023:")
print("   extract_since_2023()  # Desde 2023-01-01 hasta hoy")
print("\n📂 ESTRUCTURA DE CARPETAS:")
print("   extracciones/")
print("   ├── 2023/")
print("   │   ├── 01_Enero/")
print("   │   │   ├── ga4_data_2023-01-01.xlsx")
print("   │   │   └── ...")
print("   │   ├── 02_Febrero/")
print("   │   └── ...")
print("   ├── 2024/")
print("   │   ├── 01_Enero/")
print("   │   ├── 02_Febrero/")
print("   │   └── ...")
print("   └── 2025/")
print("       └── ...")
print("\n" + "="*60)
print("💡 Ejecuta una de las funciones de arriba para comenzar")
print("="*60 + "\n")

# 🎯 EJEMPLO DE USO - DESCOMENTA LA LÍNEA QUE QUIERAS EJECUTAR:

# Para extraer desde 2023 hasta hoy (RECOMENDADO para primera vez):
# extract_since_2023()

# Para extraer solo el año 2023:
# extract_year_2023()

# Para extraer solo el año 2024:
# extract_year_2024()

# Para extraer un mes específico:
# extract_multiple_days('2024-11-01', '2024-11-30')

# Para extraer ayer:
# extract_yesterday()
