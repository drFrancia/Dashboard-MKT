# =============================================================================
# 📊 GA4 ANALYTICS DASHBOARD - VERSIÓN CORREGIDA
# =============================================================================
# Ejecutar con: streamlit run dashboard_db.py
# Requiere: pip install streamlit pandas plotly pymysql sqlalchemy
# =============================================================================

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
# 🔧 CONFIGURACIÓN DE BASE DE DATOS
# =============================================================================

# ⚠️ ACTUALIZA ESTA CONFIGURACIÓN CON TUS DATOS DE WAMP
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Tu password de MySQL si lo tienes
    'database': 'analytics_datos',
    'port': 3306
}

# =============================================================================
# 🎨 CONFIGURACIÓN DE STREAMLIT
# =============================================================================

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

# =============================================================================
# 🗄️ CLASE DE CONEXIÓN A BASE DE DATOS
# =============================================================================

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
            
            # Test de conexión
            with self.engine.connect() as conn:
                conn.execute(text("SELECT * FROM pruebas LIMIT 1"))
            
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

# =============================================================================
# 📊 FUNCIONES DE CONSULTAS ESPECÍFICAS - CORREGIDAS
# =============================================================================

@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_metrics_summary(_db, fecha_inicio, fecha_fin):
    """Obtener resumen de métricas principales"""
    sql = """
    SELECT 
        SUM(activeUsers) as total_usuarios,
        SUM(sessions) as total_sesiones,
        SUM(screenPageViews) as total_visualizaciones,
        AVG(bounceRate) as promedio_rebote,
        AVG(averageSessionDuration) as promedio_duracion,
        COUNT(DISTINCT fecha) as dias_datos
    FROM metricas_generales 
    WHERE fecha BETWEEN %s AND %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_daily_trend(_db, fecha_inicio, fecha_fin):
    """Obtener tendencia diaria"""
    sql = """
    SELECT 
        fecha,
        activeUsers,
        sessions,
        screenPageViews,
        bounceRate,
        averageSessionDuration
    FROM metricas_generales 
    WHERE fecha BETWEEN %s AND %s
    ORDER BY fecha
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_device_breakdown(_db, fecha_inicio, fecha_fin):
    """Obtener distribución por dispositivos"""
    sql = """
    SELECT 
        deviceCategory,
        SUM(activeUsers) as usuarios,
        SUM(sessions) as sesiones,
        SUM(screenPageViews) as visualizaciones,
        ROUND(AVG(activeUsers), 0) as promedio_diario
    FROM dispositivos 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY deviceCategory
    ORDER BY usuarios DESC
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

@st.cache_data(ttl=300)
def get_top_pages(_db, fecha_inicio, fecha_fin, limit=20):
    """Obtener páginas más visitadas"""
    sql = """
    SELECT 
        pagePath,
        pageTitle,
        SUM(screenPageViews) as visualizaciones,
        SUM(sessions) as sesiones,
        AVG(bounceRate) as tasa_rebote,
        AVG(averageSessionDuration) as duracion_promedio
    FROM paginas_top 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY pagePath, pageTitle
    ORDER BY visualizaciones DESC
    LIMIT %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin, limit))

@st.cache_data(ttl=300)
def get_geographic_data(_db, fecha_inicio, fecha_fin, limit=30):
    """Obtener datos geográficos"""
    sql = """
    SELECT 
        country,
        city,
        SUM(activeUsers) as usuarios,
        SUM(sessions) as sesiones,
        SUM(screenPageViews) as visualizaciones
    FROM geografia 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY country, city
    ORDER BY usuarios DESC
    LIMIT %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin, limit))

@st.cache_data(ttl=300)
def get_marketing_channels(_db, fecha_inicio, fecha_fin, limit=20):
    """Obtener canales de marketing"""
    sql = """
    SELECT 
        channelGrouping,
        sourceMedium,
        campaignName,
        SUM(activeUsers) as usuarios,
        SUM(sessions) as sesiones,
        SUM(screenPageViews) as visualizaciones,
        AVG(bounceRate) as tasa_rebote,
        AVG(averageSessionDuration) as duracion_promedio
    FROM canales_marketing 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY channelGrouping, sourceMedium, campaignName
    ORDER BY usuarios DESC
    LIMIT %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin, limit))

@st.cache_data(ttl=300)
def get_search_terms(_db, fecha_inicio, fecha_fin, limit=20):
    """Obtener términos de búsqueda"""
    sql = """
    SELECT 
        searchTerm,
        landingPage,
        SUM(activeUsers) as usuarios,
        SUM(sessions) as sesiones,
        SUM(screenPageViews) as visualizaciones
    FROM palabras_clave 
    WHERE fecha BETWEEN %s AND %s 
    AND searchTerm != '(not set)'
    AND searchTerm != ''
    GROUP BY searchTerm, landingPage
    ORDER BY usuarios DESC
    LIMIT %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin, limit))

@st.cache_data(ttl=300)
def get_custom_events(_db, fecha_inicio, fecha_fin, limit=15):
    """Obtener eventos personalizados"""
    sql = """
    SELECT 
        eventName,
        SUM(eventCount) as total_eventos,
        SUM(uniqueEvents) as eventos_unicos,
        SUM(totalUsers) as usuarios_totales,
        AVG(eventCount) as promedio_diario
    FROM eventos_personalizados 
    WHERE fecha BETWEEN %s AND %s
    GROUP BY eventName
    ORDER BY total_eventos DESC
    LIMIT %s
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin, limit))

# =============================================================================
# 📈 FUNCIONES DE VISUALIZACIÓN
# =============================================================================

def create_trend_chart(df_trend):
    """Crear gráfico de tendencias mejorado"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('👥 Usuarios Activos', '📱 Sesiones', '👀 Páginas Vistas', '⚡ Tasa de Rebote'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": True}]]
    )
    
    # Usuarios activos
    fig.add_trace(
        go.Scatter(
            x=df_trend['fecha'], 
            y=df_trend['activeUsers'], 
            name='Usuarios Activos',
            line=dict(color='#3498db', width=3),
            hovertemplate='%{x}<br>Usuarios: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Sesiones
    fig.add_trace(
        go.Scatter(
            x=df_trend['fecha'], 
            y=df_trend['sessions'], 
            name='Sesiones',
            line=dict(color='#e74c3c', width=3),
            hovertemplate='%{x}<br>Sesiones: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # Páginas vistas
    fig.add_trace(
        go.Scatter(
            x=df_trend['fecha'], 
            y=df_trend['screenPageViews'], 
            name='Páginas Vistas',
            line=dict(color='#2ecc71', width=3),
            hovertemplate='%{x}<br>Páginas: %{y:,.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Tasa de rebote
    fig.add_trace(
        go.Scatter(
            x=df_trend['fecha'], 
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
        title_text="📈 Tendencias Diarias de Métricas Principales",
        title_x=0.5,
        font=dict(size=12)
    )
    
    return fig

def create_device_comparison(df_devices):
    """Crear gráfico de comparación de dispositivos"""
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
            values=df_devices['usuarios'],
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
            y=df_devices['sesiones'],
            name="Sesiones",
            marker_color=colors[:len(df_devices)],
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
    # Top países
    df_countries = df_geo.groupby('country')['usuarios'].sum().reset_index()
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

def create_pages_performance_chart(df_pages):
    """Crear gráfico de rendimiento de páginas"""
    df_pages_top = df_pages.head(15)
    
    fig = px.bar(
        df_pages_top,
        x='visualizaciones',
        y='pagePath',
        orientation='h',
        title="📄 Top 15 Páginas Más Visitadas",
        color='tasa_rebote',
        color_continuous_scale='RdYlGn_r',
        hover_data=['sesiones', 'tasa_rebote', 'duracion_promedio']
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder':'total ascending'},
        yaxis_title="Página",
        xaxis_title="Visualizaciones"
    )
    
    return fig

def create_marketing_channels_chart(df_marketing):
    """Crear gráfico de canales de marketing"""
    df_marketing_top = df_marketing.head(10)
    
    fig = px.treemap(
        df_marketing_top,
        path=['channelGrouping', 'sourceMedium'],
        values='usuarios',
        color='tasa_rebote',
        color_continuous_scale='RdYlGn_r',
        title="🚀 Canales de Marketing - Usuarios y Tasa de Rebote"
    )
    
    fig.update_layout(height=500)
    return fig

# =============================================================================
# 🎛️ FUNCIONES DE COMPARACIÓN DE PERÍODOS
# =============================================================================

def compare_periods(_db, fecha_inicio_1, fecha_fin_1, fecha_inicio_2, fecha_fin_2):
    """Comparar dos períodos"""
    
    # Período 1
    metrics_1 = get_metrics_summary(_db, fecha_inicio_1, fecha_fin_1)
    # Período 2  
    metrics_2 = get_metrics_summary(_db, fecha_inicio_2, fecha_fin_2)
    
    if metrics_1.empty or metrics_2.empty:
        return None, None
    
    # Calcular cambios porcentuales
    comparison = {}
    
    for col in ['total_usuarios', 'total_sesiones', 'total_visualizaciones']:
        val_1 = metrics_1[col].iloc[0] if not metrics_1.empty else 0
        val_2 = metrics_2[col].iloc[0] if not metrics_2.empty else 0
        
        if val_2 > 0:
            change = ((val_1 - val_2) / val_2) * 100
        else:
            change = 0
            
        comparison[col] = {
            'actual': val_1,
            'anterior': val_2,
            'cambio': change
        }
    
    return metrics_1, comparison

# =============================================================================
# 🖥️ INTERFAZ PRINCIPAL DEL DASHBOARD
# =============================================================================

def main():
    """Función principal del dashboard"""
    
    # Header principal
    st.title("📊 Google Analytics 4 Dashboard")
    st.markdown("### 🎯 Dashboard Avanzado con Conexión Directa a Base de Datos")
    
    # Inicializar conexión a BD
    try:
        db = DatabaseConnection(DB_CONFIG)
        if db.engine is None:
            st.stop()
    except Exception as e:
        st.error(f"❌ Error inicializando base de datos: {e}")
        st.stop()
    
    # Obtener rango de fechas disponibles
    date_info = db.get_date_range()
    
    if not date_info:
        st.warning("⚠️ No se encontraron datos en la base de datos")
        st.info("📄 Ejecuta primero el script de importación para cargar datos")
        st.stop()
    
    # =============================================================================
    # 🔧 SIDEBAR - CONTROLES DE FILTRADO
    # =============================================================================
    
    st.sidebar.header("🎛️ Panel de Control")
    st.sidebar.markdown("---")
    
    # Información de datos disponibles
    st.sidebar.subheader("📅 Datos Disponibles")
    st.sidebar.info(f"""
    **Desde:** {date_info['min_date']}\n
    **Hasta:** {date_info['max_date']}\n
    **Total días:** {date_info['total_days']:,}
    """)
    
    st.sidebar.markdown("---")
    
    # Selector de tipo de análisis
    analysis_type = st.sidebar.selectbox(
        "📊 Tipo de Análisis",
        ["📈 Análisis Simple", "🔄 Comparación de Períodos"]
    )
    
    # Filtros de fecha
    st.sidebar.subheader("📅 Rango de Fechas")
    
    # Filtros predefinidos
    quick_filters = st.sidebar.selectbox(
        "⚡ Filtros Rápidos",
        ["🎯 Personalizado", "📅 Últimos 7 días", "📅 Últimos 15 días", "📅 Últimos 30 días"]
    )
    
    # Configurar fechas según filtro
    max_date = date_info['max_date']
    min_date = date_info['min_date']
    
    if quick_filters == "📅 Últimos 7 días":
        fecha_fin = max_date
        fecha_inicio = max_date - timedelta(days=6)
    elif quick_filters == "📅 Últimos 15 días":
        fecha_fin = max_date
        fecha_inicio = max_date - timedelta(days=14)
    elif quick_filters == "📅 Últimos 30 días":
        fecha_fin = max_date
        fecha_inicio = max_date - timedelta(days=29)
    else:
        # Selector personalizado
        col1, col2 = st.sidebar.columns(2)
        with col1:
            fecha_inicio = st.date_input("Desde", min_date, min_value=min_date, max_value=max_date)
        with col2:
            fecha_fin = st.date_input("Hasta", max_date, min_value=min_date, max_value=max_date)
    
    # Configuración adicional
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Configuración")
    
    max_records = st.sidebar.slider("📊 Máx. registros en tablas", 10, 100, 20, 5)
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (cada 5 min)", False)
    
    # Botón de actualización manual
    if st.sidebar.button("🔄 Actualizar Datos", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # =============================================================================
    # 📊 CONTENIDO PRINCIPAL
    # =============================================================================
    
    if analysis_type == "📈 Análisis Simple":
        
        # Métricas principales
        st.subheader("📊 Métricas Principales")
        metrics_data = get_metrics_summary(db, fecha_inicio, fecha_fin)
        
        if not metrics_data.empty:
            metrics = metrics_data.iloc[0]
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "👥 Usuarios Activos", 
                    f"{int(metrics['total_usuarios']):,}",
                    help="Total de usuarios únicos en el período"
                )
            
            with col2:
                st.metric(
                    "📱 Sesiones", 
                    f"{int(metrics['total_sesiones']):,}",
                    help="Total de sesiones iniciadas"
                )
            
            with col3:
                st.metric(
                    "👀 Páginas Vistas", 
                    f"{int(metrics['total_visualizaciones']):,}",
                    help="Total de páginas visualizadas"
                )
            
            with col4:
                st.metric(
                    "⚡ Tasa de Rebote", 
                    f"{metrics['promedio_rebote']:.1%}",
                    help="Porcentaje promedio de sesiones con una sola página"
                )
            
            with col5:
                duracion = metrics['promedio_duracion']
                minutos = int(duracion // 60)
                segundos = int(duracion % 60)
                st.metric(
                    "⏱️ Duración Media", 
                    f"{minutos}m {segundos}s",
                    help="Tiempo promedio de sesión"
                )
        
        st.markdown("---")
        
        # Tendencias diarias
        st.subheader("📈 Tendencias Diarias")
        trend_data = get_daily_trend(db, fecha_inicio, fecha_fin)
        
        if not trend_data.empty:
            fig_trend = create_trend_chart(trend_data)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("No hay datos de tendencias para el período seleccionado")
        
        # Layout en dos columnas para el resto de gráficos
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Análisis por dispositivos
            st.subheader("📱 Análisis por Dispositivo")
            device_data = get_device_breakdown(db, fecha_inicio, fecha_fin)
            
            if not device_data.empty:
                fig_devices = create_device_comparison(device_data)
                st.plotly_chart(fig_devices, use_container_width=True)
                
                # Tabla de dispositivos
                st.dataframe(
                    device_data,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("No hay datos de dispositivos")
        
        with col_right:
            # Distribución geográfica
            st.subheader("🌍 Distribución Geográfica")
            geo_data = get_geographic_data(db, fecha_inicio, fecha_fin, max_records)
            
            if not geo_data.empty:
                fig_geo = create_geographic_chart(geo_data)
                st.plotly_chart(fig_geo, use_container_width=True)
                
                # Tabla geográfica
                st.dataframe(
                    geo_data.head(10),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("No hay datos geográficos")
        
        # Páginas más visitadas
        st.subheader("📄 Páginas Más Visitadas")
        pages_data = get_top_pages(db, fecha_inicio, fecha_fin, max_records)
        
        if not pages_data.empty:
            fig_pages = create_pages_performance_chart(pages_data)
            st.plotly_chart(fig_pages, use_container_width=True)
            
            # Tabla de páginas
            st.dataframe(
                pages_data,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No hay datos de páginas")
        
        # Canales de marketing
        st.subheader("🚀 Canales de Marketing")
        marketing_data = get_marketing_channels(db, fecha_inicio, fecha_fin, max_records)
        
        if not marketing_data.empty:
            fig_marketing = create_marketing_channels_chart(marketing_data)
            st.plotly_chart(fig_marketing, use_container_width=True)
            
            # Tabla de canales
            st.dataframe(
                marketing_data,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No hay datos de canales de marketing")
        
        # Layout para términos de búsqueda y eventos
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Términos de búsqueda
            st.subheader("🔍 Términos de Búsqueda")
            search_data = get_search_terms(db, fecha_inicio, fecha_fin, max_records//2)
            
            if not search_data.empty:
                st.dataframe(
                    search_data,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay términos de búsqueda disponibles para este período")
        
        with col_right:
            # Eventos personalizados
            st.subheader("⚡ Eventos Personalizados")
            events_data = get_custom_events(db, fecha_inicio, fecha_fin, max_records//2)
            
            if not events_data.empty:
                st.dataframe(
                    events_data,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay eventos personalizados para este período")
    
    # =============================================================================
    # 🔄 COMPARACIÓN DE PERÍODOS
    # =============================================================================
    
    elif analysis_type == "🔄 Comparación de Períodos":
        st.subheader("🔄 Comparación de Períodos")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 📅 Período Actual")
            fecha_inicio_1 = fecha_inicio
            fecha_fin_1 = fecha_fin
            st.info(f"Desde: {fecha_inicio_1}\nHasta: {fecha_fin_1}")
        
        with col_right:
            st.markdown("#### 📅 Período de Comparación")
            # Calcular período anterior automáticamente
            days_diff = (fecha_fin_1 - fecha_inicio_1).days + 1
            fecha_fin_2 = fecha_inicio_1 - timedelta(days=1)
            fecha_inicio_2 = fecha_fin_2 - timedelta(days=days_diff - 1)
            
            st.info(f"Desde: {fecha_inicio_2}\nHasta: {fecha_fin_2}")
            st.caption(f"Comparando con {days_diff} días anteriores")
        
        # Obtener datos de comparación
        metrics_actual, comparison = compare_periods(db, fecha_inicio_1, fecha_fin_1, fecha_inicio_2, fecha_fin_2)
        
        if metrics_actual is not None and comparison is not None:
            st.markdown("---")
            st.subheader("📊 Comparación de Métricas")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                usuarios_cambio = comparison['total_usuarios']['cambio']
                delta_color = "normal" if usuarios_cambio >= 0 else "inverse"
                st.metric(
                    "👥 Usuarios Activos",
                    f"{int(comparison['total_usuarios']['actual']):,}",
                    f"{usuarios_cambio:+.1f}%",
                    delta_color=delta_color
                )
            
            with col2:
                sesiones_cambio = comparison['total_sesiones']['cambio']
                delta_color = "normal" if sesiones_cambio >= 0 else "inverse"
                st.metric(
                    "📱 Sesiones",
                    f"{int(comparison['total_sesiones']['actual']):,}",
                    f"{sesiones_cambio:+.1f}%",
                    delta_color=delta_color
                )
            
            with col3:
                vistas_cambio = comparison['total_visualizaciones']['cambio']
                delta_color = "normal" if vistas_cambio >= 0 else "inverse"
                st.metric(
                    "👀 Páginas Vistas",
                    f"{int(comparison['total_visualizaciones']['actual']):,}",
                    f"{vistas_cambio:+.1f}%",
                    delta_color=delta_color
                )
        
        else:
            st.warning("No hay suficientes datos para la comparación")


# =============================================================================
# 🎯 EJECUCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    main()