"""
agents/agent_5_execute.py   -   STEP 5
======================================
AI Agent: EXECUTE the test cases and summarise the run.

True to the package's golden rule - Claude reasons, the framework EXECUTES - this
agent does not "pretend" to run anything. It shells out to real `pytest` (the
same way tests/test_00_prerequisite.py shells out to sqlcmd), captures a
machine-readable JUnit XML, and parses the true pass / fail / skip results.

Claude then writes a readable execution summary (a plain templated summary is
used when no API key is present).

Targets:
    --target existing   (default)  ->  runs the curated suite in  tests/
    --target generated             ->  runs  agents/generated_tests/
You can also pass a marker expression:  --marks "prestaging_to_staging"

By default the `existing` target runs tests/test_00_prerequisite first, which
RESETS + reloads all 4 layers from golden data - so any manually-seeded defect in
the current data is wiped before the checks run. Pass --no-reset to skip that and
validate the CURRENT data as-is (adds `not prerequisite` to the marker filter).

Run:
    python -m agents.agent_5_execute
    python -m agents.agent_5_execute --target generated
    python -m agents.agent_5_execute --no-reset      # validate current data, no reload
Outputs (in agents/output/):
    ExecutionSummary_<ts>.md      - human-readable summary
    ExecutionResults_<ts>.json    - parsed results (consumed by agent_6)
    ExecutionJUnit_<ts>.xml       - raw JUnit XML
"""

import os
import sys
import json
import argparse
import subprocess
import xml.etree.ElementTree as ET

from utilities import config_loader
from utilities.logger import get_logger
from agents import base

log = get_logger()

TARGETS = {
    "existing": "tests",
    "generated": os.path.join("agents", "generated_tests"),
}
_TABLES = ["Accounts", "Branches", "Customers", "Transactions"]
_LAYER_TOKENS = {
    "SourceToPreStaging": "SourceToPreStaging", "SRCPS": "SourceToPreStaging",
    "PreStagingToStaging": "PreStagingToStaging", "PSSTG": "PreStagingToStaging",
    "StagingToDWH": "StagingToDWH", "STGDW": "StagingToDWH",
}


def _infer_layer_table(classname, name):
    """Best-effort layer/table from the JUnit classname (module path + class)."""
    blob = f"{classname}.{name}"
    layer = ""
    for token, full in _LAYER_TOKENS.items():
        if token in blob:
            layer = full
            break
    table = next((t for t in _TABLES if t in blob), "")
    return layer, table


def _run_pytest(target_path, marks, junit_path):
    """Run pytest as a subprocess; return (returncode, combined_output)."""
    cmd = [sys.executable, "-m", "pytest", target_path,
           f"--junitxml={junit_path}"]
    if marks:
        cmd += ["-m", marks]
    log.info(f"[agent_5] running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd=config_loader.abs_path(), timeout=1800)
    return proc.returncode, (proc.stdout or "") + "\n" + (proc.stderr or "")


def _parse_junit(junit_path):
    """Parse the JUnit XML into a results dict with per-failure detail."""
    tree = ET.parse(junit_path)
    root = tree.getroot()
    # the root may be <testsuites> or a single <testsuite>
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]

    totals = {"total": 0, "passed": 0, "failed": 0, "errors": 0,
              "skipped": 0, "duration": 0.0}
    failures = []
    for suite in suites:
        totals["total"] += int(suite.get("tests", 0))
        totals["failed"] += int(suite.get("failures", 0))
        totals["errors"] += int(suite.get("errors", 0))
        totals["skipped"] += int(suite.get("skipped", 0))
        totals["duration"] += float(suite.get("time", 0) or 0)

        for tc in suite.findall("testcase"):
            fail_el = tc.find("failure")
            err_el = tc.find("error")
            problem = fail_el if fail_el is not None else err_el
            if problem is None:
                continue
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            layer, table = _infer_layer_table(classname, name)
            detail = (problem.text or problem.get("message", "")).strip()
            failures.append({
                "classname": classname,
                "test": name,
                "layer": layer,
                "table": table,
                "type": "error" if err_el is not None else "failure",
                "message": problem.get("message", "").strip(),
                "detail": detail[-2000:],   # cap - keep the tail (the assertion)
            })

    totals["failed"] = len(failures)  # authoritative count from parsed cases
    totals["passed"] = max(0, totals["total"] - totals["failed"]
                           - totals["skipped"])
    return totals, failures


def _templated_summary(target, totals, failures):
    lines = [
        f"# ETL Test Execution Summary",
        "",
        f"- **Target:** {target}",
        f"- **Total:** {totals['total']}  |  **Passed:** {totals['passed']}  "
        f"|  **Failed:** {totals['failed']}  |  **Skipped:** {totals['skipped']}",
        f"- **Duration:** {totals['duration']:.1f}s",
        "",
    ]
    if failures:
        lines.append("## Failures")
        for f in failures:
            loc = " / ".join(x for x in (f["layer"], f["table"]) if x)
            lines.append(f"- **{f['test']}** ({loc or f['classname']}) - "
                         f"{f['message'] or f['type']}")
    else:
        lines.append("All executed tests passed.")
    return "\n".join(lines) + "\n"


def _ai_summary(target, totals, failures):
    """AI narrative; falls back to the templated summary on any problem."""
    if not base.have_api_key():
        return _templated_summary(target, totals, failures)
    try:
        system = (
            "You are a QA lead. Write a concise Markdown execution summary for an "
            "ETL test run: a one-line verdict, a small results table, and a short "
            "'What failed & likely why' section grouped by ETL layer. Be factual; "
            "do not invent numbers beyond those given."
        )
        payload = {"target": target, "totals": totals,
                   "failures": [{k: f[k] for k in ("test", "layer", "table",
                                                   "message")} for f in failures]}
        user = ("Write the summary from this run data (JSON):\n"
                + json.dumps(payload, indent=2))
        text = base.ask_claude(system, user, max_tokens=1500)
        # keep the deterministic facts block at the top for reliability
        return _templated_summary(target, totals, failures) + "\n---\n\n" + text
    except Exception as exc:
        log.warning(f"[agent_5] AI summary skipped ({exc})")
        return _templated_summary(target, totals, failures)


def execute(target="existing", marks=None, no_reset=False):
    """
    Run the tests, parse results, write the summary. Returns the results dict.

    no_reset : when True, skip the prerequisite reset/reload so the CURRENT data
               is validated as-is (adds `not prerequisite` to the marker filter).
               Use this to catch defects you have manually seeded into the data;
               otherwise the `existing` suite reloads clean golden data first.
    """
    base.banner("STEP 5  -  AI Agent: Execute Test Cases")
    print(base.ai_status())

    if target not in TARGETS:
        raise ValueError(f"target must be one of {list(TARGETS)}")
    target_path = TARGETS[target]
    # one version number shared by this run's three artifacts (JUnit/Summary/Results)
    ver = base.next_version("ExecutionResults", ".json")
    junit_path = os.path.join(base.ensure_dir(base.OUTPUT_DIR),
                              f"ExecutionJUnit_{ver}.xml")

    # combine any user marker expression with the reset-skip clause
    effective_marks = marks
    if no_reset:
        clause = "not prerequisite"
        effective_marks = f"({marks}) and {clause}" if marks else clause

    reset_note = " (no reset - validating current data)" if no_reset else ""
    print(f"Executing '{target}' suite ({target_path}) with pytest{reset_note} ...")
    rc, out = _run_pytest(target_path, effective_marks, junit_path)
    print(out.strip()[-1500:])  # tail of the pytest console output

    if not os.path.exists(junit_path):
        raise RuntimeError(
            "pytest did not produce a JUnit file - see the console output above. "
            f"(exit code {rc})")

    totals, failures = _parse_junit(junit_path)
    log.info(f"[agent_5] parsed: {totals}")

    summary = _ai_summary(target, totals, failures)
    summary_path = os.path.join(base.OUTPUT_DIR, f"ExecutionSummary_{ver}.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)

    results = {"target": target, "no_reset": no_reset, "pytest_exit_code": rc,
               "totals": totals, "failures": failures, "junit": junit_path,
               "summary_md": summary_path, "version": ver}
    results_path = os.path.join(base.OUTPUT_DIR, f"ExecutionResults_{ver}.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # keep only the newest KEEP_VERSIONS of each execution artifact
    for pfx, ext in (("ExecutionJUnit", ".xml"), ("ExecutionSummary", ".md"),
                     ("ExecutionResults", ".json")):
        base.prune_versions(pfx, ext)

    print(f"\nResults: {totals['passed']} passed, {totals['failed']} failed, "
          f"{totals['skipped']} skipped (of {totals['total']}).")
    print(f"Summary : {summary_path}")
    print(f"Results : {results_path}")
    log.info(f"[agent_5] execution summary saved: {summary_path}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Execute ETL test cases via pytest.")
    ap.add_argument("--target", choices=list(TARGETS), default="existing",
                    help="which suite to run (default: existing)")
    ap.add_argument("--marks", default=None,
                    help="optional pytest -m marker expression")
    ap.add_argument("--no-reset", dest="no_reset", action="store_true",
                    help="skip the prerequisite reset/reload and validate the "
                         "CURRENT data as-is (use to catch manually-seeded defects)")
    args = ap.parse_args()
    execute(target=args.target, marks=args.marks, no_reset=args.no_reset)
