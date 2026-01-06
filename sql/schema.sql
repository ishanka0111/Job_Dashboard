-- =============================================
-- SQL Monitoring Pro - Complete Database Setup
-- =============================================
-- Run this script to create everything from scratch

-- Step 1: Create Database
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'SQL_Monitoring')
BEGIN
    CREATE DATABASE SQL_Monitoring;
    PRINT '✓ Database SQL_Monitoring created';
END
ELSE
BEGIN
    PRINT '✓ Database SQL_Monitoring already exists';
END
GO

USE SQL_Monitoring;
GO

-- =============================================
-- Step 2: Create Tables
-- =============================================

-- Table: ManagedInstances
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ManagedInstances')
BEGIN
    CREATE TABLE ManagedInstances (
        ServerName NVARCHAR(128) PRIMARY KEY,
        FriendlyName NVARCHAR(100) NOT NULL,
        IsActive BIT DEFAULT 1,
        DateAdded DATETIME DEFAULT GETDATE(),
        LastModified DATETIME DEFAULT GETDATE()
    );
    PRINT '✓ Table ManagedInstances created';
END
GO

-- Table: JobLogs (with all performance columns)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'JobLogs')
BEGIN
    CREATE TABLE JobLogs (
        LogID INT IDENTITY(1,1) PRIMARY KEY,
        ServerName NVARCHAR(128) NOT NULL,
        JobName NVARCHAR(128) NOT NULL,
        Status NVARCHAR(20) NOT NULL,
        LastRun DATETIME NOT NULL,
        ErrorMessage NVARCHAR(MAX) NULL,
        DurationSeconds INT NULL,
        CPUTimeMS INT NULL,
        StepCount INT NULL,
        CapturedAt DATETIME DEFAULT GETDATE(),
        RunDateOnly AS CAST(LastRun AS DATE) PERSISTED
    );
    PRINT '✓ Table JobLogs created';
END
GO

-- =============================================
-- Step 3: Create Indexes
-- =============================================

-- Index for quick lookups by Server and Job
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_JobLogs_ServerJob')
BEGIN
    CREATE INDEX IX_JobLogs_ServerJob 
    ON JobLogs(ServerName, JobName, LastRun DESC);
    PRINT '✓ Index IX_JobLogs_ServerJob created';
END
GO

-- Index for status filtering
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_JobLogs_Status')
BEGIN
    CREATE INDEX IX_JobLogs_Status 
    ON JobLogs(Status, LastRun DESC);
    PRINT '✓ Index IX_JobLogs_Status created';
END
GO

-- Index for date-based queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_JobLogs_RunDate')
BEGIN
    CREATE INDEX IX_JobLogs_RunDate 
    ON JobLogs(RunDateOnly);
    PRINT '✓ Index IX_JobLogs_RunDate created';
END
GO

-- Index for performance queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_JobLogs_Performance')
BEGIN
    CREATE INDEX IX_JobLogs_Performance 
    ON JobLogs(ServerName, JobName, Status, LastRun DESC)
    INCLUDE (DurationSeconds, CPUTimeMS);
    PRINT '✓ Index IX_JobLogs_Performance created';
END
GO

-- =============================================
-- Step 4: Create Views
-- =============================================

-- View: Enhanced Dashboard (Latest status with performance metrics)
CREATE OR ALTER VIEW v_EnhancedDashboard AS
WITH RankedHistory AS (
    SELECT 
        jl.*,
        ROW_NUMBER() OVER(PARTITION BY jl.ServerName, jl.JobName ORDER BY jl.LastRun DESC) as rnk
    FROM JobLogs jl
    INNER JOIN ManagedInstances mi ON jl.ServerName = mi.ServerName
    WHERE mi.IsActive = 1
),
JobStats AS (
    SELECT 
        ServerName,
        JobName,
        AVG(CAST(DurationSeconds AS FLOAT)) as AvgDuration,
        MAX(DurationSeconds) as MaxDuration,
        AVG(CAST(CPUTimeMS AS FLOAT)) as AvgCPU
    FROM JobLogs
    WHERE LastRun >= DATEADD(day, -7, GETDATE())
        AND Status = 'Succeeded'
        AND DurationSeconds IS NOT NULL
    GROUP BY ServerName, JobName
)
SELECT 
    rh.LogID,
    rh.ServerName,
    rh.JobName,
    rh.Status,
    rh.LastRun,
    rh.ErrorMessage,
    rh.DurationSeconds,
    rh.CPUTimeMS,
    rh.StepCount,
    rh.CapturedAt,
    mi.FriendlyName,
    mi.IsActive,
    ISNULL(js.AvgDuration, 0) as AvgDuration,
    ISNULL(js.MaxDuration, 0) as MaxDuration,
    ISNULL(js.AvgCPU, 0) as AvgCPU
FROM RankedHistory rh
INNER JOIN ManagedInstances mi ON rh.ServerName = mi.ServerName
LEFT JOIN JobStats js ON rh.ServerName = js.ServerName AND rh.JobName = js.JobName
WHERE rh.rnk = 1;
GO
PRINT '✓ View v_EnhancedDashboard created';

-- View: Last 24 Hour Failures
CREATE OR ALTER VIEW v_Last24HourFailures AS
SELECT 
    jl.LogID,
    jl.ServerName,
    mi.FriendlyName,
    jl.JobName,
    jl.LastRun,
    jl.ErrorMessage,
    jl.DurationSeconds,
    jl.CPUTimeMS,
    jl.StepCount,
    DATEDIFF(MINUTE, jl.LastRun, GETDATE()) as MinutesAgo,
    DATEDIFF(HOUR, jl.LastRun, GETDATE()) as HoursAgo
FROM JobLogs jl
INNER JOIN ManagedInstances mi ON jl.ServerName = mi.ServerName
WHERE jl.Status = 'Failed'
    AND jl.LastRun >= DATEADD(hour, -24, GETDATE())
    AND mi.IsActive = 1;
GO
PRINT '✓ View v_Last24HourFailures created';

-- View: Job Execution History (Last 50 runs per job)
CREATE OR ALTER VIEW v_JobExecutionHistory AS
WITH RankedRuns AS (
    SELECT 
        jl.*,
        mi.FriendlyName,
        ROW_NUMBER() OVER(PARTITION BY jl.ServerName, jl.JobName ORDER BY jl.LastRun DESC) as ExecutionRank
    FROM JobLogs jl
    INNER JOIN ManagedInstances mi ON jl.ServerName = mi.ServerName
    WHERE mi.IsActive = 1
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
    ExecutionRank
FROM RankedRuns 
WHERE ExecutionRank <= 50;
GO
PRINT '✓ View v_JobExecutionHistory created';

-- View: Performance Trends (30-day analysis)
CREATE OR ALTER VIEW v_PerformanceTrends AS
SELECT 
    jl.ServerName,
    mi.FriendlyName,
    jl.JobName,
    CAST(jl.LastRun AS DATE) as RunDate,
    COUNT(*) as ExecutionCount,
    SUM(CASE WHEN jl.Status = 'Failed' THEN 1 ELSE 0 END) as FailureCount,
    SUM(CASE WHEN jl.Status = 'Succeeded' THEN 1 ELSE 0 END) as SuccessCount,
    AVG(CAST(jl.DurationSeconds AS FLOAT)) as AvgDuration,
    MAX(jl.DurationSeconds) as MaxDuration,
    MIN(jl.DurationSeconds) as MinDuration,
    AVG(CAST(jl.CPUTimeMS AS FLOAT)) as AvgCPU,
    MAX(jl.CPUTimeMS) as MaxCPU,
    MIN(jl.CPUTimeMS) as MinCPU
FROM JobLogs jl
INNER JOIN ManagedInstances mi ON jl.ServerName = mi.ServerName
WHERE jl.LastRun >= DATEADD(day, -30, GETDATE())
    AND mi.IsActive = 1
GROUP BY jl.ServerName, mi.FriendlyName, jl.JobName, CAST(jl.LastRun AS DATE);
GO
PRINT '✓ View v_PerformanceTrends created';

-- View: Instance Health Summary
CREATE OR ALTER VIEW v_InstanceHealthSummary AS
SELECT 
    mi.ServerName,
    mi.FriendlyName,
    mi.IsActive,
    mi.DateAdded,
    COUNT(DISTINCT jl.JobName) as TotalJobs,
    SUM(CASE WHEN jl.Status = 'Failed' AND jl.LastRun >= DATEADD(hour, -24, GETDATE()) THEN 1 ELSE 0 END) as FailuresLast24h,
    SUM(CASE WHEN jl.Status = 'Succeeded' AND jl.LastRun >= DATEADD(hour, -24, GETDATE()) THEN 1 ELSE 0 END) as SuccessLast24h,
    MAX(jl.LastRun) as LastDataCollection,
    AVG(CAST(jl.DurationSeconds AS FLOAT)) as AvgJobDuration,
    AVG(CAST(jl.CPUTimeMS AS FLOAT)) as AvgCPUUsage,
    MAX(jl.CapturedAt) as LastSync
FROM ManagedInstances mi
LEFT JOIN JobLogs jl ON mi.ServerName = jl.ServerName 
    AND jl.LastRun >= DATEADD(day, -7, GETDATE())
GROUP BY mi.ServerName, mi.FriendlyName, mi.IsActive, mi.DateAdded;
GO
PRINT '✓ View v_InstanceHealthSummary created';

-- View: Persistent Dashboard (for backward compatibility)
CREATE OR ALTER VIEW v_PersistentDashboard AS
SELECT 
    LogID,
    ServerName,
    JobName,
    Status,
    LastRun,
    ErrorMessage,
    DurationSeconds,
    CPUTimeMS,
    StepCount,
    CapturedAt,
    IsActive
FROM v_EnhancedDashboard;
GO
PRINT '✓ View v_PersistentDashboard created (legacy compatibility)';

-- =============================================
-- Step 5: Create Stored Procedures
-- =============================================

-- Procedure: Cleanup Old Logs
CREATE OR ALTER PROCEDURE sp_CleanupOldLogs
    @DaysToKeep INT = 90
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @CutoffDate DATETIME = DATEADD(day, -@DaysToKeep, GETDATE());
    DECLARE @RowsDeleted INT;
    
    BEGIN TRY
        DELETE FROM JobLogs
        WHERE LastRun < @CutoffDate;
        
        SET @RowsDeleted = @@ROWCOUNT;
        
        PRINT CONCAT('✓ Deleted ', @RowsDeleted, ' records older than ', @DaysToKeep, ' days');
        
        SELECT @RowsDeleted as RowsDeleted, @CutoffDate as CutoffDate;
    END TRY
    BEGIN CATCH
        PRINT CONCAT('✗ Error: ', ERROR_MESSAGE());
        THROW;
    END CATCH
END
GO
PRINT '✓ Stored Procedure sp_CleanupOldLogs created';

-- Procedure: Get Job Statistics
CREATE OR ALTER PROCEDURE sp_GetJobStatistics
    @ServerName NVARCHAR(128) = NULL,
    @JobName NVARCHAR(128) = NULL,
    @DaysBack INT = 30
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        ServerName,
        JobName,
        COUNT(*) as TotalExecutions,
        SUM(CASE WHEN Status = 'Succeeded' THEN 1 ELSE 0 END) as SuccessCount,
        SUM(CASE WHEN Status = 'Failed' THEN 1 ELSE 0 END) as FailureCount,
        CAST(SUM(CASE WHEN Status = 'Succeeded' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,2)) as SuccessRate,
        AVG(CAST(DurationSeconds AS FLOAT)) as AvgDurationSeconds,
        MAX(DurationSeconds) as MaxDurationSeconds,
        MIN(DurationSeconds) as MinDurationSeconds,
        AVG(CAST(CPUTimeMS AS FLOAT)) as AvgCPUTimeMS,
        MAX(LastRun) as LastExecution,
        MIN(LastRun) as FirstExecution
    FROM JobLogs
    WHERE LastRun >= DATEADD(day, -@DaysBack, GETDATE())
        AND (@ServerName IS NULL OR ServerName = @ServerName)
        AND (@JobName IS NULL OR JobName = @JobName)
    GROUP BY ServerName, JobName
    ORDER BY ServerName, JobName;
END
GO
PRINT '✓ Stored Procedure sp_GetJobStatistics created';

-- Procedure: Add or Update Instance
CREATE OR ALTER PROCEDURE sp_UpsertInstance
    @ServerName NVARCHAR(128),
    @FriendlyName NVARCHAR(100),
    @IsActive BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS (SELECT 1 FROM ManagedInstances WHERE ServerName = @ServerName)
    BEGIN
        UPDATE ManagedInstances
        SET FriendlyName = @FriendlyName,
            IsActive = @IsActive,
            LastModified = GETDATE()
        WHERE ServerName = @ServerName;
        
        PRINT CONCAT('✓ Updated instance: ', @FriendlyName);
    END
    ELSE
    BEGIN
        INSERT INTO ManagedInstances (ServerName, FriendlyName, IsActive)
        VALUES (@ServerName, @FriendlyName, @IsActive);
        
        PRINT CONCAT('✓ Added new instance: ', @FriendlyName);
    END
    
    SELECT * FROM ManagedInstances WHERE ServerName = @ServerName;
END
GO
PRINT '✓ Stored Procedure sp_UpsertInstance created';

-- =============================================
-- Step 6: Insert Sample Data (Optional)
-- =============================================

-- Uncomment to add sample instances for testing
/*
EXEC sp_UpsertInstance 
    @ServerName = '(localdb)\MSSQLLocalDB', 
    @FriendlyName = 'Local Development Server',
    @IsActive = 1;

EXEC sp_UpsertInstance 
    @ServerName = 'SQL-PROD-01', 
    @FriendlyName = 'Production Server',
    @IsActive = 1;
*/

-- =============================================
-- Step 7: Verification
-- =============================================

PRINT '';
PRINT '================================================';
PRINT 'DATABASE SETUP COMPLETED SUCCESSFULLY!';
PRINT '================================================';
PRINT '';
PRINT 'Tables Created:';
SELECT name FROM sys.tables WHERE name IN ('ManagedInstances', 'JobLogs') ORDER BY name;
PRINT '';
PRINT 'Views Created:';
SELECT name FROM sys.views WHERE name LIKE 'v_%' ORDER BY name;
PRINT '';
PRINT 'Stored Procedures Created:';
SELECT name FROM sys.procedures WHERE name LIKE 'sp_%' ORDER BY name;
PRINT '';
PRINT 'Indexes Created:';
SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID('JobLogs') AND name IS NOT NULL ORDER BY name;
PRINT '';
PRINT '================================================';
PRINT 'Next Steps:';
PRINT '1. Update config.py with your server details';
PRINT '2. Run: pip install -r requirements.txt';
PRINT '3. Add instances via the Streamlit UI';
PRINT '4. Click "Sync Now" to start collecting data';
PRINT '================================================';
GO