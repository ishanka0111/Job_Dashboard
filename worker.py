import pyodbc
from config import DB_CONFIG

def run_collection():
    # 1. Connect to Central DB
    central_conn = pyodbc.connect(f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};Trusted_Connection=yes;")
    cursor = central_conn.cursor()
    
    # 2. Get active instances
    cursor.execute("SELECT ServerName FROM ManagedInstances WHERE IsActive = 1")
    instances = [row[0] for row in cursor.fetchall()]

    # 3. Read Query from File
    with open('sql/pull_jobs.sql', 'r') as f:
        job_query = f.read()

    for svr in instances:
        try:
            # Connect to Remote msdb
            remote_str = f"DRIVER={DB_CONFIG['driver']};SERVER={svr};DATABASE=msdb;Trusted_Connection=yes;"
            with pyodbc.connect(remote_str, timeout=5) as remote_conn:
                data = remote_conn.cursor().execute(job_query).fetchall()
                for row in data:
                    cursor.execute("""
                        INSERT INTO JobLogs (ServerName, JobName, Status, LastRun, ErrorMessage) 
                        VALUES (?, ?, ?, ?, ?)""", (row[0], row[1], row[2], row[3], row[4]))
                central_conn.commit()
        except Exception as e:
            # Re-raise or log so the UI can catch it
            raise Exception(f"Error reaching {svr}: {str(e)}")
    central_conn.close()