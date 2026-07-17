"""
comparison.py
-------------
Compares a SOURCE DataFrame with a TARGET DataFrame using business keys.

It answers four questions used everywhere in the reports:
  * diffs               same key, but a column value differs      (yellow)
  * missing_in_target   key exists in source but not in target    (red)
  * missing_in_source   key exists in target but not in source    (red)
  * duplicates          the same key appears more than once        (orange)

Values are "normalised" before comparing so that harmless differences
(trailing spaces, 10 vs 10.00, datetime vs date text) are NOT reported
as real differences.
"""

import math
from datetime import datetime, date
from decimal import Decimal

import pandas as pd


def _normalise(value):
    """Turn a cell value into something safe to compare."""
    if value is None:
        return None
    # pandas NaN / NaT
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    if value is pd.NaT:
        return None

    if isinstance(value, (int,)):
        return float(value)
    if isinstance(value, (float, Decimal)):
        return float(value)
    if isinstance(value, (datetime, date)):
        return str(value)
    # strings and everything else -> stripped text
    text = str(value).strip()
    return text if text != "" else None


def _values_equal(a, b, case_insensitive=False):
    """Compare two already-normalised values (with number tolerance)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 1e-9
    if case_insensitive and isinstance(a, str) and isinstance(b, str):
        return a.casefold() == b.casefold()
    return a == b


def _key_of(row, keys):
    """Build a tuple key from the key columns of a row (dict)."""
    return tuple(_normalise(row[k]) for k in keys)


def _duplicate_keys(df, keys):
    """Return the set of key tuples that appear more than once."""
    if df.empty:
        return set()
    counts = df.groupby(keys).size()
    dup = counts[counts > 1]
    return set(tuple(idx) if isinstance(idx, tuple) else (idx,)
               for idx in dup.index)


def compare_dataframes(source_df, target_df, keys, compare_columns,
                       case_insensitive=False):
    """
    Compare two DataFrames and return the detail dict.
    Only columns present in BOTH frames are compared.

    case_insensitive=True treats text values that differ only by upper/lower
    case as equal.  Use it for transformed layers where standardising case is
    an intended transformation (checked separately by Transformation_Validation).
    """
    # keep only columns that actually exist on both sides
    common_cols = [c for c in compare_columns
                   if c in source_df.columns and c in target_df.columns]

    diffs = []
    missing_in_target = []
    missing_in_source = []
    duplicates = []

    # ---- duplicates on each side -----------------------------------------
    for side, df in (("source", source_df), ("target", target_df)):
        for dup_key in _duplicate_keys(df, keys):
            mask = pd.Series([True] * len(df))
            for i, k in enumerate(keys):
                mask &= df[k].apply(_normalise) == dup_key[i]
            for _, row in df[mask].iterrows():
                rec = {c: row[c] for c in df.columns}   # keep the whole row
                rec["_side"] = side
                duplicates.append(rec)

    # ---- build key -> row lookups (first occurrence wins) ----------------
    def index_by_key(df):
        out = {}
        for _, row in df.iterrows():
            out.setdefault(_key_of(row, keys), row)
        return out

    src_by_key = index_by_key(source_df)
    tgt_by_key = index_by_key(target_df)

    src_keys = set(src_by_key)
    tgt_keys = set(tgt_by_key)

    # ---- missing records --------------------------------------------------
    for k in sorted(src_keys - tgt_keys, key=lambda t: [str(x) for x in t]):
        row = src_by_key[k]
        missing_in_target.append({c: row[c] for c in source_df.columns})

    for k in sorted(tgt_keys - src_keys, key=lambda t: [str(x) for x in t]):
        row = tgt_by_key[k]
        missing_in_source.append({c: row[c] for c in target_df.columns})

    # ---- column level diffs for keys present on both ---------------------
    # diffs      = one entry per differing cell (used for counts/messages)
    # diff_pairs = one entry per differing record, with the FULL source and
    #              target rows + the list of columns that differ (for the report)
    diff_pairs = []
    for k in sorted(src_keys & tgt_keys, key=lambda t: [str(x) for x in t]):
        s_row = src_by_key[k]
        t_row = tgt_by_key[k]
        diff_cols = []
        for col in common_cols:
            s_val = _normalise(s_row[col])
            t_val = _normalise(t_row[col])
            if not _values_equal(s_val, t_val, case_insensitive):
                diff_cols.append(col)
                rec = {key_col: s_row[key_col] for key_col in keys}
                rec["column"] = col
                rec["source_value"] = s_row[col]
                rec["target_value"] = t_row[col]
                diffs.append(rec)
        if diff_cols:
            diff_pairs.append({
                "diff_columns": diff_cols,
                "source_row": {c: s_row[c] for c in source_df.columns},
                "target_row": {c: t_row[c] for c in target_df.columns},
            })

    return {
        "columns": list(source_df.columns),   # display column order for the report
        "diffs": diffs,
        "diff_pairs": diff_pairs,
        "missing_in_target": missing_in_target,
        "missing_in_source": missing_in_source,
        "duplicates": duplicates,
        "is_match": not (diffs or missing_in_target
                         or missing_in_source or duplicates),
    }
