import streamlit as st
import pandas as pd
import pyodbc
import warnings
from config import DB_CONFIG

warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')

@st.cache_resource
def get_central_conn():
    """Cached database connection shared across modules"""
    return pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection=yes;"
    )

def _fetch_from_db(query, params=None):
    """Internal function to fetch from database"""
    try:
        conn = get_central_conn()
        return pd.read_sql(query, conn, params=params)
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_data(query, params=None):
    """Fetch data with 60-second cache"""
    return _fetch_from_db(query, params)

@st.cache_data(ttl=300)
def fetch_static_data(query, params=None):
    """For rarely changing data (5-minute cache)"""
    return _fetch_from_db(query, params)

def get_dashboard_data():
    """Fast access to dashboard data"""
    return fetch_data("SELECT * FROM v_EnhancedDashboard WHERE IsActive = 1")

def get_health_summary():
    """Fast access to health summary"""
    return fetch_data("SELECT * FROM v_InstanceHealthSummary WHERE IsActive = 1")

def get_failures_24h():
    """Fast access to 24h failures"""
    return fetch_data("SELECT * FROM v_Last24HourFailures")

def get_performance_trends():
    """Fast access to performance data"""
    return fetch_data("""
        SELECT * FROM v_PerformanceTrends 
        WHERE RunDate >= DATEADD(day, -30, GETDATE())
        ORDER BY RunDate DESC
    """)

def get_instances():
    """Fast access to instances list"""
    return fetch_static_data("SELECT ServerName, FriendlyName, IsActive, DateAdded FROM ManagedInstances ORDER BY FriendlyName")

def clear_all_caches():
    """Clear all caches when data is updated"""
    st.cache_data.clear()
    st.cache_resource.clear()
