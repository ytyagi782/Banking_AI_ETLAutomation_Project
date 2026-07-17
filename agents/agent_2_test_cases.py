"""
agents/agent_2_test_cases.py   -   STEP 2
=========================================
AI Agent: generate TEST CASES (Excel) from the mapping document / config.

The test cases cover all three ETL movements - SourceToPreStaging,
PreStagingToStaging and StagingToDWH - and every case is tied to an EXISTING
reusable validation in `validations/validations.py`. That "Suggested Validation"
column is the bridge to STEP 3 (code generation): each row becomes a pytest
method that asserts on that validation.

Columns:
    TestCaseID | Layer | Table | Column(s) | TestType | Description |
    Precondition | Test Steps | Expected Result | Priority | Suggested Validation

Deterministic baseline test cases are always produced (so this works with no API
key). When ANTHROPIC_API_KEY is present, Claude ADDS extra edge / negative cases
per layer and enriches the wording.

Run:
    python -m agents.agent_2_test_cases
Output:
    agents/output/TestCases_<timestamp>.xlsx
"""

from openpyxl import Workbook

from utilities import config_loader
from utilities.logger import get_logger
from agents import base
from agents.xlsx_util import write_sheet

log = get_logger()

LAYERS = ["SourceToPreStaging", "PreStagingToStaging", "StagingToDWH"]

HEADERS = [
    "TestCaseID", "Layer", "Table", "Column(s)", "TestType", "Description",
    "Precondition", "Test Steps", "Expected Result", "Priority",
    "Suggested Validation",
]

# short codes used in TestCaseIDs, matching the tests/ file naming
LAYER_CODE = {
    "SourceToPreStaging": "SRCPS",
    "PreStagingToStaging": "PSSTG",
    "StagingToDWH": "STGDW",
}

PRECONDITION = ("All 4 layers are loaded from the golden source data "
                "(prerequisite reset/reload has run and passed).")


# --------------------------------------------------------------------------
# the standard validation catalogue, per layer (maps 1:1 to code in step 3)
# --------------------------------------------------------------------------
def _standard_cases(layer, table, tcfg):
    """
    Return the baseline list of test-case dicts for one table in one layer.
    Each dict has: test_type, columns, description, steps, expected, priority,
    validation.
    """
    keys = ", ".join(tcfg.get("key", []))
    not_null = ", ".join(tcfg.get("not_null_columns", []))
    compare = ", ".join(tcfg.get("compare_columns", []))
    src = tcfg["source_table"]
    tgt = tcfg["target_table"]

    cases = [
        {
            "test_type": "Metadata / Schema",
            "columns": compare,
            "description": f"Verify all expected columns exist on {src} and {tgt}.",
            "steps": f"Read column lists of {src} and {tgt}; compare against the "
                     f"expected column set.",
            "expected": "All expected columns are present on both source and target.",
            "priority": "High",
            "validation": "Metadata_Validation",
        },
        {
            "test_type": "Row Count",
            "columns": keys,
            "description": f"Verify the row count moving from {src} to {tgt}.",
            "steps": f"COUNT(*) on {src} and {tgt} (with the layer's filters); "
                     f"compare the two counts.",
            "expected": "Source and target counts match for this movement.",
            "priority": "High",
            "validation": "Count_Validation",
        },
        {
            "test_type": "Duplicate Check",
            "columns": keys,
            "description": f"Verify {tgt} has no duplicate business keys ({keys}).",
            "steps": f"GROUP BY {keys} on {tgt}; assert no key appears more than once.",
            "expected": f"No duplicate {keys} values in {tgt}.",
            "priority": "High",
            "validation": "Duplicate_Validation",
        },
        {
            "test_type": "Null Check",
            "columns": not_null,
            "description": f"Verify required columns ({not_null}) are not NULL in {tgt}.",
            "steps": f"Check {not_null} in {tgt} for NULLs.",
            "expected": f"No NULLs in the required columns of {tgt}.",
            "priority": "High",
            "validation": "Null_Validation",
        },
        {
            "test_type": "Constraint / Key",
            "columns": keys,
            "description": f"Verify key columns ({keys}) are unique and not null in {tgt}.",
            "steps": f"Check {keys} in {tgt} are unique and populated.",
            "expected": f"{keys} is unique and not null in {tgt}.",
            "priority": "High",
            "validation": "Constraint_Validation",
        },
    ]

    if layer == "SourceToPreStaging":
        cases.append({
            "test_type": "Direct Move (exact copy)",
            "columns": compare,
            "description": f"Verify {tgt} is an exact copy of {src} (row + column level).",
            "steps": f"Match rows on {keys}; compare every column value between "
                     f"{src} and {tgt}.",
            "expected": "Target is an exact, unchanged copy of the source.",
            "priority": "High",
            "validation": "direct_move_Validation",
        })

    if layer in ("PreStagingToStaging", "StagingToDWH"):
        cases.append({
            "test_type": "Data Integrity",
            "columns": compare,
            "description": f"Verify accepted/current rows in {tgt} still match {src} "
                           f"(case-insensitive).",
            "steps": f"Match rows on {keys} (accepted/current only); compare "
                     f"business columns between {src} and {tgt}.",
            "expected": "Matched rows agree on all compared business columns.",
            "priority": "High",
            "validation": "data_integrity_Validation",
        })

    if layer == "PreStagingToStaging":
        transforms = tcfg.get("transformations", [])
        tcols = ", ".join(t.get("column", "") for t in transforms)
        # one overall transformation test case (maps to code in step 3)
        cases.append({
            "test_type": "Transformation / Data Quality",
            "columns": tcols,
            "description": "Verify all data-quality / transformation rules on "
                           f"{tgt}: " + "; ".join(
                               f"{t.get('column')} ({t.get('description')})"
                               for t in transforms),
            "steps": "Apply each configured rule (in_set / regex / min / length / "
                     f"no_whitespace) to the relevant column in {tgt}.".format(tgt=tgt),
            "expected": "Every transformation rule holds for all accepted rows.",
            "priority": "Medium",
            "validation": "Transformation_Validation",
        })

    return cases


def _row_from_case(layer, table, idx, case):
    tcid = f"TC_{LAYER_CODE[layer]}_{table[:3].upper()}_{idx:03d}"
    return [
        tcid, layer, table, case["columns"], case["test_type"],
        case["description"], PRECONDITION, case["steps"], case["expected"],
        case["priority"], case["validation"],
    ]


# --------------------------------------------------------------------------
# optional AI enrichment - extra edge / negative cases per layer
# --------------------------------------------------------------------------
def _maybe_ai_extra_cases(layer, tables):
    """
    Ask Claude for extra edge/negative test-case IDEAS for a layer. Each returned
    case still maps to one of the existing validations. Returns a list of case
    dicts (same shape as _standard_cases entries) with an added 'table'. Never
    raises; returns [] on any problem or when no key is present.
    """
    if not base.have_api_key():
        return []
    try:
        from pydantic import BaseModel

        VALID = ["Metadata_Validation", "Count_Validation", "Duplicate_Validation",
                 "Null_Validation", "Constraint_Validation", "direct_move_Validation",
                 "data_integrity_Validation", "Transformation_Validation"]

        class ExtraCase(BaseModel):
            table: str
            test_type: str
            columns: str
            description: str
            steps: str
            expected: str
            priority: str
            validation: str

        class ExtraCases(BaseModel):
            cases: list[ExtraCase]

        system = (
            "You are a senior ETL test analyst. Propose additional edge-case and "
            "negative test cases for one ETL layer of a banking data warehouse. "
            "Every case MUST reuse one of these existing validation functions: "
            + ", ".join(VALID) + ". Only use table names from the provided list. "
            "Be specific and non-duplicative; 2-4 cases per table is plenty."
        )
        user = (
            f"Layer: {layer}\nTables: {', '.join(tables)}\n\n"
            "Propose extra edge/negative cases (boundary values, special "
            "characters, rejection paths, SCD history, surrogate-key integrity as "
            "relevant to this layer)."
        )
        result = base.ask_claude_json(system, user, ExtraCases, max_tokens=3000)
        out = []
        for c in result.cases:
            if c.table in tables and c.validation in VALID:
                out.append(c.model_dump())
        log.info(f"[agent_2] AI added {len(out)} extra cases for {layer}")
        return out
    except Exception as exc:
        log.warning(f"[agent_2] AI extra-cases skipped for {layer} ({exc})")
        return []


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def generate():
    """Build the test-cases workbook and return the output path."""
    base.banner("STEP 2  -  AI Agent: Generate Test Cases")
    print(base.ai_status())

    wb = Workbook()
    wb.remove(wb.active)

    total = 0
    for layer in LAYERS:
        cfg = config_loader.get_layer_config(layer)
        tables = list(cfg.get("tables", {}).keys())

        rows = []
        counters = {t: 0 for t in tables}

        # deterministic baseline
        for table in tables:
            tcfg = cfg["tables"][table]
            for case in _standard_cases(layer, table, tcfg):
                counters[table] += 1
                rows.append(_row_from_case(layer, table, counters[table], case))

        # optional AI edge/negative cases
        for case in _maybe_ai_extra_cases(layer, tables):
            table = case["table"]
            counters[table] = counters.get(table, 0) + 1
            rows.append(_row_from_case(layer, table, counters[table], case))

        ws = wb.create_sheet(title=layer)
        write_sheet(ws, HEADERS, rows,
                    widths=[16, 20, 14, 22, 24, 45, 30, 45, 40, 10, 26])
        total += len(rows)
        log.info(f"[agent_2] {layer}: {len(rows)} test cases")

    out = base.versioned_output_path("TestCases", ".xlsx")
    wb.save(out)
    base.prune_versions("TestCases", ".xlsx")
    print(f"\n{total} test cases written to:\n  {out}")
    log.info(f"[agent_2] test cases saved: {out}")
    return out


if __name__ == "__main__":
    generate()
