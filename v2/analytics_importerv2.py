# =============================================================================
# 📊 ANALYTICS DATA IMPORTER - VERSIÓN CORREGIDA
# =============================================================================
# Compatible con el schema corregido de analytics_datos
# =============================================================================

import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de la base de datos
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
            return connection
    except Error as e:
        st.error(f"Error conectando a MySQL: {e}")
        return None

def create_tables(connection):
    """Crear las tablas necesarias si no existen - VERSIÓN CORREGIDA"""
    cursor = connection.cursor()
    
    # Tabla para métricas generales
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metricas_generales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            activeUsers INT DEFAULT 0,
            sessions INT DEFAULT 0,
            screenPageViews INT DEFAULT 0,
            bounceRate DECIMAL(5,4) DEFAULT 0.0000,
            averageSessionDuration DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha (fecha)
        )
    """)
    
    # Tabla para dispositivos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispositivos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            deviceCategory VARCHAR(50) NOT NULL,
            activeUsers INT DEFAULT 0,
            sessions INT DEFAULT 0,
            screenPageViews INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha_device (fecha, deviceCategory)
        )
    """)
    
    # Tabla para geografía
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geografia (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            country VARCHAR(100) DEFAULT '',
            city VARCHAR(150) DEFAULT '',
            activeUsers INT DEFAULT 0,
            sessions INT DEFAULT 0,
            screenPageViews INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha_country_city (fecha, country, city)
        )
    """)
    
    # Tabla para páginas top
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paginas_top (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            pagePath TEXT NOT NULL,
            pageTitle TEXT DEFAULT '',
            screenPageViews INT DEFAULT 0,
            sessions INT DEFAULT 0,
            bounceRate DECIMAL(5,4) DEFAULT 0.0000,
            averageSessionDuration DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha_page_path (fecha, pagePath(255))
        )
    """)
    
    # Tabla para canales de marketing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS canales_marketing (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            channelGrouping VARCHAR(100) DEFAULT '',
            sourceMedium VARCHAR(255) DEFAULT '',
            campaignName VARCHAR(255) DEFAULT '',
            activeUsers INT DEFAULT 0,
            sessions INT DEFAULT 0,
            screenPageViews INT DEFAULT 0,
            bounceRate DECIMAL(5,4) DEFAULT 0.0000,
            averageSessionDuration DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha_channel_source_campaign (fecha, channelGrouping, sourceMedium, campaignName)
        )
    """)
    
    # Tabla para palabras clave
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS palabras_clave (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            searchTerm VARCHAR(255) DEFAULT '',
            landingPage TEXT DEFAULT '',
            activeUsers INT DEFAULT 0,
            sessions INT DEFAULT 0,
            screenPageViews INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha_search_landing (fecha, searchTerm, landingPage(255))
        )
    """)
    
    # Tabla para eventos personalizados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos_personalizados (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            eventName VARCHAR(255) NOT NULL,
            eventCount INT DEFAULT 0,
            uniqueEvents INT DEFAULT 0,
            totalUsers INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha_event (fecha, eventName)
        )
    """)
    
    # Tabla de metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata_extracciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha_extraccion DATE NOT NULL,
            property_id VARCHAR(50) NOT NULL,
            extraction_timestamp TIMESTAMP NOT NULL,
            total_datasets TINYINT DEFAULT 0,
            status ENUM('pending', 'completed', 'failed', 'partial') DEFAULT 'pending',
            error_message TEXT DEFAULT NULL,
            file_generated VARCHAR(255) DEFAULT NULL,
            records_count JSON DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fecha_property (fecha_extraccion, property_id)
        )
    """)
    
    # Tabla de pruebas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pruebas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            valor VARCHAR(255) DEFAULT '',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    connection.commit()
    cursor.close()
    logging.info("Tablas creadas/verificadas exitosamente")

def insert_metricas_generales(connection, df, fecha):
    """Insertar datos de métricas generales"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT INTO metricas_generales 
                (fecha, activeUsers, sessions, screenPageViews, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                activeUsers = VALUES(activeUsers),
                sessions = VALUES(sessions),
                screenPageViews = VALUES(screenPageViews),
                bounceRate = VALUES(bounceRate),
                averageSessionDuration = VALUES(averageSessionDuration),
                updated_at = CURRENT_TIMESTAMP
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
    """Insertar datos de dispositivos"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT INTO dispositivos 
                (fecha, deviceCategory, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                activeUsers = VALUES(activeUsers),
                sessions = VALUES(sessions),
                screenPageViews = VALUES(screenPageViews),
                updated_at = CURRENT_TIMESTAMP
            """
            values = (
                fecha,
                str(row['deviceCategory']) if pd.notna(row['deviceCategory']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0
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
                INSERT INTO geografia 
                (fecha, country, city, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                activeUsers = VALUES(activeUsers),
                sessions = VALUES(sessions),
                screenPageViews = VALUES(screenPageViews),
                updated_at = CURRENT_TIMESTAMP
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
    """Insertar datos de páginas top"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT INTO paginas_top 
                (fecha, pagePath, pageTitle, screenPageViews, sessions, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                pageTitle = VALUES(pageTitle),
                screenPageViews = VALUES(screenPageViews),
                sessions = VALUES(sessions),
                bounceRate = VALUES(bounceRate),
                averageSessionDuration = VALUES(averageSessionDuration),
                updated_at = CURRENT_TIMESTAMP
            """
            values = (
                fecha,
                str(row['pagePath']) if pd.notna(row['pagePath']) else '',
                str(row['pageTitle']) if pd.notna(row['pageTitle']) else '',
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando página: {e}")
    
    connection.commit()
    cursor.close()

def insert_canales_marketing(connection, df, fecha):
    """Insertar datos de canales de marketing"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT INTO canales_marketing 
                (fecha, channelGrouping, sourceMedium, campaignName, activeUsers, sessions, 
                 screenPageViews, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                activeUsers = VALUES(activeUsers),
                sessions = VALUES(sessions),
                screenPageViews = VALUES(screenPageViews),
                bounceRate = VALUES(bounceRate),
                averageSessionDuration = VALUES(averageSessionDuration),
                updated_at = CURRENT_TIMESTAMP
            """
            values = (
                fecha,
                str(row['channelGrouping']) if pd.notna(row['channelGrouping']) else '',
                str(row['sourceMedium']) if pd.notna(row['sourceMedium']) else '',
                str(row['campaignName']) if pd.notna(row['campaignName']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando canal de marketing: {e}")
    
    connection.commit()
    cursor.close()

def insert_palabras_clave(connection, df, fecha):
    """Insertar datos de palabras clave"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT INTO palabras_clave 
                (fecha, searchTerm, landingPage, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                activeUsers = VALUES(activeUsers),
                sessions = VALUES(sessions),
                screenPageViews = VALUES(screenPageViews),
                updated_at = CURRENT_TIMESTAMP
            """
            values = (
                fecha,
                str(row['searchTerm']) if pd.notna(row['searchTerm']) else '',
                str(row['landingPage']) if pd.notna(row['landingPage']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando palabra clave: {e}")
    
    connection.commit()
    cursor.close()

def insert_eventos_personalizados(connection, df, fecha):
    """Insertar datos de eventos personalizados"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT INTO eventos_personalizados 
                (fecha, eventName, eventCount, uniqueEvents, totalUsers)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                eventCount = VALUES(eventCount),
                uniqueEvents = VALUES(uniqueEvents),
                totalUsers = VALUES(totalUsers),
                updated_at = CURRENT_TIMESTAMP
            """
            values = (
                fecha,
                str(row['eventName']) if pd.notna(row['eventName']) else '',
                int(row['eventCount']) if pd.notna(row['eventCount']) else 0,
                int(row['uniqueEvents']) if pd.notna(row['uniqueEvents']) else 0,
                int(row['totalUsers']) if pd.notna(row['totalUsers']) else 0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando evento personalizado: {e}")
    
    connection.commit()
    cursor.close()

def insert_metadata_extraction(connection, fecha, property_id, status='completed', records_count=None):
    """Insertar metadata de extracción"""
    cursor = connection.cursor()
    
    try:
        query = """
            INSERT INTO metadata_extracciones 
            (fecha_extraccion, property_id, extraction_timestamp, status, records_count)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            extraction_timestamp = VALUES(extraction_timestamp),
            status = VALUES(status),
            records_count = VALUES(records_count),
            updated_at = CURRENT_TIMESTAMP
        """
        values = (
            fecha,
            property_id,
            datetime.now(),
            status,
            records_count
        )
        cursor.execute(query, values)
        connection.commit()
        
    except Exception as e:
        logging.error(f"Error insertando metadata: {e}")
    
    cursor.close()

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

def main():
    st.set_page_config(
        page_title="Analytics Data Importer",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Analytics Data Importer - Versión Corregida")
    st.markdown("---")
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Selector de carpeta
    folder_path = st.sidebar.text_input(
        "📁 Ruta de la carpeta con archivos Excel:",
        value="C:/downloads",
        help="Especifica la carpeta donde están los archivos Excel descargados"
    )
    
    # Selector de fecha para los datos
    fecha_datos = st.sidebar.date_input(
        "📅 Fecha de los datos:",
        value=datetime.now().date(),
        help="Fecha correspondiente a los datos que se van a importar"
    )
    
    # Property ID
    property_id = st.sidebar.text_input(
        "🏷️ Property ID de GA4:",
        value="default",
        help="ID de la propiedad de Google Analytics 4"
    )
    
    # Información de conexión
    with st.sidebar.expander("🔍 Info de Conexión DB"):
        st.code(f"""
Host: {DB_CONFIG['host']}
Puerto: {DB_CONFIG['port']}
Base de datos: {DB_CONFIG['database']}
Usuario: {DB_CONFIG['user']}
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
                
                # Mostrar hojas del Excel
                try:
                    excel_sheets = pd.ExcelFile(latest_file).sheet_names
                    st.write("📋 Hojas disponibles:")
                    for sheet in excel_sheets:
                        st.write(f"- {sheet}")
                except Exception as e:
                    st.warning(f"No se pudieron leer las hojas del Excel: {e}")
                
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
                    # Crear tablas si no existen
                    create_tables(connection)
                    st.success("✅ Tablas verificadas/creadas!")
                    connection.close()
                else:
                    st.error("❌ Error de conexión")
        
        st.markdown("---")
        
        # Botón principal de importación
        if st.button("📥 Importar Datos", type="primary", disabled=latest_file is None):
            if latest_file:
                import_data(latest_file, fecha_datos, property_id)

def import_data(excel_file, fecha, property_id):
    """Función principal para importar datos"""
    try:
        with st.spinner("🔄 Procesando archivo Excel..."):
            # Leer todas las hojas del Excel
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
            st.info(f"📋 Hojas encontradas: {list(excel_data.keys())}")
            
            # Crear conexión
            connection = create_connection()
            if not connection:
                st.error("❌ No se pudo conectar a la base de datos")
                return
            
            # Crear tablas
            create_tables(connection)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = {
                'metricas_generales': 0,
                'dispositivos': 0,
                'geografia': 0,
                'paginas_top': 0,
                'canales_marketing': 0,
                'palabras_clave': 0,
                'eventos_personalizados': 0,
                'errores': []
            }
            
            # Mapeo de nombres de hojas posibles
            sheet_mappings = {
                'metricas_generales': ['metricas_generales', 'general', 'overview', 'resumen'],
                'dispositivos': ['dispositivos', 'devices', 'device_category'],
                'geografia': ['geografia', 'geography', 'geo', 'countries'],
                'paginas_top': ['paginas_top', 'pages', 'top_pages', 'page_performance'],
                'canales_marketing': ['canales_marketing', 'marketing', 'channels', 'traffic_sources'],
                'palabras_clave': ['palabras_clave', 'keywords', 'search_terms'],
                'eventos_personalizados': ['eventos_personalizados', 'events', 'custom_events']
            }
            
            # Procesar cada hoja
            total_sheets = len(sheet_mappings)
            processed_sheets = 0
            
            for table_name, possible_names in sheet_mappings.items():
                found_sheet = None
                
                # Buscar la hoja por nombre
                for sheet_name in excel_data.keys():
                    if sheet_name.lower() in [name.lower() for name in possible_names]:
                        found_sheet = sheet_name
                        break
                
                if found_sheet and not excel_data[found_sheet].empty:
                    status_text.text(f"Procesando {found_sheet}...")
                    df = excel_data[found_sheet]
                    
                    try:
                        if table_name == 'metricas_generales':
                            insert_metricas_generales(connection, df, fecha)
                            results['metricas_generales'] = len(df)
                        elif table_name == 'dispositivos':
                            insert_dispositivos(connection, df, fecha)
                            results['dispositivos'] = len(df)
                        elif table_name == 'geografia':
                            insert_geografia(connection, df, fecha)
                            results['geografia'] = len(df)
                        elif table_name == 'paginas_top':
                            insert_paginas_top(connection, df, fecha)
                            results['paginas_top'] = len(df)
                        elif table_name == 'canales_marketing':
                            insert_canales_marketing(connection, df, fecha)
                            results['canales_marketing'] = len(df)
                        elif table_name == 'palabras_clave':
                            insert_palabras_clave(connection, df, fecha)
                            results['palabras_clave'] = len(df)
                        elif table_name == 'eventos_personalizados':
                            insert_eventos_personalizados(connection, df, fecha)
                            results['eventos_personalizados'] = len(df)
                    except Exception as e:
                        results['errores'].append(f"{table_name}: {str(e)}")
                else:
                    results['errores'].append(f"Hoja para '{table_name}' no encontrada. Nombres buscados: {possible_names}")
                
                processed_sheets += 1
                progress_bar.progress(processed_sheets / total_sheets)
            
            # Insertar metadata de extracción
            records_summary = {k: v for k, v in results.items() if k != 'errores'}
            insert_metadata_extraction(connection, fecha, property_id, 'completed', str(records_summary))
            
            connection.close()
            status_text.text("✅ Proceso completado!")
            
            # Mostrar resultados
            st.success("🎉 Datos importados exitosamente!")
            
            # Crear columnas para métricas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Métricas Generales", results['metricas_generales'])
                st.metric("📱 Dispositivos", results['dispositivos'])
            
            with col2:
                st.metric("🌍 Geografía", results['geografia'])
                st.metric("📄 Páginas Top", results['paginas_top'])
            
            with col3:
                st.metric("🚀 Canales Marketing", results['canales_marketing'])
                st.metric("🔍 Palabras Clave", results['palabras_clave'])
            
            with col4:
                st.metric("⚡ Eventos Personalizados", results['eventos_personalizados'])
                
            # Mostrar errores si existen
            if results['errores']:
                with st.expander("⚠️ Advertencias y Errores"):
                    for error in results['errores']:
                        if "no encontrada" in error.lower():
                            st.warning(error)
                        else:
                            st.error(error)
            
            # Información adicional
            st.info(f"📅 Fecha de datos: {fecha}")
            st.info(f"🏷️ Property ID: {property_id}")
            st.info(f"🕐 Timestamp de importación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Resumen de registros
            total_records = sum([v for k, v in results.items() if k != 'errores'])
            st.success(f"📈 Total de registros importados: {total_records:,}")
            
    except Exception as e:
        st.error(f"❌ Error durante la importación: {str(e)}")
        logging.error(f"Error en import_data: {e}")

if __name__ == "__main__":
    main()