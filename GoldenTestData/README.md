# GoldenTestData

A **golden snapshot** of the `Bank_Source` tables as SQL `INSERT` scripts.

"Golden" means a known-good baseline. Run these scripts to reset the source
tables back to exactly the data that existed when the snapshot was taken. This
is useful for repeatable testing: you can load Source, run the ETL, run
`pytest`, and later restore Source to the same starting point.

## What's in this folder

| File | Purpose |
|---|---|
| `generate_golden_data.py` | Re-reads current source data and regenerates all `.sql` files below. **Read-only** against the DB (SELECT only). |
| `01_SRC_Branches.sql` | INSERTs for `dbo.SRC_Branches` (5 rows). |
| `02_SRC_Customers.sql` | INSERTs for `dbo.SRC_Customers` (10 rows). |
| `03_SRC_Accounts.sql` | INSERTs for `dbo.SRC_Accounts` (10 rows). |
| `04_SRC_Transactions.sql` | INSERTs for `dbo.SRC_Transactions` (20 rows). |
| `00_restore_all_source_data.sql` | One self-contained file: **deletes** all four SOURCE tables (child→parent) then **re-inserts** every row (parent→child). Source only. |
| `10_full_reset_and_reload_all_layers.sql` | **The full pipeline reset.** Deletes **all 4 layers**, re-inserts the SOURCE golden data, then runs the load stored procedures so PreStaging, Staging and DWH are rebuilt from Source. |

The number prefixes are the **foreign-key-safe order**: Branches and Customers
first, then Accounts (needs Customers), then Transactions (needs Accounts +
Branches).

## How to use

### Option A — full pipeline reset (delete all layers, reload from Source)
This is the "start completely fresh" option. Open
`10_full_reset_and_reload_all_layers.sql` in **SSMS** and run the whole file,
or from a terminal:

```bash
sqlcmd -S "DESKTOP-HL2FC2P\SQLYKT" -E -i "GoldenTestData/10_full_reset_and_reload_all_layers.sql"
```

It runs three steps in order:

1. **STEP 1 – delete** every row from all four layers (children before parents,
   warehouse first, source last):
   - `Bank_DWH`: `FactTransaction` → `DimAccount_Type1` → `DimBranch_Type2` → `DimCustomer_Type2`
   - `Bank_Staging`: `STG_Transactions` → `STG_Accounts` → `STG_Customers` → `STG_Branches`
   - `Bank_PreStaging`: `PS_Transactions` → `PS_Accounts` → `PS_Customers` → `PS_Branches`
   - `Bank_Source`: `SRC_Transactions` → `SRC_Accounts` → `SRC_Customers` → `SRC_Branches`
2. **STEP 2 – insert** the golden data back into the four `Bank_Source` tables
   (parents first: Branches → Customers → Accounts → Transactions).
3. **STEP 3 – load** the other layers by running the stored procedures, layer by
   layer:
   - Layer 1 → `usp_Load_PS_*`   (Source → PreStaging)
   - Layer 2 → `usp_Load_STG_*`  (PreStaging → Staging)
   - Layer 3 → `usp_Load_DimBranch_Type2`, `usp_Load_DimCustomer_Type2`,
     `usp_Load_DimAccount_Type1`, `usp_Load_FactTransaction`  (Staging → DWH;
     dimensions before the fact table)

`SET XACT_ABORT ON` is set at the top, so the script stops on the first error
instead of leaving a half-loaded pipeline.

> Note: do **not** pass `-d Bank_Source` here — the script switches databases
> itself with `USE`, and it touches all four databases.

### Option A2 — automatic, as the first pytest test case
This same full reset+reload also runs **automatically as the first test** every
time you run `pytest`. The test `tests/test_00_prerequisite.py`
(`test_reset_and_reload_all_layers`) shells out to `sqlcmd` to run this exact
file before any validation test. So a plain:

```bash
pytest
```

first rebuilds all 4 layers from the golden data, then validates them. If the
reset fails, every other test is skipped (the data would not be trustworthy).
To run the validations **without** rebuilding, deselect it:

```bash
pytest -m "not prerequisite"
```

### Option B — restore the SOURCE tables only
If you just want to reset Source (and not touch the other layers), run
`00_restore_all_source_data.sql`:

```bash
sqlcmd -S "DESKTOP-HL2FC2P\SQLYKT" -d Bank_Source -E -i "GoldenTestData/00_restore_all_source_data.sql"
```

This clears the four source tables and re-inserts the golden rows.

### Option C — insert into empty SOURCE tables, one file at a time
If the source tables are already empty (no `DELETE` needed), run the numbered
files **in order** 01 → 02 → 03 → 04 so foreign keys are satisfied.

## Regenerating the snapshot

If the source data changes and you want a fresh golden copy:

```bash
python GoldenTestData/generate_golden_data.py
```

This overwrites all the `.sql` files with the current contents of the source
tables.

## Notes

- These scripts insert the **key values as-is** (AccountID, BranchID, etc.).
  The source tables have no IDENTITY columns, so no `SET IDENTITY_INSERT` is
  required. If that ever changes, the generator will need updating.
- The DB connection details come from `config/settings.yaml`
  (server `DESKTOP-HL2FC2P\SQLYKT`, Windows Auth). The generator reads the
  physical database names from there too.
- The `00_`/`01`–`04` files only insert into **Source**. The
  `10_full_reset_and_reload_all_layers.sql` file additionally deletes the other
  three layers and reloads them by calling the existing load stored procedures —
  it never inserts warehouse rows directly, the procs still do the ETL work.
