-- Run this ONCE in SSMS (connected to your server, any database) if CarePulseDB does not exist yet.
-- If your data already lives in another database, skip this file and put that database name in DATABASE_URL.
IF DB_ID(N'CarePulseDB') IS NULL
    CREATE DATABASE CarePulseDB;
GO
