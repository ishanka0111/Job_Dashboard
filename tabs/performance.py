import streamlit as st
import plotly.express as px
from database import fetch_data

def render():
    st.title("⚡ Performance Analytics")
    
    perf_trends = fetch_data("""
        SELECT * FROM v_PerformanceTrends 
        WHERE RunDate >= DATEADD(day, -30, GETDATE())
        ORDER BY RunDate DESC
    """)
    
    if perf_trends.empty:
        st.warning("No performance data available for the last 30 days.")
        return

    selected_instances = st.multiselect(
        "Select Instances",
        options=perf_trends['FriendlyName'].unique(),
        default=perf_trends['FriendlyName'].unique()[:3]
    )
    
    if selected_instances:
        filtered = perf_trends[perf_trends['FriendlyName'].isin(selected_instances)]
        
        st.subheader("📊 Duration Trends")
        fig = px.line(filtered, x='RunDate', y='AvgDuration', color='JobName', facet_col='FriendlyName')
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Top 10 Longest Running Jobs**")
            st.table(filtered.groupby('JobName')['MaxDuration'].max().sort_values(ascending=False).head(10))