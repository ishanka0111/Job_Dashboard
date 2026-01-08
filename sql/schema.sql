CREATE DATABASE [SQL_Monitoring];

USE [SQL_Monitoring];

CREATE TABLE [dbo].[JobLogs](
	[LogID] [int] IDENTITY(1,1) NOT NULL,
	[ServerName] [nvarchar](128) NOT NULL,
	[JobName] [nvarchar](128) NOT NULL,
	[Status] [nvarchar](20) NOT NULL,
	[LastRun] [datetime] NOT NULL,
	[ErrorMessage] [nvarchar](max) NULL,
	[DurationSeconds] [int] NULL,
	[CPUTimeMS] [int] NULL,
	[StepCount] [int] NULL,
	[CapturedAt] [datetime] NULL,
	[RunDateOnly]  AS (CONVERT([date],[LastRun])) PERSISTED,
PRIMARY KEY CLUSTERED 
(
	[LogID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[JobLogs] ADD  DEFAULT (getdate()) FOR [CapturedAt]
GO







CREATE TABLE [dbo].[ManagedInstances](
	[ServerName] [nvarchar](128) NOT NULL,
	[FriendlyName] [nvarchar](100) NOT NULL,
	[IsActive] [bit] NULL,
	[DateAdded] [datetime] NULL,
	[LastModified] [datetime] NULL,
	[HostName] [nvarchar](100) NULL,
PRIMARY KEY CLUSTERED 
(
	[ServerName] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[ManagedInstances] ADD  DEFAULT ((1)) FOR [IsActive]
GO

ALTER TABLE [dbo].[ManagedInstances] ADD  DEFAULT (getdate()) FOR [DateAdded]
GO

ALTER TABLE [dbo].[ManagedInstances] ADD  DEFAULT (getdate()) FOR [LastModified]
GO








-- View 1: Simple Dashboard (Fast, no complex aggregations)
CREATE   VIEW [dbo].[v_EnhancedDashboard] AS
WITH LatestJobs AS (
    SELECT 
        jl.*,
        mi.FriendlyName,
        mi.IsActive,
        ROW_NUMBER() OVER(PARTITION BY jl.ServerName, jl.JobName ORDER BY jl.LastRun DESC) as rnk
    FROM JobLogs jl
    INNER JOIN ManagedInstances mi ON jl.ServerName = mi.HostName
)
SELECT 
    LogID,
    ServerName,
    FriendlyName,
    JobName,
    Status,
    LastRun,
    ErrorMessage,
    DurationSeconds,
    CPUTimeMS,
    StepCount,
    CapturedAt,
    IsActive,
    0 as AvgDuration,  -- Simplified for speed
    0 as MaxDuration,
    0 as AvgCPU
FROM LatestJobs
WHERE rnk = 1;
GO


-- View 2: Instance Health Summary

CREATE   VIEW [dbo].[v_InstanceHealthSummary] AS
SELECT 
    mi.ServerName,
    mi.FriendlyName,
    mi.IsActive,
    mi.DateAdded,
    (SELECT COUNT(DISTINCT JobName) 
     FROM JobLogs jl2 
     WHERE jl2.ServerName = mi.ServerName 
       AND jl2.LastRun >= DATEADD(day, -7, GETDATE())) as TotalJobs,
    (SELECT COUNT(*) 
     FROM JobLogs jl2 
     WHERE jl2.ServerName = mi.ServerName 
       AND jl2.Status = 'Failed' 
       AND jl2.LastRun >= DATEADD(hour, -24, GETDATE())) as FailuresLast24h,
    (SELECT COUNT(*) 
     FROM JobLogs jl2 
     WHERE jl2.ServerName = mi.ServerName 
       AND jl2.Status = 'Succeeded' 
       AND jl2.LastRun >= DATEADD(hour, -24, GETDATE())) as SuccessLast24h,
    (SELECT MAX(LastRun) 
     FROM JobLogs jl2 
     WHERE jl2.ServerName = mi.ServerName) as LastDataCollection,
    (SELECT AVG(CAST(DurationSeconds AS FLOAT)) 
     FROM JobLogs jl2 
     WHERE jl2.ServerName = mi.ServerName 
       AND jl2.LastRun >= DATEADD(day, -7, GETDATE())
       AND DurationSeconds IS NOT NULL) as AvgJobDuration,
    (SELECT AVG(CAST(CPUTimeMS AS FLOAT)) 
     FROM JobLogs jl2 
     WHERE jl2.ServerName = mi.ServerName 
       AND jl2.LastRun >= DATEADD(day, -7, GETDATE())
       AND CPUTimeMS IS NOT NULL) as AvgCPUUsage,
    (SELECT MAX(CapturedAt) 
     FROM JobLogs jl2 
     WHERE jl2.ServerName = mi.ServerName) as LastSync
FROM ManagedInstances mi;
GO




-- View 3: Failed Jobs in the last 24 hours


CREATE   VIEW [dbo].[v_Last24HourFailures] AS
SELECT 
    jl.LogID,
    jl.ServerName,
    mi.FriendlyName,
    jl.JobName,
    jl.LastRun,
    jl.ErrorMessage,
    ISNULL(jl.DurationSeconds, 0) as DurationSeconds,
    ISNULL(jl.CPUTimeMS, 0) as CPUTimeMS,
    ISNULL(jl.StepCount, 0) as StepCount,
    DATEDIFF(MINUTE, jl.LastRun, GETDATE()) as MinutesAgo,
    DATEDIFF(HOUR, jl.LastRun, GETDATE()) as HoursAgo
FROM JobLogs jl
INNER JOIN ManagedInstances mi ON jl.ServerName = mi.HostName
WHERE jl.Status = 'Failed'
    AND jl.LastRun >= DATEADD(hour, -24, GETDATE());
GO





-- View 4: Performance Trends over the last 30 days

CREATE   VIEW [dbo].[v_PerformanceTrends] AS
SELECT 
    jl.ServerName,
    mi.FriendlyName,
    jl.JobName,
    CAST(jl.LastRun AS DATE) as RunDate,
    COUNT(*) as ExecutionCount,
    SUM(CASE WHEN jl.Status = 'Failed' THEN 1 ELSE 0 END) as FailureCount,
    SUM(CASE WHEN jl.Status = 'Succeeded' THEN 1 ELSE 0 END) as SuccessCount,
    AVG(CAST(ISNULL(jl.DurationSeconds, 0) AS FLOAT)) as AvgDuration,
    MAX(ISNULL(jl.DurationSeconds, 0)) as MaxDuration,
    MIN(ISNULL(jl.DurationSeconds, 0)) as MinDuration,
    AVG(CAST(ISNULL(jl.CPUTimeMS, 0) AS FLOAT)) as AvgCPU,
    MAX(ISNULL(jl.CPUTimeMS, 0)) as MaxCPU,
    MIN(ISNULL(jl.CPUTimeMS, 0)) as MinCPU
FROM JobLogs jl
INNER JOIN ManagedInstances mi ON jl.ServerName = mi.HostName
WHERE jl.LastRun >= DATEADD(day, -30, GETDATE())
GROUP BY jl.ServerName, mi.FriendlyName, jl.JobName, CAST(jl.LastRun AS DATE);
GO

