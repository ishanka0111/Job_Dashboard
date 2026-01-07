import streamlit as st

from worker import run_collection, get_collection_status
from database import get_central_conn
# Import your new tab modules
from tabs import overview, failures, performance, management

st.set_page_config(
    page_title="SQL Server Agent Jobs Monitoring Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar Logic (Global)
st.sidebar.header("🕹️ Control Center")


last_sync = get_collection_status()
if last_sync:
    st.sidebar.info(f"📅 Last Sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")





if st.sidebar.button("🔄 Sync Now", use_container_width=True):
    with st.spinner("Collecting data..."):
        run_collection()
        st.cache_resource.clear()
        st.rerun()


st.sidebar.divider()

# Add new instance form
with st.sidebar.expander("➕ Add New Instance", expanded=False):
    with st.form("add_form", clear_on_submit=True):
        new_label = st.text_input("Name", placeholder="Production")
        new_svr = st.text_input("Instance Name", placeholder="10.xxx.xxx.xxx\InstanceName")
        new_hostname = st.text_input("Host Name", placeholder="LKELSFETEGTRPT")
        
        if st.form_submit_button("Add Server", use_container_width=True):
            if new_svr and new_label:
                try:
                    conn = get_central_conn()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO ManagedInstances (ServerName, FriendlyName, IsActive, Hostname) VALUES (?,?,1,?)",
                        new_svr, new_label, new_hostname
                    )
                    conn.commit()
                    st.success(f"Added {new_label}")
                    st.cache_resource.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add: {str(e)}")
            else:
                st.warning("Please fill all fields")

st.title(" SQL Server Agent Jobs Monitoring Dashboard ")
# Main Tabs Setup
tab_titles = [
    "📊 Overview Dashboard",
    "⚠️ 24-Hour Failures",
    # "📈 Job Execution History",
    "⚡ Performance Analytics",
    "⚙️ Instance Management"
]
t1, t2, t4, t5 = st.tabs(tab_titles)

# Lazy Loading: Logic only runs when the tab is active
with t1:
    overview.render()

with t2:
    failures.render()

# with t3:
#     history.render()

with t4:
    performance.render()

with t5:
    management.render()

st.divider()
st.caption("SQL Server Agent Jobs Monitoring Dashboard | Developed by Database Team | Softlogiclife © 2025")