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
├── main.py                       # read-only entry point (checks DB connections; no data load)
├── conftest.py                   # pytest hooks: reset store, build reports at the end
├── pytest.ini                    # markers, ordering, report options
├── requirements.txt              # dependencies
├── architecture.md               # this file
├── memory.md                     # running notes for AI / humans (what's done, what's expected)
├── .env.example                  # template for the Gmail App Password
│
├── config/                       # ALL configuration lives here (modular YAML)
│   ├── settings.yaml             # server, driver, db names, paths, logging, email, colours
│   ├── source_to_prestaging.yaml # Layer 1 tables: keys, columns, procs
│   ├── prestaging_to_staging.yaml# Layer 2 tables + transformation rules
│   └── staging_to_dwh.yaml       # Layer 3 tables: dim/fact, SCD filters
│
├── utilities/                    # reusable engine (import this from tests)
│   ├── config_loader.py          # loads + caches the YAML files
│   ├── db.py                     # SQL Server connection + pandas read helpers
│   ├── logger.py                 # run logger; keeps only 5 versions, name ends _v#
│   ├── result_store.py           # collects every validation outcome for the reports
│   └── comparison.py             # row-level diff engine (diffs / missing / duplicates)
│
├── validations/
│   └── validations.py            # the reusable checks (see below)
│
├── reporting_engine/
│   ├── excel_report.py           # Summary report + Detailed coloured report
│   ├── html_report.py            # Management HTML report
│   ├── email_report.py           # emails the report (off unless enabled)
│   └── generate.py               # builds all three reports + email in one call
│
├── tests/                        # one file per table, grouped by layer
│   ├── SourceToPreStaging/       # test_accounts / branches / customers / transactions
│   ├── PreStagingToStaging/      # same 4 tables
│   └── StagingToDWH/             # same 4 tables
│
├── logs/                         # etl_<datetime>_v#.log  (max 5 kept)
└── reports/                      # SummaryReport / DetailedReport / ManagementReport
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
   cards and tables, easy to share with management.

Email delivery (Gmail SMTP) is available but **off by default** - see below.

---

## Running

```bash
# 1. (optional) check that all databases are reachable (read-only)
python main.py

# 2. run all validations (reports + logs are produced automatically)
pytest

# run a subset using markers
pytest -m source_to_prestaging
pytest -m "basic and accounts"
pytest -m transformation
```

## Enabling email

1. Create a Gmail **App Password** (Google Account -> Security -> App passwords).
2. Copy `.env.example` to `.env` and set `EMAIL_APP_PASSWORD=...`.
3. Set `email.enabled: true` in `config/settings.yaml`.

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
