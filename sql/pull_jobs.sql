-- This is the query the Python worker uses to pull data from office servers
SELECT 
    @@SERVERNAME as ServerName, 
    j.name as JobName, 
    CASE jh.run_status WHEN 1 THEN 'Succeeded' WHEN 0 THEN 'Failed' ELSE 'Other' END as Status,
    msdb.dbo.agent_datetime(jh.run_date, jh.run_time) as LastRun,
    jh.message as ErrorMessage
FROM msdb.dbo.sysjobs j
JOIN msdb.dbo.sysjobhistory jh ON j.job_id = jh.job_id
WHERE jh.instance_id = (SELECT MAX(instance_id) FROM msdb.dbo.sysjobhistory WHERE job_id = j.job_id);



-- -- Query to get the dashboard data
-- SELECT * FROM v_PersistentDashboard;

-- -- Query to add a new server via UI
-- INSERT INTO ManagedInstances (ServerName, FriendlyName, IsActive) VALUES (?, ?, 1);

-- -- Query to deactivate a server
-- UPDATE ManagedInstances SET IsActive = 0 WHERE ServerName = ?;