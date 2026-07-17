"""
agents/schema_introspect.py
===========================
The "real facts" tool. Agents reason about the ETL pipeline, but they must
reason about the ACTUAL database, not a guess. This module reads the true
column metadata and constraints straight from SQL Server's INFORMATION_SCHEMA
using the existing read-only helpers in `utilities/db.py`.

If the database is unreachable (offline demo, no VPN, etc.) every function
falls back to what the YAML config knows (column names, keys, not-null columns)
so the agents still produce a useful artifact - just with data type / size
marked "n/a".

Nothing here writes to the database - it only runs SELECT queries against
INFORMATION_SCHEMA, keeping the framework's read-only invariant intact.
"""

from utilities import db, config_loader

# cache metadata per (logical_db, table) so repeated agent calls hit the DB once
_meta_cache = {}
_constraint_cache = {}


def _split(table):
    """'dbo.SRC_Accounts' -> ('dbo', 'SRC_Accounts'); bare name -> ('dbo', name)."""
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = "dbo", table
    return schema, name


def _num(value):
    """Return an int for a real number, or None for NULL/NaN (pandas uses NaN)."""
    if value is None:
        return None
    # pandas returns float NaN for SQL NULLs; NaN != NaN is the portable test
    if isinstance(value, float) and value != value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_size(row):
    """Turn INFORMATION_SCHEMA numbers into a friendly 'Size' string."""
    char_len = _num(row.get("CHARACTER_MAXIMUM_LENGTH"))
    num_prec = _num(row.get("NUMERIC_PRECISION"))
    num_scale = _num(row.get("NUMERIC_SCALE"))
    if char_len is not None:
        return "MAX" if char_len == -1 else str(char_len)
    if num_prec is not None:
        if num_scale:
            return f"{num_prec},{num_scale}"
        return str(num_prec)
    return ""


def column_metadata(logical_db, table):
    """
    Return a list of dicts (in column order), one per column:
        {name, data_type, size, nullable}  where nullable is "YES"/"NO".

    DB-first; on any error falls back to the YAML columns for the table.
    """
    cache_key = (logical_db, table)
    if cache_key in _meta_cache:
        return _meta_cache[cache_key]

    schema, name = _split(table)
    sql = (
        "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, "
        "NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{name}' "
        "ORDER BY ORDINAL_POSITION"
    )
    try:
        df = db.read_query(logical_db, sql)
        cols = []
        for _, r in df.iterrows():
            row = r.to_dict()
            cols.append({
                "name": row["COLUMN_NAME"],
                "data_type": row["DATA_TYPE"],
                "size": _format_size(row),
                "nullable": str(row["IS_NULLABLE"]).upper(),
            })
        if not cols:
            raise ValueError("no columns returned")
        _meta_cache[cache_key] = cols
        return cols
    except Exception as exc:  # DB down / table missing -> YAML fallback
        cols = _meta_from_yaml_fallback(table)
        _meta_cache[cache_key] = cols
        return cols


def _meta_from_yaml_fallback(table):
    """
    Best-effort column list built from the layer YAMLs when the DB is offline.
    We don't know real data types offline, so type/size are 'n/a'.
    """
    seen = []
    names = []
    for layer in ("SourceToPreStaging", "PreStagingToStaging", "StagingToDWH"):
        cfg = config_loader.get_layer_config(layer)
        for tcfg in cfg.get("tables", {}).values():
            if table in (tcfg.get("source_table"), tcfg.get("target_table")):
                for c in tcfg.get("compare_columns", []):
                    if c not in names:
                        names.append(c)
    for n in names:
        seen.append({"name": n, "data_type": "n/a", "size": "n/a", "nullable": "n/a"})
    return seen


def key_constraints(logical_db, table):
    """
    Return {column_name: [constraint_label, ...]} for a table, e.g.
        {'AccountID': ['PK'], 'CustomerID': ['FK -> dbo.SRC_Customers']}.

    Reads PRIMARY KEY / UNIQUE / FOREIGN KEY from INFORMATION_SCHEMA.
    On any error returns {} (the caller then falls back to YAML key/not-null).
    """
    cache_key = (logical_db, table)
    if cache_key in _constraint_cache:
        return _constraint_cache[cache_key]

    schema, name = _split(table)
    result = {}
    try:
        # PK / UNIQUE
        sql_pk = (
            "SELECT kcu.COLUMN_NAME, tc.CONSTRAINT_TYPE "
            "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
            "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
            "  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
            " AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA "
            f"WHERE tc.TABLE_SCHEMA = '{schema}' AND tc.TABLE_NAME = '{name}' "
            "  AND tc.CONSTRAINT_TYPE IN ('PRIMARY KEY', 'UNIQUE')"
        )
        for _, r in db.read_query(logical_db, sql_pk).iterrows():
            label = "PK" if r["CONSTRAINT_TYPE"] == "PRIMARY KEY" else "UNIQUE"
            result.setdefault(r["COLUMN_NAME"], []).append(label)

        # FK (with the referenced table)
        sql_fk = (
            "SELECT kcu.COLUMN_NAME, "
            "       rcu.TABLE_SCHEMA AS REF_SCHEMA, rcu.TABLE_NAME AS REF_TABLE "
            "FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc "
            "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
            "  ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
            "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE rcu "
            "  ON rc.UNIQUE_CONSTRAINT_NAME = rcu.CONSTRAINT_NAME "
            f"WHERE kcu.TABLE_SCHEMA = '{schema}' AND kcu.TABLE_NAME = '{name}'"
        )
        for _, r in db.read_query(logical_db, sql_fk).iterrows():
            ref = f"FK -> {r['REF_SCHEMA']}.{r['REF_TABLE']}"
            result.setdefault(r["COLUMN_NAME"], []).append(ref)

        _constraint_cache[cache_key] = result
        return result
    except Exception:
        _constraint_cache[cache_key] = {}
        return {}


def constraints_for_column(logical_db, table, column, tcfg=None):
    """
    Human-readable constraint text for ONE column, combining DB facts with the
    YAML config (key + not-null) so we still say something useful offline.
    """
    labels = list(key_constraints(logical_db, table).get(column, []))

    if tcfg:
        if column in tcfg.get("key", []) and "PK" not in labels:
            labels.append("Business Key")
        if column in tcfg.get("not_null_columns", []) and "NOT NULL" not in labels:
            labels.append("NOT NULL")

    # de-duplicate while preserving order
    seen, out = set(), []
    for lab in labels:
        if lab not in seen:
            seen.add(lab)
            out.append(lab)
    return ", ".join(out) if out else ""
