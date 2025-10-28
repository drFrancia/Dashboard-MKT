# 🏗️ Arquitectura del Proyecto

## Componentes del Sistema

Este proyecto es **parte de un sistema más grande** de análisis de GA4. Aquí está cómo encaja todo:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA COMPLETO GA4                         │
└─────────────────────────────────────────────────────────────────┘

1️⃣ EXTRACCIÓN DE DATOS (Google Colab - EXTERNO ❌ NO INCLUIDO)
   ┌──────────────────────────────────────────────┐
   │ • Conecta a Google Analytics 4 API          │
   │ • Extrae datos del día anterior              │
   │ • Transforma y limpia datos                  │
   │ • Exporta a formato procesable               │
   │ • Guarda datos localmente o en BD           │
   │ Nota: Script en tu Google Colab              │
   └────────────┬─────────────────────────────────┘
                │
                ▼
2️⃣ IMPORTACIÓN A BASE DE DATOS (Importador.py - ✅ INCLUIDO)
   ┌──────────────────────────────────────────────┐
   │ • Lee datos de Colab                         │
   │ • Valida estructura de datos                 │
   │ • Carga en MySQL local                       │
   │ • Registra logs                              │
   │ Ubicación: Produccion/Importador.py          │
   └────────────┬─────────────────────────────────┘
                │
                ▼
3️⃣ BASE DE DATOS (MySQL Local - ✅ INCLUIDO)
   ┌──────────────────────────────────────────────┐
   │ • analytics_datos (base de datos)            │
   │ • metricas_generales                         │
   │ • dispositivos                               │
   │ • paginas_top                                │
   │ • geografia                                  │
   │ • datos_horarios                             │
   │ • terminos_busqueda                          │
   │ • fuentes_trafico                            │
   │ • user_sessions                              │
   └────────────┬─────────────────────────────────┘
                │
                ▼
4️⃣ VISUALIZACIÓN (dashboard.py - ✅ INCLUIDO)
   ┌──────────────────────────────────────────────┐
   │ • Lee datos de MySQL                         │
   │ • Visualización interactiva                  │
   │ • Modo análisis individual                   │
   │ • Modo comparación                           │
   │ • Exportación de datos                       │
   │ Ubicación: v9/dashboard.py (o Produccion)   │
   └────────────┬─────────────────────────────────┘
                │
                ▼
5️⃣ USUARIO FINAL (Equipo Marketing)
   ┌──────────────────────────────────────────────┐
   │ • Accede al dashboard en navegador           │
   │ • Analiza métricas                           │
   │ • Descarga reportes                          │
   │ URL: http://localhost:8501                   │
   └──────────────────────────────────────────────┘
```

## ¿Qué incluye este Repositorio?

✅ **INCLUIDO - Este Repositorio:**
```
Dashboard-MKT/
├── Produccion/          ← v8.1 Actual (Importador + Dashboard)
│   ├── Importador.py
│   └── dashboard.py
├── v9/                  ← v9 Próxima ( Dashboard mejorado)
│   └── dashboard.py
├── requirements.txt     ← Dependencias Python
├── README.md
└── .env.example
```

❌ **NO INCLUIDO - Script Externo (Colab):**
```
Google Colab Script/
├── ga4_extraction.ipynb
├── data_processing.ipynb
└── (Genera datos para este proyecto)
```

## Flujo Típico de Datos

### Día 1 - Setup Inicial
```
1. Configuras MySQL localmente
2. Creas base de datos y tablas
3. Clonas este repositorio
4. Instalas dependencias (pip install -r requirements.txt)
5. Ejecutas tu script de Colab (genera datos iniciales)
6. Ejecutas: streamlit run Produccion/Importador.py (carga a MySQL)
7. Ejecutas: streamlit run v9/dashboard.py (visualiza datos)
```

### Días Siguientes - Actualización Diaria
```
9:00 AM  ← Ejecutas script de Colab (extrae datos GA4)
          └─→ Genera archivo de datos o guarda en BD

9:10 AM  ← Ejecutas Importador (Streamlit)
          streamlit run Produccion/Importador.py
          └─→ Lee datos de Colab
          └─→ Valida formato
          └─→ Carga en MySQL
          └─→ Se abre en http://localhost:8501

09:20 AM ← Ejecutas Dashboard (Streamlit)
          streamlit run v9/dashboard.py
          └─→ Visualiza datos actualizados
          └─→ Realiza análisis
          └─→ Descarga reportes
```

## Dependencias Entre Componentes

```
Google Colab (Externo)
        ↓
        ├─→ Produce: Datos de GA4 procesados
        └─→ Responsabilidad: Extracción y limpieza inicial
        
Importador.py (Este Proyecto)
        ↓
        ├─→ Consume: Datos de Colab
        ├─→ Produce: Datos en MySQL
        └─→ Responsabilidad: Validación y carga

MySQL Local (Este Proyecto)
        ↓
        ├─→ Consume: Datos del Importador
        ├─→ Produce: Datos para dashboard
        └─→ Responsabilidad: Almacenamiento persistente

dashboard.py (Este Proyecto)
        ↓
        ├─→ Consume: Datos de MySQL
        ├─→ Produce: Visualizaciones interactivas
        └─→ Responsabilidad: Presentación de datos
```

## Escalabilidad Futura

### Si quieres:

1. **Automatizar completamente**
   - Agregar script de Python que se comunique con Colab
   - Ejecutar automáticamente vía cron/scheduler
   - Crear alertas automáticas

2. **Agregar más análisis**
   - Nuevas tablas en MySQL
   - Nuevas visualizaciones en dashboard
   - Predicciones con ML

3. **Compartir con más usuarios**
   - Agregar autenticación a Streamlit
   - Deployar a servidor (Heroku, AWS, etc.)
   - Crear API REST

4. **Integración con otras herramientas**
   - Exportar a Tableau/Power BI
   - Conectar con Slack para alertas
   - Crear webhooks

## Preguntas Frecuentes de Arquitectura

**P: ¿Por qué separar en Colab y este proyecto?**
R: Colab maneja la conexión con Google Analytics (requiere credenciales complejas). Este proyecto solo maneja almacenamiento y visualización.

**P: ¿Puedo importar directamente desde GA4 API aquí?**
R: Sí, podrías modificar Importador.py para hacerlo, pero actualmente usas Colab como intermediario.

**P: ¿Qué pasa si falla el importador?**
R: El dashboard seguiría mostrando datos del día anterior. Revisa los logs en `./logs/import_log.txt`.

**P: ¿Puedo agregar más fuentes de datos?**
R: Sí, agrega más tablas a MySQL y modifica el importador para leerlas.

---

**Última actualización:** Octubre 2025
