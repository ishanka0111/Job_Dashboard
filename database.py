import streamlit as st
import pandas as pd
import pyodbc
from config import DB_CONFIG

@st.cache_resource
def get_central_conn():
    """Cached database connection shared across modules"""
    return pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection=yes;"
    )

def fetch_data(query, params=None):
    """Utility to fetch dataframes"""
    conn = get_central_conn()
    return pd.read_sql(query, conn, params=params)