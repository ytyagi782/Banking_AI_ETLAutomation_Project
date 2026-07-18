-- ====================================================================
-- NEW ENTITIES - master run order (SQLCMD mode)
-- ====================================================================

-- Run in SSMS with SQLCMD mode ON (Query menu -> SQLCMD Mode), or run each
-- file below in this exact order.  Assumes the 4 Bank_* databases already exist.
:setvar root "C:/Users/Yogesh Tyagi/PycharmProjects/Banking_AI_ETLAutomation_Project/database"

:r $(root)/ddl/01_source_tables.sql
:r $(root)/ddl/02_prestaging_tables.sql
:r $(root)/ddl/03_staging_tables.sql
:r $(root)/ddl/04_dwh_tables.sql
:r $(root)/procs/05_load_prestaging.sql
:r $(root)/procs/06_load_staging.sql
:r $(root)/procs/07_load_dwh.sql
:r $(root)/data/08_source_seed_data.sql
GO
PRINT 'New entities: tables + procs + seed created. Now EXEC the load procs (see README).';
GO
