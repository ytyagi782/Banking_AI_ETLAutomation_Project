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


def _module_order_key(item):
    """
    Sort key so tests run in module order:
    ETL_Automation_Module (0) -> API_Automation_Module (1) ->
    PowerBI_Automation_Module (2) -> UI_Automation_Module (3).
    Items not matching any known module keep their original position (99).
    """
    _ORDER = {
        "ETL_Automation_Module": 0,
        "API_Automation_Module": 1,
        "PowerBI_Automation_Module": 2,
        "UI_Automation_Module": 3,
    }
    fspath = str(item.fspath)
    for mod_name, rank in _ORDER.items():
        if mod_name in fspath:
            return rank
    return 99


def pytest_collection_modifyitems(config, items):
    """
    1. Sort items so modules run in the order:
       ETL -> API -> PowerBI -> UI.
    2. Apply --only marker filtering (skip non-matching tests).
    """
    items.sort(key=_module_order_key)

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
    """Record skipped tests and generate failure screenshots for sample cases."""
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

    # auto-generate HTML failure screenshots for API / PowerBI / UI tests
    if report.when == "call" and report.failed:
        _maybe_generate_screenshot(item, report)

    return report


def _maybe_generate_screenshot(item, report):
    """If the failed test is a parametrized sample case, generate a screenshot."""
    try:
        # parametrized tests expose callspec.params which contains the case dict
        if not hasattr(item, "callspec"):
            return
        case = item.callspec.params.get("case")
        if not isinstance(case, dict) or "TestCaseID" not in case:
            return

        from utilities.screenshot import generate_failure_screenshot

        # build a meaningful error string from the report
        error_text = ""
        if report.longrepr:
            error_text = str(report.longrepr)

        path = generate_failure_screenshot(case, error_text)
        if path:
            log = get_logger()
            log.info(f"Failure screenshot saved: {path}")
    except Exception:
        pass  # never let screenshot generation break the test run


def pytest_sessionstart(session):
    """Runs once, before any test is collected/executed."""
    log = get_logger()

    result_store.reset()

    # clean previous failure screenshots so only current-run failures remain
    _screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    for sub in ("API", "PowerBI", "UI"):
        folder = os.path.join(_screenshots_dir, sub)
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                if f.endswith("_failure.html"):
                    try:
                        os.remove(os.path.join(folder, f))
                    except OSError:
                        pass

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