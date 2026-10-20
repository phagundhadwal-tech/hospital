-- =============================================================================
-- CarePulse – SQL Server schema (tables for the 7 V6 CSV files)
-- Safe to re-run: every object is created only if it does not already exist.
-- It never drops, truncates or updates existing data.
-- Run in SSMS with CarePulseDB selected, or let backend/scripts/load_csv_to_sqlserver.py run it.
-- =============================================================================

IF OBJECT_ID(N'dbo.Departments', N'U') IS NULL
CREATE TABLE dbo.Departments (
    Department_ID    INT           NOT NULL CONSTRAINT PK_Departments PRIMARY KEY,
    Department_Name  NVARCHAR(100) NOT NULL
);
GO

IF OBJECT_ID(N'dbo.Patients', N'U') IS NULL
CREATE TABLE dbo.Patients (
    Patient_ID         INT          NOT NULL CONSTRAINT PK_Patients PRIMARY KEY,
    Date_Of_Birth      DATE         NULL,
    Gender             NVARCHAR(20) NULL,
    Registration_Date  DATETIME2(0) NULL
);
GO

IF OBJECT_ID(N'dbo.Wards', N'U') IS NULL
CREATE TABLE dbo.Wards (
    Ward_ID        INT           NOT NULL CONSTRAINT PK_Wards PRIMARY KEY,
    Ward_Name      NVARCHAR(150) NOT NULL,
    Department_ID  INT           NOT NULL CONSTRAINT FK_Wards_Departments REFERENCES dbo.Departments(Department_ID),
    Ward_Type      NVARCHAR(50)  NOT NULL,
    Capacity       INT           NULL
);
GO

IF OBJECT_ID(N'dbo.Beds', N'U') IS NULL
CREATE TABLE dbo.Beds (
    Bed_ID      INT          NOT NULL CONSTRAINT PK_Beds PRIMARY KEY,
    Ward_ID     INT          NOT NULL CONSTRAINT FK_Beds_Wards REFERENCES dbo.Wards(Ward_ID),
    Bed_Status  NVARCHAR(30) NOT NULL
);
GO

IF OBJECT_ID(N'dbo.Staff', N'U') IS NULL
CREATE TABLE dbo.Staff (
    Staff_ID       INT           NOT NULL CONSTRAINT PK_Staff PRIMARY KEY,
    Staff_Name     NVARCHAR(150) NOT NULL,
    Staff_Shift    NVARCHAR(30)  NULL,
    Staff_Role     NVARCHAR(50)  NULL,
    Department_ID  INT           NULL CONSTRAINT FK_Staff_Departments REFERENCES dbo.Departments(Department_ID)
);
GO

IF OBJECT_ID(N'dbo.Patient_Visits', N'U') IS NULL
CREATE TABLE dbo.Patient_Visits (
    Visit_ID                 INT           NOT NULL CONSTRAINT PK_Patient_Visits PRIMARY KEY,
    Patient_ID               INT           NOT NULL CONSTRAINT FK_Visits_Patients REFERENCES dbo.Patients(Patient_ID),
    Department_ID            INT           NOT NULL CONSTRAINT FK_Visits_Departments REFERENCES dbo.Departments(Department_ID),
    Visit_Type               NVARCHAR(30)  NOT NULL,
    Registration_Time        DATETIME2(0)  NOT NULL,
    Triage_Time              DATETIME2(0)  NULL,
    Consultation_Start_Time  DATETIME2(0)  NULL,
    Consultation_End_Time    DATETIME2(0)  NULL,
    Admission_Time           DATETIME2(0)  NULL,
    Discharge_Time           DATETIME2(0)  NULL,
    Visit_Status             NVARCHAR(30)  NOT NULL,
    Reason_for_cancellation  NVARCHAR(150) NULL
);
GO

-- NOTE: Bed_ID has NO foreign key to Beds on purpose. The V6 data contains
-- assignments whose Bed_ID does not exist in BEDS_V6.csv (reported by check_db.py).
IF OBJECT_ID(N'dbo.Bed_Assignments', N'U') IS NULL
CREATE TABLE dbo.Bed_Assignments (
    Assignment_ID     INT          NOT NULL CONSTRAINT PK_Bed_Assignments PRIMARY KEY,
    Visit_ID          INT          NOT NULL CONSTRAINT FK_BedAssign_Visits REFERENCES dbo.Patient_Visits(Visit_ID),
    Bed_ID            INT          NOT NULL,
    Assignment_Start  DATETIME2(0) NULL,
    Assignment_End    DATETIME2(0) NULL
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Visits_Registration' AND object_id = OBJECT_ID(N'dbo.Patient_Visits'))
    CREATE INDEX IX_Visits_Registration ON dbo.Patient_Visits (Registration_Time) INCLUDE (Department_ID, Visit_Type, Visit_Status);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Visits_Admission' AND object_id = OBJECT_ID(N'dbo.Patient_Visits'))
    CREATE INDEX IX_Visits_Admission ON dbo.Patient_Visits (Admission_Time) INCLUDE (Department_ID);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Visits_Discharge' AND object_id = OBJECT_ID(N'dbo.Patient_Visits'))
    CREATE INDEX IX_Visits_Discharge ON dbo.Patient_Visits (Discharge_Time) INCLUDE (Department_ID);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Beds_Ward' AND object_id = OBJECT_ID(N'dbo.Beds'))
    CREATE INDEX IX_Beds_Ward ON dbo.Beds (Ward_ID) INCLUDE (Bed_Status);
GO
