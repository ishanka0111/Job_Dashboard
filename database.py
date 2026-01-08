import streamlit as st
import pandas as pd
import pyodbc
import warnings
from config import DB_CONFIG
from datetime import datetime, timedelta
import threading
import time

# Suppress pandas pyodbc warning
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')

# Global cache dictionary for instant access
_data_cache = {}
_cache_lock = threading.Lock()

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
    """
    Fetch data with 60-second cache
    Automatically preloads common queries
    """
    return _fetch_from_db(query, params)

@st.cache_data(ttl=300)
def fetch_static_data(query, params=None):
    """
    For rarely changing data (5-minute cache)
    """
    return _fetch_from_db(query, params)

def preload_dashboard_data():
    """
    Preload all dashboard data in background
    This runs once when app starts
    """
    queries_to_preload = [
        ("dashboard", "SELECT * FROM v_EnhancedDashboard WHERE IsActive = 1"),
        ("health", "SELECT * FROM v_InstanceHealthSummary WHERE IsActive = 1"),
        ("failures", "SELECT * FROM v_Last24HourFailures"),
        ("instances", "SELECT ServerName, FriendlyName, IsActive FROM ManagedInstances WHERE IsActive = 1"),
    ]
    
    for key, query in queries_to_preload:
        try:
            # Trigger the cache by calling fetch_data
            fetch_data(query)
        except:
            pass  # Silent fail for preload

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
    with _cache_lock:
        _data_cache.clear()

# Initialize preload on module import
if 'preload_done' not in st.session_state:
    st.session_state.preload_done = False
    
if not st.session_state.preload_done:
    preload_dashboard_data()
    st.session_state.preload_done = True