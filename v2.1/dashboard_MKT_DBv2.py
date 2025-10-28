import mysql
import mysql.connector
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pymysql
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 🗄️ CONFIGURACIÓN DE BASE DE DATOS Y TABLAS (ACTUALIZADA)
# =============================================================================

# Configuracion de la conexion
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Tu password de MySQL si lo tienes
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
    'terminos_busqueda': 'terminos_busqueda',  # NUEVA TABLA
    'busqueda_interna': 'busqueda_interna'     # NUEVA TABLA
}

# 🎨 CONFIGURACIÓN DE STREAMLIT
st.set_page_config(
    page_title="GA4 Analytics Dashboard",
    page_icon="📊",
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
</style>
""", unsafe_allow_html=True)

def create_connection():
    """Crear conexión a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Conectado a las {hora_actual}")
            return connection
    except pymysql.Error as e:
        st.error(f"Error conectando a MySQL: {e}")
        return None

create_connection()


@st.cache_resource
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
            
            return True
            
        except Exception as e:
            st.error(f"❌ Error conectando a la base de datos: {e}")
            st.error("Verifica que WAMP esté ejecutándose y la configuración sea correcta")
            return False
    
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

# =============================================================================
# 📊 FUNCIONES DE CONSULTA CON FILTRO DE FECHAS (ACTUALIZADAS)
# =============================================================================

@st.cache_data(ttl=300)
def get_metrics_by_date_range(_db, fecha_inicio, fecha_fin):
    """Obtener métricas de un rango de fechas"""
    sql = f"""
    SELECT 
        DATE_FORMAT(fecha, '%%d/%%m/%%Y') AS "Fecha",
        activeUsers,
        sessions,
        screenPageViews,
        bounceRate,
        averageSessionDuration,
        created_at,
        updated_at
    FROM {TABLE_CONFIG['metricas_generales']}
    WHERE fecha BETWEEN %s AND %s
    ORDER BY fecha
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

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
    GROUP BY deviceCategory
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
        AVG(bounceRate) as "Tasa de Rebote",
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
    GROUP BY fecha
    ORDER BY fecha
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

# =============================================================================
# 🔍 NUEVAS FUNCIONES PARA TÉRMINOS DE BÚSQUEDA
# =============================================================================

@st.cache_data(ttl=300)
def get_search_terms_range(_db, fecha_inicio, fecha_fin, limit=20):
    """Obtener términos de búsqueda más utilizados en un rango de fechas"""
    sql = f"""
    SELECT 
        searchTerm as "Término de Búsqueda",
        SUM(sessions) as "Sesiones",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(screenPageViews) as "Páginas Vistas",
        AVG(averageSessionDuration) as "Duración Promedio"
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
def get_internal_search_range(_db, fecha_inicio, fecha_fin, limit=20):
    """Obtener datos de búsqueda interna en un rango de fechas"""
    sql = f"""
    SELECT 
        searchTerm as "Término Búsqueda Interna",
        pagePath as "Página",
        SUM(sessions) as "Sesiones",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(screenPageViews) as "Páginas Vistas",
        AVG(bounceRate) as "Tasa de Rebote"
    FROM {TABLE_CONFIG['busqueda_interna']} 
    WHERE fecha BETWEEN %s AND %s
    AND searchTerm IS NOT NULL 
    AND searchTerm != ''
    AND searchTerm != '(not set)'
    GROUP BY searchTerm, pagePath
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

# ____________________________________________________________________________
# 📈 FUNCIONES DE VISUALIZACIÓN AJUSTADAS Y NUEVAS
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

def create_search_terms_cloud_data(df_search):
    """Preparar datos para nube de palabras de términos de búsqueda"""
    if df_search.empty:
        return pd.DataFrame()
    
    # Tomar top 20 y preparar para visualización tipo nube
    df_cloud = df_search.head(20).copy()
    df_cloud['size'] = df_cloud['Sesiones'] / df_cloud['Sesiones'].max() * 40 + 10
    
    return df_cloud

def create_internal_search_chart(df_internal):
    """Crear gráfico de búsquedas internas"""
    if df_internal.empty:
        return None
    
    # Agrupar por término y sumar sesiones
    df_grouped = df_internal.groupby('Término Búsqueda Interna').agg({
        'Sesiones': 'sum',
        'Usuarios Activos': 'sum',
        'Tasa de Rebote': 'mean'
    }).reset_index().head(10)
    
    fig = px.scatter(
        df_grouped,
        x='Sesiones',
        y='Usuarios Activos',
        size='Sesiones',
        color='Tasa de Rebote',
        hover_name='Término Búsqueda Interna',
        title="🔍 Búsquedas Internas: Sesiones vs Usuarios",
        color_continuous_scale='RdYlBu_r'
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_search_comparison_chart(df_search, df_internal):
    """Crear gráfico de comparación entre búsquedas externas e internas"""
    if df_search.empty and df_internal.empty:
        return None
    
    # Preparar datos de comparación
    external_total = df_search['Sesiones'].sum() if not df_search.empty else 0
    internal_total = df_internal['Sesiones'].sum() if not df_internal.empty else 0
    
    if external_total == 0 and internal_total == 0:
        return None
    
    comparison_data = pd.DataFrame({
        'Tipo': ['Búsquedas Externas', 'Búsquedas Internas'],
        'Sesiones': [external_total, internal_total]
    })
    
    fig = px.pie(
        comparison_data,
        values='Sesiones',
        names='Tipo',
        title="🔍 Distribución: Búsquedas Externas vs Internas",
        color_discrete_map={
            'Búsquedas Externas': '#3498db',
            'Búsquedas Internas': '#e74c3c'
        }
    )
    
    fig.update_traces(textinfo='percent+label+value')
    fig.update_layout(height=400)
    
    return fig

# Funciones originales de visualización (sin cambios)
def create_daily_trend_chart(df_trend):
    """Crear gráfico de tendencia diaria"""
    if df_trend.empty:
        return None
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('👥 Usuarios Activos', '📱 Sesiones', '👀 Páginas Vistas', '⚡ Tasa de Rebote'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Usuarios activos
    fig.add_trace(
        go.Scatter(
            x=df_trend['Fecha'], 
            y=df_trend['Usuarios Activos'], 
            name='Usuarios Activos',
            line=dict(color='#3498db', width=3),
            fill='tonexty',
            hovertemplate='%{x}<br>Usuarios: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Sesiones
    fig.add_trace(
        go.Scatter(
            x=df_trend['Fecha'], 
            y=df_trend['Sesiones'], 
            name='Sesiones',
            line=dict(color='#e74c3c', width=3),
            fill='tonexty',
            hovertemplate='%{x}<br>Sesiones: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # Páginas vistas
    fig.add_trace(
        go.Scatter(
            x=df_trend['Fecha'], 
            y=df_trend['Vistas de Página'], 
            name='Páginas Vistas',
            line=dict(color='#2ecc71', width=3),
            fill='tonexty',
            hovertemplate='%{x}<br>Páginas: %{y:,.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Tasa de rebote
    fig.add_trace(
        go.Scatter(
            x=df_trend['Fecha'], 
            y=df_trend['Tasa de Rebote'], 
            name='Tasa de Rebote',
            line=dict(color='#f39c12', width=3),
            hovertemplate='%{x}<br>Rebote: %{y:.1%}<extra></extra>'
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        height=600, 
        showlegend=False,
        title_text="📈 Tendencia de Métricas en el Período Seleccionado",
        title_x=0.5,
        font=dict(size=12)
    )
    
    return fig

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

def create_comparison_table(df_devices):
    """Crear tabla de comparación de dispositivos"""
    if df_devices.empty:
        return pd.DataFrame()
    
    df_comparison = df_devices.copy()
    df_comparison['Usuarios por Sesión'] = (df_comparison['Usuarios Activos'] / df_comparison['Sesiones']).round(2)
    df_comparison['Páginas por Sesión'] = (df_comparison['Páginas Vistas'] / df_comparison['Sesiones']).round(2)
    
    # Renombrar columnas para mejor presentación
    df_comparison = df_comparison.rename(columns={
        'Dispositivo': 'Dispositivo',
        'Usuarios Activos': 'Usuarios Activos',
        'Sesiones': 'Sesiones',
        'Páginas Vistas': 'Páginas Vistas'
    })
    
    return df_comparison[['Dispositivo', 'Usuarios Activos', 'Sesiones', 'Páginas Vistas', 'Usuarios por Sesión', 'Páginas por Sesión']]

def create_geo_summary_table(df_geo):
    """Crear tabla resumen geográfica"""
    if df_geo.empty:
        return pd.DataFrame()
    
    df_geo_summary = df_geo.groupby('Pais').agg({
        'Usuarios Activos': 'sum',
        'Sesiones': 'sum',
        'Páginas Vistas': 'sum'
    }).reset_index()
    
    df_geo_summary = df_geo_summary.sort_values('Usuarios Activos', ascending=False).head(10)
    
    # Calcular métricas adicionales
    df_geo_summary['Páginas por Usuario'] = (df_geo_summary['Páginas Vistas'] / df_geo_summary['Usuarios Activos']).round(2)
    df_geo_summary['Sesiones por Usuario'] = (df_geo_summary['Sesiones'] / df_geo_summary['Usuarios Activos']).round(2)
    
    # Renombrar columnas
    df_geo_summary = df_geo_summary.rename(columns={
        'Pais': 'País',
        'Usuarios Activos': 'Usuarios Activos',
        'Sesiones': 'Sesiones',
        'Páginas Vistas': 'Páginas Vistas'
    })
    
    return df_geo_summary

# MODIFICADO: Nueva función para mostrar números completos
def format_number_complete(num):
    """Formatear números mostrando todos los dígitos con separadores de miles"""
    return f"{int(num):,}".replace(",", ".")

def format_percentage(num):
    """Formatear porcentajes"""
    return f"{num:.1%}"

def create_metric_card_html(title, value, icon="📊"):
    """Crear HTML para tarjetas de métricas"""
    return f"""
    <div class="metric-card">
        <h4>{icon} {title}</h4>
        <h2>{value}</h2>
    </div>
    """

def create_search_metric_card_html(title, value, icon="🔍"):
    """Crear HTML para tarjetas de métricas de búsqueda"""
    return f"""
    <div class="search-terms-card">
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
        
        # Obtener rango de fechas disponibles
        date_info = db.get_date_range()
        
        if date_info:
            st.success(f"📅 Datos disponibles: {date_info['total_days']} días")
            
            # NUEVO: Filtro de rango de fechas
            st.subheader("📅 Filtro de Fechas")
            
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input(
                    "Fecha Inicio:",
                    value=date_info['max_date'] - timedelta(days=7),  # Por defecto última semana
                    # min_value=date_info['min_date'],
                    max_value=date_info['max_date']
                )
            
            with col2:
                fecha_fin = st.date_input(
                    "Fecha Fin:",
                    value=date_info['max_date'],
                    # min_value=date_info['min_date'],
                    max_value=date_info['max_date']
                )
            
            # Validar rango de fechas
            if fecha_inicio > fecha_fin:
                st.error("❌ La fecha de inicio debe ser anterior a la fecha de fin")
                return
            
            # Mostrar información del período seleccionado
            dias_seleccionados = (fecha_fin - fecha_inicio).days + 1
            st.info(f"📊 Período seleccionado: {dias_seleccionados} día(s)")
            
            # # Botones rápidos para rangos predefinidos
            # st.subheader("⚡ Rangos Rápidos")
            
            # if st.button("📅 Último día"):
            #     fecha_inicio = fecha_fin = date_info['max_date']
            #     st.rerun()
            
            # if st.button("📅 Últimos 7 días"):
            #     fecha_inicio = date_info['max_date'] - timedelta(days=6)
            #     fecha_fin = date_info['max_date']
            #     st.rerun()
            
            # if st.button("📅 Últimos 30 días"):
            #     fecha_inicio = date_info['max_date'] - timedelta(days=29)
            #     fecha_fin = date_info['max_date']
            #     st.rerun()
            
            # Botón de actualización
            if st.button("🔄 Actualizar Datos"):
                st.cache_data.clear()
                st.rerun()
            
            # # Información sobre configuración de tablas
            # with st.expander("🗄️ Configuración de Tablas"):
            #     st.write("**Tablas actuales:**")
            #     for key, value in TABLE_CONFIG.items():
            #         st.write(f"• {key}: `{value}`")
            #     st.info("Para cambiar los nombres de las tablas, modifica el diccionario TABLE_CONFIG en el código.")
                
        else:
            st.error("❌ No se pudo conectar a la base de datos")
            return
    
    # Obtener datos para el rango de fechas seleccionado
    with st.spinner("📊 Cargando datos del período seleccionado..."):
        df_trend = get_daily_trend_data(db, fecha_inicio, fecha_fin)
        df_devices = get_device_breakdown_range(db, fecha_inicio, fecha_fin)
        df_pages = get_top_pages_range(db, fecha_inicio, fecha_fin)
        df_geo = get_geographic_data_range(db, fecha_inicio, fecha_fin)
        df_hourly = get_hourly_data_range(db, fecha_inicio, fecha_fin)
        
        # NUEVO: Cargar datos de términos de búsqueda
        df_search_terms = get_search_terms_range(db, fecha_inicio, fecha_fin)
        df_internal_search = get_internal_search_range(db, fecha_inicio, fecha_fin)
        df_search_summary = get_search_terms_summary(db, fecha_inicio, fecha_fin)
    
    # Verificar si hay datos
    if df_trend.empty:
        st.warning(f"⚠️ No hay datos disponibles para el período {fecha_inicio} - {fecha_fin}")
        return
    
    # =============================================================================
    # 📅 1. PERÍODO ANALIZADO (NUEVA POSICIÓN)
    # =============================================================================
    
    # Mostrar el período seleccionado
    st.markdown(f"""
    <div class="date-filter-card">
        <h3>📅 Período Analizado</h3>
        <p><strong>Desde:</strong> {fecha_inicio.strftime('%d/%m/%Y')} <strong>Hasta:</strong> {fecha_fin.strftime('%d/%m/%Y')}</p>
        <p><strong>Total:</strong> {dias_seleccionados} día(s) de datos</p>
    </div>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # 📈 2. RESUMEN DEL PERÍODO (CON NÚMEROS COMPLETOS)
    # =============================================================================
    
    st.header(f"📈 Resumen del Período")
    
    # Tarjetas de métricas principales CON NÚMEROS COMPLETOS
    total_users, total_sessions, total_pageviews, avg_bounce_rate = create_summary_metrics_cards(df_trend)
    
    if total_users is not None:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(create_metric_card_html(
                "Usuarios Activos", 
                format_number_complete(total_users),  # MODIFICADO: números completos
                "👥"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_metric_card_html(
                "Sesiones", 
                format_number_complete(total_sessions),  # MODIFICADO: números completos
                "📱"
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown(create_metric_card_html(
                "Páginas Vistas", 
                format_number_complete(total_pageviews),  # MODIFICADO: números completos
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
    # 📊 4. VER DATOS DETALLADOS (ACTUALIZADA CON BÚSQUEDAS)
    # =============================================================================
    
    with st.expander("📊 Ver Datos Detallados"):
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "Tendencia Diaria", 
            "Dispositivos", 
            "Geografía", 
            "Páginas", 
            "Horas", 
            "Búsquedas Externas",  # NUEVA TAB
            "Búsquedas Internas"   # NUEVA TAB
        ])
        
        with tab1:
            if not df_trend.empty:
                st.subheader("📈 Datos de Tendencia Diaria")
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
        
        # NUEVAS TABS PARA BÚSQUEDAS
        with tab6:
            if not df_search_terms.empty:
                st.subheader("🔍 Datos de Búsquedas Externas")
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
            if not df_internal_search.empty:
                st.subheader("🔍 Datos de Búsquedas Internas")
                st.dataframe(df_internal_search, use_container_width=True)
                
                # Opción de descarga
                csv = df_internal_search.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar términos de búsqueda interna (CSV)",
                    data=csv,
                    file_name=f'busquedas_internas_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos de búsquedas internas")

    st.markdown("---")
    

        # =============================================================================
    # 📊 10. RESUMEN FINAL DE BÚSQUEDAS (NUEVA SECCIÓN)
    # =============================================================================
    
    if not df_search_summary.empty:
        # st.markdown("---")
        st.header("📊 Resumen Final de Términos de Búsqueda")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔍 Top Términos Más Buscados")
            st.dataframe(df_search_summary, use_container_width=True)
        
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


    # =============================================================================
    # 🔍 3. ANÁLISIS DE TÉRMINOS DE BÚSQUEDA (NUEVA SECCIÓN)
    # =============================================================================
    
    st.header("🔍 Análisis de Términos de Búsqueda")
    
    # Métricas de búsqueda
    if not df_search_terms.empty or not df_internal_search.empty:
        col1, col2 , col3, col4 = st.columns(4)
        
        with col1:
            total_search_sessions = df_search_terms['Sesiones'].sum() if not df_search_terms.empty else 0
            st.markdown(create_search_metric_card_html(
                "Sesiones por Búsqueda Externa", 
                format_number_complete(total_search_sessions),
                "🔍"
            ), unsafe_allow_html=True)
        
        with col2:
            unique_search_terms = len(df_search_terms) if not df_search_terms.empty else 0
            st.markdown(create_search_metric_card_html(
                "Términos Únicos (Externa)", 
                format_number_complete(unique_search_terms),
                "📝"
            ), unsafe_allow_html=True)
        
        # with col3:
        #     internal_search_sessions = df_internal_search['Sesiones'].sum() if not df_internal_search.empty else 0
        #     st.markdown(create_search_metric_card_html(
        #         "Sesiones Búsqueda Interna", 
        #         format_number_complete(internal_search_sessions),
        #         "🔍"
        #     ), unsafe_allow_html=True)
        
        # with col4:
        #     unique_internal_terms = len(df_internal_search['Término Búsqueda Interna'].unique()) if not df_internal_search.empty else 0
        #     st.markdown(create_search_metric_card_html(
        #         "Términos Únicos (Interna)", 
        #         format_number_complete(unique_internal_terms),
        #         "📝"
        #     ), unsafe_allow_html=True)
        
        # Gráficos de términos de búsqueda
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if not df_search_terms.empty:
                search_chart = create_search_terms_chart(df_search_terms)
                if search_chart:
                    st.plotly_chart(search_chart, use_container_width=True)
            else:
                st.info("⚠️ No hay datos de términos de búsqueda externa disponibles")
        
        with col2:
            if not df_search_terms.empty and not df_internal_search.empty:
                comparison_chart = create_search_comparison_chart(df_search_terms, df_internal_search)
                if comparison_chart:
                    st.plotly_chart(comparison_chart, use_container_width=True)
            else:
                st.info("⚠️ Datos insuficientes para comparación de búsquedas")
        
        # # Análisis de búsquedas internas
        # if not df_internal_search.empty:
        #     st.subheader("🔍 Análisis de Búsquedas Internas")
        #     internal_chart = create_internal_search_chart(df_internal_search)
        #     if internal_chart:
        #         st.plotly_chart(internal_chart, use_container_width=True)
        
    else:
        st.warning("⚠️ No hay datos de términos de búsqueda disponibles para el período seleccionado")
    
    st.markdown("---")
    
    
    
    # =============================================================================
    # 📄 5. PÁGINAS MÁS VISITADAS
    # =============================================================================
    
    st.header("📄 Páginas Más Visitadas")
    
    if not df_pages.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de páginas
            pages_chart = create_pages_performance_chart(df_pages)
            if pages_chart:
                st.plotly_chart(pages_chart, use_container_width=True)
        
        with col2:
            # Tabla detallada de páginas
            st.subheader("📊 Detalles de Páginas")
            pages_display = df_pages[['Direccion de Página', 'Vista de Páginas', 'Sesiones', 'Tasa de Rebote']].copy()
            pages_display.columns = ['Página', 'Vistas', 'Sesiones', 'Rebote']
            pages_display['Rebote'] = pages_display['Rebote'].apply(lambda x: f"{x:.1%}")
            st.dataframe(pages_display.head(10), use_container_width=True)
    else:
        st.warning("⚠️ No hay datos de páginas disponibles")
    
    st.markdown("---")
    
    # =============================================================================
    # 📱 6. ANÁLISIS POR DISPOSITIVOS
    # =============================================================================
    
    st.header("📱 Análisis por Dispositivos")
    
    if not df_devices.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de dispositivos
            device_chart = create_device_comparison(df_devices)
            if device_chart:
                st.plotly_chart(device_chart, use_container_width=True)
        
        with col2:
            # Tabla de comparación
            device_table = create_comparison_table(df_devices)
            if not device_table.empty:
                st.dataframe(device_table, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos de dispositivos disponibles")
    
    st.markdown("---")
    
    # =============================================================================
    # 📈 7. TENDENCIA DIARIA
    # =============================================================================
    
    # Gráfico de tendencia diaria
    if not df_trend.empty and dias_seleccionados > 1:
        st.header("📈 Tendencia Diaria")
        trend_chart = create_daily_trend_chart(df_trend)
        if trend_chart:
            st.plotly_chart(trend_chart, use_container_width=True)
    
    st.markdown("---")
    
    # =============================================================================
    # 🌍 8. ANÁLISIS GEOGRÁFICO
    # =============================================================================
    
    st.header("🌍 Análisis Geográfico")
    
    if not df_geo.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico geográfico
            geo_chart = create_geographic_chart(df_geo)
            if geo_chart:
                st.plotly_chart(geo_chart, use_container_width=True)
        
        with col2:
            # Tabla resumen geográfica
            geo_table = create_geo_summary_table(df_geo)
            if not geo_table.empty:
                st.dataframe(geo_table, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos geográficos disponibles")
    
    st.markdown("---")
    
    # =============================================================================
    # ⏰ 9. ANÁLISIS POR HORAS
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

    