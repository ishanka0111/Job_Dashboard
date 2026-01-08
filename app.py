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

# Initialize session state for active tab tracking
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# Sidebar Logic (Global)
st.sidebar.header("🕹️ Control Center")

last_sync = get_collection_status()
if last_sync:
    st.sidebar.info(f"📅 Last Sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")

if st.sidebar.button("🔄 Sync Now", use_container_width=True):
    with st.spinner("Collecting data..."):
        try:
            results = run_collection()
            if results['failed']:
                st.sidebar.warning(f"⚠️ {len(results['failed'])} instance(s) failed")
                with st.sidebar.expander("View Errors"):
                    for err in results['failed']:
                        st.write(f"❌ {err}")
            st.sidebar.success(f"✅ Collected {results['total_jobs_collected']} job records")
            st.cache_resource.clear()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ Collection failed: {str(e)}")

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

st.title("SQL Server Agent Jobs Monitoring Dashboard")

# Custom Tab Navigation with Session State
tab_titles = [
    "📊 Overview Dashboard",
    "⚠️ 24-Hour Failures",
    "⚡ Performance Analytics",
    "⚙️ Instance Management"
]

# Create clickable navigation using columns
cols = st.columns(len(tab_titles))
for idx, (col, title) in enumerate(zip(cols, tab_titles)):
    with col:
        if st.button(
            title,
            key=f"tab_{idx}",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == idx else "secondary"
        ):
            st.session_state.active_tab = idx
            st.rerun()

st.divider()

# Render only the active tab
if st.session_state.active_tab == 0:
    overview.render()
elif st.session_state.active_tab == 1:
    failures.render()
elif st.session_state.active_tab == 2:
    performance.render()
elif st.session_state.active_tab == 3:
    management.render()

st.divider()
st.caption("SQL Server Agent Jobs Monitoring Dashboard | Developed by Database Team | Softlogiclife © 2025")