# Execution Flow — Banking ETL Automation Framework

This document explains, **step by step**, what happens when you run the
`pytest` command in this project. It is written so that **anyone** — even
someone new to the project — can follow the flow of execution from the very
first file that runs to the final reports that get produced.

Read this top to bottom. Each step says **which file runs**, **what it does**,
and **why**.

---

## 0. The 30-second summary

```
pytest  ->  reads pytest.ini  ->  loads conftest.py  ->  pytest_sessionstart()
        ->  collects test_*.py files under tests/
        ->  runs each test  ->  test calls validations.py
        ->  validations.py calls db.py (SELECT only) + comparison.py
        ->  every result stored in result_store.py + written to a log file
        ->  pytest_sessionfinish()  ->  generate.py builds 3 reports
        ->  reports/  +  logs/  are updated
```

Key idea: **this framework is READ-ONLY.** It never loads data and never runs
stored procedures. It only connects to SQL Server, runs `SELECT` queries, and
checks that the data moved correctly through the four ETL layers:

```
Bank_Source -> Bank_PreStaging -> Bank_Staging -> Bank_DWH
            (Layer 1)         (Layer 2)        (Layer 3)
```

---

## 1. You type `pytest` in the terminal

When you run `pytest` from the project root
(`C:\Users\...\Banking_AI_ETLAutomation_Project`), pytest does **not** run
`main.py`. `main.py` is only for the optional manual connection check
(`python main.py`). The test run is driven entirely by pytest.

The very first thing pytest looks for is a configuration file.

---

## 2. FIRST FILE READ → `pytest.ini`

**File:** `pytest.ini`

This is the first file pytest reads. It tells pytest **how** to behave for this
project. Important lines:

| Setting | Meaning |
|---|---|
| `testpaths = tests` | Only look inside the `tests/` folder for tests. |
| `python_files = test_*.py` | A file is a test file only if its name starts with `test_`. |
| `python_classes = Test*` | A class holds tests only if its name starts with `Test`. |
| `python_functions = test_*` | A method is a test only if it starts with `test_`. |
| `addopts = -v -ra --strict-markers --html=reports/pytest_html_report.html --self-contained-html` | Default command-line options: verbose output, summary of non-passing tests, reject unknown markers, and produce an extra standalone HTML report via the `pytest-html` plugin. |
| `filterwarnings` | Hides the harmless "pandas prefers SQLAlchemy" warning. |
| `markers = ...` | Declares every valid marker (layer names, table names, check types). Because `--strict-markers` is on, using an undeclared marker is an error. |

So before a single test runs, pytest already knows where to look, what counts as
a test, and which markers are legal.

---

## 3. SECOND FILE LOADED → `conftest.py`

**File:** `conftest.py`

`conftest.py` is special: pytest **auto-imports it** (you never import it
yourself). It "wires" our framework into pytest's lifecycle using hooks. As soon
as it is imported, these things happen at import time:

1. `sys.path.insert(0, ...)` — adds the project root to Python's import path so
   `from utilities import ...` and `from validations import ...` work.
2. `from utilities import result_store` — loads the in-memory results store.
3. `from utilities.logger import get_logger` — makes the logger available.

`conftest.py` then **registers four hooks** that pytest will call at the right
moments (they don't run yet, they are just defined):

- `pytest_addoption` — adds a custom `--only` command-line option.
- `pytest_collection_modifyitems` — implements `--only`.
- `pytest_runtest_makereport` — records skipped tests.
- `pytest_sessionstart` / `pytest_sessionfinish` — run once at the start / end.

---

## 4. SESSION START → `pytest_sessionstart()`

**File:** `conftest.py` → function `pytest_sessionstart()`

This runs **once**, before any test is collected or executed. It does two
things:

1. `get_logger()` → **first call to `utilities/logger.py`** (see step 5).
2. `result_store.reset()` → **clears `utilities/result_store.py`** so results
   from any previous run are wiped and this run starts clean.

It then logs: `"pytest session started - result store cleared."`

---

## 5. THE LOGGER IS CREATED → `utilities/logger.py`

**File:** `utilities/logger.py` → function `get_logger()`

This is the first "engine" file that actually does work. On the first call it:

1. Calls `config_loader.get_settings()` → **this triggers `config_loader.py`**
   (step 6) to read `config/settings.yaml`.
2. Works out the logs folder and creates it if needed.
3. Calls `_next_version()` — figures out the next version number by cycling
   `1..version_cycle` (default 10) based on the **most recently modified** log
   file (not the highest number — important once numbers wrap around).
4. Builds a filename like `etl_20260717_001258_v2.log`.
5. Creates a logger that writes to **both** the log file **and** the console.
6. Calls `_prune_old_logs()` — deletes the oldest logs so only the newest
   `keep_versions` (default 5) remain.
7. Writes the "NEW ETL TEST RUN STARTED" banner.
8. Caches itself (`_LOGGER`) so every later `get_logger()` returns the same
   logger — one log file per run.

**Result:** a new file appears in `logs/` and every step from here on is
logged.

---

## 6. CONFIG IS LOADED → `utilities/config_loader.py`

**File:** `utilities/config_loader.py`

This module reads the YAML configuration and **caches** it (each file is read
only once per run). It provides:

- `get_settings()` → reads `config/settings.yaml` (server, driver, database
  names, paths, logging, email, colours).
- `get_layer_config(layer)` → reads the layer's YAML:
  - `SourceToPreStaging`  → `config/source_to_prestaging.yaml`
  - `PreStagingToStaging` → `config/prestaging_to_staging.yaml`
  - `StagingToDWH`        → `config/staging_to_dwh.yaml`
- `get_table_config(layer, table)` → returns one table's block (keys, columns,
  rules) from inside a layer file.
- `resolve_database('source')` → turns a logical name into the real DB name
  (e.g. `Bank_Source`).

**Nothing about tables, keys, columns, or rules is hard-coded in Python** — it
all lives in these YAML files. Change a rule = edit YAML only.

---

## 7. TEST COLLECTION → pytest scans `tests/`

Now pytest scans the `tests/` folder (from `testpaths`) and collects every
`test_*.py` file. The folder is organised by ETL layer:

```
tests/
├── SourceToPreStaging/    (Layer 1)  test_SRCPS_Accounts.py, _Branches, _Customers, _Transactions
├── PreStagingToStaging/   (Layer 2)  test_PSSTG_Accounts.py, _Branches, _Customers, _Transactions
└── StagingToDWH/          (Layer 3)  test_STGDW_Accounts.py, _Branches, _Customers, _Transactions
```

**When each test file is imported**, its top-level code runs. For example, in
`tests/SourceToPreStaging/test_SRCPS_Accounts.py`:

```python
import pytest
from validations import validations as v   # <-- imports validations.py NOW

LAYER = "SourceToPreStaging"
TABLE = "Accounts"
```

Importing `validations.py` runs its top-level `log = get_logger()` — reusing the
already-created logger from step 5.

Each file defines `LAYER` and `TABLE` module constants (used later by the report
hook), and one or more test classes, e.g.:

- `TestAccountsBasic` — `test_metadata`, `test_count`, `test_duplicates`,
  `test_nulls`, `test_constraints`.
- `TestAccountsDirectMove` — `test_direct_move`.

Each class and method carries **markers** (`@pytest.mark.source_to_prestaging`,
`@pytest.mark.accounts`, `@pytest.mark.count_check`, etc.) that let you run
subsets later.

---

## 8. `--only` FILTER (if you used it) → `pytest_collection_modifyitems()`

**File:** `conftest.py` → function `pytest_collection_modifyitems()`

Right after collection, this hook runs. If you passed `--only=count_check,...`,
every test that does **not** carry one of the wanted markers is marked
**SKIP** (not deselected). This is deliberate: skipped tests still appear in the
reports as `SKIP` instead of silently disappearing.

If you did **not** pass `--only`, this hook does nothing and all tests run.

---

## 8b. PREREQUISITE TEST RUNS FIRST → `tests/test_00_prerequisite.py`

**File:** `tests/test_00_prerequisite.py` → `test_reset_and_reload_all_layers`

Although the framework is otherwise **read-only**, one special test runs
**before every other test**. It carries `@pytest.mark.order(0)` (the existing
tests use `order(1)`), so the `pytest-order` plugin always schedules it first.

What it does:

1. Shells out to **`sqlcmd`** to run
   `GoldenTestData/10_full_reset_and_reload_all_layers.sql`, which:
   - deletes all data from all 4 layers (children first),
   - re-inserts the golden data into the SOURCE tables, and
   - runs the load stored procedures to reload PreStaging, Staging and DWH.
2. Records a PASS/FAIL row in `result_store` (so it shows in the reports) and
   logs the `sqlcmd` output.
3. Sets `session.prerequisite_ok` to `True`/`False`.

**Gating:** `conftest.py`'s `pytest_runtest_setup()` checks that flag before
every other test. If the prerequisite **failed**, all remaining tests are
**skipped** — the data would not be in a known state, so validating it would be
meaningless. The prerequisite is also exempt from the `--only` filter, so it
always runs.

To run the validations **without** rebuilding the databases:
`pytest -m "not prerequisite"`.

---

## 9. RUNNING EACH TEST (the core loop)

pytest now runs each collected test method one at a time. Take
`TestAccountsBasic.test_count` as the example:

```python
@pytest.mark.count_check
def test_count(self):
    assert v.Count_Validation(LAYER, TABLE)   # LAYER="SourceToPreStaging", TABLE="Accounts"
```

The test does almost nothing itself — it just calls a reusable validation and
`assert`s the result. All the real work is in `validations/validations.py`.

### 9a. Inside `validations/validations.py`

**File:** `validations/validations.py`

Every validation function follows the same pattern:

1. **Build context** — `_context(layer, table)`:
   - Reads the layer + table config (via `config_loader`).
   - Works out source/target databases and tables, business keys, columns to
     compare, not-null columns, transformation rules, and the correct
     **WHERE filters** for that layer. For example:
     - Layer 2 (`PreStagingToStaging`): only accepted rows (`IsValid = 1`) are
       compared, but total counts must match on both sides.
     - Layer 3 (`StagingToDWH`): applies `IsValid = 1` on source and
       `IsCurrent = 1` (SCD) on the target where configured.

2. **Query the database** — calls helpers in `utilities/db.py` (step 9b).

3. **Decide pass/fail** — compares counts, looks for duplicates/nulls, or diffs
   whole DataFrames via `utilities/comparison.py` (step 9c).

4. **Record the outcome** — `_record(...)`:
   - Writes a `[PASS]` / `[FAIL]` line to the log.
   - Calls `result_store.add_result(...)` to store it for the reports.
   - Returns `True` (pass) or `False` (fail) so the test's `assert` passes or
     fails.

The reusable validations are:

| Function | What it checks |
|---|---|
| `Count_Validation` | source row count == target row count |
| `Duplicate_Validation` | target has no duplicate business keys |
| `Null_Validation` | required columns contain no NULLs |
| `direct_move_Validation` | Layer 1: target is an exact copy of source |
| `Metadata_Validation` | expected columns exist on both sides |
| `Constraint_Validation` | key columns unique + not null |
| `data_integrity_Validation` | Layers 2/3: matched rows still agree (case-insensitive) |
| `Transformation_Validation` | Layer 2: YAML data-quality rules (in_set, regex, min…) |

### 9b. Talking to the database → `utilities/db.py`

**File:** `utilities/db.py`

A thin, **read-only** wrapper around `pyodbc` for SQL Server (Windows Auth).
It builds the connection string from `settings.yaml` and provides:

- `get_row_count(db, table, where)` — `SELECT COUNT(*)`.
- `read_table(db, table, columns, where)` — reads rows into a pandas DataFrame.
- `read_query(db, sql)` — runs any `SELECT` and returns a DataFrame.
- `get_columns(db, table)` — reads column names from `INFORMATION_SCHEMA`.
- `test_connection(db)` — `SELECT 1` (used by `main.py`).

It has **no** way to INSERT/UPDATE/DELETE or run stored procedures — by design.

### 9c. Comparing data row-by-row → `utilities/comparison.py`

**File:** `utilities/comparison.py`

For validations that compare whole tables (`direct_move_Validation`,
`data_integrity_Validation`), the DataFrames are matched on the **business key**
and classified into:

- **diffs** — same key, different value → yellow in the report
- **missing_in_target** — key in source, not in target → red
- **missing_in_source** — key in target, not in source → red
- **duplicates** — key appears more than once → orange

Values are normalised first (trim spaces, `10` == `10.00`, dates as text) so
only *real* differences are flagged. The full detail is stored via
`result_store.add_comparison(...)` so the coloured detailed Excel report can be
built later.

### 9d. Storing results → `utilities/result_store.py`

**File:** `utilities/result_store.py`

An in-memory collector (reset in step 4). It keeps:

- `_results` — one row per validation (PASS / FAIL / SKIP) with layer, table,
  validation name, category, message, timestamp.
- `_comparisons` — the row-level detail behind each data comparison.

It also computes totals (`summary_counts()`, `summary_by_layer()`) used by the
reports.

### 9e. Recording SKIPs → `pytest_runtest_makereport()`

**File:** `conftest.py` → function `pytest_runtest_makereport()`

For every test, pytest calls this hook. If a test was **skipped** (e.g. because
of `--only`), the hook reads the module's `LAYER` and `TABLE` constants and the
skip reason, and records a `SKIP` row in `result_store`. This is why skipped
tests still show up in the reports instead of vanishing.

**Steps 9a–9e repeat for every test** across all four tables and all three
layers.

---

## 10. SESSION FINISH → `pytest_sessionfinish()`

**File:** `conftest.py` → function `pytest_sessionfinish()`

After the last test finishes, this hook runs **once**. It logs the exit status
and then calls the reporting engine:

```python
from reporting_engine import generate
paths = generate.generate_all()
```

(The import is done inside the function on purpose, so a reporting error can
never break the actual test run.) It then prints the report paths to the
console under a `=== Reports ===` heading.

---

## 11. BUILDING THE REPORTS → `reporting_engine/generate.py`

**File:** `reporting_engine/generate.py` → function `generate_all()`

This is the single entry point that builds everything from the data now sitting
in `result_store`. It:

1. Works out the `reports/` folder and a timestamp (`YYYYMMDD_HHMMSS`).
2. Builds three files:
   - `excel_report.build_summary_report(...)` →
     `reports/SummaryReport_<ts>.xlsx` — high-level pass/fail totals, by layer.
   - `excel_report.build_detailed_report(...)` →
     `reports/DetailedReport_<ts>.xlsx` — a "Failures" sheet plus one coloured
     sheet per table (yellow = diff, red = missing, orange = duplicate).
   - `html_report.build_html_report(...)` →
     `reports/ManagementReport_<ts>.html` — clean KPI-card HTML for management.
3. Logs the final tally (`total / passed / failed / pass_rate`).
4. Calls `email_report.send_report(...)` — **off by default**; only emails if
   `email.enabled: true` in `settings.yaml` and a Gmail App Password is set in
   `.env`.
5. Returns the dict of report paths back to `conftest.py`.

The reporting files involved:

- `reporting_engine/excel_report.py` — summary + detailed coloured Excel.
- `reporting_engine/html_report.py` — management HTML.
- `reporting_engine/email_report.py` — optional Gmail SMTP delivery.

Note: the `pytest-html` plugin also writes its own
`reports/pytest_html_report.html` (from the `--html` option in `pytest.ini`).
That is separate from our custom management report.

---

## 12. WHAT YOU END UP WITH

After `pytest` finishes:

- **Console** — verbose PASS/FAIL per test, a summary of non-passing tests, and
  the printed report paths.
- **`logs/`** — a new `etl_<datetime>_v#.log` with every step (only newest 5
  kept).
- **`reports/`** —
  - `SummaryReport_<ts>.xlsx`
  - `DetailedReport_<ts>.xlsx`
  - `ManagementReport_<ts>.html`
  - `pytest_html_report.html` (from the pytest-html plugin)

---

## 13. File-by-file order of execution (quick reference)

| Order | File | Role |
|---|---|---|
| 1 | `pytest.ini` | Config pytest reads first (paths, markers, options). |
| 2 | `conftest.py` | Auto-imported; registers hooks; sets import path. |
| 3 | `utilities/logger.py` | Creates the run's log file (via `pytest_sessionstart`). |
| 4 | `utilities/config_loader.py` | Loads + caches all YAML config. |
| 5 | `utilities/result_store.py` | Reset to start clean. |
| 5b | `tests/test_00_prerequisite.py` | Runs FIRST (`order(0)`): resets & reloads all 4 layers via `sqlcmd`. Gates the suite. |
| 6 | `tests/**/test_*.py` | Collected and run; each test calls a validation. |
| 7 | `validations/validations.py` | The reusable checks; the brains of the run. |
| 8 | `utilities/db.py` | Read-only SQL Server queries (SELECT). |
| 9 | `utilities/comparison.py` | Row-level diff engine for data comparisons. |
| 10 | `conftest.py` (`pytest_sessionfinish`) | Triggers report generation at the end. |
| 11 | `reporting_engine/generate.py` | Builds the 3 reports + optional email. |
| 12 | `reporting_engine/{excel,html,email}_report.py` | Produce each report / email. |

---

## 14. Common variations

```bash
# Run everything (default)
pytest

# Run only one layer
pytest -m source_to_prestaging

# Combine markers (basic checks on the accounts table only)
pytest -m "basic and accounts"

# Run only specific check types, SKIP (not hide) the rest — shows in reports
pytest --only=count_check,metadata_check

# Optional: just verify all four databases are reachable (does NOT run tests)
python main.py
```

In every case the **flow above is the same** — the only difference is which
tests actually execute versus get marked SKIP; the logging, result store, and
report generation always run at the end.
