import streamlit as st
from database import get_failures_24h

def render():
    st.title("⚠️ Last 24 Hours - Failures")
    
    failures_24h = get_failures_24h()
    
    if failures_24h.empty:
        st.success("🎉 No failures in the last 24 hours!")
        return
    
    # Simple metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Failures", len(failures_24h))
    col2.metric("Instances Affected", failures_24h['FriendlyName'].nunique())
    col3.metric("Jobs Affected", failures_24h['JobName'].nunique())
    
    st.divider()
    
    # Simple table - no filters, no charts
    st.dataframe(
        failures_24h[[
            'FriendlyName', 'JobName', 'LastRun', 'ErrorMessage'
        ]].rename(columns={
            'FriendlyName': 'Instance',
            'JobName': 'Job Name',
            'LastRun': 'Failed At',
            'ErrorMessage': 'Error'
        }),
        use_container_width=True,
        hide_index=True
    )