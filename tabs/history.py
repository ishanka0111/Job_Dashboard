import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import fetch_data

def render():
    st.title("📈 Job Execution History")
    
    instances_list = fetch_data(
        "SELECT DISTINCT ServerName, FriendlyName FROM ManagedInstances WHERE IsActive = 1"
    )
    
    if instances_list.empty:
        st.warning("⚠️ No active instances configured.")
        return

    col1, col2 = st.columns(2)
    with col1:
        selected_instance = st.selectbox(
            "Select Instance",
            options=instances_list['ServerName'].tolist(),
            format_func=lambda x: instances_list[instances_list['ServerName']==x]['FriendlyName'].iloc[0]
        )
    
    with col2:
        jobs_list = fetch_data(
            "SELECT DISTINCT JobName FROM JobLogs WHERE ServerName = ? ORDER BY JobName",
            params=[selected_instance]
        )
        selected_job = st.selectbox("Select Job", options=jobs_list['JobName'].tolist()) if not jobs_list.empty else None

    if selected_instance and selected_job:
        job_history = fetch_data("""
            SELECT TOP 50 LastRun, Status, DurationSeconds, CPUTimeMS, ErrorMessage
            FROM JobLogs WHERE ServerName = ? AND JobName = ?
            ORDER BY LastRun DESC
        """, params=[selected_instance, selected_job])
        
        if not job_history.empty:
            st.subheader(f"⏱️ Last 50 Executions: {selected_job}")
            # Map colors for the chart
            job_history['StatusColor'] = job_history['Status'].map({
                'Succeeded': 'green', 'Failed': 'red', 'Other': 'gray'
            })
            
            fig = go.Figure(go.Bar(
                x=job_history['LastRun'],
                y=job_history['DurationSeconds'],
                marker_color=job_history['StatusColor']
            ))
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(job_history.drop(columns=['StatusColor']), use_container_width=True, hide_index=True)