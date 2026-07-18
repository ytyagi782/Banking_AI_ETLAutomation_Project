"""
db.py
-----
Thin, easy-to-use wrapper around pyodbc for SQL Server (Windows Auth).

This module is READ-ONLY: it only runs SELECT queries. It deliberately has no
way to modify data or execute stored procedures.

Main helpers:
  * get_connection(logical_db)      -> a live pyodbc connection
  * read_table(logical_db, table)   -> pandas DataFrame of the whole table
  * read_query(logical_db, sql)     -> pandas DataFrame for any SELECT
"""

import warnings

import pyodbc
import pandas as pd

from utilities import config_loader

# pandas prefers SQLAlchemy; using pyodbc directly is fine here, so hide the notice
warnings.filterwarnings("ignore",
                        message="pandas only supports SQLAlchemy connectable")


def _build_connection_string(database):
    """Create the ODBC connection string from settings.yaml."""
    db_cfg = config_loader.get_settings()["database"]
    parts = [
        f"DRIVER={{{db_cfg['driver']}}}",
        f"SERVER={db_cfg['server']}",
        f"DATABASE={database}",
    ]
    if db_cfg.get("trusted_connection", True):
        parts.append("Trusted_Connection=yes")
    return ";".join(parts) + ";"


def get_connection(logical_db):
    """Open a connection to a logical database name ('source', 'staging', ...)."""
    database = config_loader.resolve_database(logical_db)
    timeout = config_loader.get_settings()["database"].get("timeout", 30)
    return pyodbc.connect(_build_connection_string(database), timeout=timeout)


def read_query(logical_db, sql):
    """Run any SELECT and return a pandas DataFrame."""
    conn = get_connection(logical_db)
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def read_table(logical_db, table, columns=None, where=None):
    """
    Read a table into a DataFrame.
      columns : optional list of columns (default = all, '*')
      where   : optional WHERE clause text (without the word WHERE)
    """
    col_sql = "*" if not columns else ", ".join(f"[{c}]" for c in columns)
    sql = f"SELECT {col_sql} FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return read_query(logical_db, sql)


def get_row_count(logical_db, table, where=None):
    """Return the number of rows in a table (optionally filtered)."""
    sql = f"SELECT COUNT(*) AS cnt FROM {table}"
    if where:
        sql += f" WHERE {where}"
    df = read_query(logical_db, sql)
    return int(df["cnt"].iloc[0])


def get_columns(logical_db, table):
    """Return the list of column names for a table (order preserved)."""
    # table may be 'dbo.SRC_Accounts' -> split schema and name
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = "dbo", table
    sql = (
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{name}' "
        "ORDER BY ORDINAL_POSITION"
    )
    df = read_query(logical_db, sql)
    return list(df["COLUMN_NAME"])


def test_connection(logical_db):
    """Return True if a simple SELECT 1 succeeds against the database."""
    try:
        df = read_query(logical_db, "SELECT 1 AS ok")
        return int(df["ok"].iloc[0]) == 1
    except Exception:
        return False


def check_connections():
    """Verify every logical database is reachable (read-only, SELECT 1)."""
    from utilities.logger import get_logger
    log = get_logger()
    ok = True
    for logical in ["source", "prestaging", "staging", "dwh"]:
        connected = test_connection(logical)
        log.info(f"Connection {logical:11}: {'OK' if connected else 'FAILED'}")
        ok = ok and connected
    return ok
