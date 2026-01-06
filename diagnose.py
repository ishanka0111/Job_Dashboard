"""
Quick Fix Test - Run this to verify the fix
"""

import os

print("="*70)
print("QUICK FIX - VERIFYING SQL QUERY FILE")
print("="*70)
print()

# Check if file exists
query_path = 'sql/pull_jobs.sql'
if not os.path.exists(query_path):
    print(f"✗ File not found: {query_path}")
    print("  Please ensure sql/pull_jobs.sql exists")
    exit(1)

print(f"✓ File exists: {query_path}")
print()

# Read and display the content
with open(query_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File size: {len(content)} characters")
print()

# Show first few lines
lines = content.split('\n')
print(f"Total lines: {len(lines)}")
print()
print("First 10 lines:")
print("-" * 70)
for i, line in enumerate(lines[:10], 1):
    print(f"{i:2}: {line}")
print("-" * 70)
print()

# Extract the query (same logic as worker.py)
query_lines = []
in_query = False

for line in lines:
    stripped = line.strip()
    if stripped.upper().startswith('SELECT'):
        in_query = True
    if '-- --' in line or '====' in line:
        break
    if in_query:
        query_lines.append(line)

job_query = '\n'.join(query_lines).strip()

if not job_query or len(job_query) < 50:
    # Fallback
    select_pos = content.upper().find('SELECT')
    if select_pos >= 0:
        job_query = content[select_pos:].strip()

print(f"Extracted query length: {len(job_query)} characters")
print()

if len(job_query) < 50:
    print("✗ ERROR: Query is too short or empty!")
    print()
    print("The sql/pull_jobs.sql file should start with SELECT")
    print("and contain the full query to retrieve job data.")
    print()
    print("Please replace the content of sql/pull_jobs.sql with:")
    print("-" * 70)
    print("""SELECT 
    @@SERVERNAME as ServerName,
    j.name as JobName,
    CASE jh.run_status 
        WHEN 1 THEN 'Succeeded' 
        WHEN 0 THEN 'Failed' 
        WHEN 2 THEN 'Retry'
        WHEN 3 THEN 'Canceled'
        ELSE 'Other' 
    END as Status,
    msdb.dbo.agent_datetime(jh.run_date, jh.run_time) as LastRun,
    ISNULL(jh.message, '') as ErrorMessage,
    jh.run_duration as DurationRaw,
    CASE 
        WHEN jh.run_status = 1 AND jh.run_duration > 0 
        THEN jh.run_duration * 10
        ELSE 0 
    END as CPUTimeMS,
    (SELECT COUNT(*) 
     FROM msdb.dbo.sysjobhistory jh2 
     WHERE jh2.job_id = j.job_id 
       AND jh2.run_date = jh.run_date 
       AND jh2.run_time = jh.run_time
       AND jh2.step_id > 0) as StepCount
FROM msdb.dbo.sysjobs j
INNER JOIN msdb.dbo.sysjobhistory jh 
    ON j.job_id = jh.job_id
WHERE jh.step_id = 0
ORDER BY jh.run_date DESC, jh.run_time DESC;""")
    print("-" * 70)
else:
    print("✓ Query extracted successfully!")
    print()
    print("Query preview:")
    print("-" * 70)
    print(job_query[:300] + "..." if len(job_query) > 300 else job_query)
    print("-" * 70)
    print()
    print("✓ Everything looks good!")
    print()
    print("Next steps:")
    print("1. Run: python worker.py")
    print("2. Or use the Streamlit UI: streamlit run app.py")

print()
print("="*70)