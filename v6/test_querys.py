import mysql.connector
import pandas as pd
from sqlalchemy import create_engine, text

# Configuración corregida de la conexión
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'analytics_datos',
    'port': 3306
}

def test_connection():
    """Prueba simple de conexión"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            print(f"Conexión exitosa: {result}")
            cursor.close()
            connection.close()
            return True
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def create_simple_connection():
    """Crear conexión simple con pandas"""
    try:
        connection_string = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        print(f"Error creando engine: {e}")
        return None

def test_simple_query(engine):
    """Consulta simple para verificar que las tablas existen"""
    try:
        # Verificar qué tablas existen
        query = "SHOW TABLES"
        df = pd.read_sql(query, engine)
        print("Tablas disponibles:")
        print(df)
        return df
    except Exception as e:
        print(f"Error en consulta: {e}")
        return pd.DataFrame()

def get_simple_metrics(engine, fecha_inicio, fecha_fin):
    """Consulta básica de métricas generales"""
    try:
        query = f"""
        SELECT 
            fecha,
            activeUsers,
            sessions,
            screenPageViews,
            bounceRate
        FROM metricas_generales
        WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        ORDER BY fecha
        LIMIT 10
        """
        df = pd.read_sql(query, engine)
        print(f"Filas obtenidas: {len(df)}")
        return df
    except Exception as e:
        print(f"Error en consulta de métricas: {e}")
        return pd.DataFrame()

def get_simple_devices(engine, fecha_inicio, fecha_fin):
    """Consulta básica de dispositivos"""
    try:
        query = f"""
        SELECT 
            deviceCategory,
            SUM(activeUsers) as usuarios_activos,
            SUM(sessions) as sesiones_totales
        FROM dispositivos
        WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        GROUP BY deviceCategory
        """
        df = pd.read_sql(query, engine)
        print(f"Dispositivos encontrados: {len(df)}")
        return df
    except Exception as e:
        print(f"Error en consulta de dispositivos: {e}")
        return pd.DataFrame()

def get_simple_traffic_sources(engine, fecha_inicio, fecha_fin):
    """Consulta CORREGIDA de fuentes de tráfico"""
    try:
        query = f"""
        SELECT 
            sourceMedium,
            SUM(COALESCE(activeUsers, 0)) as usuarios_activos,
            SUM(COALESCE(sessions, 0)) as sesiones_totales
        FROM fuentes_trafico
        WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        AND sourceMedium IS NOT NULL 
        AND sourceMedium != ''
        GROUP BY sourceMedium
        ORDER BY sesiones_totales DESC
        LIMIT 10
        """
        df = pd.read_sql(query, engine)
        print(f"Fuentes de tráfico encontradas: {len(df)}")
        return df
    except Exception as e:
        print(f"Error en consulta de tráfico: {e}")
        return pd.DataFrame()

def get_simple_search_terms(engine, fecha_inicio, fecha_fin):
    """Consulta CORREGIDA de términos de búsqueda"""
    try:
        query = f"""
        SELECT 
            searchTerm,
            SUM(COALESCE(sessions, 0)) as sesiones_totales,
            SUM(COALESCE(activeUsers, 0)) as usuarios_activos
        FROM terminos_busqueda
        WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        AND searchTerm IS NOT NULL 
        AND searchTerm != ''
        AND searchTerm != '(not set)'
        GROUP BY searchTerm
        ORDER BY sesiones_totales DESC
        LIMIT 10
        """
        df = pd.read_sql(query, engine)
        print(f"Términos de búsqueda encontrados: {len(df)}")
        return df
    except Exception as e:
        print(f"Error en consulta de búsqueda: {e}")
        return pd.DataFrame()

# FUNCIÓN PRINCIPAL DE PRUEBA
def diagnose_database_issues():
    """Función para diagnosticar problemas de base de datos"""
    print("=== DIAGNÓSTICO DE BASE DE DATOS ===")
    
    # 1. Probar conexión básica
    print("\n1. Probando conexión básica...")
    if not test_connection():
        print("❌ Fallo en conexión básica")
        return
    
    # 2. Crear engine
    print("\n2. Creando engine SQLAlchemy...")
    engine = create_simple_connection()
    if engine is None:
        print("❌ Fallo creando engine")
        return
    
    # 3. Verificar tablas
    print("\n3. Verificando tablas disponibles...")
    tables_df = test_simple_query(engine)
    if tables_df.empty:
        print("❌ No se pudieron obtener las tablas")
        return
    
    # 4. Probar consultas básicas
    fecha_inicio = '2024-01-01'
    fecha_fin = '2024-12-31'
    
    print(f"\n4. Probando consultas con fechas: {fecha_inicio} a {fecha_fin}")
    
    # Métricas generales
    print("\n4a. Consultando métricas generales...")
    df_metrics = get_simple_metrics(engine, fecha_inicio, fecha_fin)
    if not df_metrics.empty:
        print("✅ Métricas obtenidas correctamente")
        print(df_metrics.head())
    
    # Dispositivos
    print("\n4b. Consultando dispositivos...")
    df_devices = get_simple_devices(engine, fecha_inicio, fecha_fin)
    if not df_devices.empty:
        print("✅ Dispositivos obtenidos correctamente")
        print(df_devices)
    
    # Fuentes de tráfico
    print("\n4c. Consultando fuentes de tráfico...")
    df_traffic = get_simple_traffic_sources(engine, fecha_inicio, fecha_fin)
    if not df_traffic.empty:
        print("✅ Fuentes de tráfico obtenidas correctamente")
        print(df_traffic)
    
    # Términos de búsqueda
    print("\n4d. Consultando términos de búsqueda...")
    df_search = get_simple_search_terms(engine, fecha_inicio, fecha_fin)
    if not df_search.empty:
        print("✅ Términos de búsqueda obtenidos correctamente")
        print(df_search)
    
    engine.dispose()
    print("\n=== FIN DEL DIAGNÓSTICO ===")

# Ejecutar diagnóstico
if __name__ == "__main__":
    diagnose_database_issues()