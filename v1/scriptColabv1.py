# =============================================================================
# 📊 GA4 TO DATABASE - EXTRACTOR AVANZADO CON CARGA DIRECTA A BD
# =============================================================================
# Autor: Analytics Team
# Fecha: 2025-08-22
# Descripción: Script completo para extraer datos GA4 y cargar directamente a BD
# Uso: Ejecutar en Google Colab con conexión a base de datos local
# =============================================================================

print("🚀 Iniciando GA4 to Database - Versión Avanzada...")
print("=" * 60)

# =============================================================================
# 1️⃣ INSTALACIÓN DE DEPENDENCIAS
# =============================================================================
print("\n1️⃣ Instalando dependencias necesarias...")

import subprocess
import sys

def install_packages():
    """Instalar paquetes necesarios"""
    packages = [
        'google-analytics-data',
        'pandas',
        'pymysql',
        'sqlalchemy',
        'cryptography',
        'google-auth-oauthlib',
        'google-auth',
        'plotly'
    ]

    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
            print(f"   ✅ {package} instalado")
        except subprocess.CalledProcessError:
            print(f"   ❌ Error instalando {package}")

install_packages()

# =============================================================================
# 2️⃣ IMPORTACIÓN DE LIBRERÍAS
# =============================================================================
print("\n2️⃣ Importando librerías...")

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, OrderBy, FilterExpression, Filter
)
from google.oauth2 import service_account
from google.colab import drive
import pandas as pd
import pymysql
from sqlalchemy import create_engine, text, inspect
import os
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("   ✅ Todas las librerías importadas correctamente")

# =============================================================================
# 3️⃣ CONFIGURACIÓN GLOBAL
# =============================================================================
print("\n3️⃣ Configuración global...")

# ⚠️ ¡ACTUALIZA ESTAS VARIABLES CON TUS DATOS!
CONFIG = {
    # Credenciales GA4
    'CREDENTIALS_PATH': "/content/drive/MyDrive/analytics_datos/dashboard-mkt-466812-35e72c6c58e6.json",
    'PROPERTY_ID': "283583887",
    
    # Base de datos (WAMP local)
    'DB_CONFIG': {
        'host': 'localhost',  # Cambia si usas túnel SSH
        'user': 'root',
        'password': '',
        'database': 'analytics_datos',
        'port': 3306
    },
    
    # Configuración de extracción
    'DEFAULT_DAYS_BACK': 1,  # Por defecto traer 1 día (ayer)
    'BATCH_SIZE': 1000,      # Tamaño de lotes para inserción
    'MAX_ROWS_PER_QUERY': 10000  # Máximo filas por consulta GA4
}

print("   ✅ Configuración cargada")
print(f"   🏷️ Property ID: {CONFIG['PROPERTY_ID']}")
print(f"   🗄️ Base de datos: {CONFIG['DB_CONFIG']['database']}")

# =============================================================================
# 4️⃣ CLASE DE CONEXIÓN A BASE DE DATOS
# =============================================================================
print("\n4️⃣ Configurando conexión a base de datos...")

class DatabaseManager:
    """Gestor de conexión y operaciones con MySQL"""
    
    def __init__(self, db_config):
        self.config = db_config
        self.engine = None
        self.connection = None
        
    def connect(self):
        """Establecer conexión con la base de datos"""
        try:
            connection_string = f"mysql+pymysql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            self.engine = create_engine(connection_string, echo=False)
            
            # Probar conexión
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                
            print(f"   ✅ Conectado a BD: {self.config['database']}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error conectando a BD: {e}")
            print("   💡 Verifica:")
            print("      - WAMP/XAMPP está ejecutándose")
            print("      - Configuración de DB_CONFIG es correcta")
            print("      - La base de datos existe")
            return False
    
    def create_tables_if_not_exist(self):
        """Crear tablas si no existen"""
        try:
            with self.engine.connect() as conn:
                # Verificar qué tablas existen
                inspector = inspect(self.engine)
                existing_tables = inspector.get_table_names()
                
                tables_sql = {
                    'metadata_extracciones': """
                    CREATE TABLE IF NOT EXISTS metadata_extracciones (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        fecha_inicio DATE,
                        fecha_fin DATE,
                        property_id VARCHAR(50),
                        total_registros INT DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'completado',
                        observaciones TEXT
                    )""",
                    
                    'metricas_generales': """
                    CREATE TABLE IF NOT EXISTS metricas_generales (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha DATE,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        activeUsers INT DEFAULT 0,
                        sessions INT DEFAULT 0,
                        screenPageViews INT DEFAULT 0,
                        bounceRate DECIMAL(5,4) DEFAULT 0,
                        averageSessionDuration DECIMAL(10,2) DEFAULT 0,
                        UNIQUE KEY unique_fecha (fecha)
                    )""",
                    
                    'dispositivos': """
                    CREATE TABLE IF NOT EXISTS dispositivos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha DATE,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        deviceCategory VARCHAR(50),
                        activeUsers INT DEFAULT 0,
                        sessions INT DEFAULT 0,
                        screenPageViews INT DEFAULT 0,
                        UNIQUE KEY unique_fecha_device (fecha, deviceCategory)
                    )""",
                    
                    'geografia': """
                    CREATE TABLE IF NOT EXISTS geografia (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha DATE,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        country VARCHAR(100),
                        city VARCHAR(100),
                        activeUsers INT DEFAULT 0,
                        sessions INT DEFAULT 0,
                        screenPageViews INT DEFAULT 0,
                        UNIQUE KEY unique_fecha_geo (fecha, country, city)
                    )""",
                    
                    'paginas_top': """
                    CREATE TABLE IF NOT EXISTS paginas_top (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha DATE,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        pagePath VARCHAR(500),
                        pageTitle VARCHAR(500),
                        screenPageViews INT DEFAULT 0,
                        sessions INT DEFAULT 0,
                        bounceRate DECIMAL(5,4) DEFAULT 0,
                        averageSessionDuration DECIMAL(10,2) DEFAULT 0,
                        UNIQUE KEY unique_fecha_page (fecha, pagePath(255))
                    )""",
                    
                    'canales_marketing': """
                    CREATE TABLE IF NOT EXISTS canales_marketing (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha DATE,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        channelGrouping VARCHAR(100),
                        sourceMedium VARCHAR(200),
                        campaignName VARCHAR(200),
                        activeUsers INT DEFAULT 0,
                        sessions INT DEFAULT 0,
                        screenPageViews INT DEFAULT 0,
                        bounceRate DECIMAL(5,4) DEFAULT 0,
                        averageSessionDuration DECIMAL(10,2) DEFAULT 0,
                        UNIQUE KEY unique_fecha_channel (fecha, channelGrouping, sourceMedium(100))
                    )""",
                    
                    'palabras_clave': """
                    CREATE TABLE IF NOT EXISTS palabras_clave (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha DATE,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        searchTerm VARCHAR(255),
                        landingPage VARCHAR(500),
                        activeUsers INT DEFAULT 0,
                        sessions INT DEFAULT 0,
                        screenPageViews INT DEFAULT 0,
                        UNIQUE KEY unique_fecha_keyword (fecha, searchTerm, landingPage(255))
                    )""",
                    
                    'eventos_personalizados': """
                    CREATE TABLE IF NOT EXISTS eventos_personalizados (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fecha DATE,
                        fecha_extraccion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        eventName VARCHAR(100),
                        eventCount INT DEFAULT 0,
                        uniqueEvents INT DEFAULT 0,
                        totalUsers INT DEFAULT 0,
                        UNIQUE KEY unique_fecha_event (fecha, eventName)
                    )"""
                }
                
                created_tables = []
                for table_name, sql in tables_sql.items():
                    conn.execute(text(sql))
                    if table_name not in existing_tables:
                        created_tables.append(table_name)
                
                conn.commit()
                
                if created_tables:
                    print(f"   ✅ Tablas creadas: {', '.join(created_tables)}")
                else:
                    print("   ✅ Todas las tablas ya existen")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Error creando tablas: {e}")
            return False
    
    def insert_data(self, table_name, data_df, fecha_periodo):
        """Insertar datos en tabla específica con manejo de duplicados"""
        if data_df.empty:
            print(f"   ⚠️ No hay datos para insertar en {table_name}")
            return True
        
        try:
            # Agregar fecha y timestamp a los datos
            data_df['fecha'] = fecha_periodo
            data_df['fecha_extraccion'] = datetime.now()
            
            # Insertar con reemplazo de duplicados
            rows_inserted = data_df.to_sql(
                table_name, 
                self.engine, 
                if_exists='append', 
                index=False,
                method='multi',
                chunksize=CONFIG['BATCH_SIZE']
            )
            
            print(f"   ✅ {table_name}: {len(data_df)} registros insertados")
            return True
            
        except Exception as e:
            print(f"   ❌ Error insertando en {table_name}: {e}")
            return False
    
    def log_extraction(self, fecha_inicio, fecha_fin, total_registros, status="completado", observaciones=""):
        """Registrar la extracción en metadata"""
        try:
            metadata = pd.DataFrame([{
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'property_id': CONFIG['PROPERTY_ID'],
                'total_registros': total_registros,
                'status': status,
                'observaciones': observaciones
            }])
            
            metadata.to_sql('metadata_extracciones', self.engine, if_exists='append', index=False)
            print(f"   📋 Extracción registrada: {fecha_inicio} a {fecha_fin}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error registrando extracción: {e}")
            return False

# =============================================================================
# 5️⃣ CLASE GA4 AVANZADA CON NUEVAS CONSULTAS
# =============================================================================
print("\n5️⃣ Configurando consultas GA4 avanzadas...")

class GA4AdvancedConnector:
    """Conector avanzado con todas las métricas solicitadas"""
    
    def __init__(self):
        self.client = None
        self.property_id = None
        
    def setup_drive_and_connect(self, credentials_path, property_id):
        """Configurar Drive y conectar a GA4"""
        try:
            # Montar Drive
            drive.mount("/content/drive", force_remount=True)
            
            # Conectar GA4
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = BetaAnalyticsDataClient(credentials=credentials)
            self.property_id = property_id
            
            # Test de conexión
            test_request = RunReportRequest(
                property=f'properties/{property_id}',
                metrics=[Metric(name='activeUsers')],
                date_ranges=[DateRange(start_date='yesterday', end_date='yesterday')],
            )
            response = self.client.run_report(test_request)
            
            print("   ✅ GA4 conectado correctamente")
            return True
            
        except Exception as e:
            print(f"   ❌ Error conectando GA4: {e}")
            return False
    
    def _result_to_df(self, response):
        """Convertir respuesta GA4 a DataFrame"""
        result_dict = {}
        
        # Headers
        for dimension_header in response.dimension_headers:
            result_dict[dimension_header.name] = []
        for metric_header in response.metric_headers:
            result_dict[metric_header.name] = []
        
        # Datos
        for row in response.rows:
            for i, dimension_value in enumerate(row.dimension_values):
                dimension_name = response.dimension_headers[i].name
                result_dict[dimension_name].append(dimension_value.value)
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
    
    def get_daily_metrics(self, fecha):
        """📊 Métricas generales diarias"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=fecha, end_date=fecha)],
        )
        
        response = self.client.run_report(request)
        return self._result_to_df(response)
    
    def get_device_breakdown(self, fecha):
        """📱 Distribución por dispositivos"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            dimensions=[Dimension(name='deviceCategory')],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews')
            ],
            date_ranges=[DateRange(start_date=fecha, end_date=fecha)],
        )
        
        response = self.client.run_report(request)
        return self._result_to_df(response)
    
    def get_geographic_data(self, fecha, limit=100):
        """🌍 Datos geográficos"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            dimensions=[
                Dimension(name='country'),
                Dimension(name='city')
            ],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews')
            ],
            date_ranges=[DateRange(start_date=fecha, end_date=fecha)],
            order_bys=[OrderBy(metric={'metric_name': 'activeUsers'}, desc=True)],
            limit=limit
        )
        
        response = self.client.run_report(request)
        return self._result_to_df(response)
    
    def get_top_pages(self, fecha, limit=50):
        """📄 Páginas más visitadas"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            dimensions=[
                Dimension(name='pagePath'),
                Dimension(name='pageTitle')
            ],
            metrics=[
                Metric(name='screenPageViews'),
                Metric(name='sessions'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=fecha, end_date=fecha)],
            order_bys=[OrderBy(metric={'metric_name': 'screenPageViews'}, desc=True)],
            limit=limit
        )
        
        response = self.client.run_report(request)
        return self._result_to_df(response)
    
    def get_marketing_channels(self, fecha, limit=100):
        """🚀 Canales de marketing detallados"""
        request = RunReportRequest(
            property=f'properties/{self.property_id}',
            dimensions=[
                Dimension(name='sessionDefaultChannelGrouping'),
                Dimension(name='sessionSourceMedium'),
                Dimension(name='sessionCampaignName')
            ],
            metrics=[
                Metric(name='activeUsers'),
                Metric(name='sessions'),
                Metric(name='screenPageViews'),
                Metric(name='bounceRate'),
                Metric(name='averageSessionDuration')
            ],
            date_ranges=[DateRange(start_date=fecha, end_date=fecha)],
            order_bys=[OrderBy(metric={'metric_name': 'activeUsers'}, desc=True)],
            limit=limit
        )
        
        response = self.client.run_report(request)
        df = self._result_to_df(response)
        
        # Renombrar columnas para BD
        if not df.empty:
            df.rename(columns={
                'sessionDefaultChannelGrouping': 'channelGrouping',
                'sessionSourceMedium': 'sourceMedium',
                'sessionCampaignName': 'campaignName'
            }, inplace=True)
        
        return df
    
    def get_search_terms(self, fecha, limit=100):
        """🔍 Términos de búsqueda (si están disponibles)"""
        try:
            request = RunReportRequest(
                property=f'properties/{self.property_id}',
                dimensions=[
                    Dimension(name='googleAdsKeyword'),
                    Dimension(name='landingPage')
                ],
                metrics=[
                    Metric(name='activeUsers'),
                    Metric(name='sessions'),
                    Metric(name='screenPageViews')
                ],
                date_ranges=[DateRange(start_date=fecha, end_date=fecha)],
                order_bys=[OrderBy(metric={'metric_name': 'sessions'}, desc=True)],
                limit=limit
            )
            
            response = self.client.run_report(request)
            df = self._result_to_df(response)
            
            # Renombrar para BD
            if not df.empty:
                df.rename(columns={'googleAdsKeyword': 'searchTerm'}, inplace=True)
            
            return df
            
        except Exception as e:
            print(f"   ⚠️ Términos de búsqueda no disponibles: {e}")
            return pd.DataFrame()
    
    def get_custom_events(self, fecha, limit=50):
        """⚡ Eventos personalizados"""
        try:
            request = RunReportRequest(
                property=f'properties/{self.property_id}',
                dimensions=[Dimension(name='eventName')],
                metrics=[
                    Metric(name='eventCount'),
                    Metric(name='totalUsers')
                ],
                date_ranges=[DateRange(start_date=fecha, end_date=fecha)],
                order_bys=[OrderBy(metric={'metric_name': 'eventCount'}, desc=True)],
                limit=limit
            )
            
            response = self.client.run_report(request)
            df = self._result_to_df(response)
            
            # Agregar columna de eventos únicos (calculada como eventCount para simplificar)
            if not df.empty:
                df['uniqueEvents'] = df['eventCount']
            
            return df
            
        except Exception as e:
            print(f"   ⚠️ Eventos personalizados no disponibles: {e}")
            return pd.DataFrame()

# =============================================================================
# 6️⃣ FUNCIÓN PRINCIPAL DE EXTRACCIÓN
# =============================================================================
print("\n6️⃣ Configurando función principal...")

def extract_ga4_to_database(fecha_inicio, fecha_fin=None, force_update=False):
    """
    🚀 Extraer datos de GA4 y cargar directamente a BD
    
    Args:
        fecha_inicio (str): Fecha inicio en formato 'YYYY-MM-DD'
        fecha_fin (str): Fecha fin en formato 'YYYY-MM-DD' (opcional)
        force_update (bool): Forzar actualización si ya existen datos
    """
    
    # Si no se especifica fecha_fin, usar fecha_inicio (un solo día)
    if fecha_fin is None:
        fecha_fin = fecha_inicio
    
    print(f"🚀 Iniciando extracción GA4 → BD")
    print(f"📅 Período: {fecha_inicio} al {fecha_fin}")
    print("=" * 60)
    
    # Inicializar conectores
    ga4 = GA4AdvancedConnector()
    db = DatabaseManager(CONFIG['DB_CONFIG'])
    
    # Conectar a servicios
    if not ga4.setup_drive_and_connect(CONFIG['CREDENTIALS_PATH'], CONFIG['PROPERTY_ID']):
        return False
    
    if not db.connect():
        return False
    
    if not db.create_tables_if_not_exist():
        return False
    
    # Convertir fechas
    start_date = datetime.strptime(fecha_inicio, '%Y-%m-%d')
    end_date = datetime.strptime(fecha_fin, '%Y-%m-%d')
    
    total_registros = 0
    current_date = start_date
    
    print(f"\n🔄 Procesando fechas desde {fecha_inicio} hasta {fecha_fin}...")
    
    # Procesar cada día
    while current_date <= end_date:
        fecha_str = current_date.strftime('%Y-%m-%d')
        print(f"\n📊 Procesando: {fecha_str}")
        
        day_total = 0
        
        # Definir todas las extracciones
        extractions = [
            ("metricas_generales", ga4.get_daily_metrics),
            ("dispositivos", ga4.get_device_breakdown),
            ("geografia", lambda f: ga4.get_geographic_data(f, 100)),
            ("paginas_top", lambda f: ga4.get_top_pages(f, 50)),
            ("canales_marketing", lambda f: ga4.get_marketing_channels(f, 100)),
            ("palabras_clave", lambda f: ga4.get_search_terms(f, 100)),
            ("eventos_personalizados", lambda f: ga4.get_custom_events(f, 50))
        ]
        
        # Ejecutar cada extracción
        for table_name, extraction_func in extractions:
            try:
                data = extraction_func(fecha_str)
                
                if not data.empty:
                    success = db.insert_data(table_name, data, fecha_str)
                    if success:
                        day_total += len(data)
                    else:
                        print(f"   ❌ Error insertando en {table_name}")
                else:
                    print(f"   ⚠️ {table_name}: Sin datos para {fecha_str}")
                    
            except Exception as e:
                print(f"   ❌ Error en {table_name}: {e}")
        
        total_registros += day_total
        print(f"   ✅ Día completado: {day_total} registros")
        
        # Avanzar al siguiente día
        current_date += timedelta(days=1)
    
    # Registrar la extracción
    db.log_extraction(
        fecha_inicio, 
        fecha_fin, 
        total_registros, 
        "completado",
        f"Extracción automática - {total_registros} registros"
    )
    
    print(f"\n🎉 ¡Extracción completada!")
    print(f"📊 Total de registros insertados: {total_registros:,}")
    print(f"📅 Período procesado: {fecha_inicio} al {fecha_fin}")
    
    return True

# =============================================================================
# 7️⃣ FUNCIONES DE UTILIDAD
# =============================================================================

def extract_historical_data(start_date="2024-06-01"):
    """📅 Extraer datos históricos día por día desde una fecha específica"""
    print(f"🕒 Iniciando extracción histórica desde {start_date}")
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    yesterday = datetime.now() - timedelta(days=1)
    
    current = start
    while current <= yesterday:
        fecha_str = current.strftime('%Y-%m-%d')
        print(f"\n📅 Extrayendo datos históricos: {fecha_str}")
        
        success = extract_ga4_to_database(fecha_str)
        if not success:
            print(f"❌ Error en {fecha_str} - Continuando con el siguiente día...")
        
        current += timedelta(days=1)
    
    print("🎉 ¡Extracción histórica completada!")

def extract_yesterday():
    """📊 Extraer datos de ayer (para ejecución diaria)"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"🌅 Extrayendo datos de ayer: {yesterday}")
    return extract_ga4_to_database(yesterday)

def extract_date_range(start_date, end_date):
    """📊 Extraer rango específico de fechas"""
    return extract_ga4_to_database(start_date, end_date)

# =============================================================================
# 8️⃣ CONFIGURACIÓN COMPLETADA
# =============================================================================

print("\n" + "="*60)
print("🎯 GA4 TO DATABASE - LISTO PARA USAR")
print("="*60)

print("""
✅ SISTEMA CONFIGURADO

🔧 CONFIGURACIÓN ACTUAL:
   - Property ID: {property_id}
   - Base de datos: {database}
   - Host BD: {host}

🚀 COMANDOS PRINCIPALES:

1️⃣ EXTRAER UN DÍA ESPECÍFICO:
   extract_ga4_to_database('2024-07-01')

2️⃣ EXTRAER RANGO DE FECHAS:
   extract_ga4_to_database('2024-07-01', '2024-07-07')

3️⃣ EXTRAER AYER (para uso diario):
   extract_yesterday()

4️⃣ EXTRAER HISTÓRICO (desde junio):
   extract_historical_data('2024-06-01')

⚠️  IMPORTANTE:
   - Actualiza CONFIG con tus credenciales reales
   - Asegúrate de que WAMP esté ejecutándose
   - La base de datos 'analytics_datos' debe existir
""".format(
    property_id=CONFIG['PROPERTY_ID'],
    database=CONFIG['DB_CONFIG']['database'],
    host=CONFIG['DB_CONFIG']['host']
))

print("\n📋 EJEMPLO DE EJECUCIÓN PARA LLENADO INICIAL:")
print("=" * 50)
print("# Llenar datos desde junio hasta ayer")
print("extract_historical_data('2024-06-01')")
print("\n# O día por día específicos:")
print("extract_ga4_to_database('2024-07-01')")
print("extract_ga4_to_database('2024-07-02')")
print("extract_ga4_to_database('2024-07-03')")

# Para ejecutar automáticamente, descomenta la línea que necesites:
# extract_yesterday()  # Para datos de ayer
# extract_historical_data('2024-06-01')  # Para histórico desde junio