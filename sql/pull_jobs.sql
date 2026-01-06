SELECT 
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
ORDER BY jh.run_date DESC, jh.run_time DESC;