import subprocess
import sys

def install_packages():
    """Instalar paquetes necesarios"""
    packages = [
        'google-analytics-data',
        'pandas',
        'pymysql',
        'sqlalchemy',
        'cryptography',
        'google-auth-oauthlib',
        'google-auth',
        'plotly'
    ]

    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
            print(f"   ✅ {package} instalado")
        except subprocess.CalledProcessError:
            print(f"   ❌ Error instalando {package}")

install_packages()


# =============================================================================
# 2️⃣ IMPORTACIÓN DE LIBRERÍAS
# =============================================================================
print("\n2️⃣ Importando librerías...")

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, OrderBy, FilterExpression, Filter
)
from google.oauth2 import service_account
from google.colab import drive
import pandas as pd
import pymysql
from sqlalchemy import create_engine, text, inspect
import os
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("   ✅ Todas las librerías importadas correctamente")