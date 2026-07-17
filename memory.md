# Project Memory  (for AI + humans)

> Purpose: a running record of what this project is, what has been built, and
> what we expect next. Read this first, and keep it updated as work continues.

_Last updated: 2026-07-17_

---

## What this project is

A **modular, config-driven ETL automation testing framework** for a banking
data pipeline on SQL Server. It validates data as it flows through four layers
and produces logs + three reports (Summary, Detailed, Management HTML), with
optional email delivery.

### Environment (confirmed working)
* SQL Server instance: `DESKTOP-HL2FC2P\SQLYKT`
* Driver: `ODBC Driver 17 for SQL Server`
* Auth: **Windows Authentication** (`Trusted_Connection=yes`, no password)
* Databases: `Bank_Source`, `Bank_PreStaging`, `Bank_Staging`, `Bank_DWH`
* Python venv at `.venv`; connection to all 4 DBs tested OK.

### Layers and tables (4 per layer, discovered from the DB)
| Layer | DB | Tables | Load procs |
|-------|----|--------|------------|
| Source | Bank_Source | SRC_Accounts, SRC_Branches, SRC_Customers, SRC_Transactions | (none) |
| PreStaging | Bank_PreStaging | PS_* | usp_Load_PS_* |
| Staging | Bank_Staging | STG_* (have IsValid, RejectionReason) | usp_Load_STG_* |
| DWH | Bank_DWH | DimAccount_Type1, DimBranch_Type2, DimCustomer_Type2, FactTransaction | usp_Load_Dim*/Fact* |

### Known transformation logic (from the real data)
* PreStaging -> Staging **uppercases** text (Credit -> CREDIT, Active -> ACTIVE),
  **lowercases emails**, trims whitespace, and rejects bad/duplicate rows
  (IsValid=0 + RejectionReason).
* DWH: Type-2 dims keep history (IsCurrent flag); Fact uses surrogate keys.
* Matching is on the **natural/business key** (AccountID, BranchID, CustomerID,
  TransactionID), never the surrogate key.

---

## What has been built (DONE)

* `config/` - global `settings.yaml` + 3 layer YAMLs (all names/keys/columns/
  rules live here; no hard-coding in Python).
* `utilities/` - `config_loader`, `db`, `logger` (5-version rotation, name ends
  `_v#`), `result_store`, `comparison` (diff/missing/duplicate engine).
* `validations/validations.py` - the 6 required reusable checks +
  `data_integrity` + `Transformation`.
* `reporting_engine/` - Excel Summary, Excel Detailed, Management HTML,
  Email (SMTP, off by default), and `generate.py` to build them all.
  * Detailed report = ONE sheet per table, laid out like a NORMAL excel table:
    Layer | FailureType | RowDestination | <each real table column in its own
    cell>. FailureType = DF / Missing in Source / Missing in Target / Duplicate
    in Source / Duplicate in Target. RowDestination = Source / Target. Colours:
    DF highlights ONLY the differing column cell (yellow) and shows the record as
    two rows (Source + Target); Missing row = whole row red; Duplicate row =
    whole row orange. All layers for a table share the one sheet (Layer column).
    Enabled by comparison.py returning diff_pairs (full source/target rows +
    differing columns) and full rows for duplicates.
* `tests/` - 3 layer folders x 4 table files. Each file has a **basic** class
  (metadata, count, duplicate, null, constraint) and a **transformation/
  data-quality** class. Markers + `pytest.ini` ordering (Layer1 -> 2 -> 3).
* `conftest.py` - clears the store at start, builds all reports at the end.
* `main.py` - READ-ONLY entry point: checks DB connections only. It does NOT
  load data or execute stored procedures (per user's explicit requirement the
  framework must never run procs). `db.execute_proc` was removed too, so no
  write/proc capability exists anywhere - the framework is SELECT-only.
* Docs: `requirements.txt`, `architecture.md`, this `memory.md`, `.env.example`.

### Current test result (verified 2026-07-16, after package rename)
`68 passed, 9 failed`. Failures are **data-level detections by a working
framework**, not code errors. Three are the known, seeded direct-move defects:
* SRC_Accounts 1002: OpenDate & Balance changed in PreStaging
* SRC_Branches 101: City `Delhi` -> `Noida`
* SRC_Customers 2: DOB `1092` -> `1992`
These are intentional demonstrations; do **not** hide them by loosening
`direct_move_Validation`.

The other six are all in the **Transactions** table (PreStaging count /
duplicates / constraints / data_integrity, and DWH count / column_values) -
these appeared after the current DB data and are **not yet confirmed as
seeded vs. real**. Check the Detailed report to decide whether they are
expected defects or a genuine data issue to investigate.

### Package layout (renamed from a single `framework/` package)
The engine was split into three top-level packages; all imports and docs were
updated to match:
* `utilities/` (was `framework/`) - db, logger, config_loader, comparison, result_store
* `validations/validations.py` (was `framework/validations.py`)
* `reporting_engine/` (was `framework/reporting/`)
Each package has an `__init__.py`. Import as `from utilities import db`,
`from validations import validations as v`, `from reporting_engine import generate`.

---

## How to run
```bash
python main.py            # optional: check DB connections (read-only)
pytest                    # run all validations -> logs + reports
pytest -m transformation  # run a subset via markers
```
Reports land in `reports/`, logs in `logs/`.

---

## AI Agents layer (DONE - added 2026-07-17)

Built the `agents/` package on top of the framework (Claude generates/reasons,
framework executes/verifies). All agents have a **deterministic fallback** so
they work with no API key; Claude **enriches** when `ANTHROPIC_API_KEY` is in
`.env` (model `claude-opus-4-8`). Anthropic SDK 0.117.0 installed.

* `base.py` (Claude client + `ask_claude` / `ask_claude_json` tool-use + paths),
  `schema_introspect.py` (real `INFORMATION_SCHEMA` metadata, read-only, YAML
  fallback), `xlsx_util.py` (styled Excel writer).
* `agent_1_mapping_doc` -> `MappingDocument_<ts>.xlsx` (3 sheets, 15 cols,
  live DB types/sizes/constraints + per-column transformation rules).
* `agent_2_test_cases` -> `TestCases_<ts>.xlsx` (76 cases; each maps to an
  existing validation via a "Suggested Validation" column).
* `agent_3_generate_code` -> `agents/generated_tests/test_gen_*.py` (12 files;
  call the reusable validations; markers limited to those declared in
  pytest.ini so `--strict-markers` passes; NOT in `testpaths=tests`).
* `agent_4_test_data` -> `agents/output/testdata/*.sql` (25 rows incl. 8
  negative/edge; FK-safe; combined reset+insert+load script). WRITES .sql files
  ONLY - never connects to the DB / never executes (per user's explicit ask).
* `agent_5_execute` -> runs pytest w/ `--junitxml`, parses, writes
  `ExecutionSummary_<ts>.md` + `ExecutionResults_<ts>.json`. `--target
  existing|generated`, plus `--no-reset` to skip the prerequisite reset and
  validate CURRENT data as-is (needed to catch manually-seeded defects; the
  default `existing` run reloads golden data first and wipes them).
* `agent_6_defect_raiser` -> reads latest ExecutionResults json ->
  `Defects_<ts>.xlsx`/`.md`. Flags known seeded demo defects (does not hide).

NOTE: agents were renumbered 2026-07-17 so the file numbers match the user's
six-step spec: 4=test data (scripts only), 5=execute, 6=defects.
* `assistant.py` -> menu (default) + `--pipeline` + `--chat` (Claude tool-use).

Outputs go to `agents/output/` + `agents/generated_tests/` (both git-ignored).

## CI/CD - GitHub Actions (DONE - added 2026-07-17)

* Workflow: `.github/workflows/python-ci.yml` (name "Banking AI ETL Automation").
* Triggers: push to `main`, PR to `main`, and manual `workflow_dispatch`.
* Runner: **self-hosted, Windows, X64** (labels `[self-hosted, Windows, X64]`) -
  required because the prerequisite test rebuilds all 4 SQL Server DBs via
  `sqlcmd`, so the runner needs local SQL Server + `sqlcmd` access. A
  GitHub-hosted runner would not work.
* Steps: checkout -> setup Python 3.12 -> `pip install -r requirements.txt` ->
  "Verify Secrets" (prints FOUND/NOT FOUND for the 3 email secrets) -> `pytest`
  -> upload `Reports/` as artifact `TestReports` (`if: always()`).
* **GitHub Secrets** used as env vars: `EMAIL_SENDER`, `EMAIL_APP_PASSWORD`,
  `EMAIL_RECEIVER`. NOTE: `email_report.py` currently reads sender/recipients from
  `settings.yaml` and only the password from `EMAIL_APP_PASSWORD`; `EMAIL_SENDER`
  / `EMAIL_RECEIVER` are passed by CI but not yet consumed by the code. Revisit if
  CI should drive the addresses instead of `settings.yaml`.

## Golden test data (`GoldenTestData/`) + reset-as-first-test

* Known-good baseline of `Bank_Source` as SQL INSERT scripts (Branches 5,
  Customers 10, Accounts 10, Transactions 20). File prefixes = FK-safe order.
* `10_full_reset_and_reload_all_layers.sql` = the full pipeline reset: delete all
  4 layers (warehouse->source), re-insert Source golden data, run the load procs
  to rebuild PS/STG/DWH. `SET XACT_ABORT ON`. This is what
  `tests/test_00_prerequisite.py` runs via `sqlcmd` before every suite.
* `00_restore_all_source_data.sql` = Source only. `generate_golden_data.py`
  regenerates the .sql from live source (read-only). See `GoldenTestData/README.md`.

## Branding / assets (in the reports)

* `assets/company_logo.png` + `assets/author.png` are embedded (base64) into the
  Management HTML report header and the email; configured under
  `reporting.branding` in `settings.yaml` (company "Future Tech Skills", author
  "Yogesh Tyagi", "Sr. QA Architect").
* Report versioning: `reporting.version_cycle` / `reporting.keep_versions` (cur:
  cycle 2, keep 2) mirror the logger's scheme for the `_v#` suffix on reports.

## Config drift to remember (verify vs. docs)

* `logging.keep_versions` is currently **3** (not 5), `version_cycle` 10.
* `email.enabled: true` and sender is now `hrsoftwarejobsncr@gmail.com` ->
  recipient `ytyagi782@gmail.com` (settings.yaml).
* `.env.example` documents **two** keys: `EMAIL_APP_PASSWORD` and
  `ANTHROPIC_API_KEY`.

Verified 2026-07-17 without an API key: all 6 agents run; generated tests
collect+pass (76/76); curated suite passes 78/78 after a fresh prerequisite
reset (the earlier 9 "failures" were a prior DB state - a clean reload restores
clean golden data, so no seeded defects remain). NOTE: `email.enabled: true`, so
each pytest run (incl. via agent 4) sends the report email.

## Expectations / possible next steps
* Add more transformation rules per table in the layer-2 YAML as business rules
  are confirmed.
* Email is already ON (`email.enabled: true`; sender
  hrsoftwarejobsncr@gmail.com -> ytyagi782@gmail.com). The app password lives in
  `.env` locally and in the `EMAIL_APP_PASSWORD` GitHub Secret for CI.
* Consider a "rejection report" validation (checks every rejected staging row
  has a RejectionReason) if required.
* Keep this file updated whenever tables, rules, or logic change.
