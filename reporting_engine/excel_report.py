"""
excel_report.py
---------------
Builds TWO of the three reports:

  1. Summary report   -> high level pass / fail overview
  2. Detailed report  -> every failure, with coloured highlighting:
        yellow  = column value differs between source and target
        red     = record missing on one side
        orange  = duplicate record

(The third report - the management HTML - is in html_report.py.)
"""

from datetime import datetime, date
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from utilities import result_store
from utilities.config_loader import get_settings

_settings = get_settings()
_colors = _settings["reporting"]["colors"]

# reusable styles ----------------------------------------------------------
FILL_DIFF = PatternFill("solid", fgColor=_colors["diff"])       # yellow
FILL_MISSING = PatternFill("solid", fgColor=_colors["missing"])  # red
FILL_DUP = PatternFill("solid", fgColor=_colors["duplicate"])    # orange
FILL_HEADER = PatternFill("solid", fgColor="305496")             # blue header
FILL_PASS = PatternFill("solid", fgColor="C6EFCE")               # green
FILL_FAIL = PatternFill("solid", fgColor="FFC7CE")               # light red
FILL_SKIP = PatternFill("solid", fgColor="D9D9D9")               # grey (skipped)

FONT_HEADER = Font(bold=True, color="FFFFFF")
FONT_TITLE = Font(bold=True, size=14)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _safe(value):
    """Convert a value to something openpyxl can write."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return str(value)
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def _sheet_name(text):
    """Make a safe, unique-ish sheet name (Excel max 31 chars)."""
    bad = '[]:*?/\\'
    clean = "".join("_" if c in bad else c for c in text)
    return clean[:31]


def _write_header(ws, headers, row=1):
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=title)
        cell.fill = FILL_HEADER
        cell.font = FONT_HEADER
        cell.alignment = Alignment(horizontal="center")
        cell.border = BORDER


def _autofit(ws, max_width=50):
    for col in ws.columns:
        length = 0
        letter = col[0].column_letter
        for cell in col:
            if cell.value is not None:
                length = max(length, len(str(cell.value)))
        ws.column_dimensions[letter].width = min(max_width, max(12, length + 2))


# ==========================================================================
# 1. SUMMARY REPORT
# ==========================================================================
def build_summary_report(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    counts = result_store.summary_counts()
    ws["A1"] = "Banking ETL Automation - Summary Report"
    ws["A1"].font = FONT_TITLE
    ws["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # overall totals
    ws["A4"] = "Total"; ws["B4"] = counts["total"]
    ws["A5"] = "Passed"; ws["B5"] = counts["passed"]; ws["B5"].fill = FILL_PASS
    ws["A6"] = "Failed"; ws["B6"] = counts["failed"]
    if counts["failed"]:
        ws["B6"].fill = FILL_FAIL
    ws["A7"] = "Skipped"; ws["B7"] = counts["skipped"]
    if counts["skipped"]:
        ws["B7"].fill = FILL_SKIP
    ws["A8"] = "Pass rate %"; ws["B8"] = counts["pass_rate"]
    for r in range(4, 9):
        ws[f"A{r}"].font = Font(bold=True)

    # by layer
    ws["A10"] = "Results by layer"
    ws["A10"].font = Font(bold=True)
    _write_header(ws, ["Layer", "Passed", "Failed", "Skipped"], row=11)
    r = 12
    for layer, g in result_store.summary_by_layer().items():
        ws.cell(row=r, column=1, value=layer)
        ws.cell(row=r, column=2, value=g["passed"])
        fcell = ws.cell(row=r, column=3, value=g["failed"])
        if g["failed"]:
            fcell.fill = FILL_FAIL
        scell = ws.cell(row=r, column=4, value=g["skipped"])
        if g["skipped"]:
            scell.fill = FILL_SKIP
        r += 1

    # full result list
    start = r + 2
    ws.cell(row=start - 1, column=1, value="All validations").font = Font(bold=True)
    _write_header(ws, ["Layer", "Table", "Validation", "Category",
                       "Status", "Message"], row=start)
    row = start + 1
    status_fill = {"PASS": FILL_PASS, "FAIL": FILL_FAIL, "SKIP": FILL_SKIP}
    # executed tests first (PASS/FAIL), then the skipped ones
    for res in result_store.get_executed() + result_store.get_skipped():
        ws.cell(row=row, column=1, value=res["layer"])
        ws.cell(row=row, column=2, value=res["table"])
        ws.cell(row=row, column=3, value=res["validation"])
        ws.cell(row=row, column=4, value=res["category"])
        scell = ws.cell(row=row, column=5, value=res["status"])
        scell.fill = status_fill.get(res["status"], FILL_FAIL)
        ws.cell(row=row, column=6, value=res["message"])
        row += 1

    _autofit(ws)
    wb.save(path)
    return path


# ==========================================================================
# 2. DETAILED REPORT  (coloured)
# ==========================================================================
def _add_failures_sheet(wb):
    ws = wb.active
    ws.title = "Failures"
    ws["A1"] = "Failed Validations"
    ws["A1"].font = FONT_TITLE
    _write_header(ws, ["Layer", "Table", "Validation", "Category", "Message"],
                  row=3)
    failures = result_store.get_failures()
    if not failures:
        ws["A5"] = "No failures - all validations passed."
        ws["A5"].fill = FILL_PASS
        return
    row = 4
    for f in failures:
        ws.cell(row=row, column=1, value=f["layer"])
        ws.cell(row=row, column=2, value=f["table"])
        ws.cell(row=row, column=3, value=f["validation"])
        ws.cell(row=row, column=4, value=f["category"])
        ws.cell(row=row, column=5, value=f["message"]).fill = FILL_FAIL
        row += 1
    _autofit(ws)


# friendly layer labels shown in the "Layer" column
_LAYER_LABEL = {
    "SourceToPreStaging": "Source -> PreStaging",
    "PreStagingToStaging": "PreStaging -> Staging",
    "StagingToDWH": "Staging -> DWH",
}

# the leading (extra) columns added in front of the real table columns
_META_HEADERS = ["Layer", "FailureType", "RowDestination"]

# which highlight colour goes with which FailureType
_TYPE_FILL = {
    "DF": FILL_DIFF,                    # yellow
    "Missing in Source": FILL_MISSING,  # red
    "Missing in Target": FILL_MISSING,  # red
    "Duplicate in Source": FILL_DUP,    # orange
    "Duplicate in Target": FILL_DUP,    # orange
}


def _has_issues(detail):
    return bool(detail["diff_pairs"] or detail["missing_in_target"]
                or detail["missing_in_source"] or detail["duplicates"])


def _display_columns(details):
    """Ordered union of the real table columns across all of a table's layers."""
    cols = []
    for d in details:
        for c in d.get("columns", []):
            if c not in cols:
                cols.append(c)
    return cols


def _failure_records(detail):
    """
    Turn one comparison into failure records. Each record is:
      { layer, ftype, dest, row (dict of column->value), highlight (set of cols) }
    so the report can lay the real columns out in their own cells.
    """
    layer = _LAYER_LABEL.get(detail["layer"], detail["layer"])
    recs = []

    # DF = value differs -> show the FULL source row and the FULL target row,
    # highlighting only the columns that actually differ.
    for pair in detail["diff_pairs"]:
        hl = set(pair["diff_columns"])
        recs.append({"layer": layer, "ftype": "DF", "dest": "Source",
                     "row": pair["source_row"], "highlight": hl})
        recs.append({"layer": layer, "ftype": "DF", "dest": "Target",
                     "row": pair["target_row"], "highlight": hl})

    # record exists in source but NOT in target (whole row highlighted)
    for row in detail["missing_in_target"]:
        recs.append({"layer": layer, "ftype": "Missing in Target", "dest": "Source",
                     "row": row, "highlight": set(row.keys())})

    # record exists in target but NOT in source
    for row in detail["missing_in_source"]:
        recs.append({"layer": layer, "ftype": "Missing in Source", "dest": "Target",
                     "row": row, "highlight": set(row.keys())})

    # duplicate key (the stored _side says which table it was on)
    for row in detail["duplicates"]:
        side = row.get("_side", "source")
        dest = "Source" if side == "source" else "Target"
        clean = {c: v for c, v in row.items() if not c.startswith("_")}
        recs.append({"layer": layer, "ftype": f"Duplicate in {dest}", "dest": dest,
                     "row": clean, "highlight": set(clean.keys())})

    return recs


def _add_table_sheet(wb, table, details, max_rows):
    """
    ONE sheet per table, laid out like a normal Excel table:
    Layer | FailureType | RowDestination | <each real table column ...>
    Cells are coloured: yellow=differing value, red=missing row, orange=duplicate.
    """
    records = []
    for detail in details:                      # details are in layer order
        if _has_issues(detail):
            records.extend(_failure_records(detail))
    if not records:
        return  # this table passed everywhere - no sheet needed
    records = records[:max_rows]

    display_cols = _display_columns(details)

    ws = wb.create_sheet(_sheet_name(table))
    ws["A1"] = f"Detailed failures - {table}"
    ws["A1"].font = FONT_TITLE

    # legend explaining the colours / failure types
    ws["A2"] = "Legend:"
    ws["B2"] = "DF = value differs"; ws["B2"].fill = FILL_DIFF
    ws["C2"] = "Missing record"; ws["C2"].fill = FILL_MISSING
    ws["D2"] = "Duplicate record"; ws["D2"].fill = FILL_DUP

    # header row = extra columns + the real table columns
    _write_header(ws, _META_HEADERS + display_cols, row=4)

    # data rows
    r = 5
    n_meta = len(_META_HEADERS)
    for rec in records:
        fill = _TYPE_FILL.get(rec["ftype"])
        ws.cell(row=r, column=1, value=rec["layer"])
        ftype_cell = ws.cell(row=r, column=2, value=rec["ftype"])
        if fill:
            ftype_cell.fill = fill
        ws.cell(row=r, column=3, value=rec["dest"])
        for i, col in enumerate(display_cols, start=n_meta + 1):
            cell = ws.cell(row=r, column=i, value=_safe(rec["row"].get(col)))
            if fill and col in rec["highlight"]:
                cell.fill = fill
        r += 1

    _autofit(ws)


def build_detailed_report(path):
    wb = Workbook()
    _add_failures_sheet(wb)
    max_rows = _settings["reporting"].get("max_detail_rows", 500)

    # group all comparisons by table name  ->  exactly ONE sheet per table
    by_table = {}
    for detail in result_store.get_comparisons().values():
        by_table.setdefault(detail["table"], []).append(detail)

    for table, details in by_table.items():
        _add_table_sheet(wb, table, details, max_rows)

    wb.save(path)
    return path
