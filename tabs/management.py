import streamlit as st
from database import get_instances, get_central_conn, clear_all_caches, fetch_static_data

def render():
    st.title("⚙️ Instance Management")
    
    # Data already preloaded - instant!
    instances = get_instances()
    
    if instances.empty:
        st.info("📋 No instances configured yet. Use the sidebar to add your first SQL Server instance.")
        return
    
    st.caption("Toggle switches to activate/deactivate monitoring for each instance")
    
    # Create a grid layout for instances
    for idx, row in instances.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.write(f"**{row['FriendlyName']}**")
                st.caption(f"Added: {row['DateAdded'].strftime('%Y-%m-%d')}")
            
            with col2:
                st.code(row['ServerName'], language=None)
            
            with col3:
                is_active = st.toggle(
                    "Active",
                    value=bool(row['IsActive']),
                    key=f"toggle_{idx}_{row['ServerName']}",
                    label_visibility="collapsed"
                )
                
                # Update if changed
                if is_active != bool(row['IsActive']):
                    try:
                        conn = get_central_conn()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE ManagedInstances SET IsActive = ?, LastModified = GETDATE() WHERE ServerName = ?",
                            (1 if is_active else 0, row['ServerName'])
                        )
                        conn.commit()
                        clear_all_caches()
                        st.success(f"Updated {row['FriendlyName']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update: {str(e)}")
            
            with col4:
                if st.button("🗑️", key=f"del_{idx}_{row['ServerName']}", help="Delete instance"):
                    try:
                        conn = get_central_conn()
                        cursor = conn.cursor()
                        # First delete related job logs
                        cursor.execute("DELETE FROM JobLogs WHERE ServerName = ?", row['ServerName'])
                        # Then delete the instance
                        cursor.execute("DELETE FROM ManagedInstances WHERE ServerName = ?", row['ServerName'])
                        conn.commit()
                        clear_all_caches()
                        st.success(f"Deleted {row['FriendlyName']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {str(e)}")
        
        st.divider()
    
    # Data Maintenance Section
    st.subheader("🧹 Data Maintenance")
    
    # col1, col2 = st.columns(2)
    
    # with col1:
    #     st.write("**Clean Old Records**")
    #     days_to_keep = st.number_input(
    #         "Days of history to keep",
    #         min_value=7,
    #         max_value=365,
    #         value=90,
    #         step=1,
    #         help="Delete job logs older than this many days"
    #     )
        
    #     if st.button("🗑️ Clean Old Data", type="secondary", use_container_width=True):
    #         with st.spinner("Cleaning old records..."):
    #             try:
    #                 conn = get_central_conn()
    #                 cursor = conn.cursor()
    #                 cursor.execute("EXEC sp_CleanupOldLogs @DaysToKeep = ?", days_to_keep)
    #                 result = cursor.fetchone()
    #                 rows_deleted = result[0] if result else 0
    #                 conn.commit()
    #                 clear_all_caches()
    #                 st.success(f"✅ Deleted {rows_deleted:,} old records")
    #             except Exception as e:
    #                 st.error(f"❌ Cleanup failed: {str(e)}")
    
    # with col2:
    st.write("**Database Statistics**")
    try:
        stats = fetch_static_data("""
            SELECT 
                COUNT(*) as TotalRecords,
                MIN(LastRun) as OldestRecord,
                MAX(LastRun) as NewestRecord,
                COUNT(DISTINCT ServerName) as UniqueServers
            FROM JobLogs
        """)
        
        if not stats.empty and stats['TotalRecords'].iloc[0] > 0:
            st.metric("Total Records", f"{stats['TotalRecords'].iloc[0]:,}")
            st.metric("Unique Servers", f"{stats['UniqueServers'].iloc[0]}")
            st.write(f"**Oldest:** {stats['OldestRecord'].iloc[0].strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**Newest:** {stats['NewestRecord'].iloc[0].strftime('%Y-%m-%d %H:%M')}")
        else:
            st.info("No job logs in database yet")
    except Exception as e:
        st.error(f"Error loading stats: {str(e)}")

    # st.divider()
    
    # # Quick Actions
    # st.subheader("⚡ Quick Actions")
    
    # col1, col2 = st.columns(2)
    
    # with col1:
    #     if st.button("🔄 Refresh Data", use_container_width=True):
    #         clear_all_caches()
    #         st.success("✅ Cache cleared! Data will refresh on next load.")
    #         st.rerun()
    
    # with col2:
    #     if st.button("📊 Export Instance List", use_container_width=True):
    #         # Create CSV export
    #         csv = instances[['FriendlyName', 'ServerName', 'IsActive', 'DateAdded']].to_csv(index=False)
    #         st.download_button(
    #             label="📥 Download CSV",
    #             data=csv,
    #             file_name=f"sql_instances_export.csv",
    #             mime="text/csv",
    #             use_container_width=True
    #         )