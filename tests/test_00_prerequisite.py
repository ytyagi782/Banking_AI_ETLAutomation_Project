"""
PREREQUISITE test case - runs FIRST, before every other test.

It executes  GoldenTestData/10_full_reset_and_reload_all_layers.sql  which:
  * deletes all data from all 4 layers,
  * inserts the golden data back into the SOURCE tables, and
  * runs the load stored procedures to reload PreStaging, Staging and DWH.

So every later test runs against a known, freshly-loaded database state.

The validation framework is otherwise READ-ONLY; this single prerequisite is
the one place that (re)builds the databases. It shells out to `sqlcmd` because
the script uses `GO` batch separators and switches databases with `USE` - both
are handled by sqlcmd, not by a plain pyodbc connection.

If this test FAILS, conftest.py skips every remaining test (they cannot trust
the data). See `pytest_runtest_setup` in conftest.py.
"""

import os
import shutil
import subprocess

import pytest

from utilities import config_loader, result_store
from utilities.logger import get_logger

log = get_logger()

# shown in the reports (module constants read by conftest's report hook)
LAYER = "Prerequisite"
TABLE = "AllLayers"

SCRIPT_PATH = config_loader.abs_path(
    "GoldenTestData", "10_full_reset_and_reload_all_layers.sql"
)


def _run_reset_script(path):
    """Run the reset/reload .sql file with sqlcmd. Returns the CompletedProcess."""
    db_cfg = config_loader.get_settings()["database"]
    server = db_cfg["server"]

    if shutil.which("sqlcmd") is None:
        raise RuntimeError(
            "sqlcmd not found on PATH - it is required to run the reset script."
        )

    # -b : return a non-zero exit code if any batch errors (pairs with the
    #      SET XACT_ABORT ON already inside the script)
    # -C : trust the server certificate (ODBC Driver 18 encrypts by default)
    cmd = ["sqlcmd", "-S", server, "-b", "-C", "-i", path]
    if db_cfg.get("trusted_connection", True):
        cmd.append("-E")          # Windows Authentication

    timeout = db_cfg.get("timeout", 30)
    # the 3-layer load can take a little while - give it generous headroom
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=max(timeout, 120))


@pytest.mark.order(0)              # run before every order(1) test
@pytest.mark.prerequisite
def test_reset_and_reload_all_layers(request):
    """Reset all 4 layers and reload them from the golden source data."""
    log.info("=" * 70)
    log.info("PREREQUISITE - resetting & reloading ALL 4 layers")
    log.info(f"  script: {SCRIPT_PATH}")

    assert os.path.exists(SCRIPT_PATH), f"reset script not found: {SCRIPT_PATH}"

    result = _run_reset_script(SCRIPT_PATH)

    if result.stdout and result.stdout.strip():
        log.info("sqlcmd output:\n" + result.stdout.strip())
    if result.returncode != 0 and result.stderr and result.stderr.strip():
        log.error("sqlcmd errors:\n" + result.stderr.strip())

    passed = result.returncode == 0
    msg = ("all 4 layers reset & reloaded from golden source data"
           if passed else f"sqlcmd exit code = {result.returncode}")

    status = "PASS" if passed else "FAIL"
    (log.info if passed else log.error)(
        f"[{status}] {LAYER} | {TABLE} | Reset_And_Reload | {msg}"
    )
    result_store.add_result(LAYER, TABLE, "Reset_And_Reload", status, msg,
                            category="prerequisite")

    # tell conftest whether it is safe to run the rest of the suite
    request.session.prerequisite_ok = passed

    assert passed, (
        f"Prerequisite reset/reload failed ({msg}).\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
