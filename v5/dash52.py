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
# 🗄️ CONFIGURACIÓN DE BASE DE DATOS Y TABLAS
# =============================================================================

# Configuracion de la conexion
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Tu password de MySQL si lo tienes
    'database': 'analytics_datos',
    'port': 3306
}

# 📋 CONFIGURACIÓN DE NOMBRES DE TABLAS
# Puedes cambiar estos nombres según tu estructura de base de datos
TABLE_CONFIG = {
    'metricas_generales': 'metricas_generales',
    'dispositivos': 'dispositivos', 
    'paginas_top': 'paginas_top',
    'geografia': 'geografia',
    'datos_horarios': 'datos_horarios'
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

# Conexion a la base de datos.
def create_connection():
    """Crear conexión a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("Conectado")
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
# 📊 FUNCIONES DE CONSULTA CON FILTRO DE FECHAS - VERSIÓN CONSISTENTE
# =============================================================================

@st.cache_data(ttl=300)
def get_metrics_by_date_range(_db, fecha_inicio, fecha_fin):
    """Obtener métricas de un rango de fechas"""
    sql = f"""
    SELECT 
        fecha,
        DATE_FORMAT(fecha, '%%d/%%m/%%Y') AS fecha_formateada,
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
    """Obtener distribución por dispositivos en un rango de fechas - CORREGIDA"""
    sql = f"""
    SELECT 
        deviceCategory,
        SUM(activeUsers) as activeUsers,
        SUM(sessions) as sessions,
        SUM(screenPageViews) as screenPageViews
    FROM {TABLE_CONFIG['dispositivos']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY deviceCategory
    ORDER BY SUM(activeUsers) DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_top_pages_range(_db, fecha_inicio, fecha_fin):
    """Obtener páginas más visitadas en un rango de fechas - CORREGIDA"""
    sql = f"""
    SELECT 
        pagePath,
        pageTitle,
        SUM(screenPageViews) as screenPageViews,
        SUM(sessions) as sessions,
        AVG(bounceRate) as bounceRate,
        AVG(averageSessionDuration) as averageSessionDuration
    FROM {TABLE_CONFIG['paginas_top']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY pagePath, pageTitle
    ORDER BY SUM(screenPageViews) DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_geographic_data_range(_db, fecha_inicio, fecha_fin):
    """Obtener datos geográficos en un rango de fechas - CORREGIDA"""
    sql = f"""
    SELECT 
        country,
        city,
        SUM(activeUsers) as activeUsers,
        SUM(sessions) as sessions,
        SUM(screenPageViews) as screenPageViews
    FROM {TABLE_CONFIG['geografia']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY country, city
    ORDER BY SUM(activeUsers) DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_hourly_data_range(_db, fecha_inicio, fecha_fin):
    """Obtener datos por hora en un rango de fechas"""
    sql = f"""
    SELECT 
        hour,
        SUM(activeUsers) as activeUsers,
        SUM(sessions) as sessions,
        SUM(screenPageViews) as screenPageViews
    FROM {TABLE_CONFIG['datos_horarios']} 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY hour
    ORDER BY hour
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_daily_trend_data(_db, fecha_inicio, fecha_fin):
    """Obtener tendencia diaria para el rango de fechas - CORREGIDA"""
    sql = f"""
    SELECT 
        fecha,
        DATE_FORMAT(fecha, '%%d/%%m/%%Y') AS fecha_formateada,
        SUM(activeUsers) AS activeUsers,
        SUM(sessions) AS sessions,
        SUM(screenPageViews) AS screenPageViews,
        AVG(bounceRate) AS bounceRate,
        AVG(averageSessionDuration) AS averageSessionDuration
    FROM {TABLE_CONFIG['metricas_generales']}
    WHERE fecha BETWEEN %s AND %s
    GROUP BY fecha
    ORDER BY fecha
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))


# =============================================================================
# 📈 FUNCIONES DE VISUALIZACIÓN AJUSTADAS - VERSIÓN CONSISTENTE
# =============================================================================

def create_daily_trend_chart(df_trend):
    """Crear gráfico de tendencia diaria - CORREGIDA"""
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
            x=df_trend['fecha_formateada'], 
            y=df_trend['activeUsers'], 
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
            x=df_trend['fecha_formateada'], 
            y=df_trend['sessions'], 
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
            x=df_trend['fecha_formateada'], 
            y=df_trend['screenPageViews'], 
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
            x=df_trend['fecha_formateada'], 
            y=df_trend['bounceRate'], 
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
    """Crear gráfico de comparación de dispositivos - CORREGIDA"""
    if df_devices.empty:
        return None
    
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=('Distribución de Usuarios', 'Sesiones por Dispositivo')
    )
    
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
    
    # Pie chart
    fig.add_trace(
        go.Pie(
            labels=df_devices['deviceCategory'], 
            values=df_devices['activeUsers'],
            name="Usuarios",
            marker_colors=colors[:len(df_devices)],
            hovertemplate='%{label}<br>Usuarios: %{value:,.0f}<br>%{percent}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Bar chart
    fig.add_trace(
        go.Bar(
            x=df_devices['deviceCategory'], 
            y=df_devices['sessions'],
            name="Sesiones",
            marker_color=colors[:len(df_devices)],
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
    """Crear visualización geográfica - CORREGIDA"""
    if df_geo.empty:
        return None
    
    # Top países
    df_countries = df_geo.groupby('country')['activeUsers'].sum().reset_index()
    df_countries = df_countries.sort_values('activeUsers', ascending=True).tail(10)
    
    fig = px.bar(
        df_countries,
        x='activeUsers',
        y='country',
        orientation='h',
        title="🌍 Top 10 Países por Usuarios (Período Total)",
        color='activeUsers',
        color_continuous_scale='viridis',
        text='activeUsers'
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
    """Crear gráfico de actividad por hora - CORREGIDA"""
    if df_hourly.empty:
        return None
    
    fig = px.line(
        df_hourly,
        x='hour',
        y=['activeUsers', 'sessions'],
        title="📊 Actividad por Hora del Día (Promedio del Período)",
        labels={'hour': 'Hora del Día', 'value': 'Cantidad'}
    )
    
    fig.update_layout(
        height=400,
        xaxis=dict(tickmode='array', tickvals=list(range(0, 24, 2))),
        yaxis_title="Cantidad"
    )
    
    return fig

def create_pages_performance_chart(df_pages):
    """Crear gráfico de rendimiento de páginas - CORREGIDA"""
    if df_pages.empty:
        return None
    
    df_pages_top = df_pages.head(15)
    
    fig = px.bar(
        df_pages_top,
        x='screenPageViews',
        y='pagePath',
        orientation='h',
        title="📄 Top 15 Páginas Más Visitadas (Período Total)",
        color='bounceRate',
        color_continuous_scale='RdYlGn_r',
        hover_data=['sessions', 'bounceRate', 'averageSessionDuration']
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder':'total ascending'},
        yaxis_title="Página",
        xaxis_title="Visualizaciones"
    )
    
    return fig

def create_summary_metrics_cards(df_trend):
    """Crear tarjetas de resumen de métricas para el período - CORREGIDA"""
    if df_trend.empty:
        return None, None, None, None
    
    # Sumar todas las métricas del período
    total_users = df_trend['activeUsers'].sum()
    total_sessions = df_trend['sessions'].sum()
    total_pageviews = df_trend['screenPageViews'].sum()
    avg_bounce_rate = df_trend['bounceRate'].mean()
    
    return total_users, total_sessions, total_pageviews, avg_bounce_rate

def create_comparison_table(df_devices):
    """Crear tabla de comparación de dispositivos - CORREGIDA"""
    if df_devices.empty:
        return pd.DataFrame()
    
    df_comparison = df_devices.copy()
    df_comparison['usuarios_por_sesion'] = (df_comparison['activeUsers'] / df_comparison['sessions']).round(2)
    df_comparison['paginas_por_sesion'] = (df_comparison['screenPageViews'] / df_comparison['sessions']).round(2)
    
    # Renombrar columnas para mejor presentación
    df_comparison = df_comparison.rename(columns={
        'deviceCategory': 'Dispositivo',
        'activeUsers': 'Usuarios Activos',
        'sessions': 'Sesiones',
        'screenPageViews': 'Páginas Vistas',
        'usuarios_por_sesion': 'Usuarios por Sesión',
        'paginas_por_sesion': 'Páginas por Sesión'
    })
    
    return df_comparison[['Dispositivo', 'Usuarios Activos', 'Sesiones', 'Páginas Vistas', 'Usuarios por Sesión', 'Páginas por Sesión']]

def create_geo_summary_table(df_geo):
    """Crear tabla resumen geográfica - CORREGIDA"""
    if df_geo.empty:
        return pd.DataFrame()
    
    df_geo_summary = df_geo.groupby('country').agg({
        'activeUsers': 'sum',
        'sessions': 'sum',
        'screenPageViews': 'sum'
    }).reset_index()
    
    df_geo_summary = df_geo_summary.sort_values('activeUsers', ascending=False).head(10)
    
    # Calcular métricas adicionales
    df_geo_summary['paginas_por_usuario'] = (df_geo_summary['screenPageViews'] / df_geo_summary['activeUsers']).round(2)
    df_geo_summary['sesiones_por_usuario'] = (df_geo_summary['sessions'] / df_geo_summary['activeUsers']).round(2)
    
    # Renombrar columnas
    df_geo_summary = df_geo_summary.rename(columns={
        'country': 'País',
        'activeUsers': 'Usuarios Activos',
        'sessions': 'Sesiones',
        'screenPageViews': 'Páginas Vistas',
        'paginas_por_usuario': 'Páginas por Usuario',
        'sesiones_por_usuario': 'Sesiones por Usuario'
    })
    
    return df_geo_summary

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
            
            # Filtro de rango de fechas
            st.subheader("📅 Filtro de Fechas")
            
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input(
                    "Fecha Inicio:",
                    value=date_info['max_date'] - timedelta(days=7),  # Por defecto última semana
                    min_value=date_info['min_date'],
                    max_value=date_info['max_date']
                )
            
            with col2:
                fecha_fin = st.date_input(
                    "Fecha Fin:",
                    value=date_info['max_date'],
                    min_value=date_info['min_date'],
                    max_value=date_info['max_date']
                )
            
            # Validar rango de fechas
            if fecha_inicio > fecha_fin:
                st.error("❌ La fecha de inicio debe ser anterior a la fecha de fin")
                return
            
            # Mostrar información del período seleccionado
            dias_seleccionados = (fecha_fin - fecha_inicio).days + 1
            st.info(f"📊 Período seleccionado: {dias_seleccionados} día(s)")
            
            # Botones rápidos para rangos predefinidos
            st.subheader("⚡ Rangos Rápidos")
            
            if st.button("📅 Último día"):
                fecha_inicio = fecha_fin = date_info['max_date']
                st.rerun()
            
            if st.button("📅 Últimos 7 días"):
                fecha_inicio = date_info['max_date'] - timedelta(days=6)
                fecha_fin = date_info['max_date']
                st.rerun()
            
            if st.button("📅 Últimos 30 días"):
                fecha_inicio = date_info['max_date'] - timedelta(days=29)
                fecha_fin = date_info['max_date']
                st.rerun()
            
            # Botón de actualización
            if st.button("🔄 Actualizar Datos"):
                st.cache_data.clear()
                st.rerun()
            
            # Información sobre configuración de tablas
            with st.expander("🗄️ Configuración de Tablas"):
                st.write("**Tablas actuales:**")
                for key, value in TABLE_CONFIG.items():
                    st.write(f"• {key}: `{value}`")
                st.info("Para cambiar los nombres de las tablas, modifica el diccionario TABLE_CONFIG en el código.")
                
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
    
    # Verificar si hay datos
    if df_trend.empty:
        st.warning(f"⚠️ No hay datos disponibles para el período {fecha_inicio} - {fecha_fin}")
        return
    
    # =============================================================================
    # 📅 1. PERÍODO ANALIZADO
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
    # 📈 2. RESUMEN DEL PERÍODO
    # =============================================================================
    
    st.header(f"📈 Resumen del Período")
    
    # Tarjetas de métricas principales
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
    # 📊 3. VER DATOS DETALLADOS
    # =============================================================================
    
    with st.expander("📊 Ver Datos Detallados"):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Tendencia Diaria", "Dispositivos", "Geografía", "Páginas", "Horas"])
        
        with tab1:
            if not df_trend.empty:
                st.subheader("📈 Datos de Tendencia Diaria")
                # Mostrar datos con nombres de columna consistentes
                display_df = df_trend.rename(columns={
                    'fecha_formateada': 'Fecha',
                    'activeUsers': 'Usuarios Activos',
                    'sessions': 'Sesiones',
                    'screenPageViews': 'Vistas de Página',
                    'bounceRate': 'Tasa de Rebote',
                    'averageSessionDuration': 'Duración Media de Sesión'
                })[['Fecha', 'Usuarios Activos', 'Sesiones', 'Vistas de Página', 'Tasa de Rebote', 'Duración Media de Sesión']]
                
                st.dataframe(display_df, use_container_width=True)
                
                # Opción de descarga
                csv = display_df.to_csv(index=False)
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
                display_df = df_devices.rename(columns={
                    'deviceCategory': 'Dispositivo',
                    'activeUsers': 'Usuarios Activos',
                    'sessions': 'Sesiones',
                    'screenPageViews': 'Páginas Vistas'
                })
                st.dataframe(display_df, use_container_width=True)
                
                # Opción de descarga
                csv = display_df.to_csv(index=False)
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
                display_df = df_geo.rename(columns={
                    'country': 'País',
                    'city': 'Ciudad',
                    'activeUsers': 'Usuarios Activos',
                    'sessions': 'Sesiones',
                    'screenPageViews': 'Páginas Vistas'
                })
                st.dataframe(display_df, use_container_width=True)
                
                # Opción de descarga
                csv = display_df.to_csv(index=False)
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
                display_df = df_pages.rename(columns={
                    'pagePath': 'Ruta de Página',
                    'pageTitle': 'Título de Página',
                    'screenPageViews': 'Visualizaciones',
                    'sessions': 'Sesiones',
                    'bounceRate': 'Tasa de Rebote',
                    'averageSessionDuration': 'Duración Media'
                })
                st.dataframe(display_df, use_container_width=True)
                
                # Opción de descarga
                csv = display_df.to_csv(index=False)
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
                display_df = df_hourly.rename(columns={
                    'hour': 'Hora',
                    'activeUsers': 'Usuarios Activos',
                    'sessions': 'Sesiones',
                    'screenPageViews': 'Páginas Vistas'
                })
                st.dataframe(display_df, use_container_width=True)
                
                # Opción de descarga
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar datos horarios (CSV)",
                    data=csv,
                    file_name=f'horarios_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv'
                )
            else:
                st.info("No hay datos horarios")

    st.markdown("---")
    
    # =============================================================================
    # 📄 4. PÁGINAS MÁS VISITADAS
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
            pages_display = df_pages[['pagePath', 'screenPageViews', 'sessions', 'bounceRate']].copy()
            pages_display.columns = ['Página', 'Vistas', 'Sesiones', 'Rebote']
            pages_display['Rebote'] = pages_display['Rebote'].apply(lambda x: f"{x:.1%}")
            st.dataframe(pages_display.head(10), use_container_width=True)
    else:
        st.warning("⚠️ No hay datos de páginas disponibles")
    
    st.markdown("---")
    
    # =============================================================================
    # 📱 5. ANÁLISIS POR DISPOSITIVOS
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
    # 📈 6. TENDENCIA DIARIA
    # =============================================================================
    
    # Gráfico de tendencia diaria
    if not df_trend.empty and dias_seleccionados > 1:
        st.header("📈 Tendencia Diaria")
        trend_chart = create_daily_trend_chart(df_trend)
        if trend_chart:
            st.plotly_chart(trend_chart, use_container_width=True)
    
    st.markdown("---")
    
    # =============================================================================
    # 🌍 7. ANÁLISIS GEOGRÁFICO
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
    # ⏰ 8. ANÁLISIS POR HORAS
    # =============================================================================
    
    st.header("⏰ Actividad por Hora")
    
    if not df_hourly.empty:
        hourly_chart = create_hourly_chart(df_hourly)
        if hourly_chart:
            st.plotly_chart(hourly_chart, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos horarios disponibles")

    # =============================================================================
    # 📋 9. RESUMEN COMPARATIVO (NUEVA SECCIÓN)
    # =============================================================================
    
    st.markdown("---")
    st.header("📋 Resumen Comparativo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Métricas Calculadas")
        if not df_trend.empty and total_sessions > 0:
            # Calcular métricas derivadas
            paginas_por_sesion = total_pageviews / total_sessions
            usuarios_por_sesion = total_users / total_sessions
            sesiones_por_usuario = total_sessions / total_users
            
            metrics_data = {
                'Métrica': [
                    'Páginas por Sesión',
                    'Usuarios por Sesión', 
                    'Sesiones por Usuario',
                    'Duración Media (seg)',
                    'Tasa de Rebote Media'
                ],
                'Valor': [
                    f"{paginas_por_sesion:.2f}",
                    f"{usuarios_por_sesion:.2f}",
                    f"{sesiones_por_usuario:.2f}",
                    f"{df_trend['averageSessionDuration'].mean():.0f}",
                    f"{avg_bounce_rate:.1%}"
                ]
            }
            
            metrics_df = pd.DataFrame(metrics_data)
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🏆 Top Performers")
        
        # Top dispositivo
        if not df_devices.empty:
            top_device = df_devices.loc[df_devices['activeUsers'].idxmax()]
            st.metric(
                "📱 Dispositivo Principal", 
                top_device['deviceCategory'],
                f"{top_device['activeUsers']:,} usuarios"
            )
        
        # Top país
        if not df_geo.empty:
            geo_by_country = df_geo.groupby('country')['activeUsers'].sum()
            top_country = geo_by_country.idxmax()
            top_country_users = geo_by_country.max()
            st.metric(
                "🌍 País Principal", 
                top_country,
                f"{top_country_users:,} usuarios"
            )
        
        # Top página
        if not df_pages.empty:
            top_page = df_pages.iloc[0]
            page_name = top_page['pagePath'][:30] + "..." if len(top_page['pagePath']) > 30 else top_page['pagePath']
            st.metric(
                "📄 Página Principal", 
                page_name,
                f"{top_page['screenPageViews']:,} vistas"
            )

# =============================================================================
# 🚀 EJECUTAR APLICACIÓN
# =============================================================================

if __name__ == "__main__":
    main_dashboard()