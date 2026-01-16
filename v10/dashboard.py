import mysql.connector
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from datetime import date, datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# 🗄️ CONFIGURACIÓN DE BASE DE DATOS Y TABLAS (ACTUALIZADA)
# =============================================================================

# Configuracion de la conexion
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'analytics_datos',
    'port': 3306
}

# 📋 CONFIGURACIÓN DE NOMBRES DE TABLAS (ACTUALIZADA CON NUEVAS TABLAS)
TABLE_CONFIG = {
    'metricas_generales': 'metricas_generales',
    'dispositivos': 'dispositivos', 
    'paginas_top': 'paginas_top',
    'geografia': 'geografia',
    'datos_horarios': 'datos_horarios',
    'terminos_busqueda': 'terminos_busqueda',
    'busqueda_interna': 'busqueda_interna',
    'fuentes_trafico': 'fuentes_trafico',
    'user_sessions' : 'user_sessions'
}
# =============================================================================
# 🔄 VARIABLES DE ESTADO PARA MODO COMPARACIÓN
# =============================================================================

# Inicializar variables de sesión para modo comparación
if 'comparison_mode' not in st.session_state:
    st.session_state.comparison_mode = False
if 'period1_start' not in st.session_state:
    st.session_state.period1_start = None
if 'period1_end' not in st.session_state:
    st.session_state.period1_end = None
if 'period2_start' not in st.session_state:
    st.session_state.period2_start = None
if 'period2_end' not in st.session_state:
    st.session_state.period2_end = None
# 🎨 CONFIGURACIÓN DE STREAMLIT
st.set_page_config(
    page_title="GA4 Analytics Dashboard",
    page_icon="https://www.gonzalezgimenez.com.py/assets_front/images/icons/favicon-32x32.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 👤 SISTEMA DE TRACKING DE SESIONES DE USUARIOS DEL DASHBOARD
# =============================================================================

def get_user_session_info():
    """Capturar información de la sesión del usuario que accede al dashboard"""
    import socket
    
    # Obtener headers usando el método correcto (nuevo en Streamlit)
    headers = {}
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            headers = st.context.headers
    except:
        pass
    
    # Obtener session_id de Streamlit
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        session_id = ctx.session_id if ctx else 'local-session'
    except:
        session_id = 'local-session'
    
    # Obtener información del cliente
    user_agent = headers.get('User-Agent', 'Unknown') if headers else 'Unknown'
    ip_address = headers.get('X-Forwarded-For', headers.get('Remote-Addr', '127.0.0.1')) if headers else '127.0.0.1'
    
    # Parsear user agent para obtener detalles
    device_type = 'Desktop'
    browser_name = 'Unknown'
    browser_version = 'Unknown'
    operating_system = 'Unknown'
    
    if user_agent != 'Unknown':
        user_agent_lower = user_agent.lower()
        
        # Detectar dispositivo
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
            device_type = 'Mobile'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            device_type = 'Tablet'
        
        # Detectar navegador
        if 'chrome' in user_agent_lower and 'edg' not in user_agent_lower:
            browser_name = 'Chrome'
        elif 'firefox' in user_agent_lower:
            browser_name = 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            browser_name = 'Safari'
        elif 'edg' in user_agent_lower:
            browser_name = 'Edge'
        elif 'opera' in user_agent_lower or 'opr' in user_agent_lower:
            browser_name = 'Opera'
        
        # Detectar sistema operativo
        if 'windows' in user_agent_lower:
            operating_system = 'Windows'
        elif 'mac' in user_agent_lower:
            operating_system = 'MacOS'
        elif 'linux' in user_agent_lower:
            operating_system = 'Linux'
        elif 'android' in user_agent_lower:
            operating_system = 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            operating_system = 'iOS'
    
    return {
        'session_id': session_id,
        'ip_address': ip_address,
        'user_agent': user_agent[:500],  # Limitar longitud
        'device_type': device_type,
        'browser_name': browser_name,
        'browser_version': browser_version,
        'operating_system': operating_system
    }

def track_user_session(db_connection):
    """Registrar o actualizar la sesión del usuario en la base de datos"""
    try:
        session_info = get_user_session_info()
        cursor = db_connection.cursor()
        
        # Verificar si la sesión ya existe
        check_query = """
            SELECT id, total_visits, pages_viewed 
            FROM user_sessions 
            WHERE session_id = %s
        """
        cursor.execute(check_query, (session_info['session_id'],))
        existing = cursor.fetchone()
        
        if existing:
            # Actualizar sesión existente
            update_query = """
                UPDATE user_sessions 
                SET last_access = NOW(),
                    total_visits = total_visits + 1,
                    pages_viewed = pages_viewed + 1,
                    updated_at = NOW()
                WHERE session_id = %s
            """
            cursor.execute(update_query, (session_info['session_id'],))
        else:
            # Insertar nueva sesión
            insert_query = """
                INSERT INTO user_sessions 
                (session_id, ip_address, user_agent, device_type, browser_name, 
                 browser_version, operating_system, first_access, last_access, 
                 total_visits, pages_viewed, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 1, 1, NOW(), NOW())
            """
            cursor.execute(insert_query, (
                session_info['session_id'],
                session_info['ip_address'],
                session_info['user_agent'],
                session_info['device_type'],
                session_info['browser_name'],
                session_info['browser_version'],
                session_info['operating_system']
            ))
        
        db_connection.commit()
        cursor.close()
        
        # Guardar en session_state para mostrar info
        st.session_state.user_tracked = True
        st.session_state.session_info = session_info
        
    except Exception as e:
        # Si falla el tracking, no interrumpir el dashboard
        print(f"Error tracking session: {e}")
        pass

# CSS personalizado mejorado
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .comparison-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        text-align: center;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    .date-filter-card {
        background: linear-gradient(45deg, #74b9ff, #0984e3);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .search-terms-card {
        background: linear-gradient(135deg, #00b894, #00cec9);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stAlert > div {
        padding: 0.5rem;
        border-radius: 8px;
    }
    
    .reportview-container .main .block-container {
        max-width: 95%;
    }
    
    .sidebar .sidebar-content {
        width: 300px;
    }
    
    /* Mejorar tablas */
    .stDataFrame > div {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Botones mejorados */
    .stButton > button {
        border-radius: 20px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    /* Headers más atractivos */
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    
    .comparison-metric-card {
        background: white;
        border: 2px solid #e8ecef;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    .positive-change {
        background: linear-gradient(135deg, #00b894 0%, #00cec9 100%);
        color: white;
    }

    .negative-change {
        background: linear-gradient(135deg, #e17055 0%, #d63031 100%);
        color: white;
    }

    .neutral-change {
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        color: white;
    }

    .comparison-mode-card {
        background: linear-gradient(45deg, #fdcb6e, #e17055);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 3px solid #fd79a8;
    }

    .period-header {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 0.5rem;
        padding: 0.5rem;
        border-radius: 5px;
    }

    .period-1 {
        background: linear-gradient(45deg, #74b9ff, #0984e3);
        color: white;
    }

    .period-2 {
        background: linear-gradient(45deg, #a29bfe, #6c5ce7);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
class DatabaseConnection:
    """Clase para manejar la conexión a la base de datos"""
    
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.raw_connection = None
        self._connect()
    
    def _connect(self):
        """Establecer conexión con MySQL"""
        try:
            connection_string = f"mysql+pymysql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            self.engine = create_engine(connection_string, pool_pre_ping=True)
            
            # Test de conexión básico
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Crear conexión raw para tracking de sesiones
            self.raw_connection = mysql.connector.connect(**self.config)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Error conectando a la base de datos: {e}")
            st.error("Verifica que WAMP esté ejecutándose y la configuración sea correcta")
            return False
    
    def get_raw_connection(self):
        """Obtener conexión raw de MySQL para operaciones específicas"""
        if not self.raw_connection or not self.raw_connection.is_connected():
            self.raw_connection = mysql.connector.connect(**self.config)
        return self.raw_connection
    
    def query(self, sql, params=None):
        """Ejecutar consulta SQL"""
        try:
            return pd.read_sql(sql, self.engine, params=params)
        except Exception as e:
            st.error(f"Error en consulta: {e}")
            return pd.DataFrame()
    
    def get_date_range(self):
        """Obtener rango de fechas disponibles"""
        try:
            sql = f"""
            SELECT 
                MIN(fecha) as min_date, 
                MAX(fecha) as max_date,
                COUNT(DISTINCT fecha) as total_days
            FROM {TABLE_CONFIG['metricas_generales']} 
            WHERE fecha IS NOT NULL
            """
            result = self.query(sql)
            if not result.empty:
                return {
                    'min_date': result['min_date'].iloc[0],
                    'max_date': result['max_date'].iloc[0],
                    'total_days': result['total_days'].iloc[0]
                }
            return None
        except:
            return None

    def get_available_dates(self):
        """Obtener todas las fechas disponibles en la BD"""
        try:
            sql = f"""
            SELECT DISTINCT fecha 
            FROM {TABLE_CONFIG['metricas_generales']}
            WHERE fecha IS NOT NULL
            ORDER BY fecha
            """
            result = self.query(sql)
            if not result.empty:
                return result['fecha'].tolist()
            return []
        except:
            return []

# =============================================================================
# FUNCIONES DE CONSULTA CON FILTRO DE FECHAS
# =============================================================================

@st.cache_data(ttl=300)
def get_device_breakdown_range(_db, fecha_inicio, fecha_fin):
    """Obtener distribución por dispositivos en un rango de fechas"""
    sql = f"""
    SELECT 
        DATE_FORMAT(fecha, '%%d/%%m/%%Y') AS "Fecha",
        deviceCategory as "Dispositivo",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones",
        SUM(screenPageViews) as "Páginas Vistas"
    FROM {TABLE_CONFIG['dispositivos']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY fecha, deviceCategory
    ORDER BY fecha, deviceCategory
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_top_pages_range(_db, fecha_inicio, fecha_fin):
    """Obtener páginas más visitadas en un rango de fechas"""
    sql = f"""
    SELECT 
        pagePath as "Direccion de Página",
        pageTitle as "Titulo de página",
        SUM(screenPageViews) as "Vista de Páginas",
        SUM(sessions) as "Sesiones",
        ROUND(AVG(bounceRate) * 100, 2) as "Tasa de Rebote",
        AVG(averageSessionDuration) as "Tiempo Promedio de Vista"
    FROM {TABLE_CONFIG['paginas_top']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY pagePath, pageTitle
    ORDER BY screenPageViews DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_geographic_data_range(_db, fecha_inicio, fecha_fin):
    """Obtener datos geográficos en un rango de fechas"""
    sql = f"""
    SELECT 
        country as "Pais",
        city as "Ciudad",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones",
        SUM(screenPageViews) as "Páginas Vistas"
    FROM {TABLE_CONFIG['geografia']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY country, city
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_hourly_data_range(_db, fecha_inicio, fecha_fin):
    """Obtener datos por hora en un rango de fechas"""
    sql = f"""
    SELECT 
        hour as "Hora",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones",
        SUM(screenPageViews) as "Vista de Páginas"
    FROM {TABLE_CONFIG['datos_horarios']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY hour
    ORDER BY hour
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_daily_trend_data(_db, fecha_inicio, fecha_fin):
    """Obtener tendencia diaria para el rango de fechas"""
    sql = f"""
    SELECT 
        DATE_FORMAT(fecha, '%%d/%%m/%%Y') AS "Fecha",
        SUM(activeUsers) AS "Usuarios Activos",
        SUM(sessions) AS "Sesiones",
        SUM(screenPageViews) AS "Vistas de Página",
        AVG(bounceRate) AS "Tasa de Rebote",
        AVG(averageSessionDuration) AS "Duración Media de Sesión"
    FROM {TABLE_CONFIG['metricas_generales']}
    WHERE fecha BETWEEN %s AND %s
    GROUP BY id
    ORDER BY id DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

# =============================================================================
# FUNCIONES PARA TÉRMINOS DE BÚSQUEDA
# =============================================================================

@st.cache_data(ttl=300)
def get_search_terms_range(_db, fecha_inicio, fecha_fin, limit=20):
    """Obtener términos de búsqueda más utilizados en un rango de fechas"""
    sql = f"""
    SELECT 
        searchTerm as "Término de Búsqueda",
        SUM(sessions) as "Sesiones",
        SUM(activeUsers) as "Usuarios Activos"
    FROM {TABLE_CONFIG['terminos_busqueda']} 
    WHERE fecha BETWEEN %s AND %s
    AND searchTerm IS NOT NULL 
    AND searchTerm != ''
    AND searchTerm != '(not set)'
    GROUP BY searchTerm
    ORDER BY SUM(sessions) DESC
    LIMIT %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin, limit))

@st.cache_data(ttl=300)
def get_search_terms_summary(_db, fecha_inicio, fecha_fin):
    """Obtener resumen de términos de búsqueda"""
    sql = f"""
    SELECT 
        searchTerm as "Término",
        SUM(sessions) as "Sesiones Totales",
        COUNT(DISTINCT DATE(fecha)) as "Días Activo"
    FROM {TABLE_CONFIG['terminos_busqueda']} 
    WHERE fecha BETWEEN %s AND %s
    AND searchTerm IS NOT NULL 
    AND searchTerm != ''
    AND searchTerm != '(not set)'
    GROUP BY searchTerm
    ORDER BY SUM(sessions) DESC
    LIMIT 10
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

# =============================================================================
# NUEVAS FUNCIONES PARA FUENTES DE TRÁFICO
# =============================================================================

@st.cache_data(ttl=300)
def get_traffic_sources_range(_db, fecha_inicio, fecha_fin, limit=20):
    """Obtener fuentes de tráfico principales"""
    sql = f"""
    SELECT 
        sourceMedium as "Fuente/Medio",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones"
    FROM {TABLE_CONFIG['fuentes_trafico']} 
    WHERE fecha BETWEEN %s AND %s
    AND sourceMedium IS NOT NULL 
    AND sourceMedium != ''
    AND sourceMedium != '(not set)'
    GROUP BY sourceMedium
    ORDER BY SUM(sessions) DESC
    LIMIT %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin, limit))

# =====================================================================================
# Funciones de comparacion
# =====================================================================================

def calculate_comparison_metrics(df1, df2):
    """Calcular métricas de comparación entre dos períodos"""
    if df1.empty or df2.empty:
        return None
    
    # Sumar métricas de cada período
    metrics1 = {
        'usuarios': df1['Usuarios Activos'].sum(),
        'sesiones': df1['Sesiones'].sum(),
        'paginas': df1['Vistas de Página'].sum(),
        'rebote': df1['Tasa de Rebote'].mean()
    }
    
    metrics2 = {
        'usuarios': df2['Usuarios Activos'].sum(),
        'sesiones': df2['Sesiones'].sum(),
        'paginas': df2['Vistas de Página'].sum(),
        'rebote': df2['Tasa de Rebote'].mean()
    }
    
    # Calcular cambios porcentuales
    comparisons = {}
    for key in metrics1.keys():
        if metrics2[key] != 0:
            change = ((metrics1[key] - metrics2[key]) / metrics2[key]) * 100
        else:
            change = 0 if metrics1[key] == 0 else 100
        
        comparisons[key] = {
            'period1': metrics1[key],
            'period2': metrics2[key],
            'change_pct': change,
            'change_abs': metrics1[key] - metrics2[key]
        }
    
    return comparisons

# =============================================================================
# COMPARACIONES PERSONALIZABLES
# =============================================================================

def compare_metrics_detailed(df1, df2, metric_name):
    """Comparación detallada de una métrica específica"""
    if df1.empty or df2.empty:
        return None
    
    value1 = df1[metric_name].sum() if metric_name != 'Tasa de Rebote' else df1[metric_name].mean()
    value2 = df2[metric_name].sum() if metric_name != 'Tasa de Rebote' else df2[metric_name].mean()
    
    if value2 != 0:
        change_pct = ((value1 - value2) / value2) * 100
    else:
        change_pct = 0 if value1 == 0 else 100
    
    return {
        'period1': value1,
        'period2': value2,
        'change_pct': change_pct,
        'change_abs': value1 - value2
    }

def compare_devices(df1, df2):
    """Comparación detallada por dispositivos"""
    if df1.empty or df2.empty:
        return None
    
    # Agrupar por dispositivo
    devices1 = df1.groupby('Dispositivo')[['Usuarios Activos', 'Sesiones']].sum()
    devices2 = df2.groupby('Dispositivo')[['Usuarios Activos', 'Sesiones']].sum()
    
    comparison = {}
    for device in set(list(devices1.index) + list(devices2.index)):
        p1_users = devices1.loc[device, 'Usuarios Activos'] if device in devices1.index else 0
        p2_users = devices2.loc[device, 'Usuarios Activos'] if device in devices2.index else 0
        
        if p2_users != 0:
            change = ((p1_users - p2_users) / p2_users) * 100
        else:
            change = 0 if p1_users == 0 else 100
        
        comparison[device] = {
            'period1_users': p1_users,
            'period2_users': p2_users,
            'change_pct': change
        }
    
    return comparison

def compare_pages(df1, df2, top_n=10):
    """Comparación de páginas más visitadas"""
    if df1.empty or df2.empty:
        return None
    
    # CORRECCIÓN: Obtener TODAS las páginas únicas sin filtrar primero
    all_pages = set(list(df1['Direccion de Página'].unique()) + list(df2['Direccion de Página'].unique()))
    
    comparison = {}
    
    # Buscar en los DataFrames COMPLETOS
    for page in all_pages:
        p1_views = df1[df1['Direccion de Página'] == page]['Vista de Páginas'].sum()
        p2_views = df2[df2['Direccion de Página'] == page]['Vista de Páginas'].sum()
        
        if p2_views != 0:
            change = ((p1_views - p2_views) / p2_views) * 100
        else:
            change = 0 if p1_views == 0 else 100
        
        comparison[page] = {
            'period1_views': p1_views,
            'period2_views': p2_views,
            'change_pct': change
        }
    
    # Ordenar por valor total (suma de ambos períodos) para mostrar las páginas más relevantes
    sorted_comparison = dict(sorted(
        comparison.items(),
        key=lambda x: x[1]['period1_views'] + x[1]['period2_views'],
        reverse=True
    ))
    
    # Retornar solo el top_n pero con datos completos
    return dict(list(sorted_comparison.items())[:top_n])

def compare_search_terms(df1, df2, top_n=10):
    """Comparación de términos de búsqueda más utilizados"""
    if df1.empty or df2.empty:
        return None
    
    # CORRECCIÓN: Obtener TODOS los términos únicos sin filtrar primero
    all_terms = set(list(df1['Término de Búsqueda'].unique()) + list(df2['Término de Búsqueda'].unique()))
    
    comparison = {}
    
    # Buscar en los DataFrames COMPLETOS
    for term in all_terms:
        p1_sessions = df1[df1['Término de Búsqueda'] == term]['Sesiones'].sum()
        p2_sessions = df2[df2['Término de Búsqueda'] == term]['Sesiones'].sum()
        
        if p2_sessions != 0:
            change = ((p1_sessions - p2_sessions) / p2_sessions) * 100
        else:
            change = 0 if p1_sessions == 0 else 100
        
        comparison[term] = {
            'period1_sessions': p1_sessions,
            'period2_sessions': p2_sessions,
            'change_pct': change
        }
    
    # Ordenar por valor total (suma de ambos períodos) para mostrar los términos más relevantes
    sorted_comparison = dict(sorted(
        comparison.items(),
        key=lambda x: x[1]['period1_sessions'] + x[1]['period2_sessions'],
        reverse=True
    ))
    
    # Retornar solo el top_n pero con datos completos
    return dict(list(sorted_comparison.items())[:top_n])

def compare_geography(df1, df2, top_n=10):
    """Comparación de datos geográficos"""
    if df1.empty or df2.empty:
        return None
    
    # CORRECCIÓN: Agrupar TODOS los países sin filtrar primero
    countries1 = df1.groupby('Pais')['Usuarios Activos'].sum()
    countries2 = df2.groupby('Pais')['Usuarios Activos'].sum()
    
    comparison = {}
    all_countries = set(list(countries1.index) + list(countries2.index))
    
    # Buscar en los grupos COMPLETOS
    for country in all_countries:
        p1_users = countries1[country] if country in countries1.index else 0
        p2_users = countries2[country] if country in countries2.index else 0
        
        if p2_users != 0:
            change = ((p1_users - p2_users) / p2_users) * 100
        else:
            change = 0 if p1_users == 0 else 100
        
        comparison[country] = {
            'period1_users': p1_users,
            'period2_users': p2_users,
            'change_pct': change
        }
    
    # Ordenar por valor total (suma de ambos períodos) para mostrar los países más relevantes
    sorted_comparison = dict(sorted(
        comparison.items(),
        key=lambda x: x[1]['period1_users'] + x[1]['period2_users'],
        reverse=True
    ))
    
    # Retornar solo el top_n pero con datos completos
    return dict(list(sorted_comparison.items())[:top_n])

def compare_traffic_sources(df1, df2, top_n=10):
    """Comparación de fuentes de tráfico"""
    if df1.empty or df2.empty:
        return None
    
    # CORRECCIÓN: NO filtrar antes - obtener TODAS las fuentes únicas de ambos períodos
    all_sources = set(list(df1['Fuente/Medio'].unique()) + list(df2['Fuente/Medio'].unique()))
    
    comparison = {}
    
    # Buscar en los DataFrames COMPLETOS (sin filtrar)
    for source in all_sources:
        # Buscar en el DataFrame COMPLETO del período 1
        p1_sessions = df1[df1['Fuente/Medio'] == source]['Sesiones'].sum()
        # Buscar en el DataFrame COMPLETO del período 2
        p2_sessions = df2[df2['Fuente/Medio'] == source]['Sesiones'].sum()
        
        if p2_sessions != 0:
            change = ((p1_sessions - p2_sessions) / p2_sessions) * 100
        else:
            change = 0 if p1_sessions == 0 else 100
        
        comparison[source] = {
            'period1_sessions': p1_sessions,
            'period2_sessions': p2_sessions,
            'change_pct': change
        }
    
    # Ordenar por valor total (suma de ambos períodos) para mostrar las fuentes más relevantes
    sorted_comparison = dict(sorted(
        comparison.items(), 
        key=lambda x: x[1]['period1_sessions'] + x[1]['period2_sessions'], 
        reverse=True
    ))
    
    # Retornar solo el top_n pero con datos completos
    return dict(list(sorted_comparison.items())[:top_n])

# =============================================================================
# 🔍 FUNCIONES DE VALIDACIÓN PARA COMPARACIÓN
# =============================================================================

def validate_period_duration(start1, end1, start2, end2):
    """Validar que ambos períodos tengan la misma duración"""
    duration1 = (end1 - start1).days + 1
    duration2 = (end2 - start2).days + 1
    return duration1 == duration2

def check_data_availability(db, fecha_inicio, fecha_fin):
    """Verificar disponibilidad de datos para un período"""
    available_dates = db.get_available_dates()
    if available_dates and hasattr(available_dates[0], 'date'):
        available_dates = [d.date() for d in available_dates]
    
    missing_dates = []
    current_date = fecha_inicio
    while current_date <= fecha_fin:
        if current_date not in available_dates:
            missing_dates.append(current_date)
        current_date += timedelta(days=1)
    
    return missing_dates


def create_comparison_metric_card(title, data, icon, is_percentage=False):
    """Crear tarjeta de métrica de comparación"""
    period1_val = data['period1']
    period2_val = data['period2']
    change_pct = data['change_pct']
    change_abs = data['change_abs']
    
    # Formatear valores
    if is_percentage:
        period1_str = f"{period1_val:.2%}"
        period2_str = f"{period2_val:.2%}"
        change_abs_str = f"{change_abs:.2%}"
    else:
        period1_str = f"{int(period1_val):,}".replace(",", ".")
        period2_str = f"{int(period2_val):,}".replace(",", ".")
        change_abs_str = f"{int(change_abs):,}".replace(",", ".")
    
    # Determinar color y flecha
    color_class = "positive-change" if change_pct > 0 else "negative-change" if change_pct < 0 else "neutral-change"
    arrow = "↗️" if change_pct > 0 else "↘️" if change_pct < 0 else "➡️"
    
    return f"""
    <div class="comparison-metric-card {color_class}">
        <h4>{icon} {title}</h4>
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 1rem 0;">
            <div style="text-align: center;">
                <div style="font-size: 1.5em; font-weight: bold;">{period1_str}</div>
                <div style="font-size: 0.9em; opacity: 0.8;">Período 1</div>
            </div>
            <div style="text-align: center; margin: 0 1rem;">
                <div style="font-size: 1.2em;">{arrow}</div>
                <div style="font-size: 1em; font-weight: bold;">{change_pct:+.1f}%</div>
                <div style="font-size: 0.8em;">({'+' if change_abs >= 0 else ''}{change_abs_str})</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5em; font-weight: bold;">{period2_str}</div>
                <div style="font-size: 0.9em; opacity: 0.8;">Período 2</div>
            </div>
        </div>
    </div>
    """

def create_detailed_comparison_chart(comparison_dict, title, metric_label):
    """Crear gráfico para comparación detallada de elementos"""
    if not comparison_dict:
        return None
    
    # Preparar datos
    items = list(comparison_dict.keys())[:15]  # Top 15
    p1_values = [comparison_dict[item].get('period1_users', comparison_dict[item].get('period1_sessions', comparison_dict[item].get('period1_views', 0))) for item in items]
    p2_values = [comparison_dict[item].get('period2_users', comparison_dict[item].get('period2_sessions', comparison_dict[item].get('period2_views', 0))) for item in items]
    changes = [comparison_dict[item]['change_pct'] for item in items]
    
    # Crear dataframe
    df_comp = pd.DataFrame({
        'Item': items,
        'Período 1': p1_values,
        'Período 2': p2_values,
        'Cambio %': changes
    })
    
    # Colores basados en cambio
    colors = ['green' if c > 0 else 'red' if c < 0 else 'gray' for c in changes]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df_comp['Item'],
        x=df_comp['Período 1'],
        name='Período 1',
        orientation='h',
        marker_color='#3498db'
    ))
    
    fig.add_trace(go.Bar(
        y=df_comp['Item'],
        x=df_comp['Período 2'],
        name='Período 2',
        orientation='h',
        marker_color='#e74c3c'
    ))
    
    fig.update_layout(
        title=title,
        barmode='group',
        height=400 + (len(items) * 15),
        xaxis_title=metric_label,
        yaxis_title='',
        hovermode='y unified'
    )
    
    return fig

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN PARA FUENTES DE TRÁFICO
# =============================================================================

def create_traffic_sources_chart(df_traffic):
    """Crear gráfico de fuentes de tráfico principales"""
    if df_traffic.empty:
        return None
    
    # Tomar los top 10 para mejor visualización
    df_top = df_traffic.head(10)
    
    fig = px.bar(
        df_top,
        x='Sesiones',
        y='Fuente/Medio',
        orientation='h',
        color='Usuarios Activos',
        color_continuous_scale='plasma',
        text='Sesiones'
    )
    
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(
        height=500,
        yaxis={'categoryorder':'total ascending'},
        yaxis_title="Fuente/Medio",
        xaxis_title="Número de Sesiones"
    )
    
    return fig

# ____________________________________________________________________________
# FUNCIONES DE VISUALIZACIÓN AJUSTADAS Y NUEVAS
# =============================================================================

def create_search_terms_chart(df_search):
    """Crear gráfico de términos de búsqueda más populares"""
    if df_search.empty:
        return None
    
    # Tomar los top 15 términos
    df_top = df_search.head(15)
    
    fig = px.bar(
        df_top,
        x='Sesiones',
        y='Término de Búsqueda',
        orientation='h',
        title="🔍 Top 15 Términos de Búsqueda Más Populares",
        color='Usuarios Activos',
        color_continuous_scale='viridis',
        text='Sesiones'
    )
    
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(
        height=500,
        yaxis={'categoryorder':'total ascending'},
        yaxis_title="Término de Búsqueda",
        xaxis_title="Número de Sesiones"
    )
    
    return fig

# Funciones originales de visualización (sin cambios)
def create_device_comparison(df_devices):
    """Crear gráfico de comparación de dispositivos"""
    if df_devices.empty:
        return None
    
    # Fix: Use correct column names that match the database query
    df_devices_clean = df_devices.rename(columns={
        'Usuarios Activos': 'usuarios',
        'Sesiones': 'sesiones'
    })
    
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=('Distribución de Usuarios', 'Sesiones por Dispositivo')
    )
    
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
    
    # Pie chart - Fix: Use 'Dispositivo' (singular) which is the actual column name
    fig.add_trace(
        go.Pie(
            labels=df_devices_clean['Dispositivo'], 
            values=df_devices_clean['usuarios'],
            name="Usuarios",
            marker_colors=colors[:len(df_devices_clean)],
            hovertemplate='%{label}<br>Usuarios: %{value:,.0f}<br>%{percent}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Bar chart
    fig.add_trace(
        go.Bar(
            x=df_devices_clean['Dispositivo'], 
            y=df_devices_clean['sesiones'],
            name="Sesiones",
            marker_color=colors[:len(df_devices_clean)],
            hovertemplate='%{x}<br>Sesiones: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=400,
        title_text="📱 Análisis por Tipo de Dispositivo (Período Total)",
        title_x=0.5
    )
    
    return fig

def create_geographic_chart(df_geo):
    """Crear visualización geográfica"""
    if df_geo.empty:
        return None
    
    # Fix: Use correct column names from the query
    df_countries = df_geo.groupby('Pais')['Usuarios Activos'].sum().reset_index()
    df_countries = df_countries.sort_values('Usuarios Activos', ascending=True).tail(10)
    
    fig = px.bar(
        df_countries,
        x='Usuarios Activos',  # Fixed column name
        y='Pais',             # Fixed column name
        orientation='h',
        title="🌍 Top 10 Países por Usuarios (Período Total)",
        color='Usuarios Activos',  # Fixed column name
        color_continuous_scale='viridis',
        text='Usuarios Activos'    # Fixed column name
    )
    
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(
        height=400,
        yaxis_title="País",
        xaxis_title="Usuarios",
        showlegend=False
    )
    
    return fig

def create_hourly_chart(df_hourly):
    """Crear gráfico de actividad por hora"""
    if df_hourly.empty:
        return None
    
    # Renombrar columnas para consistencia
    df_hourly_clean = df_hourly.rename(columns={
        'Usuarios Activos': 'usuarios',
        'Sesiones': 'sesiones'
    })
    
    # Asegurar que todas las horas de 0 a 23 estén presentes
    all_hours = pd.DataFrame({'Hora': range(24)})
    df_hourly_clean = all_hours.merge(df_hourly_clean, on='Hora', how='left').fillna(0)
    
    fig = px.line(
        df_hourly_clean,
        x='Hora',
        y=['usuarios', 'sesiones'],
        title="📊 Actividad por Hora del Día (Promedio del Período)",
        labels={'Hora': 'Hora del Día', 'value': 'Cantidad'}
    )
    
    fig.update_layout(
        height=400,
        xaxis=dict(tickmode='array', tickvals=list(range(0, 24, 2))),
        yaxis_title="Cantidad"
    )
    
    return fig

def create_pages_performance_chart(df_pages):
    """Crear gráfico de rendimiento de páginas"""
    if df_pages.empty:
        return None
    
    # Preparar datos
    df_pages_clean = df_pages.copy()
    df_pages_clean['tasa_rebote'] = df_pages_clean['Tasa de Rebote']
    df_pages_clean['visualizaciones'] = df_pages_clean['Vista de Páginas']
    df_pages_clean['duracion_promedio'] = df_pages_clean['Tiempo Promedio de Vista']
    
    df_pages_top = df_pages_clean.head(15)
    
    fig = px.bar(
        df_pages_top,
        x='visualizaciones',
        y='Direccion de Página',
        orientation='h',
        title="📄 Top 15 Páginas Más Visitadas (Período Total)",
        color='tasa_rebote',
        color_continuous_scale='RdYlGn_r',
        hover_data=['Sesiones', 'tasa_rebote', 'duracion_promedio']
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder':'total ascending'},
        yaxis_title="Página",
        xaxis_title="Visualizaciones"
    )
    
    return fig

def create_summary_metrics_cards(df_trend):
    """Crear tarjetas de resumen de métricas para el período"""
    if df_trend.empty:
        return None, None, None, None
    
    # Sumar todas las métricas del período
    total_users = df_trend['Usuarios Activos'].sum()
    total_sessions = df_trend['Sesiones'].sum()
    total_pageviews = df_trend['Vistas de Página'].sum()
    avg_bounce_rate = df_trend['Tasa de Rebote'].mean()
    
    return total_users, total_sessions, total_pageviews, avg_bounce_rate

# MODIFICADO: Nueva función para mostrar números completos
def format_number_complete(num):
    """Formatear números mostrando todos los dígitos con separadores de miles"""
    return f"{int(num):,}".replace(",", ".")

def format_percentage(num):
    """Formatear porcentajes"""
    return f"{num:.2%}"

def create_metric_card_html(title, value, icon="📊"):
    """Crear HTML para tarjetas de métricas"""
    return f"""
    <div class="metric-card">
        <h4>{icon} {title}</h4>
        <h2>{value}</h2>
    </div>
    """

def main_dashboard():
    """Función principal del dashboard"""
    # Inicializar conexión
    db = DatabaseConnection(DB_CONFIG)
    
    # 👤 Tracking de sesión de usuario (solo una vez por sesión)
    if 'user_tracked' not in st.session_state:
        try:
            track_user_session(db.get_raw_connection())
        except Exception as e:
            # No interrumpir el dashboard si falla el tracking
            pass
    
    # Título principal
    st.title("📊 GA4 Analytics Dashboard")
    st.markdown("---")
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("🔧 Configuración del Dashboard")
        # Toggle para modo comparación
        comparison_mode = st.toggle(
            "🔄 Modo Comparación",
            value=st.session_state.comparison_mode,
            help="Activar para comparar dos períodos de tiempo"
        )
        
        if comparison_mode != st.session_state.comparison_mode:
            st.session_state.comparison_mode = comparison_mode
            st.rerun()
        
        if comparison_mode:
            st.markdown("""
            <div class="comparison-mode-card">
                <h4>🔄 Modo Comparación Activado</h4>
                <p>Selecciona dos períodos para comparar métricas</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Obtener fechas disponibles (todas)
        available_dates = db.get_available_dates()
        available_dates = [d for d in available_dates if d < date.today()]  # excluir hoy
        
        if available_dates:
            st.success(f"📅 Datos disponibles: {len(available_dates)} días")
            # Convertir available_dates a objetos date si no lo están ya
            if available_dates and hasattr(available_dates[0], 'date'):
                dates_only = [d.date() for d in available_dates]
            else:
                dates_only = available_dates

            # Calcular fechas mínima y máxima disponibles
            min_date = min(dates_only)
            max_date = max(dates_only)
            
            # Calcular default (últimos 7 días disponibles)
            default_start = dates_only[-7] if len(dates_only) >= 7 else dates_only[0]
            default_end = dates_only[-1]

            if comparison_mode:
                        # =============================================================================
                        # INTERFACE PARA MODO COMPARACIÓN
                        # =============================================================================
                        
                        st.subheader("📊 Configuración de Comparación")
                        
                        # Pestañas para selección de períodos
                        tab1, tab2 = st.tabs(["📅 Período 1", "📅 Período 2"])
                        
                        with tab1:
                            st.markdown('<div class="period-header period-1">Período 1 (Principal)</div>', unsafe_allow_html=True)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                period1_start = st.date_input(
                                    "Fecha Inicio P1:",
                                    value=st.session_state.period1_start or default_start,
                                    min_value=min_date,
                                    max_value=max_date,
                                    key="p1_start"
                                )
                            
                            with col2:
                                period1_end = st.date_input(
                                    "Fecha Fin P1:",
                                    value=st.session_state.period1_end or default_end,
                                    min_value=min_date,
                                    max_value=max_date,
                                    key="p1_end"
                                )
                            
                            # Validar que fecha inicio sea menor o igual a fecha fin
                            if period1_start > period1_end:
                                st.error("❌ La fecha de inicio del Período 1 debe ser anterior o igual a la fecha de fin")
                                st.stop()
                            
                            # Verificar datos disponibles para período 1
                            missing_p1 = check_data_availability(db, period1_start, period1_end)
                            if missing_p1:
                                st.warning(f"⚠️ Período 1: {len(missing_p1)} fecha(s) sin datos")
                        
                        with tab2:
                            st.markdown('<div class="period-header period-2">Período 2 (Comparación)</div>', unsafe_allow_html=True)
                            
                            # Selección manual período 2
                            col1, col2 = st.columns(2)
                            
                            # Calcular período anterior sugerido
                            duracion = (period1_end - period1_start).days + 1
                            nuevo_fin = period1_start - timedelta(days=1)
                            nuevo_inicio = nuevo_fin - timedelta(days=duracion - 1)
                            
                            with col1:
                                period2_start = st.date_input(
                                    "Fecha Inicio P2:",
                                    value=st.session_state.period2_start or nuevo_inicio,
                                    min_value=min_date,
                                    max_value=max_date,
                                    key="p2_start"
                                )
                            
                            with col2:
                                period2_end = st.date_input(
                                    "Fecha Fin P2:",
                                    value=st.session_state.period2_end or nuevo_fin,
                                    min_value=min_date,
                                    max_value=max_date,
                                    key="p2_end"
                                )
                            
                            # Validar que fecha inicio sea menor o igual a fecha fin
                            if period2_start > period2_end:
                                st.error("❌ La fecha de inicio del Período 2 debe ser anterior o igual a la fecha de fin")
                                st.stop()
                            
                            # Verificar datos disponibles para período 2
                            missing_p2 = check_data_availability(db, period2_start, period2_end)
                            if missing_p2:
                                st.warning(f"⚠️ Período 2: {len(missing_p2)} fecha(s) sin datos")
                        
                        # Validaciones
                        duration1 = (period1_end - period1_start).days + 1
                        duration2 = (period2_end - period2_start).days + 1
                        
                        if duration1 != duration2:
                            st.warning(f"⚠️ Los períodos tienen diferente duración: P1={duration1} días, P2={duration2} días. La comparación puede no ser precisa.")
                        
                        # Botón para intercambiar períodos
                        # if st.button("🔄 Intercambiar Períodos"):
                        #     period1_start, period2_start = period2_start, period1_start
                        #     period1_end, period2_end = period2_end, period1_end
                        #     st.rerun()
                        
                        # Actualizar variables de sesión
                        st.session_state.period1_start = period1_start
                        st.session_state.period1_end = period1_end
                        st.session_state.period2_start = period2_start
                        st.session_state.period2_end = period2_end
                        
                        # Asignar fechas para consultas
                        fecha_inicio, fecha_fin = period1_start, period1_end
                        fecha_inicio_p2, fecha_fin_p2 = period2_start, period2_end
                        
            else:
                        # =============================================================================
                        # MODO NORMAL - SELECCIÓN DE FECHAS ORIGINAL
                        # =============================================================================
                        
                        st.subheader("📅 Filtro de Fechas")


                        col1, col2 = st.columns(2)

                        with col1:
                            fecha_inicio = st.date_input(
                                "📅 Fecha Inicio:",
                                value=default_start,
                                min_value=min_date,
                                max_value=max_date,
                                help="Selecciona la fecha de inicio del período"
                            )

                        with col2:
                            fecha_fin = st.date_input(
                                "📅 Fecha Fin:",
                                value=default_end,
                                min_value=fecha_inicio,
                                max_value=max_date,
                                help="Selecciona la fecha de fin del período"
                            )

                        # Validar que las fechas seleccionadas estén en la base de datos
                        fechas_no_disponibles = []
                        
                        if fecha_inicio not in dates_only:
                            fechas_no_disponibles.append(f"Fecha inicio: {fecha_inicio}")
                        
                        if fecha_fin not in dates_only:
                            fechas_no_disponibles.append(f"Fecha fin: {fecha_fin}")

                        # Mostrar advertencias si hay fechas no disponibles
                        if fechas_no_disponibles:
                            st.warning(f"⚠️ Las siguientes fechas no tienen datos disponibles:\n" + 
                                    "\n".join([f"• {fecha}" for fecha in fechas_no_disponibles]))
                            
                            # Mostrar fechas disponibles más cercanas
                            st.info("💡 **Fechas disponibles más cercanas:**")
                            
                            # Encontrar fecha disponible más cercana a fecha_inicio
                            if fecha_inicio not in dates_only:
                                closest_start = min(dates_only, key=lambda x: abs((x - fecha_inicio).days))
                                st.write(f"• Para fecha inicio: {closest_start}")
                            
                            # Encontrar fecha disponible más cercana a fecha_fin
                            if fecha_fin not in dates_only:
                                closest_end = min(dates_only, key=lambda x: abs((x - fecha_fin).days))
                                st.write(f"• Para fecha fin: {closest_end}")

                        # Validar rango de fechas
                        if fecha_inicio > fecha_fin:
                            st.error("❌ La fecha de inicio debe ser anterior o igual a la fecha de fin")
                            st.stop()

                        # Filtrar solo fechas que existen en la base de datos dentro del rango
                        fechas_en_rango = [d for d in dates_only if fecha_inicio <= d <= fecha_fin]
                        
                        if not fechas_en_rango:
                            st.error("❌ No hay datos disponibles en el rango de fechas seleccionado")
                            st.stop()

                        # Mostrar información del período seleccionado
                        dias_totales = (fecha_fin - fecha_inicio).days + 1
                        dias_disponibles = len(fechas_en_rango)

                        # Mostrar fechas faltantes si las hay
                        if dias_disponibles < dias_totales:
                            fechas_faltantes = []
                            current_date = fecha_inicio
                            while current_date <= fecha_fin:
                                if current_date not in dates_only:
                                    fechas_faltantes.append(current_date)
                                current_date += timedelta(days=1)
                            
                            if fechas_faltantes:
                                with st.expander(f"⚠️ Ver {len(fechas_faltantes)} fecha(s) sin datos"):
                                    for fecha in fechas_faltantes:
                                        st.write(f"• {fecha.strftime('%Y-%m-%d')}")
        else:
            st.error("❌ No hay fechas disponibles en la base de datos")
            st.stop()
        
        # 👤 Información de sesión (opcional, para debug)
        st.markdown("---")
        with st.expander("🔐 Info de Sesión", expanded=False):
            if 'session_info' in st.session_state:
                info = st.session_state.session_info
                st.markdown(f"""
                **Dispositivo:** {info['device_type']}  
                **Navegador:** {info['browser_name']}  
                **Sistema:** {info['operating_system']}  
                **Session ID:** `{info['session_id'][:16]}...`
                """)
            else:
                st.info("Sesión no rastreada")

    
    # =============================================================================
    # 📊 CARGA DE DATOS SEGÚN MODO
    # =============================================================================
    
    if comparison_mode:
        # Cargar datos para ambos períodos
        with st.spinner("📊 Cargando datos para comparación..."):
            # Período 1
            df_trend_p1 = get_daily_trend_data(db, fecha_inicio, fecha_fin)
            df_devices_p1 = get_device_breakdown_range(db, fecha_inicio, fecha_fin)
            df_pages_p1 = get_top_pages_range(db, fecha_inicio, fecha_fin)
            df_geo_p1 = get_geographic_data_range(db, fecha_inicio, fecha_fin)
            df_hourly_p1 = get_hourly_data_range(db, fecha_inicio, fecha_fin)
            df_traffic_sources_p1 = get_traffic_sources_range(db, fecha_inicio, fecha_fin)
            df_search_terms_p1 = get_search_terms_range(db, fecha_inicio, fecha_fin)
            
            # Período 2
            df_trend_p2 = get_daily_trend_data(db, fecha_inicio_p2, fecha_fin_p2)
            df_devices_p2 = get_device_breakdown_range(db, fecha_inicio_p2, fecha_fin_p2)
            df_pages_p2 = get_top_pages_range(db, fecha_inicio_p2, fecha_fin_p2)
            df_geo_p2 = get_geographic_data_range(db, fecha_inicio_p2, fecha_fin_p2)
            df_hourly_p2 = get_hourly_data_range(db, fecha_inicio_p2, fecha_fin_p2)
            df_traffic_sources_p2 = get_traffic_sources_range(db, fecha_inicio_p2, fecha_fin_p2)
            df_search_terms_p2 = get_search_terms_range(db, fecha_inicio_p2, fecha_fin_p2)
    else:
        # Obtener datos para el rango de fechas seleccionado (MODO NORMAL)
        with st.spinner("📊 Cargando datos del período seleccionado..."):
            df_trend = get_daily_trend_data(db, fecha_inicio, fecha_fin)
            df_devices = get_device_breakdown_range(db, fecha_inicio, fecha_fin)
            df_pages = get_top_pages_range(db, fecha_inicio, fecha_fin)
            df_geo = get_geographic_data_range(db, fecha_inicio, fecha_fin)
            df_hourly = get_hourly_data_range(db, fecha_inicio, fecha_fin)
            df_traffic_sources = get_traffic_sources_range(db, fecha_inicio, fecha_fin)
            df_search_terms = get_search_terms_range(db, fecha_inicio, fecha_fin)
            df_search_summary = get_search_terms_summary(db, fecha_inicio, fecha_fin)
    
    # =============================================================================
    # 🔄 VERIFICACIÓN Y VISTA DE COMPARACIÓN
    # =============================================================================
    
    if comparison_mode:
        # Verificar datos para modo comparación
        if df_trend_p1.empty or df_trend_p2.empty:
            st.error("❌ No hay suficientes datos para realizar la comparación")
            return
        
        # Mostrar períodos comparados
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="date-filter-card period-1">
                <h3>📅 Período 1</h3>
                <p><strong>Desde:</strong> {fecha_inicio.strftime('%d/%m/%Y')} <strong>Hasta:</strong> {fecha_fin.strftime('%d/%m/%Y')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="date-filter-card period-2">
                <h3>📅 Período 2</h3>
                <p><strong>Desde:</strong> {fecha_inicio_p2.strftime('%d/%m/%Y')} <strong>Hasta:</strong> {fecha_fin_p2.strftime('%d/%m/%Y')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Calcular métricas de comparación
        comparison_data = calculate_comparison_metrics(df_trend_p1, df_trend_p2)
        
        if comparison_data:
            st.header("📊 Centro de Comparación")
            
            # Selector de tipo de comparación
            st.subheader("🔍 Selecciona qué comparar:")
            comparison_type = st.radio(
                "Tipo de comparación:",
                options=[
                    "📊 Métricas Generales",
                    "📱 Dispositivos",
                    "📄 Páginas Visitadas",
                    "🔍 Términos de Búsqueda",
                    "🌍 Geografía",
                    "🚀 Fuentes de Tráfico"
                ],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            st.markdown("---")
            
            # COMPARACIÓN: MÉTRICAS GENERALES
            if comparison_type == "📊 Métricas Generales":
                st.subheader("📊 Comparación de Métricas Generales")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(create_comparison_metric_card(
                        "Usuarios Activos", comparison_data['usuarios'], "👥"
                    ), unsafe_allow_html=True)
                    
                    st.markdown(create_comparison_metric_card(
                        "Páginas Vistas", comparison_data['paginas'], "👀"
                    ), unsafe_allow_html=True)
                
                with col2:
                    st.markdown(create_comparison_metric_card(
                        "Sesiones", comparison_data['sesiones'], "📱"
                    ), unsafe_allow_html=True)
                    
                    st.markdown(create_comparison_metric_card(
                        "Tasa de Rebote", comparison_data['rebote'], "⚡", is_percentage=True
                    ), unsafe_allow_html=True)
            
            # COMPARACIÓN: DISPOSITIVOS
            elif comparison_type == "📱 Dispositivos":
                st.subheader("📱 Comparación por Dispositivos")
                
                if not df_devices_p1.empty and not df_devices_p2.empty:
                    devices_comparison = compare_devices(df_devices_p1, df_devices_p2)
                    
                    if devices_comparison:
                        # Mostrar tabla de comparación
                        comp_data = []
                        for device, data in devices_comparison.items():
                            comp_data.append({
                                'Dispositivo': device,
                                'P1 Usuarios': int(data['period1_users']),
                                'P2 Usuarios': int(data['period2_users']),
                                'Cambio %': f"{data['change_pct']:+.1f}%"
                            })
                        
                        df_comp_display = pd.DataFrame(comp_data)
                        st.dataframe(df_comp_display, use_container_width=True)
                        
                        # Gráfico
                        chart = create_detailed_comparison_chart(
                            devices_comparison, 
                            "📱 Comparación de Usuarios por Dispositivo",
                            "Usuarios Activos"
                        )
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                else:
                    st.warning("⚠️ Datos de dispositivos no disponibles")
            
            # COMPARACIÓN: PÁGINAS
            elif comparison_type == "📄 Páginas Visitadas":
                st.subheader("📄 Comparación de Páginas Más Visitadas")
                
                if not df_pages_p1.empty and not df_pages_p2.empty:
                    pages_comparison = compare_pages(df_pages_p1, df_pages_p2, top_n=10)
                    
                    if pages_comparison:
                        comp_data = []
                        for page, data in list(pages_comparison.items())[:10]:
                            comp_data.append({
                                'Página': page[:60] + "..." if len(page) > 60 else page,
                                'P1 Vistas': int(data['period1_views']),
                                'P2 Vistas': int(data['period2_views']),
                                'Cambio %': f"{data['change_pct']:+.1f}%"
                            })
                        
                        df_comp_display = pd.DataFrame(comp_data)
                        st.dataframe(df_comp_display, use_container_width=True)
                        
                        chart = create_detailed_comparison_chart(
                            pages_comparison,
                            "📄 Comparación de Vistas por Página",
                            "Vistas de Página"
                        )
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                else:
                    st.warning("⚠️ Datos de páginas no disponibles")
            
            # COMPARACIÓN: TÉRMINOS DE BÚSQUEDA
            elif comparison_type == "🔍 Términos de Búsqueda":
                st.subheader("🔍 Comparación de Términos de Búsqueda")
                
                if not df_search_terms_p1.empty and not df_search_terms_p2.empty:
                    terms_comparison = compare_search_terms(df_search_terms_p1, df_search_terms_p2, top_n=10)
                    
                    if terms_comparison:
                        comp_data = []
                        for term, data in list(terms_comparison.items())[:10]:
                            comp_data.append({
                                'Término': term,
                                'P1 Sesiones': int(data['period1_sessions']),
                                'P2 Sesiones': int(data['period2_sessions']),
                                'Cambio %': f"{data['change_pct']:+.1f}%"
                            })
                        
                        df_comp_display = pd.DataFrame(comp_data)
                        st.dataframe(df_comp_display, use_container_width=True)
                        
                        chart = create_detailed_comparison_chart(
                            terms_comparison,
                            "🔍 Comparación de Sesiones por Término",
                            "Sesiones"
                        )
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                else:
                    st.warning("⚠️ Datos de búsqueda no disponibles")
            
            # COMPARACIÓN: GEOGRAFÍA
            elif comparison_type == "🌍 Geografía":
                st.subheader("🌍 Comparación de Países")
                
                if not df_geo_p1.empty and not df_geo_p2.empty:
                    geo_comparison = compare_geography(df_geo_p1, df_geo_p2, top_n=10)
                    
                    if geo_comparison:
                        comp_data = []
                        for country, data in list(geo_comparison.items())[:10]:
                            comp_data.append({
                                'País': country,
                                'P1 Usuarios': int(data['period1_users']),
                                'P2 Usuarios': int(data['period2_users']),
                                'Cambio %': f"{data['change_pct']:+.1f}%"
                            })
                        
                        df_comp_display = pd.DataFrame(comp_data)
                        st.dataframe(df_comp_display, use_container_width=True)
                        
                        chart = create_detailed_comparison_chart(
                            geo_comparison,
                            "🌍 Comparación de Usuarios por País",
                            "Usuarios Activos"
                        )
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                else:
                    st.warning("⚠️ Datos geográficos no disponibles")
            
            # COMPARACIÓN: FUENTES DE TRÁFICO
            elif comparison_type == "🚀 Fuentes de Tráfico":
                st.subheader("🚀 Comparación de Fuentes de Tráfico")
                
                if not df_traffic_sources_p1.empty and not df_traffic_sources_p2.empty:
                    traffic_comparison = compare_traffic_sources(df_traffic_sources_p1, df_traffic_sources_p2, top_n=10)
                    
                    if traffic_comparison:
                        comp_data = []
                        for source, data in list(traffic_comparison.items())[:10]:
                            comp_data.append({
                                'Fuente': source,
                                'P1 Sesiones': int(data['period1_sessions']),
                                'P2 Sesiones': int(data['period2_sessions']),
                                'Cambio %': f"{data['change_pct']:+.1f}%"
                            })
                        
                        df_comp_display = pd.DataFrame(comp_data)
                        st.dataframe(df_comp_display, use_container_width=True)
                        
                        chart = create_detailed_comparison_chart(
                            traffic_comparison,
                            "🚀 Comparación de Sesiones por Fuente",
                            "Sesiones"
                        )
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                else:
                    st.warning("⚠️ Datos de tráfico no disponibles")
        
        return  # Salir para no mostrar la vista normal
    else:
        # Verificar si hay datos (MODO NORMAL)
        if df_trend.empty:
            st.warning(f"⚠️ No hay datos disponibles para el período {fecha_inicio} - {fecha_fin}")
            return
    
    # =============================================================================
    # PERÍODO ANALIZADO 
    # =============================================================================
    
    # Mostrar el período seleccionado con información mejorada
    st.markdown(f"""
    <div class="date-filter-card">
        <h3>📅 Período Analizado</h3>
        <p><strong>Desde:</strong> {fecha_inicio.strftime('%d/%m/%Y')} <strong>Hasta:</strong> {fecha_fin.strftime('%d/%m/%Y')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # RESUMEN DEL PERÍODO (CON NÚMEROS COMPLETOS)
    # =============================================================================
    
    st.header(f"📈 Resumen del Período")
    
    # Tarjetas de métricas principales CON NÚMEROS COMPLETOS
    total_users, total_sessions, total_pageviews, avg_bounce_rate = create_summary_metrics_cards(df_trend)
    
    if total_users is not None:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(create_metric_card_html(
                "Usuarios Activos", 
                format_number_complete(total_users),
                "👥"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_metric_card_html(
                "Sesiones", 
                format_number_complete(total_sessions),
                "📱"
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown(create_metric_card_html(
                "Páginas Vistas", 
                format_number_complete(total_pageviews),
                "👀"
            ), unsafe_allow_html=True)
        
        with col4:
            st.markdown(create_metric_card_html(
                "Tasa de Rebote", 
                format_percentage(avg_bounce_rate), 
                "⚡"
            ), unsafe_allow_html=True)
    
    st.markdown("---")

    # =============================================================================
    # VER DATOS DETALLADOS (ACTUALIZADA CON BÚSQUEDAS)
    # =============================================================================
    
    with st.expander("📊 Ver Datos Detallados"):
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "Tendencia Diaria", 
            "Dispositivos", 
            "Geografía", 
            "Páginas", 
            "Horas", 
            "Búsquedas",
            "Fuentes Tráfico"
        ])
        
        with tab1:
            if not df_trend.empty:
                st.subheader("📈 Datos de Tendencia Diaria")
                df_trend['Tasa de Rebote'] = (df_trend['Tasa de Rebote'] * 100).round(2)
                df_trend['Duración Media de Sesión'] = pd.to_datetime(
                    df_trend['Duración Media de Sesión'], unit='s'
                ).dt.strftime("%H:%M:%S")
                st.dataframe(df_trend, use_container_width=True)
                
                # Opción de descarga
                csv = df_trend.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos de tendencia (CSV)",
                    data=csv,
                    file_name=f'tendencia_diaria_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos de tendencia")
        
        with tab2:
            if not df_devices.empty:
                st.subheader("📱 Datos por Dispositivos")
                st.dataframe(df_devices, use_container_width=True)
                
                # Opción de descarga
                csv = df_devices.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos de dispositivos (CSV)",
                    data=csv,
                    file_name=f'dispositivos_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos de dispositivos")
        
        with tab3:
            if not df_geo.empty:
                st.subheader("🌍 Datos Geográficos")
                st.dataframe(df_geo, use_container_width=True)
                
                # Opción de descarga
                csv = df_geo.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos geográficos (CSV)",
                    data=csv,
                    file_name=f'geografia_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos geográficos")
        
        with tab4:
            if not df_pages.empty:
                st.subheader("📄 Datos de Páginas")
                df_pages['Tiempo Promedio de Vista'] = pd.to_datetime(
                    df_pages['Tiempo Promedio de Vista'], unit='s'
                ).dt.strftime("%H:%M:%S")
                st.dataframe(df_pages, use_container_width=True)
                
                # Opción de descarga
                csv = df_pages.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos de páginas (CSV)",
                    data=csv,
                    file_name=f'paginas_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos de páginas")
        
        with tab5:
            if not df_hourly.empty:
                st.subheader("⏰ Datos Horarios")
                st.dataframe(df_hourly, use_container_width=True)
                
                # Opción de descarga
                csv = df_hourly.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos horarios (CSV)",
                    data=csv,
                    file_name=f'horarios_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos horarios")
        
        with tab6:
            if not df_search_terms.empty:
                st.subheader("🔍 Datos de Búsquedas")
                st.dataframe(df_search_terms, use_container_width=True)
                
                # Opción de descarga
                csv = df_search_terms.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar términos de búsqueda externa (CSV)",
                    data=csv,
                    file_name=f'busquedas_externas_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos de búsquedas externas")
        
        with tab7:
            if not df_traffic_sources.empty:
                st.subheader("🚀 Datos de Fuentes de Tráfico")
                st.dataframe(df_traffic_sources, use_container_width=True)
                
                # Opción de descarga
                csv = df_traffic_sources.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos de fuentes de tráfico (CSV)",
                    data=csv,
                    file_name=f'fuentes_trafico_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos de fuentes de tráfico")

    st.markdown("---")
    
    # =============================================================================
    # RESUMEN FINAL DE BÚSQUEDAS (NUEVA SECCIÓN)
    # =============================================================================
    
    if not df_search_summary.empty:
        st.header("📊 Resumen Final de Términos de Búsqueda")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not df_search_terms.empty:
                search_chart = create_search_terms_chart(df_search_terms)
                if search_chart:
                    st.plotly_chart(search_chart, use_container_width=True)
            else:
                st.info("⚠️ No hay datos de términos de búsqueda externa disponibles")
        
        with col2:
            if not df_search_terms.empty:
                st.subheader("📈 Estadísticas de Búsqueda")
                
                # Calcular estadísticas
                avg_sessions_per_term = df_search_terms['Sesiones'].mean()
                max_sessions_term = df_search_terms.loc[df_search_terms['Sesiones'].idxmax(), 'Término de Búsqueda']
                max_sessions_value = df_search_terms['Sesiones'].max()
                
                st.info(f"**Promedio de sesiones por término:** {avg_sessions_per_term:.1f}")
                st.success(f"**Término más popular:** '{max_sessions_term}' con {max_sessions_value:,} sesiones")
                st.warning(f"**Total de términos únicos:** {len(df_search_terms)}")
    else:
        st.warning("⚠️ No hay datos de términos de búsqueda disponibles para el período seleccionado")
    
    st.markdown("---")

    # =============================================================================
    # ANÁLISIS DE FUENTES DE TRÁFICO (NUEVA SECCIÓN)
    # =============================================================================

    st.header("🚀 Análisis de Fuentes de Tráfico")

    if not df_traffic_sources.empty:
        # Gráficos de fuentes de tráfico
        col1, col2 = st.columns([2, 1])
        
        with col1:
            traffic_chart = create_traffic_sources_chart(df_traffic_sources)
            if traffic_chart:
                st.plotly_chart(traffic_chart, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos de fuentes de tráfico disponibles para el período seleccionado")

    st.markdown("---")
    
    # =============================================================================
    # PÁGINAS MÁS VISITADAS
    # =============================================================================
    
    st.header("📄 Páginas Más Visitadas")
    
    if not df_pages.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de páginas
            pages_chart = create_pages_performance_chart(df_pages)
            if pages_chart:
                st.plotly_chart(pages_chart, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos de páginas disponibles")
    
    st.markdown("---")
    
    # =============================================================================
    # ANÁLISIS POR DISPOSITIVOS
    # =============================================================================
    
    st.header("📱 Análisis por Dispositivos")
    
    if not df_devices.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de dispositivos
            device_chart = create_device_comparison(df_devices)
            if device_chart:
                st.plotly_chart(device_chart, use_container_width=True)
    
    st.markdown("---")
    
    # =============================================================================
    # ANÁLISIS GEOGRÁFICO
    # =============================================================================
    
    st.header("🌍 Análisis Geográfico")
    
    if not df_geo.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico geográfico
            geo_chart = create_geographic_chart(df_geo)
            if geo_chart:
                st.plotly_chart(geo_chart, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos geográficos disponibles")
    
    st.markdown("---")
    
    # =============================================================================
    # ANÁLISIS POR HORAS
    # =============================================================================
    
    st.header("⏰ Actividad por Hora")
    
    if not df_hourly.empty:
        hourly_chart = create_hourly_chart(df_hourly)
        if hourly_chart:
            st.plotly_chart(hourly_chart, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos horarios disponibles")


# =============================================================================
# 🚀 EJECUTAR APLICACIÓN
# =============================================================================

if __name__ == "__main__":
    main_dashboard()

    