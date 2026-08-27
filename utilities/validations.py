"""
validations.py
--------------
Reusable validation building blocks.  Every test case calls one of these.

Each function:
  * reads what it needs from the YAML config (via `_context`)
  * runs one check against SQL Server
  * writes a PASS / FAIL line to the log file
  * records the outcome in result_store (for the reports)
  * returns True  (pass)  or  False (fail)   so pytest can `assert` on it

Required reusable checks (from the requirement):
  Count_Validation, Duplicate_Validation, Null_Validation,
  direct_move_Validation, Metadata_Validation, Constraint_Validation

Extra helpers for the transformed layers:
  data_integrity_Validation, Transformation_Validation
"""

import re

from utilities import db, comparison, result_store
from utilities.config_loader import get_layer_config, get_table_config
from utilities.logger import get_logger

log = get_logger()


# --------------------------------------------------------------------------
# context : work out the source/target tables + the right WHERE filters
# --------------------------------------------------------------------------
def _context(layer, table):
    layer_cfg = get_layer_config(layer)
    tcfg = get_table_config(layer, table)

    ctx = {
        "layer": layer,
        "table": table,
        "source_db": layer_cfg["source_db"],
        "target_db": layer_cfg["target_db"],
        "source_table": tcfg["source_table"],
        "target_table": tcfg["target_table"],
        "keys": tcfg["key"],
        "compare_columns": tcfg.get("compare_columns", []),
        "not_null_columns": tcfg.get("not_null_columns", []),
        "transformations": tcfg.get("transformations", []),
        # filters, filled in per layer below
        "source_where": None,
        "target_where": None,
        "count_source_where": None,
        "count_target_where": None,
    }

    if layer == "PreStagingToStaging":
        # only accepted rows are compared to their source
        valid = layer_cfg.get("valid_filter")            # "IsValid = 1"
        ctx["target_where"] = valid
        # every prestaging row should become an accepted OR rejected staging
        # row, so the TOTAL counts must match (no filter on either side)
        ctx["count_source_where"] = None
        ctx["count_target_where"] = None

    elif layer == "StagingToDWH":
        src_valid = layer_cfg.get("source_valid_filter")  # "IsValid = 1"
        tgt_filter = tcfg.get("target_filter")            # "IsCurrent = 1" or None
        ctx["source_where"] = src_valid
        ctx["target_where"] = tgt_filter
        ctx["count_source_where"] = src_valid
        ctx["count_target_where"] = tgt_filter

    return ctx


def _read_side(ctx, side, columns):
    """Read the source or target table with the correct filter applied."""
    if side == "source":
        return db.read_table(ctx["source_db"], ctx["source_table"],
                             columns=columns, where=ctx["source_where"])
    return db.read_table(ctx["target_db"], ctx["target_table"],
                         columns=columns, where=ctx["target_where"])


def _record(ctx, name, passed, message, category="basic"):
    """Log + store one validation outcome and return the pass flag."""
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {ctx['layer']} | {ctx['table']} | {name} | {message}"
    (log.info if passed else log.error)(line)
    result_store.add_result(ctx["layer"], ctx["table"], name, status,
                            message, category=category)
    return passed


# ==========================================================================
# 1. COUNT VALIDATION
# ==========================================================================
def Count_Validation(layer, table):
    """Source row count should equal target row count (using layer filters)."""
    ctx = _context(layer, table)
    src = db.get_row_count(ctx["source_db"], ctx["source_table"],
                           where=ctx["count_source_where"])
    tgt = db.get_row_count(ctx["target_db"], ctx["target_table"],
                           where=ctx["count_target_where"])
    passed = src == tgt
    msg = f"source={src}, target={tgt}, diff={src - tgt}"
    return _record(ctx, "Count_Validation", passed, msg)


# ==========================================================================
# 2. DUPLICATE VALIDATION  (target must not have duplicate business keys)
# ==========================================================================
def Duplicate_Validation(layer, table):
    ctx = _context(layer, table)
    keys = ctx["keys"]
    key_sql = ", ".join(f"[{k}]" for k in keys)
    where = f" WHERE {ctx['target_where']}" if ctx["target_where"] else ""
    sql = (f"SELECT {key_sql}, COUNT(*) AS cnt FROM {ctx['target_table']}"
           f"{where} GROUP BY {key_sql} HAVING COUNT(*) > 1")
    dups = db.read_query(ctx["target_db"], sql)
    passed = dups.empty
    msg = ("no duplicate keys" if passed
           else f"{len(dups)} duplicate key group(s) on {keys}")
    return _record(ctx, "Duplicate_Validation", passed, msg)


# ==========================================================================
# 3. NULL VALIDATION  (not-null columns must not contain NULLs in target)
# ==========================================================================
def Null_Validation(layer, table):
    ctx = _context(layer, table)
    bad = []
    for col in ctx["not_null_columns"]:
        where = f"[{col}] IS NULL"
        if ctx["target_where"]:
            where += f" AND {ctx['target_where']}"
        n = db.get_row_count(ctx["target_db"], ctx["target_table"], where=where)
        if n > 0:
            bad.append(f"{col}={n}")
    passed = not bad
    msg = "no nulls in required columns" if passed else "nulls found -> " + ", ".join(bad)
    return _record(ctx, "Null_Validation", passed, msg)


# ==========================================================================
# 4. DIRECT MOVE VALIDATION  (Source -> PreStaging must be identical)
# ==========================================================================
def direct_move_Validation(layer, table):
    ctx = _context(layer, table)
    cols = ctx["keys"] + [c for c in ctx["compare_columns"] if c not in ctx["keys"]]
    src_df = _read_side(ctx, "source", cols)
    tgt_df = _read_side(ctx, "target", cols)

    result = comparison.compare_dataframes(src_df, tgt_df,
                                           ctx["keys"], ctx["compare_columns"])
    # store detail for the coloured detailed report
    result_store.add_comparison(layer, table, ctx["keys"], result)
    passed = result["is_match"]
    msg = (f"diffs={len(result['diffs'])}, "
           f"missing_in_target={len(result['missing_in_target'])}, "
           f"missing_in_source={len(result['missing_in_source'])}, "
           f"duplicates={len(result['duplicates'])}")
    return _record(ctx, "direct_move_Validation", passed, msg)


# ==========================================================================
# 5. METADATA VALIDATION  (expected columns exist on both sides)
# ==========================================================================
def Metadata_Validation(layer, table):
    ctx = _context(layer, table)
    expected = ctx["keys"] + [c for c in ctx["compare_columns"] if c not in ctx["keys"]]
    src_cols = set(db.get_columns(ctx["source_db"], ctx["source_table"]))
    tgt_cols = set(db.get_columns(ctx["target_db"], ctx["target_table"]))

    missing_src = [c for c in expected if c not in src_cols]
    missing_tgt = [c for c in expected if c not in tgt_cols]
    passed = not missing_src and not missing_tgt
    if passed:
        msg = f"all {len(expected)} expected columns present on both sides"
    else:
        msg = f"missing in source={missing_src}, missing in target={missing_tgt}"
    return _record(ctx, "Metadata_Validation", passed, msg)


# ==========================================================================
# 6. CONSTRAINT VALIDATION  (key columns unique + not null in target)
# ==========================================================================
def Constraint_Validation(layer, table):
    ctx = _context(layer, table)
    keys = ctx["keys"]
    problems = []

    # 6a. key columns not null
    for k in keys:
        where = f"[{k}] IS NULL"
        if ctx["target_where"]:
            where += f" AND {ctx['target_where']}"
        n = db.get_row_count(ctx["target_db"], ctx["target_table"], where=where)
        if n > 0:
            problems.append(f"{k} has {n} null(s)")

    # 6b. key uniqueness
    key_sql = ", ".join(f"[{k}]" for k in keys)
    where = f" WHERE {ctx['target_where']}" if ctx["target_where"] else ""
    sql = (f"SELECT {key_sql} FROM {ctx['target_table']}{where} "
           f"GROUP BY {key_sql} HAVING COUNT(*) > 1")
    dups = db.read_query(ctx["target_db"], sql)
    if not dups.empty:
        problems.append(f"{len(dups)} duplicate key group(s)")

    passed = not problems
    msg = "key constraints OK (unique + not null)" if passed else "; ".join(problems)
    return _record(ctx, "Constraint_Validation", passed, msg)


# ==========================================================================
# EXTRA: DATA INTEGRITY  (transformed layers - matched records must agree)
# ==========================================================================
def data_integrity_Validation(layer, table):
    """
    For PreStaging->Staging and Staging->DWH:
    every accepted/current target record must match its source record on the
    compared columns.  Rejected source rows (PreStaging->Staging only) are
    tolerated and NOT counted as failures.
    """
    ctx = _context(layer, table)
    cols = ctx["keys"] + [c for c in ctx["compare_columns"] if c not in ctx["keys"]]
    src_df = _read_side(ctx, "source", cols)
    tgt_df = _read_side(ctx, "target", cols)

    # transformed layers standardise case (e.g. Credit -> CREDIT); that is an
    # intended change, so compare text case-insensitively here.
    result = comparison.compare_dataframes(src_df, tgt_df,
                                           ctx["keys"], ctx["compare_columns"],
                                           case_insensitive=True)
    result_store.add_comparison(layer, table, ctx["keys"], result)

    tolerate_rejects = (layer == "PreStagingToStaging")
    missing_tgt = 0 if tolerate_rejects else len(result["missing_in_target"])

    passed = (not result["diffs"]
              and not result["missing_in_source"]
              and not result["duplicates"]
              and missing_tgt == 0)
    msg = (f"diffs={len(result['diffs'])}, "
           f"orphan_target={len(result['missing_in_source'])}, "
           f"duplicates={len(result['duplicates'])}, "
           f"missing_in_target={len(result['missing_in_target'])}"
           f"{' (tolerated)' if tolerate_rejects else ''}")
    return _record(ctx, "data_integrity_Validation", passed, msg)


# ==========================================================================
# EXTRA: TRANSFORMATION RULES  (data-quality rules on the target table)
# ==========================================================================
def _rule_fails(series, rule, value):
    """Return a boolean Series that is True where the rule is BROKEN."""
    s = series
    if rule == "not_null":
        return s.isna()
    if rule == "no_whitespace":
        text = s.astype("string")
        return text.notna() & (text != text.str.strip())
    if rule == "length_equals":
        text = s.astype("string")
        return text.notna() & (text.str.len() != int(value))
    if rule == "in_set":
        allowed = set(str(v) for v in value)
        text = s.astype("string")
        return text.notna() & (~text.isin(allowed))
    if rule == "min_value":
        nums = s.astype("float")
        return nums.notna() & (nums < float(value))
    if rule == "regex":
        pattern = re.compile(value)
        text = s.astype("string")
        return text.notna() & (~text.map(lambda x: bool(pattern.match(x))
                                         if x is not None else True))
    raise ValueError(f"Unknown transformation rule '{rule}'")


def Transformation_Validation(layer, table):
    """Apply every transformation rule from the YAML to the target table."""
    ctx = _context(layer, table)
    rules = ctx["transformations"]
    if not rules:
        return _record(ctx, "Transformation_Validation", True,
                       "no transformation rules configured", category="transformation")

    cols = list({r["column"] for r in rules} | set(ctx["keys"]))
    tgt_df = _read_side(ctx, "target", cols)

    broken = []
    for r in rules:
        col, rule = r["column"], r["rule"]
        value = r.get("value")
        fail_mask = _rule_fails(tgt_df[col], rule, value)
        n = int(fail_mask.sum())
        if n > 0:
            broken.append(f"{col}[{rule}]={n}")

    passed = not broken
    desc = "; ".join(f"{r['column']}:{r['rule']}" for r in rules)
    msg = (f"all rules passed ({desc})" if passed
           else "rule breaks -> " + ", ".join(broken))
    return _record(ctx, "Transformation_Validation", passed, msg,
                   category="transformation")
