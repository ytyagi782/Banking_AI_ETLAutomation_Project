"""
main.py
-------
Simple entry point for the Banking ETL Automation *testing* framework.

This framework is READ-ONLY. It does NOT load data and it does NOT execute any
stored procedures - it only connects to SQL Server, reads data with SELECT
queries, and validates it. Loading the data (running the load stored
procedures) is done separately in the database, outside this framework.

What this file does:
  * checks that all four databases are reachable
  * reminds you to run the validations with `pytest`

Usage:
    python main.py        # check connections, then run `pytest` to validate
"""

from utilities import db
from utilities.logger import get_logger

log = get_logger()


def check_connections():
    """Verify every logical database is reachable (read-only, SELECT 1)."""
    ok = True
    for logical in ["source", "prestaging", "staging", "dwh"]:
        connected = db.test_connection(logical)
        log.info(f"Connection {logical:11}: {'OK' if connected else 'FAILED'}")
        ok = ok and connected
    return ok


if __name__ == "__main__":
    log.info("Checking database connections (read-only)...")
    if check_connections():
        print("\nAll connections OK.")
    else:
        print("\nSome connections FAILED - check the log for details.")
    print("This framework does not load data or run stored procedures.")
    print("To run the validations and build the reports, use:  pytest")
