import streamlit as st
import pandas as pd
import pyodbc
from config import DB_CONFIG
from worker import run_collection 

st.set_page_config(page_title="SQL Monitoring Pro", layout="wide")

def get_central_conn():
    return pyodbc.connect(f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};Trusted_Connection=yes;")

# --- SIDEBAR: SYNC & ADD ---
st.sidebar.header("🕹️ Controls")
if st.sidebar.button("🔄 Sync Now (Manual Refresh)"):
    with st.spinner("Syncing office servers..."):
        run_collection()
        st.toast("Sync Complete!", icon="✅")

with st.sidebar.form("add_form", clear_on_submit=True):
    st.subheader("➕ Add Instance")
    new_svr = st.text_input("Server IP/Host")
    new_label = st.text_input("Friendly Name")
    if st.form_submit_button("Add Server"):
        with get_central_conn() as conn:
            conn.cursor().execute("INSERT INTO ManagedInstances (ServerName, FriendlyName) VALUES (?,?)", new_svr, new_label)
            conn.commit()
        st.rerun()

# --- MAIN LAYOUT: DASHBOARD & MANAGEMENT ---
tab1, tab2 = st.tabs(["📊 Dashboard", "⚙️ Manage Instances"])

with tab1:
    st.title("SQL Job Dashboard")
    with get_central_conn() as conn:
        df = pd.read_sql("SELECT * FROM v_PersistentDashboard WHERE IsActive = 1", conn)

    # KPI Metrics
    failed_df = df[df['Status'] == 'Failed']
    c1, c2 = st.columns(2)
    c1.metric("Total Jobs", len(df))
    c2.metric("Critical Failures", len(failed_df), delta_color="inverse")

    # Table with Friendly Names
    st.subheader("🚨 Failed Jobs (Need Action)")
    if not failed_df.empty:
        # Displaying FriendlyName instead of just Hostname
        st.dataframe(
            failed_df[['FriendlyName', 'JobName', 'LastRun', 'ErrorMessage']], 
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("All systems healthy.")

with tab2:
    st.subheader("Instance Management")
    st.caption("Toggle the switch to start or stop monitoring a server.")
    
    with get_central_conn() as conn:
        instances = pd.read_sql("SELECT ServerName, FriendlyName, IsActive FROM ManagedInstances", conn)
    
    # Grid for Instance Switches
    for index, row in instances.iterrows():
        col_name, col_switch = st.columns([3, 1])
        col_name.write(f"**{row['FriendlyName']}** ({row['ServerName']})")
        
        # The Switch UI
        is_on = col_switch.toggle("Active", value=bool(row['IsActive']), key=f"sw_{row['ServerName']}")
        
        # Update database if switch state changes
        if is_on != bool(row['IsActive']):
            with get_central_conn() as conn:
                conn.cursor().execute(
                    "UPDATE ManagedInstances SET IsActive = ? WHERE ServerName = ?",
                    (1 if is_on else 0, row['ServerName'])
                )
                conn.commit()
            st.rerun()