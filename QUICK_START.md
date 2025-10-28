# GUÍA RÁPIDA DE INICIO

> ⚠️ **Nota Importante:** Este proyecto SOLO contiene Importador.py y dashboard.py
> 
> Tu script de Colab (extracción de GA4) es **EXTERNO** y debe ejecutarse **ANTES** que el importador

## ✅ Checklist de Configuración Inicial

### 1. Preparar el Sistema
- [ ] Python 3.11+ instalado
- [ ] MySQL 8.0+ instalado y ejecutándose (WAMP/LAMP)
- [ ] Git instalado
- [ ] Tu script de Colab funcionando correctamente

### 2. Clonar y Preparar
```bash
git clone https://github.com/drFrancia/Dashboard-MKT.git
cd Dashboard-MKT
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# o
source venv/bin/activate     # Linux/Mac
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Base de Datos MySQL
```bash
# Crear base de datos
mysql -u root -p < setup_database.sql

# O ejecutar manualmente en MySQL:
# CREATE DATABASE IF NOT EXISTS analytics_datos;
```

### 5. Configurar Archivo .env
```bash
# Copiar ejemplo
cp .env.example .env

# Editar con tus credenciales de MySQL
# Solo necesitas: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
```

### 6. Ejecutar Tu Script de Colab
```
⚠️ IMPORTANTE: Ejecuta PRIMERO tu script de Colab
   (El que extrae datos de Google Analytics)
```

### 7. Ejecutar Importador (Streamlit)
```bash
cd Produccion
streamlit run Importador.py
```
✅ Esto cargará los datos en MySQL

### 8. Ejecutar Dashboard (Streamlit)
```bash
cd v9  # o cd Produccion para versión actual v8.1
streamlit run dashboard.py
```

### 9. Acceder
- 🌐 Se abre automáticamente en: http://localhost:8501
- Si no abre, accede manualmente en esa URL

> ℹ️ **Nota:** Ambos (Importador y Dashboard) se ejecutan con `streamlit run`

---

## 🔄 Flujo de Ejecución Diaria

```
9:00 AM  → Ejecuta tu script de Colab 
           (extrae datos de Google Analytics)

9:30 AM  → Ejecuta Importador (Streamlit)
           cd Produccion
           streamlit run Importador.py
           └─→ Carga datos a MySQL
           └─→ Se abre en http://localhost:8501

10:00 AM → Ejecuta Dashboard (Streamlit)
           cd v9
           streamlit run dashboard.py
           └─→ Abre http://localhost:8501
           └─→ Equipo visualiza datos actualizados
```

---

## ⚠️ Errores Comunes

### Error: "Can't connect to MySQL server"
✅ **Solución:** 
- Inicia WAMP/LAMP 
- Verifica MySQL está corriendo
- Revisa MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD en .env

### Error: "Table doesn't exist"
✅ **Solución:** 
- Ejecuta: `mysql -u root -p < setup_database.sql`
- O crea tablas manualmente desde MySQL

### Error: "Streamlit not found"
✅ **Solución:** 
- Ejecuta: `pip install -r requirements.txt`

### Error: "No data to display"
✅ **Solución:** 
1. Primero: Ejecuta tu script de Colab (genera datos)
2. Luego: Ejecuta Importador.py (carga a MySQL)
3. Finalmente: Abre dashboard (visualiza datos)

### Error: "Permission denied" en importador
✅ **Solución:** 
- Verifica que tu usuario MySQL tiene permisos
- Revisa MYSQL_USER tiene acceso a analytics_datos

---

## � Documentación

- **README.md** - Documentación completa
- **ARCHITECTURE.md** - Arquitectura y flujo de datos
- **Este archivo** - Guía rápida

---

## 🆘 Necesitas Ayuda?

1. **Revisar documentación:** Lee README.md
2. **Entender arquitectura:** Lee ARCHITECTURE.md
3. **Verificar MySQL:** `mysql -u root -p -e "SHOW DATABASES;"`
4. **Ver logs:** `cat ./logs/import_log.txt`

---

**Última actualización:** Octubre 2025 | **Versión Actual:** 8.1

