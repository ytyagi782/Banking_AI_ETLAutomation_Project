"""
conftest.py
-----------
Wires pytest into the framework:
  * before the run  -> initialise the logger and clear the result store
  * --only option   -> RUN only the chosen tests, SKIP the rest (so the skipped
                       ones still appear in the report as "SKIP", not vanish)
  * skip recording  -> every skipped test is recorded so it shows in the reports
  * after the run   -> build the three reports and (optionally) email them
"""

import os
import sys

import pytest

# make sure the project root is importable (framework package)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities import result_store
from utilities.logger import get_logger


def pytest_addoption(parser):
    """
    Run only tests matching a marker expression.
    All other tests are marked as SKIPPED so they still appear in reports.

    Examples:
        pytest --only="count_check"
        pytest --only="count_check or metadata_check"
        pytest --only="count_check and smoke"
    """
    parser.addoption(
        "--only",
        action="store",
        default=None,
        help=(
            "Run only tests matching a marker expression. "
            "All other tests are marked as SKIPPED. "
            "Examples: "
            "--only='count_check', "
            "--only='count_check or metadata_check', "
            "--only='count_check and smoke'"
        ),
    )


def pytest_collection_modifyitems(config, items):
    """
    Execute only the markers specified in --only.
    Skip all other tests.
    """

    only = config.getoption("--only")

    if not only:
        return

    allowed_markers = {
        marker.strip()
        for marker in only.replace("or", ",").split(",")
        if marker.strip()
    }

    skip_marker = pytest.mark.skip(
        reason=f"Skipped because marker not in --only={only}"
    )

    for item in items:

        marker_names = {mark.name for mark in item.iter_markers()}

        if marker_names.intersection(allowed_markers):
            continue

        item.add_marker(skip_marker)


def pytest_runtest_setup(item):
    """Gate the suite on the prerequisite: if it failed, skip everything else."""
    if item.get_closest_marker("prerequisite"):
        return                                   # never skip the prerequisite

    if getattr(item.session, "prerequisite_ok", True) is False:
        pytest.skip("prerequisite reset/reload failed - data not in a known state")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """Record every skipped test into the result store so reports show it."""
    report = yield

    if report.when == "setup" and report.skipped:
        module = getattr(item, "module", None)
        layer = getattr(module, "LAYER", "")
        table = getattr(module, "TABLE", "")

        reason = "skipped"
        if isinstance(report.longrepr, tuple) and len(report.longrepr) == 3:
            reason = str(report.longrepr[2]).replace("Skipped: ", "")

        result_store.add_result(
            layer,
            table,
            item.originalname,
            "SKIP",
            reason,
            category="skipped",
        )

    return report


def pytest_sessionstart(session):
    """Runs once, before any test is collected/executed."""
    log = get_logger()

    result_store.reset()

    # gated to False only if the prerequisite reset/reload test fails; when the
    # prerequisite is not run at all, it stays True so the rest of the suite
    # is never skipped.
    session.prerequisite_ok = True

    log.info("pytest session started - result store cleared.")


def pytest_sessionfinish(session, exitstatus):
    """Runs once, after all tests finished - build the reports."""
    log = get_logger()

    log.info(f"pytest session finished (exit status = {exitstatus}).")

    try:
        # imported here so a report error never blocks the test run itself
        from reporting_engine import generate

        paths = generate.generate_all()

        log.info("All reports generated successfully.")

        print("\n=== Reports ===")
        for name, path in paths.items():
            print(f"  {name:9}: {path}")

    except Exception as e:
        log.error(f"Report generation failed: {e}")