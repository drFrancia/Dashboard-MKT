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


# Configuracion de la conexion.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Tu password de MySQL si lo tienes
    'database': 'analytics_datos',
    'port': 3306
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
            sql = """
            SELECT 
                MIN(fecha) as min_date, 
                MAX(fecha) as max_date,
                COUNT(DISTINCT fecha) as total_days
            FROM metricas_generales 
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


# Obtener resumen de las metricas@st.
@st.cache_data(ttl=300)
def get_metrics_by_date(_db, fecha):
    """Obtener métricas de un día específico"""
    sql = """
    SELECT 
        id,
        fecha,
        activeUsers,
        sessions,
        screenPageViews,
        bounceRate,
        averageSessionDuration,
        created_at,
        updated_at
    FROM metricas_generales
    WHERE fecha = %s
    """
    return _db.query(sql, params=(fecha,))

@st.cache_data(ttl=300)
def get_device_breakdown(_db, fecha):
    """Obtener distribución por dispositivos"""
    sql = """
    SELECT 
        fecha,
        deviceCategory,
        activeUsers,
        sessions,
        screenPageViews
    FROM dispositivos 
    WHERE fecha = %s
    GROUP BY deviceCategory
    """
    return _db.query(sql, params=(fecha,))


@st.cache_data(ttl=300)
def get_top_pages(_db, fecha):
    """Obtener páginas más visitadas"""
    sql = """
    SELECT 
        fecha,
        pagePath,
        pageTitle,
        screenPageViews,
        sessions,
        bounceRate,
        averageSessionDuration
    FROM paginas_top 
    WHERE fecha = %s
    """
    return _db.query(sql, params=(fecha,))

@st.cache_data(ttl=300)
def get_geographic_data(_db, fecha):
    """Obtener datos geográficos"""
    sql = """
    SELECT 
        fecha,
        country,
        city,
        activeUsers,
        sessions,
        screenPageViews
    FROM geografia 
    WHERE fecha = %s
    
    """
    return _db.query(sql, params=(fecha,))


@st.cache_data(ttl=300)
def get_hourly_data(_db, fecha):
    """Obtener datos por hora"""
    sql = """
    SELECT 
        fecha,
        hour,
        activeUsers,
        sessions,
        screenPageViews
    FROM datos_horarios 
    WHERE fecha = %s
    """
    return _db.query(sql, params=(fecha,))

# ____________________________________________________________________________
# 📈 FUNCIONES DE VISUALIZACIÓN AJUSTADAS
# =============================================================================

def create_daily_metrics_chart(df_metrics):
    """Crear gráfico de métricas diarias"""
    if df_metrics.empty:
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
            x=df_metrics['fecha'], 
            y=df_metrics['activeUsers'], 
            name='Usuarios Activos',
            line=dict(color='#3498db', width=3),
            hovertemplate='%{x}<br>Usuarios: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Sesiones
    fig.add_trace(
        go.Scatter(
            x=df_metrics['fecha'], 
            y=df_metrics['sessions'], 
            name='Sesiones',
            line=dict(color='#e74c3c', width=3),
            hovertemplate='%{x}<br>Sesiones: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # Páginas vistas
    fig.add_trace(
        go.Scatter(
            x=df_metrics['fecha'], 
            y=df_metrics['screenPageViews'], 
            name='Páginas Vistas',
            line=dict(color='#2ecc71', width=3),
            hovertemplate='%{x}<br>Páginas: %{y:,.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Tasa de rebote
    fig.add_trace(
        go.Scatter(
            x=df_metrics['fecha'], 
            y=df_metrics['bounceRate'], 
            name='Tasa de Rebote',
            line=dict(color='#f39c12', width=3),
            hovertemplate='%{x}<br>Rebote: %{y:.1%}<extra></extra>'
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        height=600, 
        showlegend=False,
        title_text="📈 Métricas del Día Seleccionado",
        title_x=0.5,
        font=dict(size=12)
    )
    
    return fig

def create_device_comparison(df_devices):
    """Crear gráfico de comparación de dispositivos"""
    if df_devices.empty:
        return None
    
    # Renombrar columnas para consistencia
    df_devices_clean = df_devices.rename(columns={
        'activeUsers': 'usuarios',
        'sessions': 'sesiones'
    })
    
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=('Distribución de Usuarios', 'Sesiones por Dispositivo')
    )
    
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
    
    # Pie chart
    fig.add_trace(
        go.Pie(
            labels=df_devices_clean['deviceCategory'], 
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
            x=df_devices_clean['deviceCategory'], 
            y=df_devices_clean['sesiones'],
            name="Sesiones",
            marker_color=colors[:len(df_devices_clean)],
            hovertemplate='%{x}<br>Sesiones: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=400,
        title_text="📱 Análisis por Tipo de Dispositivo",
        title_x=0.5
    )
    
    return fig

def create_geographic_chart(df_geo):
    """Crear visualización geográfica"""
    if df_geo.empty:
        return None
    
    # Renombrar columnas para consistencia
    df_geo_clean = df_geo.rename(columns={'activeUsers': 'usuarios'})
    
    # Top países
    df_countries = df_geo_clean.groupby('country')['usuarios'].sum().reset_index()
    df_countries = df_countries.sort_values('usuarios', ascending=True).tail(10)
    
    fig = px.bar(
        df_countries,
        x='usuarios',
        y='country',
        orientation='h',
        title="🌍 Top 10 Países por Usuarios",
        color='usuarios',
        color_continuous_scale='viridis',
        text='usuarios'
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
        'activeUsers': 'usuarios',
        'sessions': 'sesiones'
    })
    
    fig = px.line(
        df_hourly_clean,
        x='hour',
        y=['usuarios', 'sesiones'],
        title="📊 Actividad por Hora del Día",
        labels={'hour': 'Hora del Día', 'value': 'Cantidad'}
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
    df_pages_clean['tasa_rebote'] = df_pages_clean['bounceRate']
    df_pages_clean['visualizaciones'] = df_pages_clean['screenPageViews']
    df_pages_clean['duracion_promedio'] = df_pages_clean['averageSessionDuration']
    
    df_pages_top = df_pages_clean.head(15)
    
    fig = px.bar(
        df_pages_top,
        x='visualizaciones',
        y='pagePath',
        orientation='h',
        title="📄 Top 15 Páginas Más Visitadas",
        color='tasa_rebote',
        color_continuous_scale='RdYlGn_r',
        hover_data=['sessions', 'tasa_rebote', 'duracion_promedio']
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder':'total ascending'},
        yaxis_title="Página",
        xaxis_title="Visualizaciones"
    )
    
    return fig

def create_summary_metrics_cards(df_metrics):
    """Crear tarjetas de resumen de métricas"""
    if df_metrics.empty:
        return None, None, None, None
    
    # Sumar todas las métricas del período
    total_users = df_metrics['activeUsers'].sum()
    total_sessions = df_metrics['sessions'].sum()
    total_pageviews = df_metrics['screenPageViews'].sum()
    avg_bounce_rate = df_metrics['bounceRate'].mean()
    
    return total_users, total_sessions, total_pageviews, avg_bounce_rate

def create_comparison_table(df_devices):
    """Crear tabla de comparación de dispositivos"""
    if df_devices.empty:
        return pd.DataFrame()
    
    df_comparison = df_devices.copy()
    df_comparison['Usuarios por Sesión'] = (df_comparison['activeUsers'] / df_comparison['sessions']).round(2)
    df_comparison['Páginas por Sesión'] = (df_comparison['screenPageViews'] / df_comparison['sessions']).round(2)
    
    # Renombrar columnas para mejor presentación
    df_comparison = df_comparison.rename(columns={
        'deviceCategory': 'Dispositivo',
        'activeUsers': 'Usuarios Activos',
        'sessions': 'Sesiones',
        'screenPageViews': 'Páginas Vistas'
    })
    
    return df_comparison[['Dispositivo', 'Usuarios Activos', 'Sesiones', 'Páginas Vistas', 'Usuarios por Sesión', 'Páginas por Sesión']]

def create_geo_summary_table(df_geo):
    """Crear tabla resumen geográfica"""
    if df_geo.empty:
        return pd.DataFrame()
    
    df_geo_summary = df_geo.groupby('country').agg({
        'activeUsers': 'sum',
        'sessions': 'sum',
        'screenPageViews': 'sum'
    }).reset_index()
    
    df_geo_summary = df_geo_summary.sort_values('activeUsers', ascending=False).head(10)
    
    # Calcular métricas adicionales
    df_geo_summary['Páginas por Usuario'] = (df_geo_summary['screenPageViews'] / df_geo_summary['activeUsers']).round(2)
    df_geo_summary['Sesiones por Usuario'] = (df_geo_summary['sessions'] / df_geo_summary['activeUsers']).round(2)
    
    # Renombrar columnas
    df_geo_summary = df_geo_summary.rename(columns={
        'country': 'País',
        'activeUsers': 'Usuarios Activos',
        'sessions': 'Sesiones',
        'screenPageViews': 'Páginas Vistas'
    })
    
    return df_geo_summary

def format_number(num):
    """Formatear números para mejor visualización"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    else:
        return f"{num:.0f}"

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
    
    # Sidebar para selección de fecha
    with st.sidebar:
        st.header("🔧 Configuración")
        
        # Obtener rango de fechas disponibles
        date_info = db.get_date_range()
        
        if date_info:
            st.success(f"📅 Datos disponibles: {date_info['total_days']} días")
            
            # Selector de fecha
            selected_date = st.date_input(
                "Selecciona una fecha:",
                value=date_info['max_date'],
                min_value=date_info['min_date'],
                max_value=date_info['max_date']
            )
            
            # Botón de actualización
            if st.button("🔄 Actualizar Datos"):
                st.cache_data.clear()
                st.rerun()
                
        else:
            st.error("❌ No se pudo conectar a la base de datos")
            return
    
    # Obtener datos para la fecha seleccionada
    with st.spinner("📊 Cargando datos..."):
        df_metrics = get_metrics_by_date(db, selected_date)
        df_devices = get_device_breakdown(db, selected_date)
        df_pages = get_top_pages(db, selected_date)
        df_geo = get_geographic_data(db, selected_date)
        df_hourly = get_hourly_data(db, selected_date)
    
    # Verificar si hay datos
    if df_metrics.empty:
        st.warning(f"⚠️ No hay datos disponibles para {selected_date}")
        return
    
    # =============================================================================
    # 📈 SECCIÓN DE MÉTRICAS PRINCIPALES
    # =============================================================================
    
    st.header(f"📈 Métricas del {selected_date.strftime('%d/%m/%Y')}")
    
    # Tarjetas de métricas principales
    if not df_metrics.empty:
        row = df_metrics.iloc[0]  # Tomar la primera fila ya que es un día específico
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(create_metric_card_html(
                "Usuarios Activos", 
                format_number(row['activeUsers']), 
                "👥"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_metric_card_html(
                "Sesiones", 
                format_number(row['sessions']), 
                "📱"
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown(create_metric_card_html(
                "Páginas Vistas", 
                format_number(row['screenPageViews']), 
                "👀"
            ), unsafe_allow_html=True)
        
        with col4:
            st.markdown(create_metric_card_html(
                "Tasa de Rebote", 
                format_percentage(row['bounceRate']), 
                "⚡"
            ), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =============================================================================
    # 📱 ANÁLISIS POR DISPOSITIVOS
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
    # 🌍 ANÁLISIS GEOGRÁFICO
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
    # ⏰ ANÁLISIS POR HORAS
    # =============================================================================
    
    st.header("⏰ Actividad por Hora")
    
    if not df_hourly.empty:
        hourly_chart = create_hourly_chart(df_hourly)
        if hourly_chart:
            st.plotly_chart(hourly_chart, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos horarios disponibles")
    
    st.markdown("---")
    
    # =============================================================================
    # 📄 ANÁLISIS DE PÁGINAS
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
    
    # =============================================================================
    # 📊 SECCIÓN DE DATOS DETALLADOS
    # =============================================================================
    
    with st.expander("📊 Ver Datos Detallados"):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Métricas", "Dispositivos", "Geografía", "Páginas", "Horas"])
        
        with tab1:
            if not df_metrics.empty:
                st.dataframe(df_metrics, use_container_width=True)
            else:
                st.info("No hay datos de métricas")
        
        with tab2:
            if not df_devices.empty:
                st.dataframe(df_devices, use_container_width=True)
            else:
                st.info("No hay datos de dispositivos")
        
        with tab3:
            if not df_geo.empty:
                st.dataframe(df_geo, use_container_width=True)
            else:
                st.info("No hay datos geográficos")
        
        with tab4:
            if not df_pages.empty:
                st.dataframe(df_pages, use_container_width=True)
            else:
                st.info("No hay datos de páginas")
        
        with tab5:
            if not df_hourly.empty:
                st.dataframe(df_hourly, use_container_width=True)
            else:
                st.info("No hay datos horarios")

# =============================================================================
# 🚀 EJECUTAR APLICACIÓN
# =============================================================================

if __name__ == "__main__":
    main_dashboard()




# _____________________________________________________________________________
# # Crear instancia
# db = DatabaseConnection(DB_CONFIG)

# # Fecha a consultar
# fecha_consulta = '2025-08-02'

# # Obtener métricas
# df_metricas = get_metrics_by_date(db, fecha_consulta)
# df_devices = get_device_breakdown(db, fecha_consulta)
# df_pagesTop = get_top_pages(db, fecha_consulta)
# df_geografia = get_geographic_data(db, fecha_consulta)
# df_hora = get_hourly_data(db, fecha_consulta)

# # Mostrar en Streamlit
# st.write(df_metricas)
# st.write(df_devices)
# st.write(df_pagesTop)
# st.write(df_geografia)
# st.write(df_hora)