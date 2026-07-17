"""
generate.py
-----------
One call to build all three reports and (optionally) email them.
Called at the end of the pytest run from conftest.py.
"""

import os
import re
import glob
from datetime import datetime

from utilities import config_loader, result_store
from utilities.logger import get_logger
from reporting_engine import excel_report, html_report, email_report

log = get_logger()

# the three framework reports the reports/ folder holds: (filename prefix, ext)
# (the pytest-html plugin's own pytest_html_report.html is kept too, but it is
#  written by pytest itself - see pytest.ini - not versioned here.)
_REPORT_KINDS = [
    ("SummaryReport_", ".xlsx"),
    ("DetailedReport_", ".xlsx"),
    ("ManagementReport_", ".html"),
]


def _reports_dir():
    path = config_loader.abs_path(config_loader.get_settings()["paths"]["reports"])
    os.makedirs(path, exist_ok=True)
    return path


def _keep_versions():
    keep = config_loader.get_settings().get("reporting", {}).get("keep_versions", 3)
    return max(1, int(keep))


def _version_cycle():
    cycle = config_loader.get_settings().get("reporting", {}).get("version_cycle", 5)
    return max(1, int(cycle))


def _next_report_version(reports_dir, cycle):
    """
    Next version number for the reports, cycling 1..`cycle` and restarting at 1.
    Same idea as utilities/logger._next_version: the "latest" comes from the most
    recently written report (by mtime), so once numbers wrap the newest run is
    still detected correctly. All three reports of one run share this number.
    """
    files = glob.glob(os.path.join(reports_dir, "SummaryReport_*_v*.xlsx"))
    if not files:
        return 1
    newest = max(files, key=os.path.getmtime)
    m = re.search(r"_v(\d+)\.xlsx$", newest)
    last = int(m.group(1)) if m else 0
    return (last % cycle) + 1


def _prune_old_reports(reports_dir):
    """
    Keep only the newest `reporting.keep_versions` (default 3) of each report
    type, so the folder holds up to 3 versions each of SummaryReport /
    DetailedReport / ManagementReport. The pytest-html report is left alone.
    """
    keep = _keep_versions()
    for prefix, ext in _REPORT_KINDS:
        files = sorted(glob.glob(os.path.join(reports_dir, f"{prefix}*{ext}")),
                       key=os.path.getmtime, reverse=True)
        for old in files[keep:]:
            try:
                os.remove(old)
            except OSError:
                pass


def generate_all():
    """Build summary + detailed + html reports, then try to email. Returns paths."""
    reports_dir = _reports_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # version suffix (_v1.._vN) shared by all three reports of this run; the
    # number cycles within version_cycle, while only keep_versions are retained
    version = _next_report_version(reports_dir, _version_cycle())
    suffix = f"{stamp}_v{version}"

    summary_path = os.path.join(reports_dir, f"SummaryReport_{suffix}.xlsx")
    detailed_path = os.path.join(reports_dir, f"DetailedReport_{suffix}.xlsx")
    html_path = os.path.join(reports_dir, f"ManagementReport_{suffix}.html")

    excel_report.build_summary_report(summary_path)
    excel_report.build_detailed_report(detailed_path)
    html_report.build_html_report(html_path)

    counts = result_store.summary_counts()
    log.info(f"Reports generated in {reports_dir}")
    log.info(f"  Summary : {os.path.basename(summary_path)}")
    log.info(f"  Detailed: {os.path.basename(detailed_path)}")
    log.info(f"  HTML    : {os.path.basename(html_path)}")
    log.info(f"RESULT -> total={counts['total']} passed={counts['passed']} "
             f"failed={counts['failed']} pass_rate={counts['pass_rate']}%")

    email_report.send_report(html_path, attachments=[summary_path, detailed_path])

    # keep the folder to just the three reports (newest of each)
    _prune_old_reports(reports_dir)

    return {"summary": summary_path, "detailed": detailed_path, "html": html_path}
