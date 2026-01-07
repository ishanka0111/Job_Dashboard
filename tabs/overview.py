import streamlit as st
import plotly.express as px
from database import fetch_data

def render():
    st.title("🎯 Overview")
    dashboard_df = fetch_data("SELECT * FROM v_EnhancedDashboard WHERE IsActive = 1")
    health_summary = fetch_data("SELECT * FROM v_InstanceHealthSummary WHERE IsActive = 1")
    
    if dashboard_df.empty:
        st.warning("⚠️ No job data available.")
        return

    col1, col2, col3, col4 = st.columns(4)
    total_jobs = len(dashboard_df)
    failed_jobs = len(dashboard_df[dashboard_df['Status'] == 'Failed'])
    success_rate = ((total_jobs - failed_jobs) / total_jobs * 100) if total_jobs > 0 else 0
    
    col1.metric("📦 Total Jobs", total_jobs)
    col2.metric("❌ Failed Jobs", failed_jobs, delta=f"-{failed_jobs}", delta_color="inverse")
    col3.metric("✅ Success Rate", f"{success_rate:.1f}%")
    col4.metric("🖥️ Active Instances", len(health_summary))


    st.divider()
    
    # Instance Health Overview
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("🏥 Instance Health Status")
        if not health_summary.empty:
            # Create status indicator
            health_display = health_summary.copy()
            health_display['Status'] = health_display['FailuresLast24h'].apply(
                lambda x: '🔴 Critical' if x > 5 else ('🟡 Warning' if x > 0 else '🟢 Healthy')
            )
    
            
            st.dataframe(
                health_display[[
                    'FriendlyName', 'ServerName', 'Status'
                ]].rename(columns={
                    'FriendlyName': 'Instance Name',
                    'ServerName': 'Instance'
                }),
                use_container_width=True,
                hide_index=True
            )
    
    with col_right:
        st.subheader("📊 Status Distribution")
        status_counts = dashboard_df['Status'].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            color=status_counts.index,
            color_discrete_map={
                'Succeeded': '#22c55e',
                'Failed': '#ef4444',
                'Other': '#94a3b8'
            },
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Critical Failures Table
    st.subheader("🚨 Critical Jobs Requiring Attention")
    failed_df = dashboard_df[dashboard_df['Status'] == 'Failed'].sort_values('LastRun', ascending=False)
    
    if not failed_df.empty:
        # Handle NULL values
        failed_df['DurationSeconds'] = failed_df['DurationSeconds'].fillna(0)
        failed_df['ErrorMessage'] = failed_df['ErrorMessage'].fillna('No error message')
        
        st.dataframe(
            failed_df[[
                'FriendlyName', 'JobName', 'LastRun', 
                'DurationSeconds', 'ErrorMessage'
            ]].rename(columns={
                'FriendlyName': 'Instance',
                'JobName': 'Job Name',
                'LastRun': 'Failed At',
                'DurationSeconds': 'Duration(s)',
                'ErrorMessage': 'Error Details'
            }),
            use_container_width=True,
            hide_index=True,
            column_config={
                'Error Details': st.column_config.TextColumn(width="large")
            }
        )
    else:
        st.success("🎉 All jobs are running successfully!")
