"""
generate_golden_data.py
------------------------
Reads the CURRENT data from the four Bank_Source tables and writes SQL
INSERT scripts into this GoldenTestData folder. This is a "golden" snapshot:
run the generated scripts later to restore the source tables to exactly the
data that existed when this generator was run.

READ-ONLY against the database: it only runs SELECT queries to read the data.
It does NOT modify any table. The scripts it *writes* contain the INSERT (and
optional DELETE) statements you would run by hand in SSMS / sqlcmd.

Usage:
    python GoldenTestData/generate_golden_data.py

Output (all inside GoldenTestData/):
    01_SRC_Branches.sql
    02_SRC_Customers.sql
    03_SRC_Accounts.sql
    04_SRC_Transactions.sql
    00_restore_all_source_data.sql   (deletes + inserts everything, one file)
"""

import os
import sys
import datetime
import decimal

# make the project root importable so `utilities` resolves when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilities import db, config_loader
from utilities.logger import get_logger

log = get_logger()

HERE = os.path.dirname(os.path.abspath(__file__))

# Tables listed in FK-safe INSERT order (parents before children):
#   Branches  -> no dependency
#   Customers -> no dependency
#   Accounts  -> references Customers
#   Transactions -> references Accounts + Branches
# Each entry: (file_prefix, config_table_name, full_table_name)
TABLES_INSERT_ORDER = [
    ("01", "Branches", "dbo.SRC_Branches"),
    ("02", "Customers", "dbo.SRC_Customers"),
    ("03", "Accounts", "dbo.SRC_Accounts"),
    ("04", "Transactions", "dbo.SRC_Transactions"),
]

SOURCE_LOGICAL_DB = "source"          # -> Bank_Source (see config/settings.yaml)
LAYER = "SourceToPreStaging"

# --------------------------------------------------------------------------
# Full-reset metadata (used only by the "reset & reload all layers" script)
# --------------------------------------------------------------------------
# DELETE order: children before parents, warehouse first, source last.
#   (logical_db, [tables in delete order])
DELETE_ORDER = [
    ("dwh", ["dbo.FactTransaction", "dbo.DimAccount_Type1",
             "dbo.DimBranch_Type2", "dbo.DimCustomer_Type2"]),
    ("staging", ["dbo.STG_Transactions", "dbo.STG_Accounts",
                 "dbo.STG_Customers", "dbo.STG_Branches"]),
    ("prestaging", ["dbo.PS_Transactions", "dbo.PS_Accounts",
                    "dbo.PS_Customers", "dbo.PS_Branches"]),
    ("source", ["dbo.SRC_Transactions", "dbo.SRC_Accounts",
                "dbo.SRC_Customers", "dbo.SRC_Branches"]),
]

# LOAD proc order: parents before children, one layer at a time.
#   (title, target_logical_db, [procs in run order])
LOAD_PROC_ORDER = [
    ("Layer 1 : Source -> PreStaging", "prestaging",
     ["dbo.usp_Load_PS_Branches", "dbo.usp_Load_PS_Customers",
      "dbo.usp_Load_PS_Accounts", "dbo.usp_Load_PS_Transactions"]),
    ("Layer 2 : PreStaging -> Staging", "staging",
     ["dbo.usp_Load_STG_Branches", "dbo.usp_Load_STG_Customers",
      "dbo.usp_Load_STG_Accounts", "dbo.usp_Load_STG_Transactions"]),
    ("Layer 3 : Staging -> DWH", "dwh",
     ["dbo.usp_Load_DimBranch_Type2", "dbo.usp_Load_DimCustomer_Type2",
      "dbo.usp_Load_DimAccount_Type1", "dbo.usp_Load_FactTransaction"]),
]


def sql_value(value):
    """Turn a Python value into a SQL Server literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, decimal.Decimal)):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, datetime.datetime):
        # keep milliseconds; SQL Server datetime is fine with 3 decimals
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "'"
    if isinstance(value, datetime.date):
        return "'" + value.strftime("%Y-%m-%d") + "'"
    # everything else -> string, escape single quotes by doubling them
    return "'" + str(value).replace("'", "''") + "'"


def read_rows(full_table):
    """Return (columns, list_of_row_tuples) for a table, in column order."""
    conn = db.get_connection(SOURCE_LOGICAL_DB)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {full_table}")
        columns = [d[0] for d in cur.description]
        rows = [tuple(r) for r in cur.fetchall()]
        return columns, rows
    finally:
        conn.close()


def build_insert_block(full_table, columns, rows):
    """Build the INSERT statements text for one table."""
    lines = []
    col_list = ", ".join(f"[{c}]" for c in columns)
    if not rows:
        lines.append(f"-- (no rows in {full_table} at snapshot time)")
        return "\n".join(lines)
    for row in rows:
        values = ", ".join(sql_value(v) for v in row)
        lines.append(f"INSERT INTO {full_table} ({col_list}) VALUES ({values});")
    return "\n".join(lines)


def header(title):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_name = config_loader.resolve_database(SOURCE_LOGICAL_DB)
    return (
        "-- =====================================================================\n"
        f"-- {title}\n"
        f"-- Golden snapshot of source data  |  database: {db_name}\n"
        f"-- Generated: {stamp}\n"
        "-- Generated by GoldenTestData/generate_golden_data.py (READ-ONLY snapshot)\n"
        "-- =====================================================================\n"
    )


def build_full_reset_script(snapshots):
    """
    Build ONE self-contained script that:
      STEP 1 - deletes ALL data from all 4 layers (children before parents)
      STEP 2 - inserts the golden data into the 4 SOURCE tables
      STEP 3 - runs the load stored procedures to populate PreStaging,
               Staging and DWH from Source.
    """
    db_of = config_loader.resolve_database
    parts = [header("FULL RESET & RELOAD  -  all 4 layers")]
    parts.append(
        "-- Run this whole file in SSMS (or sqlcmd). It performs, in order:\n"
        "--   STEP 1: DELETE all rows from every table in all 4 layers\n"
        "--   STEP 2: INSERT the golden data back into the SOURCE tables\n"
        "--   STEP 3: EXEC the load stored procedures (Source -> PreStaging ->\n"
        "--           Staging -> DWH) so every layer is reloaded from Source.\n"
        "--\n"
        "-- SET XACT_ABORT ON stops the run on the first error so a half-load\n"
        "-- can never happen.\n"
    )
    parts.append("SET XACT_ABORT ON;")
    parts.append("SET NOCOUNT ON;")
    parts.append("GO\n")

    # ---- STEP 1 : delete everything (children first, warehouse -> source) ----
    parts.append("-- =====================================================================")
    parts.append("-- STEP 1 : DELETE all data from all 4 layers (children before parents)")
    parts.append("-- =====================================================================")
    for logical, tables in DELETE_ORDER:
        parts.append(f"USE [{db_of(logical)}];")
        parts.append("GO")
        for t in tables:
            parts.append(f"DELETE FROM {t};")
        parts.append("GO\n")

    # ---- STEP 2 : insert golden data into source (parents first) ----
    parts.append("-- =====================================================================")
    parts.append("-- STEP 2 : INSERT golden data into the SOURCE tables (parents first)")
    parts.append("-- =====================================================================")
    parts.append(f"USE [{db_of(SOURCE_LOGICAL_DB)}];")
    parts.append("GO")
    for _prefix, _cfg, full_table, columns, rows in snapshots:
        parts.append(f"-- ---- {full_table} ({len(rows)} row(s)) ----")
        parts.append(build_insert_block(full_table, columns, rows))
        parts.append("")
    parts.append("GO\n")

    # ---- STEP 3 : run the load stored procedures, layer by layer ----
    parts.append("-- =====================================================================")
    parts.append("-- STEP 3 : RUN load stored procedures (Source -> PreStaging -> Staging -> DWH)")
    parts.append("-- =====================================================================")
    for title, logical, procs in LOAD_PROC_ORDER:
        parts.append(f"-- ---- {title} ----")
        parts.append(f"USE [{db_of(logical)}];")
        parts.append("GO")
        for p in procs:
            parts.append(f"EXEC {p};")
        parts.append("GO\n")

    parts.append("PRINT 'Full reset & reload complete - all 4 layers reloaded from Source.';")
    parts.append("GO")
    return "\n".join(parts)


def main():
    log.info("Generating golden source-data INSERT scripts...")

    # snapshot each table once, keep it for both the per-table and master files
    snapshots = []   # (prefix, table_cfg_name, full_table, columns, rows)
    for prefix, cfg_name, full_table in TABLES_INSERT_ORDER:
        columns, rows = read_rows(full_table)
        snapshots.append((prefix, cfg_name, full_table, columns, rows))
        log.info(f"  {full_table}: {len(rows)} row(s), {len(columns)} column(s)")

    # ---- per-table files (pure INSERTs, numbered in FK-safe order) ----
    for prefix, cfg_name, full_table, columns, rows in snapshots:
        path = os.path.join(HERE, f"{prefix}_{full_table.split('.')[-1]}.sql")
        body = build_insert_block(full_table, columns, rows)
        text = (
            header(f"INSERT golden data into {full_table}")
            + f"USE {config_loader.resolve_database(SOURCE_LOGICAL_DB)};\nGO\n\n"
            + body + "\nGO\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        log.info(f"  wrote {os.path.basename(path)}")

    # ---- master restore file: delete (reverse FK order) + insert (forward) ----
    master_path = os.path.join(HERE, "00_restore_all_source_data.sql")
    parts = [header("RESTORE ALL SOURCE TABLES to the golden snapshot")]
    parts.append(f"USE {config_loader.resolve_database(SOURCE_LOGICAL_DB)};\nGO\n")
    parts.append(
        "-- Step 1: clear existing rows (children first, to respect foreign keys)\n"
    )
    for _, _, full_table, _, _ in reversed(snapshots):
        parts.append(f"DELETE FROM {full_table};")
    parts.append("GO\n")
    parts.append(
        "-- Step 2: re-insert the golden rows (parents first)\n"
    )
    for _, _, full_table, columns, rows in snapshots:
        parts.append(f"-- ---- {full_table} ({len(rows)} row(s)) ----")
        parts.append(build_insert_block(full_table, columns, rows))
        parts.append("")
    parts.append("GO\n")
    with open(master_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    log.info(f"  wrote {os.path.basename(master_path)}")

    # ---- full reset & reload file: delete all layers + insert source + load ----
    full_path = os.path.join(HERE, "10_full_reset_and_reload_all_layers.sql")
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(build_full_reset_script(snapshots))
    log.info(f"  wrote {os.path.basename(full_path)}")

    log.info("Golden data generation complete.")
    print("\nGolden data scripts written to:", HERE)


if __name__ == "__main__":
    main()
