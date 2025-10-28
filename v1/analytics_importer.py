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
    """Crear las tablas necesarias si no existen"""
    cursor = connection.cursor()
    
    # Tabla para métricas generales
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metricas_generales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            activeUsers INT,
            sessions INT,
            screenPageViews INT,
            bounceRate DECIMAL(5,2),
            averageSessionDuration DECIMAL(10,2),
            fecha_insercion DATETIME,
            UNIQUE KEY unique_fecha (fecha_insercion)
        )
    """)
    
    # Tabla para dispositivos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispositivos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            deviceCategory VARCHAR(100),
            activeUsers INT,
            sessions INT,
            screenPageViews INT,
            fecha_insercion DATETIME,
            UNIQUE KEY unique_device_fecha (deviceCategory, fecha_insercion)
        )
    """)
    
    # Tabla para geografía
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geografia (
            id INT AUTO_INCREMENT PRIMARY KEY,
            country VARCHAR(100),
            city VARCHAR(100),
            activeUsers INT,
            sessions INT,
            screenPageViews INT,
            fecha_insercion DATETIME,
            UNIQUE KEY unique_geo_fecha (country, city, fecha_insercion)
        )
    """)
    
    # Tabla para páginas top
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paginas_top (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pagePath TEXT,
            pageTitle TEXT,
            screenPageViews INT,
            sessions INT,
            bounceRate DECIMAL(5,2),
            averageSessionDuration DECIMAL(10,2),
            fecha_insercion DATETIME,
            UNIQUE KEY unique_page_fecha (pagePath(191), fecha_insercion)
        )
    """)
    
    # Tabla para tendencia diaria
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tendencia_diaria (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATETIME,
            activeUsers INT,
            sessions INT,
            screenPageViews INT,
            bounceRate DECIMAL(5,2),
            UNIQUE KEY unique_date (date)
        )
    """)
    
    connection.commit()
    cursor.close()
    logging.info("Tablas creadas/verificadas exitosamente")

def insert_metricas_generales(connection, df, timestamp):
    """Insertar datos de métricas generales"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO metricas_generales 
                (activeUsers, sessions, screenPageViews, bounceRate, averageSessionDuration, fecha_insercion)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0,
                timestamp
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando métrica general: {e}")
    
    connection.commit()
    cursor.close()

def insert_dispositivos(connection, df, timestamp):
    """Insertar datos de dispositivos"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO dispositivos 
                (deviceCategory, activeUsers, sessions, screenPageViews, fecha_insercion)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                str(row['deviceCategory']) if pd.notna(row['deviceCategory']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                timestamp
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando dispositivo: {e}")
    
    connection.commit()
    cursor.close()

def insert_geografia(connection, df, timestamp):
    """Insertar datos de geografía"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO geografia 
                (country, city, activeUsers, sessions, screenPageViews, fecha_insercion)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                str(row['country']) if pd.notna(row['country']) else '',
                str(row['city']) if pd.notna(row['city']) else '',
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                timestamp
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando geografía: {e}")
    
    connection.commit()
    cursor.close()

def insert_paginas_top(connection, df, timestamp):
    """Insertar datos de páginas top"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO paginas_top 
                (pagePath, pageTitle, screenPageViews, sessions, bounceRate, averageSessionDuration, fecha_insercion)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                str(row['pagePath']) if pd.notna(row['pagePath']) else '',
                str(row['pageTitle']) if pd.notna(row['pageTitle']) else '',
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0,
                float(row['averageSessionDuration']) if pd.notna(row['averageSessionDuration']) else 0.0,
                timestamp
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando página: {e}")
    
    connection.commit()
    cursor.close()

def insert_tendencia_diaria(connection, df):
    """Insertar datos de tendencia diaria"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            # Convertir la fecha si es necesario
            if isinstance(row['date'], str):
                fecha = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S')
            else:
                fecha = row['date']
            
            query = """
                INSERT IGNORE INTO tendencia_diaria 
                (date, activeUsers, sessions, screenPageViews, bounceRate)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                fecha,
                int(row['activeUsers']) if pd.notna(row['activeUsers']) else 0,
                int(row['sessions']) if pd.notna(row['sessions']) else 0,
                int(row['screenPageViews']) if pd.notna(row['screenPageViews']) else 0,
                float(row['bounceRate']) if pd.notna(row['bounceRate']) else 0.0
            )
            cursor.execute(query, values)
        except Exception as e:
            logging.error(f"Error insertando tendencia diaria: {e}")
    
    connection.commit()
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
    
    st.title("📊 Analytics Data Importer")
    st.markdown("---")
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Selector de carpeta
    folder_path = st.sidebar.text_input(
        "📁 Ruta de la carpeta con archivos Excel:",
        value="C:/downloads",
        help="Especifica la carpeta donde están los archivos Excel descargados"
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
                    connection.close()
                else:
                    st.error("❌ Error de conexión")
        
        # Botón principal de importación
        if st.button("📥 Importar Datos", type="primary", disabled=latest_file is None):
            if latest_file:
                import_data(latest_file)

def import_data(excel_file):
    """Función principal para importar datos"""
    try:
        with st.spinner("🔄 Procesando archivo Excel..."):
            # Leer todas las hojas del Excel
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
            # Timestamp para las inserciones
            timestamp = datetime.now()
            
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
                'tendencia_diaria': 0,
                'errores': []
            }
            
            # Procesar cada hoja
            sheets_to_process = ['metricas_generales', 'dispositivos', 'geografia', 'paginas_top', 'tendencia_diaria']
            
            for i, sheet_name in enumerate(sheets_to_process):
                if sheet_name in excel_data:
                    status_text.text(f"Procesando {sheet_name}...")
                    df = excel_data[sheet_name]
                    
                    if not df.empty:
                        try:
                            if sheet_name == 'metricas_generales':
                                insert_metricas_generales(connection, df, timestamp)
                                results['metricas_generales'] = len(df)
                            elif sheet_name == 'dispositivos':
                                insert_dispositivos(connection, df, timestamp)
                                results['dispositivos'] = len(df)
                            elif sheet_name == 'geografia':
                                insert_geografia(connection, df, timestamp)
                                results['geografia'] = len(df)
                            elif sheet_name == 'paginas_top':
                                insert_paginas_top(connection, df, timestamp)
                                results['paginas_top'] = len(df)
                            elif sheet_name == 'tendencia_diaria':
                                insert_tendencia_diaria(connection, df)
                                results['tendencia_diaria'] = len(df)
                        except Exception as e:
                            results['errores'].append(f"{sheet_name}: {str(e)}")
                    
                    progress_bar.progress((i + 1) / len(sheets_to_process))
                else:
                    results['errores'].append(f"Hoja '{sheet_name}' no encontrada en el Excel")
            
            connection.close()
            status_text.text("✅ Proceso completado!")
            
            # Mostrar resultados
            st.success("🎉 Datos importados exitosamente!")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Métricas Generales", results['metricas_generales'])
                st.metric("📱 Dispositivos", results['dispositivos'])
            
            with col2:
                st.metric("🌍 Geografía", results['geografia'])
                st.metric("📄 Páginas Top", results['paginas_top'])
            
            with col3:
                st.metric("📈 Tendencia Diaria", results['tendencia_diaria'])
                
            if results['errores']:
                with st.expander("⚠️ Errores encontrados"):
                    for error in results['errores']:
                        st.error(error)
            
            # Información adicional
            st.info(f"🕐 Timestamp de inserción: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        st.error(f"❌ Error durante la importación: {str(e)}")
        logging.error(f"Error en import_data: {e}")

if __name__ == "__main__":
    main()