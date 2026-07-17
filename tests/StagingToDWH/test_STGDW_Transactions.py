"""Layer 3 : Staging -> DWH  |  Transactions -> FactTransaction.

The basic checks use the common validations.validations functions (shared by
every table).  The last two checks are FACT-SPECIFIC (foreign keys + value
columns), so their logic is written here in the test file rather than in
validations/validations.py, which is reserved for the common, reusable checks.
They still use the shared read/utility helpers (db, comparison, result_store,
logger) so their results show up in the log file and the reports.
"""

import pytest

from validations import validations as v
from utilities import db, comparison, result_store
from utilities.logger import get_logger

LAYER = "StagingToDWH"
TABLE = "Transactions"

log = get_logger()

# --- Fact-specific settings (only relevant to FactTransaction) --------------
SOURCE_DB = "staging"                  # Bank_Staging
TARGET_DB = "dwh"                      # Bank_DWH
STG_TABLE = "dbo.STG_Transactions"
FACT_TABLE = "dbo.FactTransaction"
KEY = "TransactionID"
VALID_FILTER = "IsValid = 1"           # only accepted staging rows reach the fact

# the non-key value columns whose data must match the staging source
VALUE_COLUMNS = ["TransactionNumber", "TransactionType", "Amount",
                 "CurrencyCode", "TransactionDate"]

# surrogate foreign keys -> the dimension table they must point to
# allow_null=False means a NULL surrogate key is treated as a failure
FOREIGN_KEYS = [
    {"column": "AccountSK",  "ref_table": "dbo.DimAccount_Type1",  "ref_column": "AccountSK",  "allow_null": False},
    {"column": "BranchSK",   "ref_table": "dbo.DimBranch_Type2",   "ref_column": "BranchSK",   "allow_null": False},
    {"column": "CustomerSK", "ref_table": "dbo.DimCustomer_Type2", "ref_column": "CustomerSK", "allow_null": False},
]


def _record(name, passed, message, category):
    """Log + store the outcome so it appears in the log and the reports."""
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {LAYER} | {TABLE} | {name} | {message}"
    (log.info if passed else log.error)(line)
    result_store.add_result(LAYER, TABLE, name, status, message, category=category)
    return passed


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.transactions
@pytest.mark.fact
@pytest.mark.basic
class TestTransactionsBasic:
    """Common reusable validations (from validations.validations)."""

    @pytest.mark.metadata_check
    def test_metadata(self):
        assert v.Metadata_Validation(LAYER, TABLE)

    @pytest.mark.count_check
    def test_count(self):
        assert v.Count_Validation(LAYER, TABLE)

    @pytest.mark.duplicate_check
    def test_duplicates(self):
        assert v.Duplicate_Validation(LAYER, TABLE)

    @pytest.mark.null_check
    def test_nulls(self):
        assert v.Null_Validation(LAYER, TABLE)

    @pytest.mark.constraint_check
    def test_constraints(self):
        assert v.Constraint_Validation(LAYER, TABLE)


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.transactions
@pytest.mark.fact
@pytest.mark.transformation
class TestTransactionsFact:
    """Fact-specific checks - logic defined here, not in validations.py."""

    def test_foreign_keys(self):
        """Every surrogate key in the fact must exist in its dimension."""
        problems = []
        for fk in FOREIGN_KEYS:
            col, ref_table, ref_col = fk["column"], fk["ref_table"], fk["ref_column"]

            # orphans: a non-null key value with no matching dimension row
            orphan_where = (f"[{col}] IS NOT NULL AND [{col}] NOT IN "
                            f"(SELECT [{ref_col}] FROM {ref_table})")
            orphans = db.get_row_count(TARGET_DB, FACT_TABLE, where=orphan_where)
            if orphans:
                problems.append(f"{col}: {orphans} orphan(s) not in {ref_table}")

            # nulls (only a problem when nulls are not allowed)
            if not fk["allow_null"]:
                nulls = db.get_row_count(TARGET_DB, FACT_TABLE, where=f"[{col}] IS NULL")
                if nulls:
                    problems.append(f"{col}: {nulls} null(s)")

        passed = not problems
        cols = ", ".join(fk["column"] for fk in FOREIGN_KEYS)
        msg = (f"all foreign keys valid ({cols})" if passed
               else "FK problems -> " + "; ".join(problems))
        assert _record("ForeignKey_Check", passed, msg, category="foreign_key")

    def test_column_values(self):
        """The non-key value columns in the fact must match the staging source."""
        cols = [KEY] + VALUE_COLUMNS
        src = db.read_table(SOURCE_DB, STG_TABLE, columns=cols, where=VALID_FILTER)
        tgt = db.read_table(TARGET_DB, FACT_TABLE, columns=cols)

        result = comparison.compare_dataframes(src, tgt, [KEY], VALUE_COLUMNS,
                                               case_insensitive=True)
        # feed the coloured detailed report
        result_store.add_comparison(LAYER, TABLE, [KEY], result)

        passed = result["is_match"]
        msg = (f"diffs={len(result['diffs'])}, "
               f"missing_in_target={len(result['missing_in_target'])}, "
               f"missing_in_source={len(result['missing_in_source'])}, "
               f"duplicates={len(result['duplicates'])}")
        assert _record("ColumnValues_Check", passed, msg, category="value_check")
