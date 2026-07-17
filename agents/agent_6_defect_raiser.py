"""
agents/agent_6_defect_raiser.py   -   STEP 6
============================================
AI Agent: turn test FAILURES into DEFECT / ISSUE tickets.

It reads the results produced by STEP 5 (the newest ExecutionResults_*.json) and
writes one ticket per failing test:

    DefectID | Severity | Layer | Table | Title | Steps to Reproduce |
    Expected Result | Actual Result | Probable Root Cause | Suggested Fix | Status

Deterministic tickets are always produced from the raw failure data. When an
ANTHROPIC_API_KEY is present, Claude sharpens the title, severity, root-cause
hypothesis and suggested fix.

IMPORTANT (honesty): memory.md records that a few Layer-1 direct-move failures
are INTENTIONALLY seeded demos (e.g. SRC_Accounts 1002, SRC_Branches 101 City,
SRC_Customers 2 DOB). Those are surfaced as tickets too - never hidden - but the
root-cause note flags them as likely seeded so they are not mistaken for new bugs.

Run:
    python -m agents.agent_6_defect_raiser
Outputs (agents/output/):
    Defects_<ts>.xlsx  and  Defects_<ts>.md
"""

import os
import json

from openpyxl import Workbook

from utilities import db, comparison
from utilities.logger import get_logger
from agents import base
from agents.xlsx_util import write_sheet

log = get_logger()


HEADERS = [
    "DefectID", "Defect Type", "Severity", "Layer", "Table", "Title",
    "Steps to Reproduce", "Expected Result", "Actual Result",
    "Probable Root Cause", "Suggested Fix", "Status",
]

# map a generated/curated test method to its validation + a friendly expectation
TEST_META = {
    "test_metadata":       ("Metadata_Validation", "High",
                            "All expected columns exist on source and target."),
    "test_count":          ("Count_Validation", "High",
                            "Source and target row counts match for the movement."),
    "test_duplicates":     ("Duplicate_Validation", "Medium",
                            "No duplicate business keys in the target."),
    "test_nulls":          ("Null_Validation", "High",
                            "Required columns contain no NULLs."),
    "test_constraints":    ("Constraint_Validation", "High",
                            "Key columns are unique and not null."),
    "test_direct_move":    ("direct_move_Validation", "High",
                            "Target is an exact copy of the source."),
    "test_data_integrity": ("data_integrity_Validation", "High",
                            "Matched rows still agree on all business columns."),
    "test_column_values":  ("column_values_check", "High",
                            "Fact value columns match the staging source."),
    "test_transformation": ("Transformation_Validation", "Medium",
                            "All transformation / data-quality rules hold."),
    "test_transformation_rules": ("Transformation_Validation", "Medium",
                            "All transformation / data-quality rules hold."),
    "test_foreign_keys":   ("ForeignKey_Check", "High",
                            "Every fact surrogate key exists in its dimension "
                            "and required keys are populated."),
}

# tests whose failures are re-derived column-by-column from the live DB
_COMPARISON_TESTS = ("test_direct_move", "test_data_integrity", "test_column_values")

# known intentionally-seeded demo defects (from memory.md) - flagged, not hidden
_SEEDED_HINTS = {
    ("SourceToPreStaging", "Accounts"): "May include the seeded demo defect "
        "(SRC_Accounts 1002 OpenDate/Balance changed in PreStaging).",
    ("SourceToPreStaging", "Branches"): "May include the seeded demo defect "
        "(SRC_Branches 101 City Delhi -> Noida).",
    ("SourceToPreStaging", "Customers"): "May include the seeded demo defect "
        "(SRC_Customers 2 DOB 1092 -> 1992).",
}


def _load_results(path=None):
    path = path or base.latest_output("ExecutionResults_", ext=".json")
    if not path or not os.path.exists(path):
        raise FileNotFoundError(
            "No ExecutionResults_*.json found in agents/output/. "
            "Run the executor first (python -m agents.agent_5_execute).")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


# --------------------------------------------------------------------------
# Findings: a failing comparison test can hide SEVERAL distinct problems.
# We recompute the comparison from the live DB and emit one finding per problem:
#   Column Value Mismatch | Missing Record in Target | Missing Record in Source |
#   Duplicate Record. Each finding carries the actual row/column data + a
#   type-specific root cause. Read-only; works because agent 5 --no-reset leaves
#   the data in place. Non-comparison tests produce one finding.
# --------------------------------------------------------------------------
def _resolve(logical):
    from utilities import config_loader
    try:
        return config_loader.resolve_database(logical)
    except Exception:
        return logical


def _fmt_row(row, keys):
    """Render a full row as 'col=value | col=value ...' (key columns first)."""
    ordered = list(keys) + [c for c in row if c not in keys and c != "_side"]
    return " | ".join(f"{c}={row[c]!r}" for c in ordered if c in row)


def _comparison_findings(layer, table):
    """Recompute the comparison from the live DB -> list of typed findings."""
    from validations import validations as v
    ctx = v._context(layer, table)
    keys = ctx["keys"]
    cols = keys + [c for c in ctx["compare_columns"] if c not in keys]
    src = v._read_side(ctx, "source", cols)
    tgt = v._read_side(ctx, "target", cols)
    ci = layer != "SourceToPreStaging"      # layers 2/3 compare case-insensitively
    res = comparison.compare_dataframes(src, tgt, keys, ctx["compare_columns"],
                                        case_insensitive=ci)

    st, tt = ctx["source_table"], ctx["target_table"]
    sdb, tdb = _resolve(ctx["source_db"]), _resolve(ctx["target_db"])
    seed = _SEEDED_HINTS.get((layer, table), "") if layer == "SourceToPreStaging" else ""
    out = []

    for d in res["diffs"]:
        kd = ", ".join(f"{k}={d[k]}" for k in keys)
        out.append({
            "type": "Column Value Mismatch",
            "severity": "High",
            "title": f"{d['column']} value differs at [{kd}]",
            "expected": f"{d['column']} must be identical in source and target.",
            "actual": (f"[{kd}] Column '{d['column']}' -> "
                       f"Source {st}({sdb}) = '{d['source_value']}'  |  "
                       f"Target {tt}({tdb}) = '{d['target_value']}'"),
            "root_cause": (f"The '{d['column']}' value was not carried correctly "
                           f"from {st} to {tt} (it changed during the movement). "
                           + seed).strip(),
            "fix": f"Fix the load logic so '{d['column']}' is preserved, or correct "
                   f"the source data; then reload {tt}.",
        })

    for row in res["missing_in_target"]:
        kd = ", ".join(f"{k}={row[k]}" for k in keys)
        out.append({
            "type": "Missing Record in Target",
            "severity": "High",
            "title": f"Record [{kd}] is in source but MISSING in target ({tt})",
            "expected": f"Every record in {st} must also exist in {tt}.",
            "actual": (f"Present in {st}({sdb}) but NOT found in {tt}({tdb}).\n"
                       f"Source row: {_fmt_row(row, keys)}"),
            "root_cause": (f"Record [{kd}] exists in {st} but was not loaded into "
                           f"{tt} - the row was dropped or rejected during the "
                           f"movement (check load filters / rejection logic)."),
            "fix": f"Investigate why the record was not loaded and reload {tt}.",
        })

    for row in res["missing_in_source"]:
        kd = ", ".join(f"{k}={row[k]}" for k in keys)
        out.append({
            "type": "Missing Record in Source (extra in target)",
            "severity": "Medium",
            "title": f"Record [{kd}] is in target ({tt}) but MISSING in source",
            "expected": f"{tt} must not contain records absent from {st}.",
            "actual": (f"Present in {tt}({tdb}) but NOT found in {st}({sdb}).\n"
                       f"Target row: {_fmt_row(row, keys)}"),
            "root_cause": (f"Record [{kd}] exists in {tt} but not in {st} - an "
                           f"orphan/unexpected insert, or the source row was "
                           f"deleted after the target was loaded."),
            "fix": f"Verify the source; remove the orphan {tt} row or restore the "
                   f"source record, then reconcile.",
        })

    # the comparison returns one row PER occurrence of a duplicated key; group by
    # (side, key) so each duplicated key becomes ONE finding (not one per copy)
    dup_groups = {}
    for row in res["duplicates"]:
        side = row.get("_side", "")
        kt = tuple(row.get(k) for k in keys)
        dup_groups.setdefault((side, kt), []).append(row)
    for (side, kt), rows in dup_groups.items():
        kd = ", ".join(f"{k}={val}" for k, val in zip(keys, kt))
        side_tbl = st if side == "source" else tt
        out.append({
            "type": "Duplicate Record",
            "severity": "High",
            "title": f"Duplicate business key [{kd}] on the {side} side",
            "expected": "Each business key must appear at most once.",
            "actual": (f"Duplicate in {side_tbl} ({side} side): key [{kd}] appears "
                       f"{len(rows)} times. Example row: {_fmt_row(rows[0], keys)}"),
            "root_cause": (f"Business key {keys} appears more than once in "
                           f"{side_tbl} (missing de-duplication or unique key)."),
            "fix": "Add/enforce a unique constraint or a de-duplication step.",
        })

    return out


def _single_finding(layer, table, test, fail):
    """One finding for non-comparison tests (count/null/duplicate/etc.)."""
    from validations import validations as v
    validation, severity, expected = TEST_META.get(
        test, ("(unknown)", "Medium", "The validation passes."))
    dtype = "Validation Failure"
    actual = ""
    root = "Data does not satisfy the validation for this movement."
    fix = ("Review the failing rows in the DetailedReport; fix the load logic / "
           "source data, then re-run.")
    try:
        ctx = v._context(layer, table)
        if test == "test_count":
            s = db.get_row_count(ctx["source_db"], ctx["source_table"],
                                 where=ctx["count_source_where"])
            t = db.get_row_count(ctx["target_db"], ctx["target_table"],
                                 where=ctx["count_target_where"])
            dtype = "Row Count Mismatch"
            actual = f"Source rows = {s}  |  Target rows = {t}  (diff = {s - t})"
            root = (f"Source and target counts differ by {s - t} "
                    f"({'rows lost' if s > t else 'extra rows'} in the movement).")
        elif test == "test_nulls":
            bad = []
            for col in ctx["not_null_columns"]:
                where = f"[{col}] IS NULL"
                if ctx["target_where"]:
                    where += f" AND {ctx['target_where']}"
                n = db.get_row_count(ctx["target_db"], ctx["target_table"], where=where)
                if n:
                    bad.append(f"{col} = {n} NULL(s)")
            dtype = "NULL in Required Column"
            actual = "NULLs in target required column(s): " + "; ".join(bad)
            root = "Required (NOT NULL) column(s) contain NULLs in the target."
        elif test == "test_duplicates":
            key_sql = ", ".join(f"[{k}]" for k in ctx["keys"])
            where = f" WHERE {ctx['target_where']}" if ctx["target_where"] else ""
            sql = (f"SELECT {key_sql}, COUNT(*) AS cnt FROM {ctx['target_table']}"
                   f"{where} GROUP BY {key_sql} HAVING COUNT(*) > 1")
            dups = db.read_query(ctx["target_db"], sql)
            dtype = "Duplicate Business Key"
            actual = "Duplicate key(s) in target: " + ", ".join(
                "/".join(str(r[k]) for k in ctx["keys"]) + f" (x{int(r['cnt'])})"
                for _, r in dups.head(15).iterrows())
            root = f"Business key {ctx['keys']} is duplicated in the target."
        elif test in ("test_transformation", "test_transformation_rules"):
            dtype = "Transformation Rule Violation"
            root = ("One or more transformation / data-quality rules failed; see "
                    "the log and DetailedReport for the offending values.")
        elif test == "test_metadata":
            dtype = "Schema / Metadata"
            root = "Expected column(s) are missing on the source or target."
        elif test == "test_constraints":
            dtype = "Constraint Violation"
            root = "Key column(s) are not unique / not populated in the target."
        elif test == "test_foreign_keys":
            dtype = "Foreign Key Violation"
            root = ("A fact surrogate key has no matching dimension row (orphan) "
                    "or a required key column is NULL.")
    except Exception as exc:
        log.warning(f"[agent_6] single-finding recompute failed "
                    f"({layer}/{table}/{test}): {exc}")

    if not actual:
        actual = fail.get("message") or "Validation returned False (assertion failed)."
        if fail.get("detail"):
            actual = (actual + "\n\n" + fail["detail"]).strip()

    return [{"type": dtype, "severity": severity, "title": f"{validation} failed",
             "expected": expected, "actual": actual, "root_cause": root, "fix": fix}]


def _findings_for_failure(fail):
    """Return the list of typed findings for one failing test."""
    layer, table, test = (fail.get("layer", ""), fail.get("table", ""),
                          fail.get("test", ""))
    if test in _COMPARISON_TESTS and layer and table:
        try:
            findings = _comparison_findings(layer, table)
            if findings:
                return findings
        except Exception as exc:
            log.warning(f"[agent_6] comparison recompute failed "
                        f"({layer}/{table}/{test}): {exc}")
    return _single_finding(layer, table, test, fail)


def _ticket_from_finding(defect_id, fail, finding):
    layer, table, test = (fail.get("layer", ""), fail.get("table", ""),
                          fail.get("test", ""))
    validation = TEST_META.get(test, ("(unknown)",))[0]
    loc = " / ".join(x for x in (layer, table) if x) or fail.get("classname", "")
    steps = (
        f"1. Ensure the data is loaded/seeded for this scenario.\n"
        f"2. Run `{validation}` for {table or 'the table'} in "
        f"{layer or 'the layer'} (test `{test}`).\n"
        f"3. Observe: {finding['type']}."
    )
    return {
        "DefectID": f"DEF_{defect_id:03d}",
        "Defect Type": finding["type"],
        "Severity": finding["severity"],
        "Layer": layer,
        "Table": table,
        "Title": f"{loc}: {finding['title']}",
        "Steps to Reproduce": steps,
        "Expected Result": finding["expected"],
        "Actual Result": str(finding["actual"])[:2000],
        "Probable Root Cause": finding["root_cause"],
        "Suggested Fix": finding["fix"],
        "Status": "New",
    }


def _maybe_ai_enrich(tickets):
    """
    Ask Claude to improve Title / Severity / Root Cause / Suggested Fix for each
    ticket. The Actual Result (real data) is never sent for rewriting - it is
    kept verbatim. Returns the tickets list (mutated copies). Never raises.
    """
    if not base.have_api_key() or not tickets:
        return tickets
    try:
        from pydantic import BaseModel

        class Enriched(BaseModel):
            defect_id: str
            severity: str
            title: str
            probable_root_cause: str
            suggested_fix: str

        class Enrichment(BaseModel):
            defects: list[Enriched]

        system = (
            "You are a QA/defect analyst for an ETL data warehouse. For each "
            "failing test, write a crisp defect Title, a Severity "
            "(Critical/High/Medium/Low), a Probable Root Cause and a Suggested "
            "Fix. Be specific to the ETL layer and validation. If a note says a "
            "failure may be an intentionally seeded demo defect, keep the ticket "
            "but say so in the root cause. Preserve each defect_id exactly."
        )
        payload = [{
            "defect_id": t["DefectID"], "defect_type": t["Defect Type"],
            "layer": t["Layer"], "table": t["Table"],
            "expected": t["Expected Result"], "actual": t["Actual Result"][:600],
            "current_root_cause": t["Probable Root Cause"],
        } for t in tickets]
        user = "Enrich these defects (JSON):\n" + json.dumps(payload, indent=2)
        result = base.ask_claude_json(system, user, Enrichment, max_tokens=3000)
        by_id = {d.defect_id: d for d in result.defects}
        for t in tickets:
            e = by_id.get(t["DefectID"])
            if e:
                t["Severity"] = e.severity or t["Severity"]
                t["Title"] = e.title or t["Title"]
                t["Probable Root Cause"] = e.probable_root_cause or t["Probable Root Cause"]
                t["Suggested Fix"] = e.suggested_fix or t["Suggested Fix"]
        log.info(f"[agent_6] AI enriched {len(by_id)} defects")
        return tickets
    except Exception as exc:
        log.warning(f"[agent_6] AI enrichment skipped ({exc})")
        return tickets


def _write_excel(tickets, ver):
    wb = Workbook()
    ws = wb.active
    ws.title = "Defects"
    rows = [[t[h] for h in HEADERS] for t in tickets]
    write_sheet(ws, HEADERS, rows,
                widths=[10, 26, 9, 20, 13, 40, 36, 30, 50, 44, 40, 8])
    path = os.path.join(base.ensure_dir(base.OUTPUT_DIR), f"Defects_{ver}.xlsx")
    wb.save(path)
    return path


def _write_md(tickets, results, ver):
    lines = [f"# Defect Report", "",
             f"- Source run target: **{results.get('target')}**",
             f"- Failures: **{len(tickets)}**", ""]
    if not tickets:
        lines.append("No failures - no defects raised. ")
    for t in tickets:
        actual = t["Actual Result"] or ""
        lines += [
            f"## {t['DefectID']} - {t['Title']}",
            f"- **Defect Type:** {t['Defect Type']}",
            f"- **Severity:** {t['Severity']}  |  **Status:** {t['Status']}",
            f"- **Layer / Table:** {t['Layer']} / {t['Table']}",
            f"- **Expected:** {t['Expected Result']}",
            f"- **Actual (data):**",
            "",
            "  ```",
            *[f"  {ln}" for ln in actual.splitlines()],
            "  ```",
            f"- **Probable Root Cause:** {t['Probable Root Cause']}",
            f"- **Suggested Fix:** {t['Suggested Fix']}",
            "",
        ]
    path = os.path.join(base.OUTPUT_DIR, f"Defects_{ver}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def raise_defects(results_path=None):
    """Build defect tickets from the latest execution results. Returns paths."""
    base.banner("STEP 6  -  AI Agent: Raise Issues / Defects")
    print(base.ai_status())

    results, path = _load_results(results_path)
    print(f"Reading execution results from:\n  {path}")
    failures = results.get("failures", [])

    # a single failing test can yield SEVERAL typed findings (column mismatch,
    # missing in target/source, duplicate) - each becomes its own defect ticket.
    # De-duplicate two ways:
    #   * comparison findings are recomputed per (layer, table) only ONCE, even
    #     when several comparison-type tests fail for that table, and
    #   * identical findings (same layer/table/type/actual) are collapsed.
    tickets = []
    n = 0
    seen_sig = set()
    done_comparison = set()
    for fail in failures:
        layer, table, test = (fail.get("layer", ""), fail.get("table", ""),
                              fail.get("test", ""))
        if test in _COMPARISON_TESTS:
            if (layer, table) in done_comparison:
                continue                      # already produced this table's findings
            done_comparison.add((layer, table))
        for finding in _findings_for_failure(fail):
            sig = (layer, table, finding["type"], finding["actual"])
            if sig in seen_sig:
                continue                      # collapse an identical finding
            seen_sig.add(sig)
            n += 1
            tickets.append(_ticket_from_finding(n, fail, finding))
    tickets = _maybe_ai_enrich(tickets)

    # one shared version for this run's Defects .xlsx + .md, cycling 1..5 / keep 2
    ver = base.next_version("Defects", ".xlsx")
    xlsx = _write_excel(tickets, ver)
    md = _write_md(tickets, results, ver)
    base.prune_versions("Defects", ".xlsx")
    base.prune_versions("Defects", ".md")

    if tickets:
        print(f"\n{len(tickets)} defect(s) raised:")
        for t in tickets:
            print(f"  {t['DefectID']} [{t['Severity']}] {t['Title']}")
    else:
        print("\nNo failures in the latest run - no defects raised.")
    print(f"\nDefects (Excel): {xlsx}\nDefects (MD)   : {md}")
    log.info(f"[agent_6] raised {len(tickets)} defects -> {xlsx}")
    return {"xlsx": xlsx, "md": md, "count": len(tickets)}


if __name__ == "__main__":
    raise_defects()
