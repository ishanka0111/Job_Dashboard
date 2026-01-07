import streamlit as st
from database import fetch_data, get_central_conn

def render():
    st.title("⚙️ Instance Management")
    conn = get_central_conn()
    instances = fetch_data("SELECT ServerName, FriendlyName, IsActive FROM ManagedInstances ORDER BY FriendlyName")
    
    for idx, row in instances.iterrows():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        col1.write(f"**{row['FriendlyName']}**")
        col2.write(f"`{row['ServerName']}`")
        
        if col3.toggle("Active", value=bool(row['IsActive']), key=f"t_{idx}"):
            # Logic to update IsActive in DB would go here
            pass
            
        if col4.button("🗑️", key=f"d_{idx}"):
            # Logic to delete instance would go here
            st.rerun()

    st.divider()
    st.subheader("🧹 Data Maintenance")
    days = st.number_input("Days to keep", 7, 365, 90)
    if st.button("Clean Old Data"):
        cursor = conn.cursor()
        cursor.execute("EXEC sp_CleanupOldLogs @DaysToKeep = ?", days)
        conn.commit()
        st.success("Cleanup complete.")