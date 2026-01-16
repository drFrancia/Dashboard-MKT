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
            print("Conectado")
            return connection
    except Error as e:
        st.error(f"Error conectando a MySQL: {e}")
        return None
    
create_connection()

# Metricas Generales
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

# Dispositivos
def insert_dispositivos(connection, df, fecha):
    """Insertar datos de dispositivos"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO dispositivos 
                (fecha, deviceCategory, activeUsers, sessions, screenPageViews)
                VALUES (%s, %s, %s, %s, %s)
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

# Geografia
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

# Páginas Top
def insert_paginas_top(connection, df, fecha):
    """Insertar datos de páginas top"""
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        try:
            query = """
                INSERT IGNORE INTO paginas_top 
                (fecha, pagePath, pageTitle, screenPageViews, sessions, bounceRate, averageSessionDuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
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

# Datos Horarios
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

# Último Excel
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

# Funcionalidad completa dashboard
def main():
    st.set_page_config(
        page_title="Analytics Data Importer",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Analytics Data Importer - Versión Adaptada")
    st.markdown("### Importa datos de GA4 a tu base de datos existente")
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
                            st.write(f"**{sheet_name}**: {len(df)} registros")
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
                    with st.expander("Ver tablas"):
                        for table in sorted(tables):
                            st.write(f"• {table}")
                    
                    connection.close()
                else:
                    st.error("❌ Error de conexión")
        
        st.markdown("---")
        
        # Información importante
        st.info("""
            **📌 Importante:**
            
            • Las tablas deben existir previamente
            • Los datos se asignan a la fecha seleccionada
            • Se evitan duplicados con INSERT IGNORE
        """)
        
        # Botón principal de importación
        if st.button("📥 Importar Datos", type="primary", disabled=latest_file is None):
            if latest_file:
                import_data(latest_file, target_date)

# Importador de datos
def import_data(excel_file, target_date):
    """Función principal para importar datos"""
    try:
        with st.spinner("🔄 Procesando archivo Excel..."):
            # Leer todas las hojas del Excel
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
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
                # 'canales_marketing': 0,
                # 'palabras_clave': 0,
                # 'eventos_personalizados': 0,
                'datos_horarios': 0,
                'errores': []
            }
            
            # Mapeo de funciones de inserción
            insert_functions = {
                'metricas_generales': insert_metricas_generales,
                'dispositivos': insert_dispositivos,
                'geografia': insert_geografia,
                'paginas_top': insert_paginas_top,
                # 'canales_marketing': insert_canales_marketing,
                # 'palabras_clave': insert_palabras_clave,
                # 'eventos_personalizados': insert_eventos_personalizados,
                'datos_horarios': insert_datos_horarios
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
                            st.success(f"✅ {sheet_name}: {len(df)} registros procesados")
                        except Exception as e:
                            error_msg = f"{sheet_name}: {str(e)}"
                            results['errores'].append(error_msg)
                            st.error(f"❌ {error_msg}")
                    else:
                        st.warning(f"⚠️ {sheet_name}: Sin datos para procesar")
                    
                    progress_bar.progress((i + 1) / len(sheets_to_process))
                else:
                    warning_msg = f"Hoja '{sheet_name}' no encontrada en el Excel"
                    results['errores'].append(warning_msg)
                    st.warning(f"⚠️ {warning_msg}")
            
            connection.close()
            status_text.text("✅ Proceso completado!")
            
            # Mostrar resultados
            st.balloons()
            st.success("🎉 Importación completada!")
            
            # Métricas de resultados
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Métricas Generales", results['metricas_generales'])
                st.metric("📱 Dispositivos", results['dispositivos'])
            
            with col2:
                st.metric("🌍 Geografía", results['geografia'])
                st.metric("📄 Páginas Top", results['paginas_top'])
            
            # with col3:
            #     st.metric("🚀 Canales Marketing", results['canales_marketing'])
            #     st.metric("🔍 Palabras Clave", results['palabras_clave'])
            
            with col4:
                # st.metric("⚡ Eventos", results['eventos_personalizados'])
                st.metric("🕐 Datos Horarios", results['datos_horarios'])
            
            # Mostrar errores si los hay
            if results['errores']:
                st.subheader("⚠️ Advertencias y Errores")
                for error in results['errores']:
                    st.warning(error)
            
            # Información adicional
            total_records = sum([v for k, v in results.items() if k != 'errores'])
            st.info(f"""
            **📈 Resumen de Importación:**
            • **Fecha asignada:** {target_date}
            • **Total registros:** {total_records:,}
            • **Tiempo:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """)
            
    except Exception as e:
        st.error(f"❌ Error durante la importación: {str(e)}")
        logging.error(f"Error en import_data: {e}")


if __name__ == "__main__":
    main()