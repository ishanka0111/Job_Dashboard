import streamlit as st
import plotly.express as px
from database import fetch_data

def render():
    st.title("⚠️ Last 24 Hours - Failure Analysis")
    failures_24h = fetch_data("SELECT * FROM v_Last24HourFailures")
    
    if not failures_24h.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Failures", len(failures_24h))
        col2.metric("Affected Instances", failures_24h['FriendlyName'].nunique())
        col3.metric("Affected Jobs", failures_24h['JobName'].nunique())
        col4.metric("Avg Time Ago", f"{failures_24h['MinutesAgo'].mean():.0f} min")
        
        st.divider()
        
        # Timeline chart
        st.subheader("📉 Failure Timeline")
        
        # Handle NULL durations
        failures_24h['DurationSeconds'] = failures_24h['DurationSeconds'].fillna(1)
        
        fig = px.scatter(
            failures_24h,
            x='LastRun',
            y='JobName',
            color='FriendlyName',
            size='DurationSeconds',
            hover_data=['ErrorMessage'],
            title='Job Failures Over Last 24 Hours'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Detailed failure table
        st.subheader("📋 Detailed Failure Log")
        
        # Filter options
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            selected_instance = st.multiselect(
                "Filter by Instance",
                options=failures_24h['FriendlyName'].unique(),
                default=None
            )
        with col_filter2:
            selected_job = st.multiselect(
                "Filter by Job",
                options=failures_24h['JobName'].unique(),
                default=None
            )
        
        # Apply filters
        filtered_df = failures_24h.copy()
        if selected_instance:
            filtered_df = filtered_df[filtered_df['FriendlyName'].isin(selected_instance)]
        if selected_job:
            filtered_df = filtered_df[filtered_df['JobName'].isin(selected_job)]
        
        st.dataframe(
            filtered_df[[
                'FriendlyName', 'JobName', 'LastRun', 
                'MinutesAgo', 'DurationSeconds', 'ErrorMessage'
            ]].rename(columns={
                'FriendlyName': 'Instance',
                'JobName': 'Job Name',
                'LastRun': 'Failed At',
                'MinutesAgo': 'Minutes Ago',
                'DurationSeconds': 'Duration (s)',
                'ErrorMessage': 'Error Message'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("🎉 No failures in the last 24 hours!")

    # ... Paste your original Tab 2 logic here ...