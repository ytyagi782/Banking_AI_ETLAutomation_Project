"""
agents/agent_1_mapping_doc.py   -   STEP 1
==========================================
AI Agent: generate the Source -> Target MAPPING DOCUMENT as an Excel workbook.

One sheet per ETL layer:
    SourceToPreStaging | PreStagingToStaging | StagingToDWH

Each row maps ONE target column back to its source column and carries the full
metadata the user asked for:

    Source: DB | Table | Column | Data Type | Size | Nullability | Constraints
    Transformation Rule
    Target: DB | Table | Column | Data Type | Size | Nullability | Constraints

Where the facts come from:
  * column data type / size / nullability -> real DB metadata via
    agents/schema_introspect.py (falls back to YAML column names if DB is down)
  * constraints                            -> DB keys/FKs + YAML key/not-null
  * transformation rule                    -> derived from the layer YAML
    (direct move / cleaning rules / SCD & surrogate-key notes). When an
    ANTHROPIC_API_KEY is present, Claude rewrites those rules into clearer,
    business-friendly English (deterministic text is used otherwise).

Run:
    python -m agents.agent_1_mapping_doc
Output:
    agents/output/MappingDocument_<timestamp>.xlsx
"""

from openpyxl import Workbook

from utilities import config_loader
from utilities.logger import get_logger
from agents import base, schema_introspect as si
from agents.xlsx_util import write_sheet

log = get_logger()

LAYERS = ["SourceToPreStaging", "PreStagingToStaging", "StagingToDWH"]

HEADERS = [
    "Source DB Name", "Source Table Name", "Source Column Name",
    "Source Data Type", "Source Size", "Source Nullability", "Source Constraints",
    "Transformation Rule",
    "Target DB Name", "Target Table Name", "Target Column Name",
    "Target Data Type", "Target Size", "Target Nullability", "Target Constraints",
]
GROUP_BANDS = [("SOURCE", 7, "source"), ("TRANSFORM", 1, "transform"),
               ("TARGET", 7, "target")]

# audit / control columns that are populated by the load proc, not the source
_AUDIT = {"createddate", "updateddate", "loaddate", "loadedon", "insertdate"}
_SCD = {"iscurrent", "effectivedate", "expirydate", "startdate", "enddate",
        "validfrom", "validto", "rowversion"}


# --------------------------------------------------------------------------
# transformation-rule logic (deterministic; optionally AI-polished)
# --------------------------------------------------------------------------
def _layer2_rule_map(tcfg):
    """Column -> combined transformation description from the layer-2 YAML."""
    rules = {}
    for t in tcfg.get("transformations", []):
        col = t.get("column")
        desc = t.get("description") or f"{t.get('rule')} = {t.get('value')}"
        rules.setdefault(col, []).append(desc)
    return {c: "; ".join(v) for c, v in rules.items()}


def _rule_for(layer, tcfg, target_col, has_source):
    """Return the transformation-rule text for a single target column."""
    low = target_col.lower()

    if layer == "SourceToPreStaging":
        return ("Direct move - exact copy from source"
                if has_source else "Populated by load procedure (not in source)")

    if layer == "PreStagingToStaging":
        rmap = _layer2_rule_map(tcfg)
        if target_col in rmap:
            return rmap[target_col]
        if low == "isvalid":
            return "Validity flag set by load proc: 1 = accepted, 0 = rejected"
        if low == "rejectionreason":
            return "Reason text populated when the row is rejected (IsValid = 0)"
        if low in _AUDIT:
            return "Populated by load procedure (audit column)"
        if has_source:
            return "Cleaned & standardised (trim spaces, standardise case), then copied"
        return "Populated by load procedure (not in source)"

    if layer == "StagingToDWH":
        dim_type = tcfg.get("dim_type", "")
        if low.endswith("sk"):
            return "Surrogate key generated in the warehouse"
        if low in _SCD:
            return "SCD control column (tracks the current/historical version)"
        if low in _AUDIT:
            return "Populated by load procedure (audit column)"
        if dim_type == "Type1":
            base_rule = "Type-1 dimension load - overwrites with the latest value (no history)"
        elif dim_type == "Type2":
            base_rule = "Type-2 dimension load - history preserved; current row has IsCurrent = 1"
        elif dim_type == "Fact":
            base_rule = ("Fact load - natural keys replaced by surrogate keys "
                         "(...SK) via dimension lookup")
        else:
            base_rule = "Loaded into the warehouse"
        if not has_source:
            return f"{base_rule} (derived in target)"
        return base_rule

    return ""


# --------------------------------------------------------------------------
# AI enrichment (optional) - polish the distinct rule strings into clearer English
# --------------------------------------------------------------------------
def _maybe_ai_polish(rules):
    """
    Given a set of distinct rule strings, return {original: improved}. Uses Claude
    when a key is present; otherwise returns identity. Never raises - on any
    error it falls back to the original text.
    """
    unique = sorted(set(rules))
    if not unique or not base.have_api_key():
        return {r: r for r in unique}
    try:
        from pydantic import BaseModel

        class Rule(BaseModel):
            original: str
            improved: str

        class Rules(BaseModel):
            rules: list[Rule]

        system = (
            "You are an ETL data-mapping analyst. Rewrite each terse "
            "transformation rule as ONE clear, business-friendly sentence. "
            "Keep it accurate and concise; do not invent rules that are not "
            "implied by the original. Preserve every 'original' string exactly."
        )
        user = "Rewrite these transformation rules:\n" + "\n".join(
            f"- {r}" for r in unique)
        result = base.ask_claude_json(system, user, Rules, max_tokens=2000)
        mapping = {r.original: r.improved for r in result.rules}
        # guarantee full coverage even if the model dropped one
        return {r: mapping.get(r, r) for r in unique}
    except Exception as exc:
        log.warning(f"[agent_1] AI polish skipped ({exc}); using deterministic text")
        return {r: r for r in unique}


# --------------------------------------------------------------------------
# build one layer's rows
# --------------------------------------------------------------------------
def _build_layer_rows(layer):
    cfg = config_loader.get_layer_config(layer)
    src_db_logical = cfg["source_db"]
    tgt_db_logical = cfg["target_db"]
    src_db = config_loader.resolve_database(src_db_logical)
    tgt_db = config_loader.resolve_database(tgt_db_logical)

    rows = []
    for table_name, tcfg in cfg.get("tables", {}).items():
        src_table = tcfg["source_table"]
        tgt_table = tcfg["target_table"]

        src_cols = si.column_metadata(src_db_logical, src_table)
        tgt_cols = si.column_metadata(tgt_db_logical, tgt_table)
        src_by_name = {c["name"].lower(): c for c in src_cols}

        for tcol in tgt_cols:
            scol = src_by_name.get(tcol["name"].lower())
            has_source = scol is not None
            rule = _rule_for(layer, tcfg, tcol["name"], has_source)

            src_cons = (si.constraints_for_column(src_db_logical, src_table,
                                                  scol["name"], tcfg)
                        if has_source else "")
            tgt_cons = si.constraints_for_column(tgt_db_logical, tgt_table,
                                                 tcol["name"], tcfg)

            rows.append([
                src_db if has_source else "",
                src_table if has_source else "",
                scol["name"] if has_source else "",
                scol["data_type"] if has_source else "",
                scol["size"] if has_source else "",
                scol["nullable"] if has_source else "",
                src_cons,
                rule,
                tgt_db, tgt_table, tcol["name"],
                tcol["data_type"], tcol["size"], tcol["nullable"], tgt_cons,
            ])
    return rows


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def generate():
    """Build the mapping document and return the output path."""
    base.banner("STEP 1  -  AI Agent: Generate Mapping Document")
    print(base.ai_status())

    wb = Workbook()
    wb.remove(wb.active)  # drop the default empty sheet

    all_rules = []
    layer_rows = {}
    for layer in LAYERS:
        rows = _build_layer_rows(layer)
        layer_rows[layer] = rows
        all_rules.extend(r[7] for r in rows)  # column 8 = Transformation Rule
        log.info(f"[agent_1] {layer}: {len(rows)} mapping rows")

    # optional AI polish of the transformation-rule wording
    polish = _maybe_ai_polish(all_rules)

    for layer in LAYERS:
        ws = wb.create_sheet(title=layer)
        rows = layer_rows[layer]
        for r in rows:
            r[7] = polish.get(r[7], r[7])
        write_sheet(ws, HEADERS, rows, group_bands=GROUP_BANDS)

    out = base.versioned_output_path("MappingDocument", ".xlsx")
    wb.save(out)
    base.prune_versions("MappingDocument", ".xlsx")
    print(f"\nMapping document written to:\n  {out}")
    log.info(f"[agent_1] mapping document saved: {out}")
    return out


if __name__ == "__main__":
    generate()
