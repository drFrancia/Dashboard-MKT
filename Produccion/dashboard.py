import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, date
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
        AVG(bounceRate) AS "Tasa de Rebote", -- aca estamos trabajando
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
    """CORREGIDA - usando solo campos que existen"""
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
    LIMIT {limit}
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=300)
def get_traffic_sources_summary(_db, fecha_inicio, fecha_fin):
    """CORREGIDA - usando solo campos que existen"""
    sql = f"""
    SELECT 
        sourceMedium as "Medio",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones Totales",
        COUNT(*) as "Registros"
    FROM {TABLE_CONFIG['fuentes_trafico']} 
    WHERE fecha BETWEEN %s AND %s
    AND sourceMedium IS NOT NULL 
    AND sourceMedium != ''
    AND sourceMedium != '(not set)'
    GROUP BY sourceMedium
    ORDER BY SUM(sessions) DESC
    LIMIT 10
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=300)
def get_top_traffic_sources(_db, fecha_inicio, fecha_fin):
    """CORREGIDA - usando solo sourceMedium que es lo que tienes"""
    sql = f"""
    SELECT 
        sourceMedium as "Fuente",
        SUM(activeUsers) as "Usuarios Activos",
        SUM(sessions) as "Sesiones"
    FROM {TABLE_CONFIG['fuentes_trafico']} 
    WHERE fecha BETWEEN %s AND %s
    AND sourceMedium IS NOT NULL 
    AND sourceMedium != ''
    AND sourceMedium != '(not set)'
    GROUP BY sourceMedium
    ORDER BY SUM(sessions) DESC
    LIMIT 15
    """
    return _db.query(sql, params=(fecha_inicio, fecha_fin))

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
    
    # Título principal
    st.title("📊 GA4 Analytics Dashboard")
    st.markdown("---")
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("🔧 Configuración del Dashboard")
        
        # Obtener fechas disponibles (todas)
        available_dates = db.get_available_dates()
        available_dates = [d for d in available_dates if d < date.today()]  # excluir hoy
        
        if available_dates:
            st.success(f"📅 Datos disponibles: {len(available_dates)} días")

            st.subheader("📅 Filtro de Fechas")

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
                import datetime
                fechas_faltantes = []
                current_date = fecha_inicio
                while current_date <= fecha_fin:
                    if current_date not in dates_only:
                        fechas_faltantes.append(current_date)
                    current_date += datetime.timedelta(days=1)
                
                if fechas_faltantes:
                    with st.expander(f"⚠️ Ver {len(fechas_faltantes)} fecha(s) sin datos"):
                        for fecha in fechas_faltantes:
                            st.write(f"• {fecha.strftime('%Y-%m-%d')}")

            # Botones de acción mejorados
            st.markdown("### 🔧 Acciones Rápidas")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("🔄 Actualizar Datos", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
            
            with col_btn2:
                if st.button("📅 Últimos 7 días", use_container_width=True):
                    # Forzar recarga con últimos 7 días
                    st.session_state.fecha_inicio = default_start
                    st.session_state.fecha_fin = default_end
                    st.rerun()
        else:
            st.error("❌ No hay fechas disponibles en la base de datos")
            st.stop()

    
    # Obtener datos para el rango de fechas seleccionado
    with st.spinner("📊 Cargando datos del período seleccionado..."):
        df_trend = get_daily_trend_data(db, fecha_inicio, fecha_fin)
        df_devices = get_device_breakdown_range(db, fecha_inicio, fecha_fin)
        df_pages = get_top_pages_range(db, fecha_inicio, fecha_fin)
        df_geo = get_geographic_data_range(db, fecha_inicio, fecha_fin)
        df_hourly = get_hourly_data_range(db, fecha_inicio, fecha_fin)
        df_traffic_sources = get_traffic_sources_range(db, fecha_inicio, fecha_fin)
        df_search_terms = get_search_terms_range(db, fecha_inicio, fecha_fin)
        df_search_summary = get_search_terms_summary(db, fecha_inicio, fecha_fin)
    
    # Verificar si hay datos
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

    