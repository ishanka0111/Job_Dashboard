import streamlit as st
import plotly.express as px
from database import get_performance_trends

def render():
    st.title("⚡ Performance Analytics")
    
    perf_trends = get_performance_trends()
    
    if perf_trends.empty:
        st.warning("⚠️ No performance data available.")
        return

    # Simple instance selector - just one at a time
    all_instances = perf_trends['FriendlyName'].unique().tolist()
    
    selected_instance = st.selectbox(
        "Select Instance",
        options=all_instances,
        key="perf_selector"
    )
    
    if not selected_instance:
        return
    
    filtered = perf_trends[perf_trends['FriendlyName'] == selected_instance]
    st.divider()


    # filtered = perf_trends[perf_trends['FriendlyName'].isin(selected_instances)]
    
    # Duration Trends
    st.subheader("📊 Average Duration Trends (30 Days)")
    
    # Limit jobs shown if too many
    unique_jobs = filtered['JobName'].nunique()
    if unique_jobs > 15:  # Reduced from 20 for faster rendering
        st.info(f"ℹ️ {unique_jobs} jobs found. Showing top 15 by max duration for better performance.")
        top_jobs = (filtered.groupby('JobName')['MaxDuration']
                   .max()
                   .sort_values(ascending=False)
                   .head(15)
                   .index.tolist())
        filtered_chart = filtered[filtered['JobName'].isin(top_jobs)]
    else:
        filtered_chart = filtered
    
    # Only show chart if reasonable amount of data
    if len(filtered_chart) < 1000:
        fig_duration = px.line(
            filtered_chart,
            x='RunDate',
            y='AvgDuration',
            color='JobName',
            facet_col='FriendlyName',
            facet_col_wrap=2,
            title='Job Duration Trends by Instance',
            labels={'AvgDuration': 'Average Duration (seconds)'}
        )
        fig_duration.update_layout(height=500, showlegend=True)
        fig_duration.update_xaxes(title_text='Date')
        st.plotly_chart(fig_duration, use_container_width=True, key="duration_chart")
    else:
        st.warning("Too much data to display chart. Please select fewer instances or jobs.")
    









    st.divider()
    
    # Simple table - Top 10 slowest jobs
    st.subheader("🐌 Top 10 Slowest Jobs")
    
    top_slow = (filtered.groupby('JobName')['MaxDuration']
               .max()
               .sort_values(ascending=False)
               .head(10))
    
    st.dataframe(
        top_slow.reset_index().rename(columns={
            'JobName': 'Job Name',
            'MaxDuration': 'Max Duration (seconds)'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    # Simple table - Jobs with failures
    st.subheader("❌ Jobs with Failures")
    
    summary = filtered.groupby('JobName').agg({
        'ExecutionCount': 'sum',
        'FailureCount': 'sum'
    }).reset_index()
    
    failed_jobs = summary[summary['FailureCount'] > 0].sort_values('FailureCount', ascending=False)
    
    if not failed_jobs.empty:
        st.dataframe(
            failed_jobs.rename(columns={
                'JobName': 'Job Name',
                'ExecutionCount': 'Total Runs',
                'FailureCount': 'Failures'
            }),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.success("✅ All jobs successful!")