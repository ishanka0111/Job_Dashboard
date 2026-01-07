import pyodbc
from config import DB_CONFIG
from datetime import datetime

def parse_sql_duration(duration_hhmmss):
    """Convert SQL Server duration format (HHMMSS) to seconds"""
    if not duration_hhmmss or duration_hhmmss == 0:
        return 0
    
    duration_str = str(duration_hhmmss).zfill(6)
    hours = int(duration_str[:-4] or 0)
    minutes = int(duration_str[-4:-2])
    seconds = int(duration_str[-2:])
    
    return hours * 3600 + minutes * 60 + seconds

def run_collection():
    """Enhanced collection with error handling and performance metrics"""
    central_conn = pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection=yes;"
    )
    cursor = central_conn.cursor()
    
    # Get active instances
    cursor.execute("SELECT ServerName, FriendlyName FROM ManagedInstances WHERE IsActive = 1")
    instances = cursor.fetchall()
    cursor.execute("""
        TRUNCATE TABLE JobLogs 
    """)
    
    # Read enhanced query
    with open('sql/pull_jobs.sql', 'r', encoding='utf-8') as f:
        full_content = f.read()
        
        # Extract the main SELECT query, stopping at the separator comment line
        lines = full_content.split('\n')
        query_lines = []
        in_query = False
        
        for line in lines:
            stripped = line.strip()
            # Start collecting when we hit SELECT
            if stripped.upper().startswith('SELECT'):
                in_query = True
            # Stop at the separator (lines with multiple dashes)
            if '-- --' in line or '====' in line:
                break
            # Collect query lines
            if in_query:
                query_lines.append(line)
        
        job_query = '\n'.join(query_lines).strip()
        
        # Fallback: if query is empty, just take everything
        if not job_query or len(job_query) < 50:
            # Find the first SELECT and take everything after
            select_pos = full_content.upper().find('SELECT')
            if select_pos >= 0:
                job_query = full_content[select_pos:].strip()
    
    collection_results = {
        'success': [],
        'failed': [],
        'total_jobs_collected': 0
    }
    
    for svr_name, friendly_name in instances:
        try:
            # Connect to remote msdb
            remote_str = (
                f"DRIVER={DB_CONFIG['driver']};"
                f"SERVER={svr_name};"
                f"DATABASE=msdb;"
                f"Trusted_Connection=yes;"
            )
            
            with pyodbc.connect(remote_str, timeout=10) as remote_conn:
                data = remote_conn.cursor().execute(job_query).fetchall()

                jobs_inserted = 0
                for row in data:
                    # Parse duration from HHMMSS format
                    duration_seconds = parse_sql_duration(row[5])
                    
                    cursor.execute("""
                        INSERT INTO JobLogs 
                        (ServerName, JobName, Status, LastRun, ErrorMessage, 
                         DurationSeconds, CPUTimeMS, StepCount) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row[0],  # ServerName
                        row[1],  # JobName
                        row[2],  # Status
                        row[3],  # LastRun
                        row[4],  # ErrorMessage
                        duration_seconds,  # DurationSeconds (parsed)
                        row[6],  # CPUTimeMS
                        row[7]   # StepCount
                    ))
                    jobs_inserted += 1
                
                central_conn.commit()
                collection_results['success'].append(friendly_name or svr_name)
                collection_results['total_jobs_collected'] += jobs_inserted
                
        except pyodbc.Error as e:
            error_msg = f"Database error on {friendly_name or svr_name}: {str(e)}"
            collection_results['failed'].append(error_msg)
            print(error_msg)
            
        except Exception as e:
            error_msg = f"Error reaching {friendly_name or svr_name}: {str(e)}"
            collection_results['failed'].append(error_msg)
            print(error_msg)
    
    central_conn.close()
    return collection_results

def get_collection_status():
    """Get the last collection timestamp"""
    try:
        conn = pyodbc.connect(
            f"DRIVER={DB_CONFIG['driver']};"
            f"SERVER={DB_CONFIG['server']};"
            f"DATABASE={DB_CONFIG['database']};"
            f"Trusted_Connection=yes;"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(CapturedAt) FROM JobLogs")
        last_capture = cursor.fetchone()[0]
        conn.close()
        return last_capture
    except:
        return None