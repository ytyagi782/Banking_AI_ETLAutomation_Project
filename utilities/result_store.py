"""
result_store.py
---------------
A single place that collects the outcome of every validation during a run.
The reporting modules read from here at the end to build the Excel / HTML
reports and the email body.

There are two kinds of information:

  1. results       -> one row per validation (PASS / FAIL)  [summary + counts]
  2. comparisons   -> the row-level detail behind a data comparison, used to
                      colour the detailed Excel report:
                        diffs      (yellow)  - same key, different column value
                        missing    (red)     - record on only one side
                        duplicates (orange)  - duplicate key on a side
"""

from datetime import datetime

# module-level singletons (reset at the start of each run)
_results = []
_comparisons = {}          # key = "layer :: table" -> comparison detail dict


def reset():
    """Clear everything - call once when a run starts."""
    _results.clear()
    _comparisons.clear()


def add_result(layer, table, validation, status, message,
               category="basic", source_value=None, target_value=None):
    """Record the outcome of a single validation."""
    _results.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "layer": layer,
        "table": table,
        "validation": validation,
        "category": category,
        "status": str(status).upper(),
        "message": message,
        "source_value": source_value,
        "target_value": target_value,
    })


def add_comparison(layer, table, keys, result):
    """
    Store the row-level detail behind a comparison for the detailed report.
    `result` is the dict returned by comparison.compare_dataframes(...).
    """
    _comparisons[f"{layer} :: {table}"] = {
        "layer": layer,
        "table": table,
        "keys": keys,                                  # business key columns
        "columns": result.get("columns", []),          # display column order
        "diff_pairs": result.get("diff_pairs", []),    # full rows that differ
        "missing_in_target": result["missing_in_target"],  # full source rows
        "missing_in_source": result["missing_in_source"],  # full target rows
        "duplicates": result["duplicates"],            # full rows + _side
    }


def get_failures():
    """Only the failed validation rows."""
    return [r for r in _results if r["status"] == "FAIL"]


def get_comparisons():
    """All stored comparison details."""
    return dict(_comparisons)


def get_skipped():
    """Only the skipped validation rows."""
    return [r for r in _results if r["status"] == "SKIP"]


def get_executed():
    """Only the rows that actually ran (PASS or FAIL, not SKIP)."""
    return [r for r in _results if r["status"] != "SKIP"]


def summary_counts():
    """Return totals used by the summary report and email."""
    total = len(_results)
    failed = len(get_failures())
    skipped = len(get_skipped())
    passed = total - failed - skipped
    executed = passed + failed
    # pass rate is measured over the tests that actually ran
    pass_rate = round((passed / executed) * 100, 2) if executed else 0.0
    return {"total": total, "passed": passed, "failed": failed,
            "skipped": skipped, "executed": executed, "pass_rate": pass_rate}


def summary_by_layer():
    """Pass/fail/skip counts grouped by layer -> used in the summary report."""
    grouped = {}
    for r in _results:
        g = grouped.setdefault(r["layer"],
                               {"passed": 0, "failed": 0, "skipped": 0})
        if r["status"] == "FAIL":
            g["failed"] += 1
        elif r["status"] == "SKIP":
            g["skipped"] += 1
        else:
            g["passed"] += 1
    return grouped
