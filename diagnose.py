"""
Check what's actually in your SQL_Monitoring database
"""

import pyodbc
from config import DB_CONFIG

print("="*70)
print("DATABASE STATUS CHECK")
print("="*70)
print()

try:
    conn = pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection=yes;"
    )
    cursor = conn.cursor()
    
    # Check 1: ManagedInstances
    print("1. Managed Instances:")
    print("-" * 70)
    cursor.execute("SELECT ServerName, FriendlyName, IsActive, DateAdded FROM ManagedInstances")
    instances = cursor.fetchall()
    
    if instances:
        for idx, (svr, fname, active, added) in enumerate(instances, 1):
            status = "✓ ACTIVE" if active else "✗ INACTIVE"
            print(f"  [{idx}] {fname}")
            print(f"      Server: {svr}")
            print(f"      Status: {status}")
            print(f"      Added: {added}")
            print()
    else:
        print("  ⚠ No instances configured!")
        print("  → Add instances via the web UI sidebar")
    
    print()
    
    # Check 2: JobLogs
    print("2. Job Logs:")
    print("-" * 70)
    cursor.execute("SELECT COUNT(*) FROM JobLogs")
    total_logs = cursor.fetchone()[0]
    print(f"  Total records: {total_logs}")
    
    if total_logs > 0:
        # Show latest records
        cursor.execute("""
            SELECT TOP 5 
                ServerName, JobName, Status, LastRun, CapturedAt
            FROM JobLogs 
            ORDER BY CapturedAt DESC
        """)
        print()
        print("  Latest 5 records:")
        for svr, job, status, lastrun, captured in cursor.fetchall():
            print(f"    - {svr}: {job[:30]:<30} [{status}] at {lastrun}")
        
        # Show breakdown by status
        cursor.execute("""
            SELECT Status, COUNT(*) as Count
            FROM JobLogs
            GROUP BY Status
        """)
        print()
        print("  Status breakdown:")
        for status, count in cursor.fetchall():
            print(f"    - {status}: {count}")
        
        # Show last sync time
        cursor.execute("SELECT MAX(CapturedAt) FROM JobLogs")
        last_sync = cursor.fetchone()[0]
        print()
        print(f"  Last sync: {last_sync}")
    else:
        print("  ⚠ No job data collected yet!")
        print()
        print("  Possible reasons:")
        print("  1. Sync hasn't been run yet")
        print("  2. Remote servers are unreachable")
        print("  3. No SQL Agent jobs exist on remote servers")
        print("  4. Permission issues accessing msdb")
        print()
        print("  → Click '🔄 Sync Now' in the sidebar to collect data")
    
    print()
    
    # Check 3: Views
    print("3. Testing Views:")
    print("-" * 70)
    
    views = [
        ('v_EnhancedDashboard', 'Main dashboard data'),
        ('v_Last24HourFailures', '24-hour failure view'),
        ('v_InstanceHealthSummary', 'Instance health metrics')
    ]
    
    for view_name, description in views:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {view_name}: {count} row(s) - {description}")
        except Exception as e:
            print(f"  ✗ {view_name}: ERROR - {str(e)[:50]}")
    
    print()
    
    # Check 4: Active instances with job data
    print("4. Active Instances with Data:")
    print("-" * 70)
    cursor.execute("""
        SELECT 
            mi.FriendlyName,
            mi.ServerName,
            COUNT(jl.LogID) as JobCount
        FROM ManagedInstances mi
        LEFT JOIN JobLogs jl ON mi.ServerName = jl.ServerName
        WHERE mi.IsActive = 1
        GROUP BY mi.FriendlyName, mi.ServerName
    """)
    
    active_instances = cursor.fetchall()
    if active_instances:
        for fname, svr, count in active_instances:
            if count > 0:
                print(f"  ✓ {fname} ({svr}): {count} job record(s)")
            else:
                print(f"  ⚠ {fname} ({svr}): NO DATA - sync needed!")
    else:
        print("  ⚠ No active instances found!")
    
    print()
    
    conn.close()
    
    print("="*70)
    print("RECOMMENDATIONS:")
    print("="*70)
    
    if not instances:
        print("→ Add SQL Server instances via the web UI")
    elif total_logs == 0:
        print("→ Run sync to collect job data:")
        print("  1. Open the web UI")
        print("  2. Click '🔄 Sync Now' in the sidebar")
        print("  OR")
        print("  3. Run: python worker.py")
    elif any(count == 0 for _, _, count in active_instances):
        print("→ Some instances have no data - check connectivity")
        print("  Run: python test_remote_connection.py")
    else:
        print("✓ Everything looks good!")
        print("  If dashboard shows 'No data', try:")
        print("  1. Refresh the page (Ctrl+R)")
        print("  2. Check browser console for errors")
        print("  3. Verify views with: SELECT * FROM v_EnhancedDashboard")
    
    print("="*70)
    
except Exception as e:
    print(f"✗ Error connecting to database: {e}")
    print()
    print("Check:")
    print("1. SQL Server is running")
    print("2. config.py has correct server name")
    print("3. Database SQL_Monitoring exists")
    print("4. You have permissions to access it")