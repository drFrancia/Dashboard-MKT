import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import logging
from sqlalchemy import create_engine, text

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de la base de datos - ACTUALIZA AQUÍ
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'analytics_datos',
    'user': 'root',
    'password': ''
}

def create_connection():
    """Crear conexión a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Conectado a las {hora_actual}")
            return connection
    except Error as e:
        st.error(f"Error conectando a MySQL: {e}")
        return None


# =============================================================================
# FUNCIONES DE INSERCIÓN EXISTENTES
# =============================================================================

def insert_metricas_generales(connection, df, fecha):
    """Insertar datos de métricas generales"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO metricas_generales 
                (fecha, activeUsers, sessions, screenPageViews, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando métrica general: {e}")
    
    connection.commit()
    cursor.close()

def insert_dispositivos(connection, df, fecha):
    """Insertar datos de dispositivos - ACTUALIZADO con operatingSystem y browser"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO dispositivos 
                (fecha, deviceCategory, operatingSystem, browser, activeUsers, sessions, screenPageViews, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                str(row['deviceCategory']) if pd.notna(row['deviceCategory']) else '',
                str(row['operatingSystem']) if pd.notna(row['operatingSystem']) else '',
                str(row['browser']) if pd.notna(row['browser']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando dispositivo: {e}")
    
    connection.commit()
    cursor.close()

def insert_geografia(connection, df, fecha):
    """Insertar datos de geografía"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO geografia 
                (fecha, country, city, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                str(row['country']) if pd.notna(row['country']) else '',
                str(row['city']) if pd.notna(row['city']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando geografía: {e}")
    
    connection.commit()
    cursor.close()

def insert_paginas_top(connection, df, fecha):
    """Insertar datos de páginas top - ACTUALIZADO con bounceRate y sessions"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            # El Excel de paginas_top tiene: pagePath, pageTitle, screenPageViews, activeUsers, sessions, bounceRate, averageSessionDuration
            query = """
                INSERT IGNORE INTO paginas_top 
                (fecha, pagePath, pageTitle, screenPageViews, activeUsers, sessions, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                str(row['pagePath']) if pd.notna(row['pagePath']) else '',
                str(row['pageTitle']) if pd.notna(row['pageTitle']) else '',
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando página: {e}")
    
    connection.commit()
    cursor.close()

def insert_datos_horarios(connection, df, fecha):
    """Insertar datos horarios"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO datos_horarios 
                (fecha, hour, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                int(row['hour']) if pd.notna(row['hour']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando dato horario: {e}")
    
    connection.commit()
    cursor.close()

# =============================================================================
# NUEVAS FUNCIONES DE INSERCIÓN PARA TÉRMINOS DE BÚSQUEDA
# =============================================================================

def insert_terminos_busqueda(connection, df, fecha):
    """Insertar datos de términos de búsqueda"""
    cursor = connection.cursor()

    query = """
        INSERT IGNORE INTO terminos_busqueda 
        (fecha, searchTerm, sessions, activeUsers, screenPageViews, averageSessionDuration)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    for _, row in df.iterrows():
        values = (
            fecha,
            str(row['searchTerm']) if pd.notna(row['searchTerm']) else '',
            int(row['sessions']) if pd.notna(row['sessions']) else 0,
            int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
            int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
            float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
        )
        try:
            cursor.execute(query, values)
        except Exception as e:
            print(f"❌ Error insertando término {values}: {e}")

    connection.commit()
    cursor.close()

def insert_busqueda_interna(connection, df, fecha):
    """Insertar datos de búsqueda interna"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO busqueda_interna 
                (fecha, searchTerm, pagePath, sessions, activeUsers, screenPageViews, bounceRate)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                str(row['searchTerm']) if pd.notna(row['searchTerm']) else '',
                str(row['pagePath']) if pd.notna(row['pagePath']) else '',
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando búsqueda interna: {e}")
    
    connection.commit()
    cursor.close()

# Diccionario de traducciones de fuentes de tráfico
SOURCE_TRANSLATIONS = {
    "google / organic": "Tráfico orgánico desde Google",
    "(direct) / (none)": "Tráfico directo",
    "accounts.google.com / referral": "Referencia desde cuentas de Google",
    "(not set)": "Fuente desconocida",
    "google / cpc": "Publicidad pagada en Google (CPC)",
    "linktr.ee / referral": "Referencia desde Linktree",
    "bing / organic": "Tráfico orgánico desde Bing",
    "py.linktails.com / referral": "Referencia desde Linktails"
}

def insert_fuentes_trafico(connection, df, fecha):
    """Insertar datos de fuentes de tráfico - ACTUALIZADO con todas las columnas"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO fuentes_trafico 
                (fecha, sourceMedium, sessionSource, sessionMedium, activeUsers, sessions, 
                 screenPageViews, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            fuente = str(row['sourceMedium']) if pd.notna(row['sourceMedium']) else ''
            
            values = (
                fecha,
                fuente,  # sourceMedium combinada (para compatibilidad)
                str(row['sessionSource']) if pd.notna(row['sessionSource']) else '',
                str(row['sessionMedium']) if pd.notna(row['sessionMedium']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando fuente de tráfico: {e}")
    
    connection.commit()
    cursor.close()

def insert_utm_tracking(connection, df, fecha):
    """Insertar datos de seguimiento UTM - NUEVA FUNCIÓN"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO utm_tracking 
                (fecha, sessionSource, sessionMedium, sessionCampaignName, 
                 sessions, activeUsers, screenPageViews, bounceRate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                str(row['sessionSource']) if pd.notna(row['sessionSource']) else '',
                str(row['sessionMedium']) if pd.notna(row['sessionMedium']) else '',
                str(row['sessionCampaignName']) if pd.notna(row['sessionCampaignName']) else '',
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando UTM tracking: {e}")
    
    connection.commit()
    cursor.close()

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def get_latest_excel_file(folder_path):
    """Obtener el archivo Excel más reciente de la carpeta"""
    try:
        excel_files = [f for f in os.listdir(folder_path) if f.endswith(('.xlsx', '.xls'))]
        if not excel_files:
            return None
        
        latest_file = max(excel_files, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))
        return os.path.join(folder_path, latest_file)
    except Exception as e:
        st.error(f"Error buscando archivos: {e}")
        return None

# =============================================================================
# DASHBOARD PRINCIPAL
# =============================================================================

def main():
    st.set_page_config(
        page_title="Analytics Data Importer v2.1",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Analytics Data Importer v2.1")
    st.markdown("### Importa datos completos de GA4 incluyendo términos de búsqueda")
    st.markdown("---")
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Selector de carpeta
    folder_path = st.sidebar.text_input(
        "📁 Ruta de la carpeta con archivos Excel:",
        value="C:/downloads",
        help="Especifica la carpeta donde están los archivos Excel descargados"
    )
    
    # Selector de fecha
    target_date = st.sidebar.date_input(
        "📅 Fecha de los datos:",
        value=datetime.now().date(),
        help="Fecha que se asignará a los datos importados"
    )
    
    # Información de conexión
    with st.sidebar.expander("🔍 Info de Conexión DB"):
        st.code(f"""
        Host: {DB_CONFIG['host']}
        Puerto: {DB_CONFIG['port']}
        Base de datos: {DB_CONFIG['database']}
        Usuario: {DB_CONFIG['user']}
        """)
    
    # Información de tablas esperadas
    with st.sidebar.expander("📋 Tablas Esperadas"):
        st.markdown("""
        **Tablas que debe tener tu BD:**
        - `metricas_generales`
        - `dispositivos`
        - `geografia`  
        - `paginas_top`
        - `fuentes_trafico`
        - `terminos_busqueda`
        - `busqueda_interna`
        - `datos_horarios`
        """)
    
    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📄 Archivo Excel")
        
        if os.path.exists(folder_path):
            latest_file = get_latest_excel_file(folder_path)
            if latest_file:
                st.success(f"✅ Archivo más reciente encontrado:")
                st.code(latest_file)
                
                # Mostrar información del archivo
                file_stats = os.stat(latest_file)
                modification_time = datetime.fromtimestamp(file_stats.st_mtime)
                st.info(f"📅 Última modificación: {modification_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Mostrar hojas disponibles
                try:
                    excel_data = pd.read_excel(latest_file, sheet_name=None)
                    st.success(f"📋 Hojas encontradas: {len(excel_data)}")
                    
                    with st.expander("Ver hojas disponibles"):
                        for sheet_name, df in excel_data.items():
                            if sheet_name == 'metadata':
                                continue
                            records = len(df)
                            # Agregar emojis para las nuevas hojas
                            # emoji = "⭐" if sheet_name in ['terminos_busqueda', 'busqueda_interna'] else ""
                            st.write(f"**{sheet_name}**: {records} registros")
                except Exception as e:
                    st.warning(f"No se pudo leer el archivo: {e}")
                
            else:
                st.warning("⚠️ No se encontraron archivos Excel en la carpeta especificada")
                latest_file = None
        else:
            st.error("❌ La carpeta especificada no existe")
            latest_file = None
    
    with col2:
        st.subheader("🔄 Acciones")
        
        # Test de conexión
        if st.button("🔍 Probar Conexión DB", type="secondary"):
            with st.spinner("Probando conexión..."):
                connection = create_connection()
                if connection:
                    st.success("✅ Conexión exitosa!")
                    
                    # Verificar tablas existentes
                    cursor = connection.cursor()
                    cursor.execute("SHOW TABLES")
                    tables = [table[0] for table in cursor.fetchall()]
                    cursor.close()
                    
                    st.info(f"📋 Tablas encontradas: {len(tables)}")
                    
                    # Verificar tablas requeridas
                    required_tables = [
                        'metricas_generales', 'dispositivos', 'geografia', 
                        'paginas_top', 'fuentes_trafico', 'terminos_busqueda', 
                        'busqueda_interna', 'datos_horarios', 'utm_tracking'
                    ]
                    
                    with st.expander("Ver estado de tablas"):
                        for table in required_tables:
                            if table in tables:
                                # emoji = "⭐" if table in ['terminos_busqueda', 'busqueda_interna'] else ""
                                st.write(f"✅ {table}")
                            else:
                                st.write(f"❌ {table} (FALTA)")
                    
                    connection.close()
                else:
                    st.error("❌ Error de conexión")
        
        st.markdown("---")
        
        
        # Botón principal de importación
        if st.button("📥 Importar Todos los Datos", type="primary", disabled=latest_file is None):
            if latest_file:
                import_data(latest_file, target_date)

def import_data(excel_file, target_date):
    """Función principal para importar datos - ACTUALIZADA"""
    try:
        with st.spinner("🔄 Procesando archivo Excel..."):
            # Leer todas las hojas del Excel
            excel_data_raw = pd.read_excel(excel_file, sheet_name=None)
            
            # DEBUG: Mostrar hojas encontradas
            with st.expander("📄 DEBUG: Hojas encontradas en Excel", expanded=True):
                for i, sheet_name in enumerate(excel_data_raw.keys(), 1):
                    st.write(f"{i}. `{sheet_name}` ({len(excel_data_raw[sheet_name])} registros)")
            
            # Mapeo de nombres de hojas (acepta ambos formatos: español con mayúsculas y minúsculas)
            sheet_mapping = {
                # Formato con mayúsculas y acentos (Colab antiguo)
                'Métricas Básicas': 'metricas_generales',
                'Usuarios por Dispositivo': 'dispositivos',
                'Fuentes de Tráfico': 'fuentes_trafico',
                'Datos Geográficos': 'geografia',
                'Rendimiento de Páginas': 'paginas_top',
                'Términos de Búsqueda': 'terminos_busqueda',
                'Búsqueda Interna': 'busqueda_interna',
                'Datos por Hora': 'datos_horarios',
                'Seguimiento UTM': 'utm_tracking',
                # Formato directo en minúsculas (Colab actual)
                'metricas_generales': 'metricas_generales',
                'dispositivos': 'dispositivos',
                'fuentes_trafico': 'fuentes_trafico',
                'geografia': 'geografia',
                'paginas_top': 'paginas_top',
                'terminos_busqueda': 'terminos_busqueda',
                'busqueda_interna': 'busqueda_interna',
                'datos_horarios': 'datos_horarios',
                'utm_tracking': 'utm_tracking'
            }
            
            # Convertir nombres de hojas al formato esperado
            excel_data = {}
            mapped_count = 0
            
            with st.expander("🔄 DEBUG: Proceso de mapeo", expanded=True):
                for spanish_name, english_name in sheet_mapping.items():
                    if spanish_name in excel_data_raw:
                        excel_data[english_name] = excel_data_raw[spanish_name]
                        mapped_count += 1
                        st.success(f"✅ '{spanish_name}' → '{english_name}' ({len(excel_data_raw[spanish_name])} registros)")
                    else:
                        st.error(f"❌ '{spanish_name}' NO ENCONTRADA en el Excel")
                
                # También incluir hojas que ya tengan nombre en inglés (por compatibilidad)
                for sheet_name, df in excel_data_raw.items():
                    if sheet_name not in sheet_mapping.keys() and sheet_name not in ['metadata', 'resumen']:
                        excel_data[sheet_name] = df
                        st.info(f"ℹ️ Hoja '{sheet_name}' incluida tal cual ({len(df)} registros)")
                
                st.info(f"📊 Total hojas mapeadas: {mapped_count}/{len(sheet_mapping)}")
            
            # Crear conexión
            connection = create_connection()
            if not connection:
                st.error("❌ No se pudo conectar a la base de datos")
                return
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = {
                'metricas_generales': 0,
                'dispositivos': 0,
                'geografia': 0,
                'paginas_top': 0,
                'fuentes_trafico': 0,
                'terminos_busqueda': 0,      # NUEVO
                'busqueda_interna': 0,       # NUEVO
                'datos_horarios': 0,
                'utm_tracking': 0,           # NUEVO - Seguimiento UTM
                'errores': []
            }
            
            # Mapeo de funciones de inserción - ACTUALIZADO
            insert_functions = {
                'metricas_generales': insert_metricas_generales,
                'dispositivos': insert_dispositivos,
                'geografia': insert_geografia,
                'paginas_top': insert_paginas_top,
                'fuentes_trafico': insert_fuentes_trafico,
                'terminos_busqueda': insert_terminos_busqueda,      # NUEVO
                'busqueda_interna': insert_busqueda_interna,        # NUEVO
                'datos_horarios': insert_datos_horarios,
                'utm_tracking': insert_utm_tracking                 # NUEVO - Seguimiento UTM
            }
            
            # Procesar cada hoja
            sheets_to_process = list(insert_functions.keys())
            
            for i, sheet_name in enumerate(sheets_to_process):
                if sheet_name in excel_data:
                    status_text.text(f"Procesando {sheet_name}...")
                    df = excel_data[sheet_name]
                    
                    if not df.empty:
                        try:
                            insert_functions[sheet_name](connection, df, target_date)
                            results[sheet_name] = len(df)
                            
                            # Emoji especial para las nuevas tablas
                            emoji = "✅" if sheet_name in ['terminos_busqueda', 'busqueda_interna'] else "✅"
                            st.success(f"{emoji} {sheet_name}: {len(df)} registros procesados")
                        except Exception as e:
                            error_msg = f"{sheet_name}: {str(e)}"
                            results['errores'].append(error_msg)
                            st.error(f"❌ {error_msg}")
                            logging.error(f"Error procesando {sheet_name}: {e}")
                    else:
                        st.warning(f"⚠️ {sheet_name}: Sin datos para procesar")
                    
                    progress_bar.progress((i + 1) / len(sheets_to_process))
                else:
                    # ⚠️ Advertencia menos severa - no detiene el proceso
                    warning_msg = f"Hoja '{sheet_name}' no encontrada en el Excel (OMITIDA)"
                    results['errores'].append(warning_msg)
                    st.info(f"ℹ️ {warning_msg}")
                    progress_bar.progress((i + 1) / len(sheets_to_process))
            
            connection.close()
            status_text.text("✅ Proceso completado!")
            
            # Mostrar resultados
            st.balloons()
            st.success("🎉 Importación completada con todas las métricas!")
            
            # Métricas de resultados - ACTUALIZADO con utm_tracking
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Métricas Generales", results['metricas_generales'])
                st.metric("📱 Dispositivos", results['dispositivos'])
            
            with col2:
                st.metric("🌍 Geografía", results['geografia'])
                st.metric("📄 Páginas Top", results['paginas_top'])
            
            with col3:
                st.metric("🚀 Fuentes Tráfico", results['fuentes_trafico'])
                st.metric("🕐 Datos Horarios", results['datos_horarios'])
            
            with col4:
                st.metric("🔍 Términos Búsqueda", results['terminos_busqueda'])
                st.metric("🔍 Búsqueda Interna", results['busqueda_interna'])
            
            # Mostrar utm_tracking por separado si tiene datos
            if results['utm_tracking'] > 0:
                st.metric("🎯 UTM Tracking (NUEVO)", results['utm_tracking'])
            
            # Mostrar advertencias/errores si los hay
            if results['errores']:
                with st.expander("⚠️ Advertencias y Errores", expanded=False):
                    for error in results['errores']:
                        if "no encontrada" in error.lower() or "omitida" in error.lower():
                            st.info(error)
                        else:
                            st.warning(error)
            
            # Información adicional
            total_records = sum([v for k, v in results.items() if k != 'errores'])
            st.info(f"""
            **📈 Resumen de Importación v3.0:**
            • **Fecha asignada:** {target_date}
            • **Total registros:** {total_records:,}
            • **Tablas completas:** 9 datasets (incluye UTM Tracking)
            • **Fuentes tráfico:** Ahora con 9 columnas completas
            • **Tiempo:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """)
            
    except Exception as e:
        st.error(f"❌ Error durante la importación: {str(e)}")
        logging.error(f"Error en import_data: {e}")

if __name__ == "__main__":
    main()