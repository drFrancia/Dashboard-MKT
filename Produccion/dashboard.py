import mysql.connector
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from datetime import date, datetime, timedelta
import warnings
import logging

# Configurar logging para producción
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Solo ignorar warnings específicos, no todos
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')
warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')

# =============================================================================
# 🗄️ CONFIGURACIÓN DE BASE DE DATOS Y TABLAS (ACTUALIZADA)
# =============================================================================

# Configuracion de la conexion
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # ⚠️ IMPORTANTE: Configurar password en producción
    'database': 'analytics_datos',
    'port': 3306
}

# 📋 CONFIGURACIÓN DE NOMBRES DE TABLAS (ACTUALIZADA - SOLO TABLAS ACTIVAS)
TABLE_CONFIG = {
    'metricas_generales': 'metricas_generales',
    'dispositivos': 'dispositivos', 
    'paginas_top': 'paginas_top',
    'datos_horarios': 'datos_horarios',
    'fuentes_trafico': 'fuentes_trafico',
    'utm_tracking': 'utm_tracking'
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
    page_icon="📊",  # Emoji seguro en lugar de URL externa
    layout="wide",
    initial_sidebar_state="expanded"
)

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

class DatabaseConnection:
    """Clase para manejar la conexión a la base de datos"""
    
    def __init__(self, config):
        self.config = config
        self.engine = None
        self._connect()
    
    def _connect(self):
        """Establecer conexión con MySQL"""
        try:
            connection_string = f"mysql+pymysql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            self.engine = create_engine(connection_string, pool_pre_ping=True)
            
            # Test de conexión básico
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Conexión a base de datos establecida exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            st.error(f"❌ Error conectando a la base de datos: {e}")
            st.error("Verifica que WAMP/MySQL esté ejecutándose y la configuración sea correcta")
            return False
    
    def query(self, sql, params=None):
        """Ejecutar consulta SQL"""
        try:
            if self.engine is None:
                logger.error("Intento de query sin conexión a base de datos")
                return pd.DataFrame()
            return pd.read_sql(sql, self.engine, params=params)
        except Exception as e:
            logger.error(f"Error en consulta SQL: {e}")
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
        except Exception as e:
            logger.error(f"Error obteniendo rango de fechas: {e}")
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
# FUNCIONES HELPER PARA FORMATO DE NÚMEROS
# =============================================================================

def format_dataframe_numbers(df, columns=None):
    """
    Formatear columnas numéricas de un DataFrame con separador de miles.
    Si columns es None, formatea todas las columnas numéricas.
    """
    df_formatted = df.copy()
    
    if columns is None:
        # Detectar columnas numéricas automáticamente
        numeric_cols = df_formatted.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
    else:
        numeric_cols = [col for col in columns if col in df_formatted.columns]
    
    for col in numeric_cols:
        # Verificar si la columna no tiene ya formato de porcentaje
        if df_formatted[col].dtype in ['int64', 'int32']:
            df_formatted[col] = df_formatted[col].apply(lambda x: f'{int(x):,}' if pd.notnull(x) else '')
        elif df_formatted[col].dtype in ['float64', 'float32']:
            # Para floats, mantener decimales si son relevantes
            df_formatted[col] = df_formatted[col].apply(
                lambda x: f'{int(x):,}' if pd.notnull(x) and x == int(x) else (f'{x:,.2f}' if pd.notnull(x) else '')
            )
    
    return df_formatted

# =============================================================================
# FUNCIONES DE CONSULTA CON FILTRO DE FECHAS
# =============================================================================

@st.cache_data(ttl=300)  # 5 minutos de caché
def get_device_breakdown_range(_db, fecha_inicio, fecha_fin):
    """Obtener distribución por dispositivos en un rango de fechas (optimizado)"""
    sql = f"""
    SELECT 
        deviceCategory as "Dispositivo",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones",
        SUM(screenPageViews) as "Páginas Vistas"
    FROM {TABLE_CONFIG['dispositivos']}
    WHERE fecha BETWEEN %s AND %s
    GROUP BY deviceCategory
    ORDER BY SUM(sessions) DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)  # 5 minutos de caché
def get_top_pages_range(_db, fecha_inicio, fecha_fin, limit=50):
    """Obtener páginas más visitadas en un rango de fechas (optimizado)"""
    sql = f"""
    SELECT
        pagePath as "Direccion de Página",
        pageTitle as "Titulo de página",
        SUM(screenPageViews) as "Vista de Páginas",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones"
    FROM {TABLE_CONFIG['paginas_top']}
    WHERE fecha BETWEEN %s AND %s
    GROUP BY pagePath, pageTitle
    ORDER BY SUM(screenPageViews) DESC
    LIMIT {limit}
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)  # 5 minutos de caché
def get_hourly_data_range(_db, fecha_inicio, fecha_fin):
    """Obtener datos por hora en un rango de fechas (optimizado)"""
    sql = f"""
    SELECT 
        hour as "Hora",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones"
    FROM {TABLE_CONFIG['datos_horarios']}
    WHERE fecha BETWEEN %s AND %s
    GROUP BY hour
    ORDER BY hour
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)  # 5 minutos de caché
def get_daily_trend_data(_db, fecha_inicio, fecha_fin):
    """Obtener tendencia diaria para el rango de fechas (optimizado)"""
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
    GROUP BY fecha
    ORDER BY fecha DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

# =============================================================================
# FUNCIONES PARA USUARIOS POR PERÍODO (MENSUAL/ANUAL)
# =============================================================================

@st.cache_data(ttl=300)
def get_users_by_month(_db, fecha_inicio, fecha_fin):
    """Obtener usuarios desglosados por mes y año"""
    sql = f"""
    SELECT
        YEAR(fecha) as anio,
        MONTH(fecha) as mes,
        SUM(activeUsers) as usuarios,
        SUM(sessions) as sesiones,
        SUM(screenPageViews) as vistas,
        AVG(bounceRate) as tasa_rebote
    FROM {TABLE_CONFIG['metricas_generales']}
    WHERE fecha BETWEEN %s AND %s
    GROUP BY YEAR(fecha), MONTH(fecha)
    ORDER BY YEAR(fecha), MONTH(fecha)
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_users_by_year(_db, fecha_inicio, fecha_fin):
    """Obtener usuarios agrupados por año"""
    sql = f"""
    SELECT
        YEAR(fecha) as anio,
        SUM(activeUsers) as usuarios,
        SUM(sessions) as sesiones,
        SUM(screenPageViews) as vistas,
        AVG(bounceRate) as tasa_rebote
    FROM {TABLE_CONFIG['metricas_generales']}
    WHERE fecha BETWEEN %s AND %s
    GROUP BY YEAR(fecha)
    ORDER BY YEAR(fecha)
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_users_by_month_filtered(_db, fecha_inicio, fecha_fin, fuentes=None, medios=None):
    """Obtener usuarios por mes filtrados por fuente/medio (case-insensitive)"""
    
    conditions = ["f.fecha BETWEEN %s AND %s"]
    params = [fecha_inicio, fecha_fin]
    
    if fuentes and len(fuentes) > 0:
        fuentes_lower = [f.lower() for f in fuentes]
        placeholders = ', '.join(['%s'] * len(fuentes_lower))
        conditions.append(f"LOWER(f.sessionSource) IN ({placeholders})")
        params.extend(fuentes_lower)
    
    if medios and len(medios) > 0:
        medios_lower = [m.lower() for m in medios]
        placeholders = ', '.join(['%s'] * len(medios_lower))
        conditions.append(f"LOWER(f.sessionMedium) IN ({placeholders})")
        params.extend(medios_lower)
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
    SELECT
        YEAR(f.fecha) as anio,
        MONTH(f.fecha) as mes,
        SUM(f.activeUsers) as usuarios,
        SUM(f.sessions) as sesiones,
        SUM(f.screenPageViews) as vistas
    FROM {TABLE_CONFIG['fuentes_trafico']} f
    WHERE {where_clause}
    GROUP BY YEAR(f.fecha), MONTH(f.fecha)
    ORDER BY YEAR(f.fecha), MONTH(f.fecha)
    """
    return _db.query(sql, params=tuple(params))

@st.cache_data(ttl=300)
def get_available_years(_db):
    """Obtener lista de años disponibles en la base de datos"""
    sql = f"""
    SELECT DISTINCT YEAR(fecha) as anio
    FROM {TABLE_CONFIG['metricas_generales']}
    ORDER BY anio
    """
    result = _db.query(sql)
    return result['anio'].tolist() if not result.empty else []

# =============================================================================
# NUEVAS FUNCIONES PARA FUENTES DE TRÁFICO
# =============================================================================

@st.cache_data(ttl=300)  # 5 minutos de caché
def get_traffic_sources_range(_db, fecha_inicio, fecha_fin, limit=10):
    """Obtener fuentes de tráfico principales (optimizado)"""
    sql = f"""
    SELECT
        sourceMedium as "Fuente/Medio",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones",
        SUM(screenPageViews) as "Vistas de Página"
    FROM {TABLE_CONFIG['fuentes_trafico']}
    WHERE fecha BETWEEN %s AND %s
    AND sourceMedium IS NOT NULL 
    AND sourceMedium != ''
    AND sourceMedium != '(not set)'
    GROUP BY sourceMedium
    ORDER BY SUM(sessions) DESC
    LIMIT {limit}
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_available_sources(_db, fecha_inicio, fecha_fin):
    """Obtener lista de fuentes disponibles para filtro (normalizado a minúsculas)"""
    sql = f"""
    SELECT DISTINCT LOWER(sessionSource) as fuente
    FROM {TABLE_CONFIG['fuentes_trafico']}
    WHERE fecha BETWEEN %s AND %s
    AND sessionSource IS NOT NULL 
    AND sessionSource != ''
    AND sessionSource != '(not set)'
    ORDER BY LOWER(sessionSource)
    """
    result = _db.query(sql, params=(fecha_inicio, fecha_fin))
    return result['fuente'].tolist() if not result.empty else []

@st.cache_data(ttl=300)
def get_available_mediums(_db, fecha_inicio, fecha_fin):
    """Obtener lista de medios disponibles para filtro (normalizado a minúsculas)"""
    sql = f"""
    SELECT DISTINCT LOWER(sessionMedium) as medio
    FROM {TABLE_CONFIG['fuentes_trafico']}
    WHERE fecha BETWEEN %s AND %s
    AND sessionMedium IS NOT NULL 
    AND sessionMedium != ''
    AND sessionMedium != '(not set)'
    ORDER BY LOWER(sessionMedium)
    """
    result = _db.query(sql, params=(fecha_inicio, fecha_fin))
    return result['medio'].tolist() if not result.empty else []

@st.cache_data(ttl=300)
def get_mediums_by_source(_db, fecha_inicio, fecha_fin, fuentes):
    """Obtener medios disponibles filtrados por las fuentes seleccionadas (normalizado a minúsculas)"""
    if not fuentes or len(fuentes) == 0:
        return get_available_mediums(_db, fecha_inicio, fecha_fin)
    
    # Convertir fuentes a minúsculas para comparación
    fuentes_lower = [f.lower() for f in fuentes]
    placeholders = ', '.join(['%s'] * len(fuentes_lower))
    sql = f"""
    SELECT DISTINCT LOWER(sessionMedium) as medio
    FROM {TABLE_CONFIG['fuentes_trafico']}
    WHERE fecha BETWEEN %s AND %s
    AND LOWER(sessionSource) IN ({placeholders})
    AND sessionMedium IS NOT NULL 
    AND sessionMedium != ''
    AND sessionMedium != '(not set)'
    ORDER BY LOWER(sessionMedium)
    """
    params = [fecha_inicio, fecha_fin] + fuentes_lower
    result = _db.query(sql, params=tuple(params))
    return result['medio'].tolist() if not result.empty else []

@st.cache_data(ttl=300)
def get_traffic_sources_filtered(_db, fecha_inicio, fecha_fin, fuentes=None, medios=None, limit=50):
    """Obtener fuentes de tráfico con filtros de fuente y medio (case-insensitive)"""
    
    # Construir condiciones de filtro
    conditions = ["fecha BETWEEN %s AND %s"]
    params = [fecha_inicio, fecha_fin]
    
    if fuentes and len(fuentes) > 0:
        # Convertir a minúsculas para comparación case-insensitive
        fuentes_lower = [f.lower() for f in fuentes]
        placeholders = ', '.join(['%s'] * len(fuentes_lower))
        conditions.append(f"LOWER(sessionSource) IN ({placeholders})")
        params.extend(fuentes_lower)
    
    if medios and len(medios) > 0:
        # Convertir a minúsculas para comparación case-insensitive
        medios_lower = [m.lower() for m in medios]
        placeholders = ', '.join(['%s'] * len(medios_lower))
        conditions.append(f"LOWER(sessionMedium) IN ({placeholders})")
        params.extend(medios_lower)
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
    SELECT
        LOWER(sessionSource) as "Fuente",
        LOWER(sessionMedium) as "Medio",
        CONCAT(LOWER(sessionSource), ' / ', LOWER(sessionMedium)) as "Fuente/Medio",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones",
        SUM(screenPageViews) as "Vistas de Página"
    FROM {TABLE_CONFIG['fuentes_trafico']}
    WHERE {where_clause}
    GROUP BY LOWER(sessionSource), LOWER(sessionMedium)
    ORDER BY SUM(sessions) DESC
    LIMIT {limit}
    """
    return _db.query(sql, params=tuple(params))

@st.cache_data(ttl=300)
def get_traffic_sources_monthly(_db, fecha_inicio, fecha_fin, limit=10):
    """Obtener fuentes de tráfico desglosadas por mes"""
    sql = f"""
    SELECT
        YEAR(fecha) as anio,
        MONTH(fecha) as mes,
        sourceMedium as fuente,
        SUM(sessions) as sesiones
    FROM {TABLE_CONFIG['fuentes_trafico']}
    WHERE fecha BETWEEN %s AND %s
    AND sourceMedium IS NOT NULL 
    AND sourceMedium != ''
    AND sourceMedium != '(not set)'
    GROUP BY YEAR(fecha), MONTH(fecha), sourceMedium
    ORDER BY YEAR(fecha), MONTH(fecha), SUM(sessions) DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_traffic_sources_monthly_filtered(_db, fecha_inicio, fecha_fin, fuentes=None, medios=None):
    """Obtener fuentes de tráfico desglosadas por mes con filtros de fuente y medio (case-insensitive)"""
    
    conditions = ["fecha BETWEEN %s AND %s"]
    params = [fecha_inicio, fecha_fin]
    
    if fuentes and len(fuentes) > 0:
        # Convertir a minúsculas para comparación case-insensitive
        fuentes_lower = [f.lower() for f in fuentes]
        placeholders = ', '.join(['%s'] * len(fuentes_lower))
        conditions.append(f"LOWER(sessionSource) IN ({placeholders})")
        params.extend(fuentes_lower)
    
    if medios and len(medios) > 0:
        # Convertir a minúsculas para comparación case-insensitive
        medios_lower = [m.lower() for m in medios]
        placeholders = ', '.join(['%s'] * len(medios_lower))
        conditions.append(f"LOWER(sessionMedium) IN ({placeholders})")
        params.extend(medios_lower)
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
    SELECT
        YEAR(fecha) as anio,
        MONTH(fecha) as mes,
        LOWER(sessionSource) as fuente_source,
        LOWER(sessionMedium) as medio,
        CONCAT(LOWER(sessionSource), ' / ', LOWER(sessionMedium)) as fuente,
        SUM(sessions) as sesiones
    FROM {TABLE_CONFIG['fuentes_trafico']}
    WHERE {where_clause}
    GROUP BY YEAR(fecha), MONTH(fecha), LOWER(sessionSource), LOWER(sessionMedium)
    ORDER BY YEAR(fecha), MONTH(fecha), SUM(sessions) DESC
    """
    return _db.query(sql, params=tuple(params))

# =============================================================================
# FUNCIONES PARA UTM TRACKING
# =============================================================================

@st.cache_data(ttl=300)  # 5 minutos de caché
def get_utm_tracking_range(_db, fecha_inicio, fecha_fin, limit=10):
    """Obtener datos de seguimiento UTM (campañas) (optimizado)"""
    sql = f"""
    SELECT
        sessionSource as "Fuente",
        sessionMedium as "Medio",
        sessionCampaignName as "Campaña",
        SUM(sessions) as "Sesiones",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(screenPageViews) as "Vistas de Página"
    FROM {TABLE_CONFIG['utm_tracking']}
    WHERE fecha BETWEEN %s AND %s
    AND sessionCampaignName IS NOT NULL 
    AND sessionCampaignName != ''
    AND sessionCampaignName != '(not set)'
    GROUP BY sessionSource, sessionMedium, sessionCampaignName
    ORDER BY SUM(sessions) DESC
    LIMIT {limit}
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=30)
def get_utm_summary(_db, fecha_inicio, fecha_fin):
    """Obtener resumen de campañas UTM"""
    sql = f"""
    SELECT 
        COUNT(DISTINCT sessionCampaignName) as total_campaigns,
        SUM(sessions) as total_sessions,
        SUM(activeUsers) as total_users,
        AVG(bounceRate) as avg_bounce_rate
    FROM {TABLE_CONFIG['utm_tracking']} 
    WHERE fecha BETWEEN %s AND %s
    AND sessionCampaignName IS NOT NULL 
    AND sessionCampaignName != '(not set)'
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

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
    """Comparación de páginas más visitadas - CORREGIDO para incluir todas las páginas"""
    if df1.empty or df2.empty:
        return None
    
    # Obtener TODAS las páginas únicas de ambos períodos
    all_pages = set(list(df1['Direccion de Página'].unique()) + list(df2['Direccion de Página'].unique()))
    
    comparison = {}
    
    # Comparar todas las páginas
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
    
    # Ordenar por relevancia total (suma de ambos períodos)
    sorted_comparison = dict(sorted(
        comparison.items(),
        key=lambda x: x[1]['period1_views'] + x[1]['period2_views'],
        reverse=True
    ))
    
    # Retornar solo el top_n más relevante
    return dict(list(sorted_comparison.items())[:top_n])

# Funciones compare_search_terms y compare_geography eliminadas - tablas deshabilitadas

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

# Función create_search_terms_chart eliminada - funcionalidad deshabilitada

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
    
    # Preparar datos con columnas disponibles
    df_pages_clean = df_pages.copy()
    df_pages_clean['visualizaciones'] = df_pages_clean['Vista de Páginas']
    df_pages_clean['usuarios'] = df_pages_clean['Usuarios Activos']
    
    df_pages_top = df_pages_clean.head(15)
    
    # Preparar hover_data solo con columnas que existen
    hover_cols = ['Usuarios Activos', 'Vista de Páginas']
    if 'Sesiones' in df_pages_top.columns:
        hover_cols.append('Sesiones')
    if 'Tasa de Rebote' in df_pages_top.columns:
        hover_cols.append('Tasa de Rebote')
    if 'Tiempo Promedio de Vista' in df_pages_top.columns:
        hover_cols.append('Tiempo Promedio de Vista')
    
    fig = px.bar(
        df_pages_top,
        x='visualizaciones',
        y='Direccion de Página',
        orientation='h',
        title="📄 Top 15 Páginas Más Visitadas (Período Total)",
        color='usuarios',
        color_continuous_scale='Viridis',
        hover_data=hover_cols
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
            
            # Calcular default (SIEMPRE últimos 7 días, nunca más)
            default_end = dates_only[-1]
            default_start = dates_only[-7] if len(dates_only) >= 7 else dates_only[-1]

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
                                # Si no hay valor guardado, usar default_start
                                p1_start_value = st.session_state.period1_start if st.session_state.period1_start else default_start
                                period1_start = st.date_input(
                                    "Fecha Inicio P1:",
                                    value=p1_start_value,
                                    min_value=min_date,
                                    max_value=max_date,
                                    key="p1_start"
                                )
                            
                            with col2:
                                # Si no hay valor guardado, usar default_end
                                p1_end_value = st.session_state.period1_end if st.session_state.period1_end else default_end
                                period1_end = st.date_input(
                                    "Fecha Fin P1:",
                                    value=p1_end_value,
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
                            
                            # Calcular período anterior sugerido solo si no hay valores guardados
                            if st.session_state.period2_start is None or st.session_state.period2_end is None:
                                duracion = (period1_end - period1_start).days + 1
                                nuevo_fin = period1_start - timedelta(days=1)
                                nuevo_inicio = nuevo_fin - timedelta(days=duracion - 1)
                                # Asegurar que estén dentro del rango disponible
                                if nuevo_inicio < min_date:
                                    nuevo_inicio = min_date
                                if nuevo_fin < min_date:
                                    nuevo_fin = min_date
                                p2_start_value = nuevo_inicio
                                p2_end_value = nuevo_fin
                            else:
                                p2_start_value = st.session_state.period2_start
                                p2_end_value = st.session_state.period2_end
                            
                            with col1:
                                period2_start = st.date_input(
                                    "Fecha Inicio P2:",
                                    value=p2_start_value,
                                    min_value=min_date,
                                    max_value=max_date,
                                    key="p2_start"
                                )
                            
                            with col2:
                                period2_end = st.date_input(
                                    "Fecha Fin P2:",
                                    value=p2_end_value,
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

                        # ⚠️ VALIDACIÓN: Advertir si el rango es muy grande
                        dias_seleccionados = (fecha_fin - fecha_inicio).days + 1
                        if dias_seleccionados > 90:
                            st.warning(f"⚠️ Has seleccionado {dias_seleccionados} días. Rangos grandes pueden tardar en cargar. Se recomienda máximo 90 días.")
                        
                        if dias_seleccionados > 365:
                            st.error("❌ El rango máximo permitido es 365 días para evitar problemas de rendimiento.")
                            st.stop()

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

    
    # =============================================================================
    # 📊 CARGA DE DATOS SEGÚN MODO
    # =============================================================================
    
    if comparison_mode:
        # Cargar solo datos críticos al inicio (LAZY LOADING para comparación)
        with st.spinner("📊 Cargando métricas principales para comparación..."):
            # Período 1 - Solo datos esenciales
            df_trend_p1 = get_daily_trend_data(db, fecha_inicio, fecha_fin)
            df_devices_p1 = get_device_breakdown_range(db, fecha_inicio, fecha_fin)
            
            # Período 2 - Solo datos esenciales
            df_trend_p2 = get_daily_trend_data(db, fecha_inicio_p2, fecha_fin_p2)
            df_devices_p2 = get_device_breakdown_range(db, fecha_inicio_p2, fecha_fin_p2)
            
            # Los demás datos se cargarán bajo demanda en cada tab
            df_pages_p1 = None
            df_pages_p2 = None
            df_hourly_p1 = None
            df_hourly_p2 = None
            df_traffic_sources_p1 = None
            df_traffic_sources_p2 = None
    else:
        # Obtener datos para el rango de fechas seleccionado (MODO NORMAL - LAZY LOADING)
        with st.spinner("📊 Cargando métricas principales..."):
            # Solo cargar métricas críticas al inicio
            df_trend = get_daily_trend_data(db, fecha_inicio, fecha_fin)
            df_devices = get_device_breakdown_range(db, fecha_inicio, fecha_fin)
            
            # Los demás datos se cargarán bajo demanda (lazy loading)
            df_pages = None
            df_hourly = None
            df_traffic_sources = None
            df_utm = None
            df_utm_summary = None
    
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

                # === DESGLOSE MENSUAL ===
                st.markdown("---")
                st.subheader("📅 Desglose Mensual de Métricas Generales")
                meses_nombres = {
                    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                }
                with st.spinner("🔄 Cargando desglose mensual..."):
                    df_mes_p1 = get_users_by_month(db, fecha_inicio, fecha_fin)
                    df_mes_p2 = get_users_by_month(db, fecha_inicio_p2, fecha_fin_p2)
                if df_mes_p1 is not None and not df_mes_p1.empty and df_mes_p2 is not None and not df_mes_p2.empty:
                    meses = sorted(set(df_mes_p1['mes'].unique()).union(df_mes_p2['mes'].unique()))
                    comp_mensual = []
                    for mes in meses:
                        p1 = df_mes_p1[df_mes_p1['mes'] == mes]
                        p2 = df_mes_p2[df_mes_p2['mes'] == mes]
                        usuarios_p1 = int(p1['usuarios'].iloc[0]) if not p1.empty else 0
                        usuarios_p2 = int(p2['usuarios'].iloc[0]) if not p2.empty else 0
                        sesiones_p1 = int(p1['sesiones'].iloc[0]) if not p1.empty else 0
                        sesiones_p2 = int(p2['sesiones'].iloc[0]) if not p2.empty else 0
                        vistas_p1 = int(p1['vistas'].iloc[0]) if not p1.empty else 0
                        vistas_p2 = int(p2['vistas'].iloc[0]) if not p2.empty else 0
                        if usuarios_p1 > 0:
                            dif_usuarios = ((usuarios_p2 - usuarios_p1) / usuarios_p1) * 100
                        else:
                            dif_usuarios = 100.0 if usuarios_p2 > 0 else 0.0
                        comp_mensual.append({
                            'Mes': meses_nombres[mes],
                            f'{fecha_inicio.year} Usuarios': usuarios_p1,
                            f'{fecha_inicio_p2.year} Usuarios': usuarios_p2,
                            '% Dif Usuarios': f"{dif_usuarios:+.1f}%",
                            f'{fecha_inicio.year} Sesiones': sesiones_p1,
                            f'{fecha_inicio_p2.year} Sesiones': sesiones_p2,
                            f'{fecha_inicio.year} Vistas': vistas_p1,
                            f'{fecha_inicio_p2.year} Vistas': vistas_p2
                        })
                    df_comp_mes = pd.DataFrame(comp_mensual)
                    df_comp_mes_formatted = format_dataframe_numbers(df_comp_mes)
                    st.dataframe(df_comp_mes_formatted, use_container_width=True)
                    # Gráfico
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_comp_mes['Mes'],
                        y=df_comp_mes[f'{fecha_inicio.year} Usuarios'],
                        name=f'{fecha_inicio.year} Usuarios',
                        marker_color='#1f77b4'
                    ))
                    fig.add_trace(go.Bar(
                        x=df_comp_mes['Mes'],
                        y=df_comp_mes[f'{fecha_inicio_p2.year} Usuarios'],
                        name=f'{fecha_inicio_p2.year} Usuarios',
                        marker_color='#ff7f0e'
                    ))
                    fig.update_layout(
                        title="👥 Usuarios por Mes (Comparación)",
                        xaxis_title="Mes",
                        yaxis_title="Usuarios",
                        barmode='group',
                        hovermode='x unified',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos mensuales para el desglose.")
            
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
                        df_comp_formatted = format_dataframe_numbers(
                            df_comp_display,
                            columns=['P1 Usuarios', 'P2 Usuarios']
                        )
                        st.dataframe(df_comp_formatted, use_container_width=True)
                    # === DESGLOSE MENSUAL ===
                    st.markdown("---")
                    st.subheader("📅 Desglose Mensual de Dispositivos")
                    meses_nombres = {
                        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                    }
                    with st.spinner("🔄 Cargando desglose mensual..."):
                        # Obtener datos mensuales por dispositivo
                        sql = f"""
                        SELECT YEAR(fecha) as anio, MONTH(fecha) as mes, deviceCategory as dispositivo, SUM(activeUsers) as usuarios
                        FROM {TABLE_CONFIG['dispositivos']}
                        WHERE fecha BETWEEN %s AND %s
                        GROUP BY anio, mes, dispositivo
                        ORDER BY anio, mes
                        """
                        df_mes_p1 = db.query(sql, params=(fecha_inicio, fecha_fin))
                        df_mes_p2 = db.query(sql, params=(fecha_inicio_p2, fecha_fin_p2))
                    if df_mes_p1 is not None and not df_mes_p1.empty and df_mes_p2 is not None and not df_mes_p2.empty:
                        dispositivos = sorted(set(df_mes_p1['dispositivo'].unique()).union(df_mes_p2['dispositivo'].unique()))
                        meses = sorted(set(df_mes_p1['mes'].unique()).union(df_mes_p2['mes'].unique()))
                        for dispositivo in dispositivos:
                            st.markdown(f"**{dispositivo.capitalize()}**")
                            comp_mensual = []
                            for mes in meses:
                                p1 = df_mes_p1[(df_mes_p1['mes'] == mes) & (df_mes_p1['dispositivo'] == dispositivo)]
                                p2 = df_mes_p2[(df_mes_p2['mes'] == mes) & (df_mes_p2['dispositivo'] == dispositivo)]
                                usuarios_p1 = int(p1['usuarios'].iloc[0]) if not p1.empty else 0
                                usuarios_p2 = int(p2['usuarios'].iloc[0]) if not p2.empty else 0
                                if usuarios_p1 > 0:
                                    dif_usuarios = ((usuarios_p2 - usuarios_p1) / usuarios_p1) * 100
                                else:
                                    dif_usuarios = 100.0 if usuarios_p2 > 0 else 0.0
                                comp_mensual.append({
                                    'Mes': meses_nombres[mes],
                                    f'{fecha_inicio.year} Usuarios': usuarios_p1,
                                    f'{fecha_inicio_p2.year} Usuarios': usuarios_p2,
                                    '% Dif Usuarios': f"{dif_usuarios:+.1f}%"
                                })
                            df_comp_mes = pd.DataFrame(comp_mensual)
                            df_comp_mes_formatted = format_dataframe_numbers(df_comp_mes)
                            st.dataframe(df_comp_mes_formatted, use_container_width=True)
                            # Gráfico
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=df_comp_mes['Mes'],
                                y=df_comp_mes[f'{fecha_inicio.year} Usuarios'],
                                name=f'{fecha_inicio.year} Usuarios',
                                marker_color='#1f77b4'
                            ))
                            fig.add_trace(go.Bar(
                                x=df_comp_mes['Mes'],
                                y=df_comp_mes[f'{fecha_inicio_p2.year} Usuarios'],
                                name=f'{fecha_inicio_p2.year} Usuarios',
                                marker_color='#ff7f0e'
                            ))
                            fig.update_layout(
                                title=f"👥 Usuarios por Mes - {dispositivo.capitalize()}",
                                xaxis_title="Mes",
                                yaxis_title="Usuarios",
                                barmode='group',
                                hovermode='x unified',
                                height=350
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos mensuales para el desglose.")
                else:
                    st.warning("⚠️ Datos de dispositivos no disponibles")
            
            # COMPARACIÓN: PÁGINAS
            elif comparison_type == "📄 Páginas Visitadas":
                st.subheader("📄 Comparación de Páginas Más Visitadas")
                
                # Lazy loading: cargar datos solo cuando se accede a este tab
                if df_pages_p1 is None:
                    with st.spinner("🔄 Cargando datos de páginas período 1..."):
                        df_pages_p1 = get_top_pages_range(db, fecha_inicio, fecha_fin, limit=10)
                if df_pages_p2 is None:
                    with st.spinner("🔄 Cargando datos de páginas período 2..."):
                        df_pages_p2 = get_top_pages_range(db, fecha_inicio_p2, fecha_fin_p2, limit=10)
                
                if df_pages_p1 is not None and not df_pages_p1.empty and df_pages_p2 is not None and not df_pages_p2.empty:
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
                        df_comp_formatted = format_dataframe_numbers(
                            df_comp_display,
                            columns=['P1 Vistas', 'P2 Vistas']
                        )
                        st.dataframe(df_comp_formatted, use_container_width=True)
                        # === DESGLOSE MENSUAL ===
                        st.markdown("---")
                        st.subheader("📅 Desglose Mensual de Páginas")
                        meses_nombres = {
                            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                        }
                        with st.spinner("🔄 Cargando desglose mensual..."):
                            sql = f"""
                            SELECT YEAR(fecha) as anio, MONTH(fecha) as mes, pagePath as pagina, SUM(screenPageViews) as vistas
                            FROM {TABLE_CONFIG['paginas']}
                            WHERE fecha BETWEEN %s AND %s
                            GROUP BY anio, mes, pagina
                            ORDER BY anio, mes
                            """
                            df_mes_p1 = db.query(sql, params=(fecha_inicio, fecha_fin))
                            df_mes_p2 = db.query(sql, params=(fecha_inicio_p2, fecha_fin_p2))
                        if df_mes_p1 is not None and not df_mes_p1.empty and df_mes_p2 is not None and not df_mes_p2.empty:
                            paginas = sorted(set(df_mes_p1['pagina'].unique()).union(df_mes_p2['pagina'].unique()))
                            meses = sorted(set(df_mes_p1['mes'].unique()).union(df_mes_p2['mes'].unique()))
                            for pagina in paginas:
                                st.markdown(f"**{pagina[:60] + '...' if len(pagina) > 60 else pagina}**")
                                comp_mensual = []
                                for mes in meses:
                                    p1 = df_mes_p1[(df_mes_p1['mes'] == mes) & (df_mes_p1['pagina'] == pagina)]
                                    p2 = df_mes_p2[(df_mes_p2['mes'] == mes) & (df_mes_p2['pagina'] == pagina)]
                                    vistas_p1 = int(p1['vistas'].iloc[0]) if not p1.empty else 0
                                    vistas_p2 = int(p2['vistas'].iloc[0]) if not p2.empty else 0
                                    if vistas_p1 > 0:
                                        dif_vistas = ((vistas_p2 - vistas_p1) / vistas_p1) * 100
                                    else:
                                        dif_vistas = 100.0 if vistas_p2 > 0 else 0.0
                                    comp_mensual.append({
                                        'Mes': meses_nombres[mes],
                                        f'{fecha_inicio.year} Vistas': vistas_p1,
                                        f'{fecha_inicio_p2.year} Vistas': vistas_p2,
                                        '% Dif Vistas': f"{dif_vistas:+.1f}%"
                                    })
                                df_comp_mes = pd.DataFrame(comp_mensual)
                                df_comp_mes_formatted = format_dataframe_numbers(df_comp_mes)
                                st.dataframe(df_comp_mes_formatted, use_container_width=True)
                                # Gráfico
                                fig = go.Figure()
                                fig.add_trace(go.Bar(
                                    x=df_comp_mes['Mes'],
                                    y=df_comp_mes[f'{fecha_inicio.year} Vistas'],
                                    name=f'{fecha_inicio.year} Vistas',
                                    marker_color='#1f77b4'
                                ))
                                fig.add_trace(go.Bar(
                                    x=df_comp_mes['Mes'],
                                    y=df_comp_mes[f'{fecha_inicio_p2.year} Vistas'],
                                    name=f'{fecha_inicio_p2.year} Vistas',
                                    marker_color='#ff7f0e'
                                ))
                                fig.update_layout(
                                    title=f"👁️ Vistas por Mes - {pagina[:60] + '...' if len(pagina) > 60 else pagina}",
                                    xaxis_title="Mes",
                                    yaxis_title="Vistas",
                                    barmode='group',
                                    hovermode='x unified',
                                    height=350
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No hay datos mensuales para el desglose.")
                else:
                    st.warning("⚠️ Datos de páginas no disponibles")
            
            # Tab de términos de búsqueda eliminado - funcionalidad deshabilitada
            elif comparison_type == "🔍 Términos de Búsqueda":
                st.info("⚠️ La funcionalidad de términos de búsqueda ha sido deshabilitada")
            
            # Tab de Geografía eliminado - tabla deshabilitada
            elif comparison_type == "🌍 Geografía":
                st.info("⚠️ La funcionalidad de datos geográficos ha sido deshabilitada")
            
            # COMPARACIÓN: FUENTES DE TRÁFICO
            elif comparison_type == "🚀 Fuentes de Tráfico":
                st.subheader("🚀 Comparación de Fuentes de Tráfico")
                
                # Filtros de fuente y medio
                st.markdown("#### 🔍 Filtros")
                
                # Obtener fuentes disponibles de ambos períodos
                available_sources_p1 = get_available_sources(db, fecha_inicio, fecha_fin)
                available_sources_p2 = get_available_sources(db, fecha_inicio_p2, fecha_fin_p2)
                all_available_sources = sorted(list(set(available_sources_p1 + available_sources_p2)))
                
                col_f1, col_f2 = st.columns(2)
                
                with col_f1:
                    comp_selected_sources = st.multiselect(
                        "🔍 Filtrar por Fuente",
                        options=all_available_sources,
                        default=[],
                        placeholder="Selecciona fuentes (ej: ig, google...)",
                        key="comp_traffic_sources"
                    )
                
                with col_f2:
                    # Obtener medios vinculados a las fuentes seleccionadas (de ambos períodos)
                    if comp_selected_sources:
                        available_mediums_p1 = get_mediums_by_source(db, fecha_inicio, fecha_fin, comp_selected_sources)
                        available_mediums_p2 = get_mediums_by_source(db, fecha_inicio_p2, fecha_fin_p2, comp_selected_sources)
                        all_available_mediums = sorted(list(set(available_mediums_p1 + available_mediums_p2)))
                    else:
                        available_mediums_p1 = get_available_mediums(db, fecha_inicio, fecha_fin)
                        available_mediums_p2 = get_available_mediums(db, fecha_inicio_p2, fecha_fin_p2)
                        all_available_mediums = sorted(list(set(available_mediums_p1 + available_mediums_p2)))
                    
                    comp_selected_mediums = st.multiselect(
                        "🎯 Filtrar por Medio",
                        options=all_available_mediums,
                        default=[],
                        placeholder="Selecciona medios (ej: paid, organic...)",
                        help="Solo muestra medios vinculados a las fuentes seleccionadas." if comp_selected_sources else "Selecciona medios.",
                        key="comp_traffic_mediums"
                    )
                
                st.markdown("---")
                
                # Selector de vista: Total o Mensual
                vista_trafico = st.radio(
                    "Seleccionar vista:",
                    ["Comparación Total", "Desglose Mensual"],
                    horizontal=True
                )
                
                if vista_trafico == "Comparación Total":
                    # Vista con filtros aplicados
                    with st.spinner("🔄 Cargando datos..."):
                        if comp_selected_sources or comp_selected_mediums:
                            # Usar función filtrada
                            df_traffic_sources_p1 = get_traffic_sources_filtered(
                                db, fecha_inicio, fecha_fin,
                                fuentes=comp_selected_sources if comp_selected_sources else None,
                                medios=comp_selected_mediums if comp_selected_mediums else None,
                                limit=50
                            )
                            df_traffic_sources_p2 = get_traffic_sources_filtered(
                                db, fecha_inicio_p2, fecha_fin_p2,
                                fuentes=comp_selected_sources if comp_selected_sources else None,
                                medios=comp_selected_mediums if comp_selected_mediums else None,
                                limit=50
                            )
                            
                            # Mostrar filtros aplicados
                            filter_info = []
                            if comp_selected_sources:
                                filter_info.append(f"**Fuentes:** {', '.join(comp_selected_sources)}")
                            if comp_selected_mediums:
                                filter_info.append(f"**Medios:** {', '.join(comp_selected_mediums)}")
                            st.info(f"🔍 Filtros: {' | '.join(filter_info)}")
                        else:
                            # Sin filtros - cargar top 10
                            df_traffic_sources_p1 = get_traffic_sources_range(db, fecha_inicio, fecha_fin, limit=10)
                            df_traffic_sources_p2 = get_traffic_sources_range(db, fecha_inicio_p2, fecha_fin_p2, limit=10)
                    
                    if df_traffic_sources_p1 is not None and not df_traffic_sources_p1.empty and df_traffic_sources_p2 is not None and not df_traffic_sources_p2.empty:
                        # Determinar la columna de comparación según si hay filtros
                        if comp_selected_sources or comp_selected_mediums:
                            # Con filtros - usar Fuente/Medio
                            col_name = 'Fuente/Medio'
                        else:
                            col_name = 'Fuente/Medio'
                        
                        # Comparar datos
                        all_sources = set(list(df_traffic_sources_p1[col_name].unique()) + list(df_traffic_sources_p2[col_name].unique()))
                        
                        comp_data = []
                        for source in all_sources:
                            p1_sessions = df_traffic_sources_p1[df_traffic_sources_p1[col_name] == source]['Sesiones'].sum()
                            p2_sessions = df_traffic_sources_p2[df_traffic_sources_p2[col_name] == source]['Sesiones'].sum()
                            
                            if p2_sessions != 0:
                                change_pct = ((p1_sessions - p2_sessions) / p2_sessions) * 100
                            else:
                                change_pct = 0 if p1_sessions == 0 else 100
                            
                            comp_data.append({
                                'Fuente/Medio': source,
                                f'P1 Sesiones ({fecha_inicio} a {fecha_fin})': int(p1_sessions),
                                f'P2 Sesiones ({fecha_inicio_p2} a {fecha_fin_p2})': int(p2_sessions),
                                'Cambio %': f"{change_pct:+.1f}%"
                            })
                        
                        # Ordenar por sesiones totales
                        comp_data.sort(key=lambda x: x[f'P1 Sesiones ({fecha_inicio} a {fecha_fin})'] + x[f'P2 Sesiones ({fecha_inicio_p2} a {fecha_fin_p2})'], reverse=True)
                        
                        df_comp_display = pd.DataFrame(comp_data[:20])  # Limitar a 20
                        
                        # Mostrar métricas resumen
                        col_m1, col_m2, col_m3 = st.columns(3)
                        with col_m1:
                            total_p1 = sum(d[f'P1 Sesiones ({fecha_inicio} a {fecha_fin})'] for d in comp_data)
                            st.metric("Total P1", f"{total_p1:,}")
                        with col_m2:
                            total_p2 = sum(d[f'P2 Sesiones ({fecha_inicio_p2} a {fecha_fin_p2})'] for d in comp_data)
                            st.metric("Total P2", f"{total_p2:,}")
                        with col_m3:
                            if total_p2 > 0:
                                cambio_total = ((total_p1 - total_p2) / total_p2) * 100
                            else:
                                cambio_total = 0
                            st.metric("Cambio Total", f"{cambio_total:+.1f}%")
                        
                        df_comp_formatted = format_dataframe_numbers(df_comp_display)
                        st.dataframe(df_comp_formatted, use_container_width=True)
                    else:
                        st.warning("⚠️ No hay datos con los filtros seleccionados")
                
                else:  # Vista Desglose Mensual
                    st.markdown("### 📊 Comparación Mensual de Fuentes de Tráfico")
                    
                    # Si hay filtros aplicados, mostrarlos
                    if comp_selected_sources or comp_selected_mediums:
                        filter_info = []
                        if comp_selected_sources:
                            filter_info.append(f"**Fuentes:** {', '.join(comp_selected_sources)}")
                        if comp_selected_mediums:
                            filter_info.append(f"**Medios:** {', '.join(comp_selected_mediums)}")
                        st.info(f"🔍 Filtros aplicados: {' | '.join(filter_info)}")
                    
                    with st.spinner("🔄 Cargando datos mensuales..."):
                        # Usar función filtrada si hay filtros, si no usar la normal
                        if comp_selected_sources or comp_selected_mediums:
                            df_monthly_p1 = get_traffic_sources_monthly_filtered(
                                db, fecha_inicio, fecha_fin,
                                fuentes=comp_selected_sources if comp_selected_sources else None,
                                medios=comp_selected_mediums if comp_selected_mediums else None
                            )
                            df_monthly_p2 = get_traffic_sources_monthly_filtered(
                                db, fecha_inicio_p2, fecha_fin_p2,
                                fuentes=comp_selected_sources if comp_selected_sources else None,
                                medios=comp_selected_mediums if comp_selected_mediums else None
                            )
                        else:
                            df_monthly_p1 = get_traffic_sources_monthly(db, fecha_inicio, fecha_fin)
                            df_monthly_p2 = get_traffic_sources_monthly(db, fecha_inicio_p2, fecha_fin_p2)
                    
                    if df_monthly_p1 is not None and not df_monthly_p1.empty:
                        # Identificar las fuentes más importantes
                        top_sources = df_monthly_p1.groupby('fuente')['sesiones'].sum().nlargest(10).index.tolist()
                        
                        if not top_sources and df_monthly_p2 is not None and not df_monthly_p2.empty:
                            top_sources = df_monthly_p2.groupby('fuente')['sesiones'].sum().nlargest(10).index.tolist()
                        
                        if top_sources:
                            # Selector de fuente
                            fuente_seleccionada = st.selectbox(
                                "Seleccionar fuente de tráfico:",
                                top_sources
                            )
                            
                            # Filtrar por la fuente seleccionada
                            data_p1 = df_monthly_p1[df_monthly_p1['fuente'] == fuente_seleccionada].copy()
                            data_p2 = df_monthly_p2[df_monthly_p2['fuente'] == fuente_seleccionada].copy() if df_monthly_p2 is not None else pd.DataFrame()
                            
                            # Crear diccionarios para acceso rápido
                            meses_nombres = {
                                1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                                5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                                9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                            }
                            
                            # Determinar qué meses están en el rango seleccionado
                            meses_p1 = set(data_p1['mes'].unique()) if not data_p1.empty else set()
                            meses_p2 = set(data_p2['mes'].unique()) if not data_p2.empty else set()
                            meses_disponibles = sorted(meses_p1.union(meses_p2))
                            
                            if not meses_disponibles:
                                mes_inicio = fecha_inicio.month
                                mes_fin = fecha_fin.month
                                if fecha_inicio.year == fecha_fin.year:
                                    meses_disponibles = list(range(mes_inicio, mes_fin + 1))
                                else:
                                    meses_disponibles = list(range(1, 13))
                            
                            # Crear tabla comparativa
                            comparacion_mensual = []
                            
                            for mes in meses_disponibles:
                                p1_data = data_p1[data_p1['mes'] == mes]
                                p2_data = data_p2[data_p2['mes'] == mes]
                                
                                sesiones_p1 = int(p1_data['sesiones'].iloc[0]) if not p1_data.empty else 0
                                sesiones_p2 = int(p2_data['sesiones'].iloc[0]) if not p2_data.empty else 0
                                
                                if sesiones_p1 > 0:
                                    diferencia_pct = ((sesiones_p2 - sesiones_p1) / sesiones_p1) * 100
                                else:
                                    diferencia_pct = 100.0 if sesiones_p2 > 0 else 0.0
                                
                                comparacion_mensual.append({
                                    'Mes': meses_nombres[mes],
                                    f'{fecha_inicio.year} Sesiones': sesiones_p1,
                                    f'{fecha_inicio_p2.year} Sesiones': sesiones_p2,
                                    '% Diferencia': f"{diferencia_pct:+.1f}%"
                                })
                            
                            df_comparacion = pd.DataFrame(comparacion_mensual)
                            df_comparacion_formatted = format_dataframe_numbers(df_comparacion)
                            st.dataframe(df_comparacion_formatted, use_container_width=True)
                            
                            # Crear gráfico comparativo
                            fig = go.Figure()
                            
                            fig.add_trace(go.Bar(
                                x=df_comparacion['Mes'],
                                y=df_comparacion[f'{fecha_inicio.year} Sesiones'],
                                name=f'{fecha_inicio.year}',
                                marker_color='#1f77b4'
                            ))
                            
                            fig.add_trace(go.Bar(
                                x=df_comparacion['Mes'],
                                y=df_comparacion[f'{fecha_inicio_p2.year} Sesiones'],
                                name=f'{fecha_inicio_p2.year}',
                                marker_color='#ff7f0e'
                            ))
                            
                            fig.update_layout(
                                title=f"📊 Comparación Mensual - {fuente_seleccionada}",
                                xaxis_title="Mes",
                                yaxis_title="Sesiones",
                                barmode='group',
                                hovermode='x unified',
                                height=500
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("⚠️ No hay fuentes disponibles con los filtros aplicados")
                    else:
                        st.warning("⚠️ No hay datos mensuales disponibles")
        
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
    
    # =============================================================================
    # VER DATOS DETALLADOS (ACTUALIZADA CON BÚSQUEDAS)
    # =============================================================================
    
    with st.expander("📊 Ver Datos Detallados"):
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "📅 Usuarios Período",
            "Tendencia Diaria", 
            "Dispositivos", 
            "Páginas", 
            "Horas", 
            "Búsquedas Externas",
            "Fuentes Tráfico",
            "Campañas UTM"
        ])
        
        with tab1:
            st.subheader("👥 Usuarios por Período")
            st.caption("Visualiza el total de usuarios desglosado por año y mes, con opción de filtrar por fuente y medio de tráfico.")
            
            # Opciones de vista
            col_view1, col_view2 = st.columns([1, 2])
            with col_view1:
                view_type = st.radio(
                    "Tipo de vista:",
                    ["📊 Por Mes", "📈 Por Año", "🔍 Con Filtros"],
                    horizontal=True,
                    key="users_view_type"
                )
            
            meses_nombres = {
                1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
            }
            
            if view_type == "📊 Por Mes":
                # Vista mensual sin filtros
                with st.spinner("🔄 Cargando datos mensuales..."):
                    df_users_month = get_users_by_month(db, fecha_inicio, fecha_fin)
                
                if df_users_month is not None and not df_users_month.empty:
                    # Preparar datos para mostrar
                    monthly_data = []
                    for _, row in df_users_month.iterrows():
                        mes_num = int(row['mes'])
                        anio = int(row['anio'])
                        monthly_data.append({
                            'Año': anio,
                            'Mes': meses_nombres.get(mes_num, f'Mes {mes_num}'),
                            'Mes Num': mes_num,
                            'Usuarios': int(row['usuarios']),
                            'Sesiones': int(row['sesiones']),
                            'Vistas': int(row['vistas']),
                            'Tasa Rebote': f"{row['tasa_rebote']*100:.1f}%"
                        })
                    
                    df_display = pd.DataFrame(monthly_data)
                    df_display = df_display.sort_values(['Año', 'Mes Num'])
                    
                    # Métricas totales
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    with col_m1:
                        st.metric("Total Usuarios", f"{df_display['Usuarios'].sum():,}")
                    with col_m2:
                        st.metric("Total Sesiones", f"{df_display['Sesiones'].sum():,}")
                    with col_m3:
                        st.metric("Total Vistas", f"{df_display['Vistas'].sum():,}")
                    with col_m4:
                        st.metric("Meses", f"{len(df_display)}")
                    
                    # Tabla con formato de miles
                    df_display_formatted = format_dataframe_numbers(
                        df_display[['Año', 'Mes', 'Usuarios', 'Sesiones', 'Vistas', 'Tasa Rebote']],
                        columns=['Usuarios', 'Sesiones', 'Vistas']
                    )
                    st.dataframe(df_display_formatted, use_container_width=True)
                    
                    # Gráfico
                    df_display['Periodo'] = df_display.apply(lambda x: f"{x['Mes'][:3]} {x['Año']}", axis=1)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_display['Periodo'],
                        y=df_display['Usuarios'],
                        name='Usuarios',
                        marker_color='#1f77b4',
                        text=df_display['Usuarios'].apply(lambda x: f'{x:,}'),
                        textposition='outside'
                    ))
                    fig.add_trace(go.Scatter(
                        x=df_display['Periodo'],
                        y=df_display['Sesiones'],
                        name='Sesiones',
                        mode='lines+markers',
                        line=dict(color='#ff7f0e', width=2),
                        yaxis='y2'
                    ))
                    
                    # fig.update_layout(
                    #     title="👥 Usuarios y Sesiones por Mes",
                    #     xaxis_title="Periodo",
                    #     yaxis_title="Usuarios",
                    #     yaxis2=dict(title="Sesiones", overlaying='y', side='right'),
                    #     hovermode='x unified',
                    #     height=450,
                    #     legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    # )
                    
                    # st.plotly_chart(fig, use_container_width=True)
                    
                    # Descarga
                    csv = df_display[['Año', 'Mes', 'Usuarios', 'Sesiones', 'Vistas', 'Tasa Rebote']].to_csv(index=False)
                    st.download_button(
                        label="💾 Descargar datos mensuales (CSV)",
                        data=csv,
                        file_name=f'usuarios_mensual_{fecha_inicio}_{fecha_fin}.csv',
                        mime='text/csv',
                        key="download_users_monthly"
                    )
                else:
                    st.info("No hay datos para el período seleccionado")
            
            elif view_type == "📈 Por Año":
                # Vista anual
                with st.spinner("🔄 Cargando datos anuales..."):
                    df_users_year = get_users_by_year(db, fecha_inicio, fecha_fin)
                
                if df_users_year is not None and not df_users_year.empty:
                    yearly_data = []
                    for _, row in df_users_year.iterrows():
                        yearly_data.append({
                            'Año': int(row['anio']),
                            'Usuarios': int(row['usuarios']),
                            'Sesiones': int(row['sesiones']),
                            'Vistas': int(row['vistas']),
                            'Tasa Rebote': f"{row['tasa_rebote']*100:.1f}%"
                        })
                    
                    df_year_display = pd.DataFrame(yearly_data)
                    
                    # Métricas
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Total Usuarios", f"{df_year_display['Usuarios'].sum():,}")
                    with col_m2:
                        st.metric("Total Sesiones", f"{df_year_display['Sesiones'].sum():,}")
                    with col_m3:
                        st.metric("Años", f"{len(df_year_display)}")
                    
                    # Comparación año vs año
                    if len(df_year_display) > 1:
                        st.markdown("#### 📊 Comparación Año vs Año")
                        comp_data = []
                        for i in range(1, len(df_year_display)):
                            prev = df_year_display.iloc[i-1]
                            curr = df_year_display.iloc[i]
                            
                            if prev['Usuarios'] > 0:
                                cambio_usuarios = ((curr['Usuarios'] - prev['Usuarios']) / prev['Usuarios']) * 100
                            else:
                                cambio_usuarios = 0
                            
                            if prev['Sesiones'] > 0:
                                cambio_sesiones = ((curr['Sesiones'] - prev['Sesiones']) / prev['Sesiones']) * 100
                            else:
                                cambio_sesiones = 0
                            
                            comp_data.append({
                                'Comparación': f"{prev['Año']} → {curr['Año']}",
                                'Usuarios Antes': prev['Usuarios'],
                                'Usuarios Después': curr['Usuarios'],
                                'Cambio Usuarios': f"{cambio_usuarios:+.1f}%",
                                'Sesiones Antes': prev['Sesiones'],
                                'Sesiones Después': curr['Sesiones'],
                                'Cambio Sesiones': f"{cambio_sesiones:+.1f}%"
                            })
                        
                        df_comp = pd.DataFrame(comp_data)
                        df_comp_formatted = format_dataframe_numbers(
                            df_comp,
                            columns=['Usuarios Antes', 'Usuarios Después', 'Sesiones Antes', 'Sesiones Después']
                        )
                        st.dataframe(df_comp_formatted, use_container_width=True)
                    
                    # Tabla principal
                    st.markdown("#### 📋 Datos por Año")
                    df_year_formatted = format_dataframe_numbers(
                        df_year_display,
                        columns=['Usuarios', 'Sesiones', 'Vistas']
                    )
                    st.dataframe(df_year_formatted, use_container_width=True)
                    
                    # Gráfico
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_year_display['Año'].astype(str),
                        y=df_year_display['Usuarios'],
                        name='Usuarios',
                        marker_color='#2ecc71',
                        text=df_year_display['Usuarios'].apply(lambda x: f'{x:,}'),
                        textposition='outside'
                    ))
                    
                    # fig.update_layout(
                    #     title="👥 Total Usuarios por Año",
                    #     xaxis_title="Año",
                    #     yaxis_title="Usuarios",
                    #     height=400
                    # )
                    
                    # st.plotly_chart(fig, use_container_width=True)
                    
                    # Descarga
                    csv = df_year_display.to_csv(index=False)
                    st.download_button(
                        label="💾 Descargar datos anuales (CSV)",
                        data=csv,
                        file_name=f'usuarios_anual_{fecha_inicio}_{fecha_fin}.csv',
                        mime='text/csv',
                        key="download_users_yearly"
                    )
                else:
                    st.info("No hay datos para el período seleccionado")
            
            else:  # Con Filtros
                st.markdown("#### 🔍 Usuarios por Período con Filtros de Tráfico")
                st.caption("Filtra los usuarios según la fuente y medio de tráfico")
                
                # Filtros
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    available_sources = get_available_sources(db, fecha_inicio, fecha_fin)
                    filter_sources = st.multiselect(
                        "🔍 Filtrar por Fuente",
                        options=available_sources,
                        default=[],
                        placeholder="Ej: google, facebook, instagram...",
                        key="users_filter_sources"
                    )
                
                with col_f2:
                    available_mediums = get_mediums_by_source(db, fecha_inicio, fecha_fin, filter_sources)
                    filter_mediums = st.multiselect(
                        "🎯 Filtrar por Medio",
                        options=available_mediums,
                        default=[],
                        placeholder="Ej: organic, cpc, referral...",
                        key="users_filter_mediums"
                    )
                
                if filter_sources or filter_mediums:
                    # Mostrar filtros activos
                    filter_info = []
                    if filter_sources:
                        filter_info.append(f"**Fuentes:** {', '.join(filter_sources)}")
                    if filter_mediums:
                        filter_info.append(f"**Medios:** {', '.join(filter_mediums)}")
                    st.info(f"🔍 Filtros aplicados: {' | '.join(filter_info)}")
                    
                    with st.spinner("🔄 Aplicando filtros..."):
                        df_users_filtered = get_users_by_month_filtered(
                            db, fecha_inicio, fecha_fin,
                            fuentes=filter_sources if filter_sources else None,
                            medios=filter_mediums if filter_mediums else None
                        )
                    
                    if df_users_filtered is not None and not df_users_filtered.empty:
                        # Preparar datos
                        filtered_data = []
                        for _, row in df_users_filtered.iterrows():
                            mes_num = int(row['mes'])
                            anio = int(row['anio'])
                            filtered_data.append({
                                'Año': anio,
                                'Mes': meses_nombres.get(mes_num, f'Mes {mes_num}'),
                                'Mes Num': mes_num,
                                'Usuarios': int(row['usuarios']),
                                'Sesiones': int(row['sesiones']),
                                'Vistas': int(row['vistas'])
                            })
                        
                        df_filtered_display = pd.DataFrame(filtered_data)
                        df_filtered_display = df_filtered_display.sort_values(['Año', 'Mes Num'])
                        
                        # Métricas
                        col_m1, col_m2, col_m3 = st.columns(3)
                        with col_m1:
                            st.metric("Total Usuarios", f"{df_filtered_display['Usuarios'].sum():,}")
                        with col_m2:
                            st.metric("Total Sesiones", f"{df_filtered_display['Sesiones'].sum():,}")
                        with col_m3:
                            st.metric("Meses con datos", f"{len(df_filtered_display)}")
                        
                        # Tabla con formato de miles
                        df_filtered_formatted = format_dataframe_numbers(
                            df_filtered_display[['Año', 'Mes', 'Usuarios', 'Sesiones', 'Vistas']],
                            columns=['Usuarios', 'Sesiones', 'Vistas']
                        )
                        st.dataframe(df_filtered_formatted, use_container_width=True)
                        
                        # Gráfico
                        df_filtered_display['Periodo'] = df_filtered_display.apply(
                            lambda x: f"{x['Mes'][:3]} {x['Año']}", axis=1
                        )
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=df_filtered_display['Periodo'],
                            y=df_filtered_display['Usuarios'],
                            name='Usuarios',
                            marker_color='#9b59b6',
                            text=df_filtered_display['Usuarios'].apply(lambda x: f'{x:,}'),
                            textposition='outside'
                        ))
                        
                        fig.update_layout(
                            title="👥 Usuarios por Mes (Filtrado por Tráfico)",
                            xaxis_title="Periodo",
                            yaxis_title="Usuarios",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Descarga
                        csv = df_filtered_display[['Año', 'Mes', 'Usuarios', 'Sesiones', 'Vistas']].to_csv(index=False)
                        st.download_button(
                            label="💾 Descargar datos filtrados (CSV)",
                            data=csv,
                            file_name=f'usuarios_filtrado_{fecha_inicio}_{fecha_fin}.csv',
                            mime='text/csv',
                            key="download_users_filtered"
                        )
                    else:
                        st.warning("⚠️ No hay datos con los filtros seleccionados")
                else:
                    st.info("👆 Selecciona al menos una fuente o medio para ver los datos filtrados")
        
        with tab2:
            if df_trend is not None and not df_trend.empty:
                st.subheader("📈 Datos de Tendencia Diaria")
                df_trend['Tasa de Rebote'] = (df_trend['Tasa de Rebote'] * 100).round(2)
                df_trend['Duración Media de Sesión'] = pd.to_datetime(
                    df_trend['Duración Media de Sesión'], unit='s'
                ).dt.strftime("%H:%M:%S")
                df_trend_formatted = format_dataframe_numbers(
                    df_trend,
                    columns=['Usuarios Activos', 'Sesiones', 'Vistas de Página']
                )
                st.dataframe(df_trend_formatted, use_container_width=True)
                
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
        
        with tab3:
            if df_devices is not None and not df_devices.empty:
                st.subheader("📱 Datos por Dispositivos")
                df_devices_formatted = format_dataframe_numbers(
                    df_devices,
                    columns=['Usuarios Activos', 'Sesiones']
                )
                st.dataframe(df_devices_formatted, use_container_width=True)
                
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
        
        with tab4:
            # Lazy loading: cargar solo cuando se accede al tab
            if df_pages is None:
                with st.spinner("📄 Cargando datos de páginas..."):
                    df_pages = get_top_pages_range(db, fecha_inicio, fecha_fin)
            
            if df_pages is not None and not df_pages.empty:
                st.subheader("📄 Datos de Páginas")
                df_pages_display = df_pages.copy()
                
                # Formatear Tiempo Promedio de Vista si existe
                if 'Tiempo Promedio de Vista' in df_pages_display.columns:
                    df_pages_display['Tiempo Promedio de Vista'] = pd.to_datetime(
                        df_pages_display['Tiempo Promedio de Vista'], unit='s', errors='coerce'
                    ).dt.strftime("%H:%M:%S")
                
                # Formatear Tasa de Rebote si existe
                if 'Tasa de Rebote' in df_pages_display.columns:
                    df_pages_display['Tasa de Rebote'] = (df_pages_display['Tasa de Rebote'].fillna(0) * 100).round(2).astype(str) + '%'
                
                df_pages_formatted = format_dataframe_numbers(
                    df_pages_display,
                    columns=['Vistas', 'Usuarios Activos', 'Sesiones']
                )
                st.dataframe(df_pages_formatted, use_container_width=True)
                
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
            # Lazy loading: cargar solo cuando se accede al tab
            if df_hourly is None:
                with st.spinner("⏰ Cargando datos horarios..."):
                    df_hourly = get_hourly_data_range(db, fecha_inicio, fecha_fin)
            
            if df_hourly is not None and not df_hourly.empty:
                st.subheader("⏰ Datos Horarios")
                df_hourly_formatted = format_dataframe_numbers(
                    df_hourly,
                    columns=['Usuarios Activos', 'Sesiones']
                )
                st.dataframe(df_hourly_formatted, use_container_width=True)
                
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
            # Funcionalidad de términos de búsqueda deshabilitada
            st.info("⚠️ La funcionalidad de términos de búsqueda ha sido deshabilitada")
        
        with tab7:
            st.subheader("🚀 Fuentes de Tráfico - Filtros Avanzados")
            
            # Obtener listas de fuentes disponibles
            available_sources = get_available_sources(db, fecha_inicio, fecha_fin)
            
            # Crear filtros en columnas
            col_filter1, col_filter2 = st.columns(2)
            
            with col_filter1:
                selected_sources = st.multiselect(
                    "🔍 Filtrar por Fuente (sessionSource)",
                    options=available_sources,
                    default=[],
                    placeholder="Selecciona fuentes (ej: google, ig, facebook...)",
                    help="Selecciona una o más fuentes. Deja vacío para ver todas.",
                    key="tab6_sources"
                )
            
            with col_filter2:
                # Obtener medios vinculados a las fuentes seleccionadas
                available_mediums = get_mediums_by_source(db, fecha_inicio, fecha_fin, selected_sources)
                
                selected_mediums = st.multiselect(
                    "🎯 Filtrar por Medio (sessionMedium)",
                    options=available_mediums,
                    default=[],
                    placeholder="Selecciona medios (ej: organic, paid, referral...)",
                    help="Solo muestra medios vinculados a las fuentes seleccionadas." if selected_sources else "Selecciona uno o más medios. Deja vacío para ver todos.",
                    key="tab6_mediums"
                )
            
            # Cargar datos según filtros
            if selected_sources or selected_mediums:
                # Usar función filtrada
                with st.spinner("🔄 Aplicando filtros..."):
                    df_traffic_filtered = get_traffic_sources_filtered(
                        db, fecha_inicio, fecha_fin,
                        fuentes=selected_sources if selected_sources else None,
                        medios=selected_mediums if selected_mediums else None,
                        limit=50
                    )
                    
                    # También cargar datos mensuales filtrados
                    df_monthly_filtered = get_traffic_sources_monthly_filtered(
                        db, fecha_inicio, fecha_fin,
                        fuentes=selected_sources if selected_sources else None,
                        medios=selected_mediums if selected_mediums else None
                    )
                
                if df_traffic_filtered is not None and not df_traffic_filtered.empty:
                    # Mostrar resumen de filtros aplicados
                    filter_info = []
                    if selected_sources:
                        filter_info.append(f"**Fuentes:** {', '.join(selected_sources)}")
                    if selected_mediums:
                        filter_info.append(f"**Medios:** {', '.join(selected_mediums)}")
                    
                    st.info(f"🔍 Filtros aplicados: {' | '.join(filter_info)}")
                    
                    # Mostrar métricas resumen
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Total Sesiones", f"{df_traffic_filtered['Sesiones'].sum():,}")
                    with col_m2:
                        st.metric("Total Usuarios", f"{df_traffic_filtered['Usuarios Activos'].sum():,}")
                    with col_m3:
                        st.metric("Combinaciones", f"{len(df_traffic_filtered)}")
                    
                    df_traffic_formatted = format_dataframe_numbers(
                        df_traffic_filtered,
                        columns=['Usuarios Activos', 'Sesiones', 'Vistas de Página']
                    )
                    st.dataframe(df_traffic_formatted, use_container_width=True)
                    
                    # Opción de descarga
                    csv = df_traffic_filtered.to_csv(index=False)
                    st.download_button(
                        label="💾 Descargar datos filtrados (CSV)",
                        data=csv,
                        file_name=f'fuentes_trafico_filtrado_{fecha_inicio}_{fecha_fin}.csv',
                        mime='text/csv'
                    )
                    
                    # ========== DESGLOSE MENSUAL ==========
                    st.markdown("---")
                    st.subheader("📅 Desglose Mensual")
                    
                    if df_monthly_filtered is not None and not df_monthly_filtered.empty:
                        # Agrupar por mes para el desglose
                        meses_nombres = {
                            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                        }
                        
                        # Agregar los datos por mes
                        df_by_month = df_monthly_filtered.groupby(['anio', 'mes']).agg({
                            'sesiones': 'sum'
                        }).reset_index()
                        
                        # Crear tabla de desglose mensual
                        monthly_data = []
                        for _, row in df_by_month.iterrows():
                            mes_num = int(row['mes'])
                            anio = int(row['anio'])
                            monthly_data.append({
                                'Año': anio,
                                'Mes': meses_nombres.get(mes_num, f'Mes {mes_num}'),
                                'Mes Num': mes_num,
                                'Sesiones': int(row['sesiones'])
                            })
                        
                        df_monthly_display = pd.DataFrame(monthly_data)
                        df_monthly_display = df_monthly_display.sort_values(['Año', 'Mes Num'])
                        
                        # Mostrar tabla sin columna auxiliar, con formato de miles
                        df_monthly_formatted = format_dataframe_numbers(
                            df_monthly_display[['Año', 'Mes', 'Sesiones']],
                            columns=['Sesiones']
                        )
                        st.dataframe(df_monthly_formatted, use_container_width=True)
                        
                        # Crear gráfico de barras mensual
                        df_monthly_display['Periodo'] = df_monthly_display.apply(
                            lambda x: f"{x['Mes']} {x['Año']}", axis=1
                        )
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=df_monthly_display['Periodo'],
                            y=df_monthly_display['Sesiones'],
                            marker_color='#1f77b4',
                            text=df_monthly_display['Sesiones'].apply(lambda x: f'{x:,}'),
                            textposition='outside'
                        ))
                        
                        fig.update_layout(
                            title="📊 Sesiones por Mes (Filtrado)",
                            xaxis_title="Periodo",
                            yaxis_title="Sesiones",
                            hovermode='x unified',
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Opción de descarga del desglose mensual
                        csv_monthly = df_monthly_display[['Año', 'Mes', 'Sesiones']].to_csv(index=False)
                        st.download_button(
                            label="💾 Descargar desglose mensual (CSV)",
                            data=csv_monthly,
                            file_name=f'fuentes_trafico_mensual_{fecha_inicio}_{fecha_fin}.csv',
                            mime='text/csv',
                            key="download_monthly_filtered"
                        )
                    else:
                        st.info("No hay datos para el desglose mensual con los filtros aplicados")
                else:
                    st.warning("⚠️ No hay datos con los filtros seleccionados")
            else:
                # Sin filtros - mostrar top 10 como antes
                if df_traffic_sources is None:
                    with st.spinner("🚀 Cargando fuentes de tráfico..."):
                        df_traffic_sources = get_traffic_sources_range(db, fecha_inicio, fecha_fin, limit=10)
                
                if df_traffic_sources is not None and not df_traffic_sources.empty:
                    st.caption("💡 Usa los filtros arriba para buscar fuentes o medios específicos")
                    df_traffic_formatted = format_dataframe_numbers(
                        df_traffic_sources,
                        columns=['Usuarios Activos', 'Sesiones', 'Vistas de Página']
                    )
                    st.dataframe(df_traffic_formatted, use_container_width=True)
                    
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
        
        with tab8:
            # Lazy loading: cargar solo cuando se accede al tab
            if df_utm is None:
                with st.spinner("🎯 Cargando campañas UTM..."):
                    df_utm = get_utm_tracking_range(db, fecha_inicio, fecha_fin, limit=10)
            
            if df_utm is not None and not df_utm.empty:
                st.subheader("🎯 Datos de Campañas UTM")
                
                # Formatear tasa de rebote
                df_utm_display = df_utm.copy()
                if 'Tasa de Rebote' in df_utm_display.columns:
                    df_utm_display['Tasa de Rebote'] = (df_utm_display['Tasa de Rebote'].fillna(0) * 100).round(2).astype(str) + '%'
                
                df_utm_formatted = format_dataframe_numbers(
                    df_utm_display,
                    columns=['Usuarios Activos', 'Sesiones', 'Vistas de Página']
                )
                st.dataframe(df_utm_formatted, use_container_width=True)
                
                # Opción de descarga
                csv = df_utm.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos de campañas UTM (CSV)",
                    data=csv,
                    file_name=f'utm_tracking_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos de campañas UTM")

    st.markdown("---")

    # =============================================================================
    # ANÁLISIS DE CAMPAÑAS UTM
    # =============================================================================
    
    st.header("🎯 Análisis de Campañas UTM")
    
    # Lazy loading: cargar solo si no están disponibles
    if df_utm is None:
        with st.spinner("🎯 Cargando campañas UTM..."):
            df_utm = get_utm_tracking_range(db, fecha_inicio, fecha_fin, limit=15)
    
    if df_utm_summary is None:
        with st.spinner("🎯 Cargando resumen de campañas..."):
            df_utm_summary = get_utm_summary(db, fecha_inicio, fecha_fin)
    
    if df_utm is not None and not df_utm.empty and df_utm_summary is not None and not df_utm_summary.empty:
        # Métricas resumen de UTM
        summary_row = df_utm_summary.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(create_metric_card_html(
                "Total de Campañas", 
                format_number_complete(summary_row['total_campaigns']),
                "📢"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_metric_card_html(
                "Sesiones desde Campañas", 
                format_number_complete(summary_row['total_sessions']),
                "📱"
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown(create_metric_card_html(
                "Usuarios desde Campañas", 
                format_number_complete(summary_row['total_users']),
                "👥"
            ), unsafe_allow_html=True)
        
        with col4:
            st.markdown(create_metric_card_html(
                "Tasa de Rebote Promedio", 
                format_percentage(summary_row['avg_bounce_rate']),
                "⚡"
            ), unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.subheader("📊 Top Campañas por Sesiones")
            
            # Tabla de campañas
            df_utm_display = df_utm.head(10).copy()
            
            # Formatear tasa de rebote
            if 'Tasa de Rebote' in df_utm_display.columns:
                df_utm_display['Tasa de Rebote'] = (df_utm_display['Tasa de Rebote'].fillna(0) * 100).round(2).astype(str) + '%'
            
            df_utm_display_formatted = format_dataframe_numbers(
                df_utm_display,
                columns=['Usuarios Activos', 'Sesiones', 'Vistas de Página']
            )
            st.dataframe(df_utm_display_formatted, use_container_width=True)
            
            # Gráfico de barras
            fig_utm = px.bar(
                df_utm.head(10),
                x='Sesiones',
                y='Campaña',
                orientation='h',
                title='Top 10 Campañas por Sesiones',
                color='Usuarios Activos',
                color_continuous_scale='Viridis',
                text='Sesiones'
            )
            fig_utm.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_utm.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                height=400
            )
            st.plotly_chart(fig_utm, use_container_width=True)
        
        with col2:
            st.subheader("📈 Análisis de Fuentes UTM")
            
            # Agrupar por fuente
            df_by_source = df_utm.groupby('Fuente').agg({
                'Sesiones': 'sum',
                'Usuarios Activos': 'sum',
                'Vistas de Página': 'sum'
            }).reset_index().sort_values('Sesiones', ascending=False).head(5)
            
            st.markdown("**Top 5 Fuentes:**")
            for idx, row in df_by_source.iterrows():
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                            color: white; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;">
                    <strong>{row['Fuente']}</strong><br>
                    Sesiones: {int(row['Sesiones']):,} | Usuarios: {int(row['Usuarios Activos']):,}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Agrupar por medio
            df_by_medium = df_utm.groupby('Medio').agg({
                'Sesiones': 'sum',
                'Usuarios Activos': 'sum'
            }).reset_index().sort_values('Sesiones', ascending=False).head(5)
            
            st.markdown("**Top 5 Medios:**")
            for idx, row in df_by_medium.iterrows():
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, #00b894 0%, #00cec9 100%); 
                            color: white; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;">
                    <strong>{row['Medio']}</strong><br>
                    Sesiones: {int(row['Sesiones']):,} | Usuarios: {int(row['Usuarios Activos']):,}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("⚠️ No hay datos de campañas UTM disponibles para el período seleccionado")
    
    st.markdown("---")

    # =============================================================================
    # ANÁLISIS DE FUENTES DE TRÁFICO (NUEVA SECCIÓN)
    # =============================================================================

    st.header("🚀 Análisis de Fuentes de Tráfico")

    if df_traffic_sources is not None and not df_traffic_sources.empty:
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
    
    if df_pages is not None and not df_pages.empty:
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
    
    if df_devices is not None and not df_devices.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de dispositivos
            device_chart = create_device_comparison(df_devices)
            if device_chart:
                st.plotly_chart(device_chart, use_container_width=True)
    
    st.markdown("---")
    st.markdown("---")
    
    # =============================================================================
    # ANÁLISIS POR HORAS
    # =============================================================================
    
    st.header("⏰ Actividad por Hora")
    
    if df_hourly is not None and not df_hourly.empty:
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

    