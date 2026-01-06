-- Run this once to setup the environment
CREATE DATABASE SQL_Monitoring;
GO
USE SQL_Monitoring;

CREATE TABLE ManagedInstances (
    ServerName NVARCHAR(128) PRIMARY KEY,
    FriendlyName NVARCHAR(100),
    IsActive BIT DEFAULT 1
);

CREATE TABLE JobLogs (
    LogID INT IDENTITY(1,1) PRIMARY KEY,
    ServerName NVARCHAR(128),
    JobName NVARCHAR(128),
    Status NVARCHAR(20),
    LastRun DATETIME,
    ErrorMessage NVARCHAR(MAX),
    CapturedAt DATETIME DEFAULT GETDATE()
);

-- THE CORE LOGIC: Persistent Failure View
-- Failures stay until a new success record is added
GO
CREATE OR ALTER VIEW v_PersistentDashboard AS
WITH RankedHistory AS (
    SELECT *, ROW_NUMBER() OVER(PARTITION BY ServerName, JobName ORDER BY LastRun DESC) as rnk
    FROM JobLogs
)
SELECT * FROM RankedHistory WHERE rnk = 1;