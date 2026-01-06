import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config import DB_CONFIG
from worker import run_collection, get_collection_status

st.set_page_config(
    page_title="SQL Monitoring Pro - Enhanced",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

def get_central_conn():
    return pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection=yes;"
    )

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("🕹️ Control Center")

# Display last sync time
last_sync = get_collection_status()
if last_sync:
    st.sidebar.info(f"📅 Last Sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.sidebar.warning("⚠️ No data collected yet")

# Manual sync button
if st.sidebar.button("🔄 Sync Now", use_container_width=True):
    with st.spinner("Collecting data from all active instances..."):
        try:
            results = run_collection()
            if results['failed']:
                st.sidebar.warning(f"⚠️ {len(results['failed'])} instance(s) failed")
                with st.sidebar.expander("View Errors"):
                    for err in results['failed']:
                        st.write(f"❌ {err}")
            st.sidebar.success(f"✅ Collected {results['total_jobs_collected']} job records")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ Collection failed: {str(e)}")

st.sidebar.divider()

# Add new instance form
with st.sidebar.expander("➕ Add New Instance", expanded=False):
    with st.form("add_form", clear_on_submit=True):
        new_svr = st.text_input("Server IP/Hostname", placeholder="SQL-SERVER-01")
        new_label = st.text_input("Friendly Name", placeholder="Production Server")
        if st.form_submit_button("Add Server", use_container_width=True):
            if new_svr and new_label:
                try:
                    with get_central_conn() as conn:
                        conn.cursor().execute(
                            "INSERT INTO ManagedInstances (ServerName, FriendlyName, IsActive) VALUES (?,?,1)",
                            new_svr, new_label
                        )
                        conn.commit()
                    st.success(f"Added {new_label}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add: {str(e)}")
            else:
                st.warning("Please fill both fields")

# --- MAIN TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview Dashboard",
    "⚠️ 24-Hour Failures",
    "📈 Job Execution History",
    "⚡ Performance Analytics",
    "⚙️ Instance Management"
])

# ============ TAB 1: OVERVIEW DASHBOARD ============
with tab1:
    st.title("🎯 SQL Job Monitoring - Overview")
    
    with get_central_conn() as conn:
        # Get summary data
        dashboard_df = pd.read_sql("SELECT * FROM v_EnhancedDashboard", conn)
        health_summary = pd.read_sql("SELECT * FROM v_InstanceHealthSummary WHERE IsActive = 1", conn)
    
    # Top KPI Row
    col1, col2, col3, col4 = st.columns(4)
    
    total_jobs = len(dashboard_df)
    failed_jobs = len(dashboard_df[dashboard_df['Status'] == 'Failed'])
    success_rate = ((total_jobs - failed_jobs) / total_jobs * 100) if total_jobs > 0 else 0
    active_instances = len(health_summary)
    
    col1.metric("📦 Total Jobs", total_jobs)
    col2.metric("❌ Failed Jobs", failed_jobs, delta=f"-{failed_jobs}", delta_color="inverse")
    col3.metric("✅ Success Rate", f"{success_rate:.1f}%", delta=f"{success_rate:.1f}%")
    col4.metric("🖥️ Active Instances", active_instances)
    
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
                    'FriendlyName', 'Status', 'TotalJobs', 
                    'FailuresLast24h', 'AvgJobDuration', 'LastDataCollection'
                ]].rename(columns={
                    'FriendlyName': 'Instance',
                    'TotalJobs': 'Jobs',
                    'FailuresLast24h': 'Failures (24h)',
                    'AvgJobDuration': 'Avg Duration (s)',
                    'LastDataCollection': 'Last Seen'
                }),
                use_container_width=True,
                hide_index=True
            )
    
    with col_right:
        st.subheader("📊 Status Distribution")
        if not dashboard_df.empty:
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
        st.dataframe(
            failed_df[[
                'FriendlyName', 'JobName', 'LastRun', 
                'DurationSeconds', 'ErrorMessage'
            ]].rename(columns={
                'FriendlyName': 'Instance',
                'JobName': 'Job Name',
                'LastRun': 'Failed At',
                'DurationSeconds': 'Duration (s)',
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

# ============ TAB 2: 24-HOUR FAILURES ============
with tab2:
    st.title("⚠️ Last 24 Hours - Failure Analysis")
    
    with get_central_conn() as conn:
        failures_24h = pd.read_sql("SELECT * FROM v_Last24HourFailures", conn)
    
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

# ============ TAB 3: JOB EXECUTION HISTORY ============
with tab3:
    st.title("📈 Job Execution History")
    
    with get_central_conn() as conn:
        instances_list = pd.read_sql(
            "SELECT DISTINCT ServerName, FriendlyName FROM ManagedInstances WHERE IsActive = 1",
            conn
        )
    
    # Selection controls
    col1, col2 = st.columns(2)
    with col1:
        selected_instance = st.selectbox(
            "Select Instance",
            options=instances_list['ServerName'].tolist(),
            format_func=lambda x: instances_list[instances_list['ServerName']==x]['FriendlyName'].iloc[0]
        )
    
    with col2:
        with get_central_conn() as conn:
            jobs_list = pd.read_sql(
                f"SELECT DISTINCT JobName FROM JobLogs WHERE ServerName = '{selected_instance}' ORDER BY JobName",
                conn
            )
        selected_job = st.selectbox("Select Job", options=jobs_list['JobName'].tolist())
    
    if selected_instance and selected_job:
        with get_central_conn() as conn:
            job_history = pd.read_sql(f"""
                SELECT TOP 50
                    LastRun, Status, DurationSeconds, CPUTimeMS, ErrorMessage
                FROM JobLogs
                WHERE ServerName = '{selected_instance}' AND JobName = '{selected_job}'
                ORDER BY LastRun DESC
            """, conn)
        
        if not job_history.empty:
            # Execution timeline
            st.subheader("⏱️ Last 50 Executions")
            
            # Create status color mapping
            job_history['StatusColor'] = job_history['Status'].map({
                'Succeeded': 'green',
                'Failed': 'red',
                'Other': 'gray'
            })
            
            fig = go.Figure()
            
            # Add bars for duration
            fig.add_trace(go.Bar(
                x=job_history['LastRun'],
                y=job_history['DurationSeconds'],
                marker_color=job_history['StatusColor'],
                name='Duration',
                hovertemplate='<b>%{x}</b><br>Duration: %{y}s<br>Status: %{customdata}<extra></extra>',
                customdata=job_history['Status']
            ))
            
            fig.update_layout(
                title=f'Execution Timeline: {selected_job}',
                xaxis_title='Execution Time',
                yaxis_title='Duration (seconds)',
                height=400,
                hovermode='closest'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Performance metrics
            col1, col2, col3, col4 = st.columns(4)
            success_count = len(job_history[job_history['Status'] == 'Succeeded'])
            total_count = len(job_history)
            
            col1.metric("Success Rate", f"{(success_count/total_count*100):.1f}%")
            col2.metric("Avg Duration", f"{job_history['DurationSeconds'].mean():.1f}s")
            col3.metric("Max Duration", f"{job_history['DurationSeconds'].max():.1f}s")
            col4.metric("Executions", total_count)
            
            st.divider()
            
            # Detailed history table
            st.subheader("📊 Execution Details")
            st.dataframe(
                job_history[[
                    'LastRun', 'Status', 'DurationSeconds', 
                    'CPUTimeMS', 'ErrorMessage'
                ]].rename(columns={
                    'LastRun': 'Executed At',
                    'DurationSeconds': 'Duration (s)',
                    'CPUTimeMS': 'CPU Time (ms)',
                    'ErrorMessage': 'Error (if any)'
                }),
                use_container_width=True,
                hide_index=True
            )

# ============ TAB 4: PERFORMANCE ANALYTICS ============
with tab4:
    st.title("⚡ Performance Analytics")
    
    with get_central_conn() as conn:
        perf_trends = pd.read_sql("""
            SELECT * FROM v_PerformanceTrends 
            WHERE RunDate >= DATEADD(day, -30, GETDATE())
            ORDER BY RunDate DESC
        """, conn)
    
    if not perf_trends.empty:
        # Instance selector
        selected_instances_perf = st.multiselect(
            "Select Instances to Analyze",
            options=perf_trends['FriendlyName'].unique(),
            default=perf_trends['FriendlyName'].unique()[:3]  # Default to first 3
        )
        
        filtered_perf = perf_trends[perf_trends['FriendlyName'].isin(selected_instances_perf)]
        
        if not filtered_perf.empty:
            # Duration trend over time
            st.subheader("📊 Average Duration Trends (30 Days)")
            fig_duration = px.line(
                filtered_perf,
                x='RunDate',
                y='AvgDuration',
                color='JobName',
                facet_col='FriendlyName',
                facet_col_wrap=2,
                title='Job Duration Trends by Instance'
            )
            fig_duration.update_layout(height=500)
            st.plotly_chart(fig_duration, use_container_width=True)
            
            # CPU usage trend
            st.subheader("💻 CPU Usage Trends")
            fig_cpu = px.line(
                filtered_perf,
                x='RunDate',
                y='AvgCPU',
                color='JobName',
                facet_col='FriendlyName',
                facet_col_wrap=2,
                title='Average CPU Time by Instance'
            )
            fig_cpu.update_layout(height=500)
            st.plotly_chart(fig_cpu, use_container_width=True)
            
            # Failure rate heatmap
            st.subheader("🔥 Failure Rate Heatmap")
            failure_pivot = filtered_perf.pivot_table(
                values='FailureCount',
                index='JobName',
                columns='RunDate',
                aggfunc='sum',
                fill_value=0
            )
            
            fig_heat = px.imshow(
                failure_pivot,
                labels=dict(x="Date", y="Job Name", color="Failures"),
                color_continuous_scale='Reds',
                aspect='auto'
            )
            fig_heat.update_layout(height=400)
            st.plotly_chart(fig_heat, use_container_width=True)
            
            # Top resource consumers
            st.subheader("🏆 Top Resource Consumers")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Longest Running Jobs**")
                top_duration = filtered_perf.groupby(['FriendlyName', 'JobName'])['MaxDuration'].max().sort_values(ascending=False).head(10)
                st.dataframe(top_duration, use_container_width=True)
            
            with col2:
                st.write("**Highest CPU Usage Jobs**")
                top_cpu = filtered_perf.groupby(['FriendlyName', 'JobName'])['MaxCPU'].max().sort_values(ascending=False).head(10)
                st.dataframe(top_cpu, use_container_width=True)
        else:
            st.info("Please select at least one instance")
    else:
        st.warning("No performance data available for the last 30 days")

# ============ TAB 5: INSTANCE MANAGEMENT ============
with tab5:
    st.title("⚙️ Instance Management")
    
    with get_central_conn() as conn:
        instances = pd.read_sql(
            "SELECT ServerName, FriendlyName, IsActive FROM ManagedInstances ORDER BY FriendlyName",
            conn
        )
    
    st.caption("Toggle switches to activate/deactivate monitoring for each instance")
    
    # Create a grid layout
    for idx, row in instances.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.write(f"**{row['FriendlyName']}**")
            
            with col2:
                st.write(f"`{row['ServerName']}`")
            
            with col3:
                is_active = st.toggle(
                    "Active",
                    value=bool(row['IsActive']),
                    key=f"toggle_{row['ServerName']}",
                    label_visibility="collapsed"
                )
                
                # Update if changed
                if is_active != bool(row['IsActive']):
                    with get_central_conn() as conn:
                        conn.cursor().execute(
                            "UPDATE ManagedInstances SET IsActive = ? WHERE ServerName = ?",
                            (1 if is_active else 0, row['ServerName'])
                        )
                        conn.commit()
                    st.rerun()
            
            with col4:
                if st.button("🗑️", key=f"del_{row['ServerName']}", help="Delete instance"):
                    with get_central_conn() as conn:
                        conn.cursor().execute(
                            "DELETE FROM ManagedInstances WHERE ServerName = ?",
                            row['ServerName']
                        )
                        conn.commit()
                    st.rerun()
        
        st.divider()
    
    # Data cleanup section
    st.subheader("🧹 Data Maintenance")
    col1, col2 = st.columns(2)
    
    with col1:
        days_to_keep = st.number_input("Days of history to keep", min_value=7, max_value=365, value=90)
        if st.button("Clean Old Data", type="secondary"):
            with get_central_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("EXEC sp_CleanupOldLogs @DaysToKeep = ?", days_to_keep)
                rows_deleted = cursor.fetchone()[0]
                conn.commit()
            st.success(f"Deleted {rows_deleted} old records")
    
    with col2:
        with get_central_conn() as conn:
            stats = pd.read_sql("""
                SELECT 
                    COUNT(*) as TotalRecords,
                    MIN(LastRun) as OldestRecord,
                    MAX(LastRun) as NewestRecord
                FROM JobLogs
            """, conn)
        
        st.metric("Total Records", f"{stats['TotalRecords'].iloc[0]:,}")
        st.write(f"**Oldest:** {stats['OldestRecord'].iloc[0]}")
        st.write(f"**Newest:** {stats['NewestRecord'].iloc[0]}")

# Footer
st.divider()
st.caption("SQL Monitoring Pro - Enhanced Edition | Built with Streamlit & SQL Server")