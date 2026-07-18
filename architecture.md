# Banking ETL Automation Framework - Architecture

A modular, config-driven framework that **validates** a banking ETL pipeline
built on SQL Server. It checks that data moves correctly through four layers:

```
Bank_Source  ->  Bank_PreStaging  ->  Bank_Staging  ->  Bank_DWH
             (1)                  (2)                (3)
```

| # | Movement                | What happens                                             |
|---|-------------------------|----------------------------------------------------------|
| 1 | Source -> PreStaging    | Direct move (must be an exact copy)                      |
| 2 | PreStaging -> Staging   | Transformation, cleaning, duplicate rejection            |
| 3 | Staging -> DWH          | Load into Dimensions (Type1/Type2) and Fact tables       |

The load itself is done by **stored procedures** that already exist in each
database - that step runs in the database, **outside** this framework. This
framework is **read-only**: it only connects, reads with SELECT queries, and
runs **pytest** validations, producing logs and three reports. It never loads
data or executes stored procedures.

---

## Folder structure

```
Banking_AI_ETLAutomation_Project/
│
├── conftest.py                   # pytest hooks: reset store, build reports at the end
├── pytest.ini                    # markers, ordering, report options
├── requirements.txt              # dependencies
├── architecture.md               # this file
├── flow.md                       # step-by-step execution walk-through of a pytest run
├── memory.md                     # running notes for AI / humans (what's done, what's expected)
│
├── .github/
│   └── workflows/
│       └── python-ci.yml         # GitHub Actions CI (self-hosted Windows runner) - see below
│
├── config/                       # ALL configuration lives here (modular YAML)
│   ├── settings.yaml             # server, driver, db names, paths, logging, reporting, email, branding
│   ├── source_to_prestaging.yaml # Layer 1 tables: keys, columns, procs
│   ├── prestaging_to_staging.yaml# Layer 2 tables + transformation rules
│   └── staging_to_dwh.yaml       # Layer 3 tables: dim/fact, SCD filters
│
├── utilities/                    # reusable engine (import this from tests)
│   ├── config_loader.py          # loads + caches the YAML files
│   ├── db.py                     # SQL Server connection + pandas read helpers
│   ├── logger.py                 # run logger; version-cycled, keeps newest N, name ends _v#
│   ├── result_store.py           # collects every validation outcome for the reports
│   └── comparison.py             # row-level diff engine (diffs / missing / duplicates)
│
├── validations/
│   └── validations.py            # the reusable checks (see below)
│
├── reporting_engine/
│   ├── excel_report.py           # Summary report + Detailed coloured report
│   ├── html_report.py            # Management HTML report (branded header)
│   ├── email_report.py           # emails the report (Gmail SMTP; on when enabled + password set)
│   └── generate.py               # builds all three reports + email in one call
│
├── tests/                        # one file per table, grouped by layer
│   ├── test_00_prerequisite.py   # runs FIRST: resets + reloads all 4 layers, gates the suite
│   ├── SourceToPreStaging/       # 10 tables: accounts/branches/customers/transactions + 6 new
│   ├── PreStagingToStaging/      # same 10 tables
│   └── StagingToDWH/             # same 10 tables
│
├── database/                     # 6 NEW entities x 4 layers (DDL + load procs + seed)
│   ├── generate_schema.py        # generator (source of truth); emits everything below
│   ├── ddl/                      # CREATE TABLE for SRC_/PS_/STG_/Dim_/Fact_
│   ├── procs/                    # usp_Load_* (PS direct-move, STG validate, DWH Type1/Type2/Fact)
│   ├── data/                     # source seed data
│   ├── 09_run_all_new_entities.sql          # master run order (SSMS / SQLCMD mode)
│   └── README.md                 # what the 6 entities are + how to deploy
│
├── GoldenTestData/               # single self-contained reset script (the golden baseline)
│   └── 10_full_reset_and_reload_all_layers.sql # delete all 4 layers -> insert golden Source -> EXEC load procs
│
├── assets/                       # branding images embedded in the HTML / email report header
│   ├── company_logo.png
│   └── author.png
│
├── logs/                         # etl_<datetime>_v#.log  (git-ignored; newest N kept)
└── reports/                      # SummaryReport / DetailedReport / ManagementReport (git-ignored)
```

---

## Reusable validations (`validations/validations.py`)

Every test case simply calls one of these and asserts the result. Each one
logs a PASS/FAIL line and records the outcome for the reports.

| Function                     | Checks                                                            |
|------------------------------|-------------------------------------------------------------------|
| `Count_Validation`           | source row count == target row count                              |
| `Duplicate_Validation`       | target has no duplicate business keys                             |
| `Null_Validation`            | required columns contain no NULLs                                 |
| `direct_move_Validation`     | Layer 1: target is an exact copy of source (row + column level)   |
| `Metadata_Validation`        | expected columns exist on both source and target                  |
| `Constraint_Validation`      | key columns are unique and not null                               |
| `data_integrity_Validation`  | Layers 2/3: accepted/current rows still match source (case-insens.)|
| `Transformation_Validation`  | Layer 2: data-quality rules from YAML (in_set, regex, min, etc.)  |

---

## How data is compared (`comparison.py`)

Rows are matched on the **business key** (e.g. `AccountID`). It then reports:

* **diffs**              - same key, different column value  -> highlighted **yellow**
* **missing_in_target**  - key in source but not target      -> highlighted **red**
* **missing_in_source**  - key in target but not source      -> highlighted **red**
* **duplicates**         - key appears more than once         -> highlighted **orange**

Values are normalised before comparing (trim spaces, 10 vs 10.00, dates as
text) so only *real* differences are reported. For the transformed layers the
comparison is case-insensitive because standardising case is an intended step.

---

## Reports (built automatically after every `pytest` run)

1. **Summary report**  (`SummaryReport_<ts>.xlsx`) - high-level pass/fail, totals, by layer.
2. **Detailed report** (`DetailedReport_<ts>.xlsx`) - a "Failures" sheet plus **one
   sheet per table**. Each table sheet is laid out like a **normal Excel table** -
   the real table columns each get their own cell - with two extra columns added
   in front:

   ```
   Layer | FailureType | RowDestination | <col1> | <col2> | <col3> | ...
   ```

   | Extra column | Meaning |
   |--------------|---------|
   | Layer | which movement the failure was found in |
   | FailureType | `DF` (value differs), `Missing in Source`, `Missing in Target`, `Duplicate in Source`, `Duplicate in Target` |
   | RowDestination | `Source` or `Target` - which side this row came from |

   Cell colouring: for a **`DF`** only the differing column cell is **yellow** (and
   the record is shown as two rows, its Source version and its Target version);
   a **Missing** record is fully **red**; a **Duplicate** record is fully **orange**.
   All layers for a table share the one sheet (told apart by the `Layer` column).
3. **Management report** (`ManagementReport_<ts>.html`) - clean HTML page with KPI
   cards and tables, easy to share with management. The header is **branded** from
   `reporting.branding` in `settings.yaml` (company name + logo on the left, author
   name/role + photo on the right); the images in `assets/` are embedded as base64
   so the file stays self-contained.

All three reports are **version-cycled** the same way as the logs: `reporting.version_cycle`
sets how far the `_v#` suffix counts before wrapping, and `reporting.keep_versions`
keeps only the newest N of each report type (default: cycle 2, keep 2).

Email delivery (Gmail SMTP) sends the HTML report with the Excel reports attached.
It runs when `email.enabled: true` **and** an app password is available - see below.

---

## Running

```bash
# 1. (optional) check that all databases are reachable (read-only)
python -c "from utilities import db; db.check_connections()"

# 2. run all validations (reports + logs are produced automatically)
pytest

# run a subset using markers
pytest -m source_to_prestaging
pytest -m "basic and accounts"
pytest -m transformation
```

## Enabling email

1. Create a Gmail **App Password** (Google Account -> Security -> App passwords).
2. Create a `.env` file and set `EMAIL_APP_PASSWORD=...`.
3. Set `email.enabled: true` in `config/settings.yaml`.

The `sender` and `recipients` are read from `settings.yaml`; only the app password
comes from `.env` (key `EMAIL_APP_PASSWORD`) or an environment variable of the same
name. Email is currently **enabled** in `settings.yaml`.

## Golden test data (`GoldenTestData/`)

A known-good baseline of `Bank_Source`, stored as a single self-contained SQL
script, so any run can start from an identical, repeatable state.

* `10_full_reset_and_reload_all_layers.sql` - the **only** file in the folder. In
  one run it: (1) deletes **all four layers** (warehouse first, source last),
  (2) re-inserts the golden Source rows for all 10 entities, then (3) runs the
  load stored procedures to rebuild PreStaging, Staging and DWH. `SET XACT_ABORT ON`
  stops on the first error. This is the exact script `tests/test_00_prerequisite.py`
  shells out to (via `sqlcmd`) before every validation run.

## Continuous integration (`.github/workflows/python-ci.yml`)

CI runs the whole suite in GitHub Actions:

* **Triggers:** push to `main`, pull request to `main`, and manual
  `workflow_dispatch`.
* **Runner:** a **self-hosted Windows x64** runner - it needs local access to the
  SQL Server instance and `sqlcmd`, since the prerequisite test rebuilds the four
  databases.
* **Steps:** checkout -> set up Python 3.12 -> `pip install -r requirements.txt`
  -> verify secrets are present -> `pytest` -> upload the `Reports/` folder as a
  `TestReports` build artifact (`if: always()`, so reports are kept even on failure).
* **GitHub Secrets** (injected as env vars for the run): `EMAIL_SENDER`,
  `EMAIL_APP_PASSWORD`, `EMAIL_RECEIVER`. `EMAIL_APP_PASSWORD` is what
  `email_report.py` reads to send the report email from CI.

## Configuration first

Nothing about tables, keys, columns or rules is hard-coded in Python - it all
lives in the `config/*.yaml` files. To validate a new table or change a rule,
edit YAML only.

---

## AI Agents (`agents/`)

A layer of AI agents sits **on top of** this framework and automates the whole
ETL-testing lifecycle. Guiding rule: **Claude generates & reasons; the framework
executes & verifies.** Each agent works with no API key (deterministic output
from config + DB) and is *enriched* by Claude when `ANTHROPIC_API_KEY` is set.

```
agents/
├── base.py               # .env + Claude client (ask_claude / ask_claude_json) + paths
├── schema_introspect.py  # real column metadata/constraints from INFORMATION_SCHEMA (read-only)
├── xlsx_util.py          # shared styled-Excel writer
├── agent_1_mapping_doc.py    # 1. Source→Target mapping document (3 sheets)
├── agent_2_test_cases.py     # 2. test cases (all 3 layers) -> Excel
├── agent_3_generate_code.py  # 3. pytest code -> agents/generated_tests/
├── agent_4_test_data.py      # 4. synthetic source data (pos+neg) -> INSERT .sql (scripts only)
├── agent_5_execute.py        # 5. run pytest, parse JUnit, AI summary
├── agent_6_defect_raiser.py  # 6. failures -> defect tickets (Excel + md)
├── assistant.py              # end-to-end assistant (menu + --chat tool-use)
├── output/               # all artifacts (git-ignored)
└── generated_tests/      # generated pytest files (git-ignored; NOT in testpaths)
```

Run `python -m agents.assistant` for the menu, or a single agent with
`python -m agents.agent_1_mapping_doc` etc. See `agents/README.md` for details.
The agents stay **read-only** against the DB (only SELECT / INFORMATION_SCHEMA);
generated INSERT scripts are written to disk and run by you, not executed
automatically.
