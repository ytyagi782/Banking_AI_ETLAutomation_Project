"""
generate_schema.py
------------------
Code-generator for the SIX new banking entities that extend the ETL testing
framework.  It is the single source of truth for their schema, so DDL, load
stored procedures, seed data, pytest files and YAML config always stay in sync.

It is a *developer* tool (like GoldenTestData/generate_golden_data.py).  It only
WRITES local files - it never touches the databases.  The framework itself stays
strictly READ-ONLY.

Run:
    .venv/Scripts/python.exe database/generate_schema.py

It emits (all paths relative to the project root):
    database/ddl/01_source_tables.sql
    database/ddl/02_prestaging_tables.sql
    database/ddl/03_staging_tables.sql
    database/ddl/04_dwh_tables.sql
    database/procs/05_load_prestaging.sql
    database/procs/06_load_staging.sql
    database/procs/07_load_dwh.sql
    database/data/08_source_seed_data.sql
    database/09_run_all_new_entities.sql
    database/_config_additions/*.yaml         (snippets to merge into config/)
    database/_config_additions/pytest_markers.txt
    tests/SourceToPreStaging/test_SRCPS_<Entity>.py   (x6)
    tests/PreStagingToStaging/test_PSSTG_<Entity>.py  (x6)
    tests/StagingToDWH/test_STGDW_<Entity>.py         (x6)

The six new entities and their DWH modelling:
    Employees        -> DimEmployee_Type2     (SCD-2)
    Loans            -> DimLoan_Type2          (SCD-2)
    Cards            -> DimCard_Type1          (SCD-1)
    Merchants        -> DimMerchant_Type1      (SCD-1)
    CardTransactions -> FactCardTransaction    (Fact, refs DimCard + DimMerchant)
    LoanPayments     -> FactLoanPayment        (Fact, refs DimLoan)
"""

import os

# --------------------------------------------------------------------------
# database names (must match config/settings.yaml -> databases)
# --------------------------------------------------------------------------
DB_SOURCE = "Bank_Source"
DB_PRESTAGING = "Bank_PreStaging"
DB_STAGING = "Bank_Staging"
DB_DWH = "Bank_DWH"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ==========================================================================
# ENTITY DEFINITIONS
# ==========================================================================
# Column tuples are (name, sql_type, nullable).
# `nkey`  = the natural / business key (INT, PRIMARY KEY in SRC/PS/STG).
# `cols`  = business columns that live in EVERY layer (incl. the DWH dim/fact).
# For FACTS, `fk_cols` are natural foreign keys that exist in SRC/PS/STG but are
# REPLACED by surrogate keys (from `refs`) in the fact table.
#
# `transforms` drive both the STG load proc (standardise + validate) and the
# framework's Transformation_Validation (validations/validations.py).
#   rules: no_whitespace | in_set | min_value | length_equals | regex
# ==========================================================================

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

DIMENSIONS = [
    {
        "singular": "Employee", "plural": "Employees",
        "nkey": "EmployeeID", "dwh": "Type2",
        "cols": [
            ("EmployeeCode", "NVARCHAR(20)", False),
            ("FirstName", "NVARCHAR(50)", True),
            ("LastName", "NVARCHAR(50)", True),
            ("Email", "NVARCHAR(100)", True),
            ("Phone", "NVARCHAR(20)", True),
            ("Designation", "NVARCHAR(50)", True),
            ("BranchID", "INT", True),
            ("Salary", "DECIMAL(18,2)", True),
            ("HireDate", "DATE", True),
            ("Status", "NVARCHAR(20)", True),
        ],
        "not_null": ["EmployeeID", "EmployeeCode"],
        "transforms": [
            {"column": "FirstName", "rule": "no_whitespace",
             "description": "First name must be trimmed"},
            {"column": "LastName", "rule": "no_whitespace",
             "description": "Last name must be trimmed"},
            {"column": "Email", "rule": "regex", "value": EMAIL_REGEX,
             "description": "Email must be a valid email format"},
            {"column": "Status", "rule": "in_set",
             "value": ["ACTIVE", "INACTIVE", "ONLEAVE", "RESIGNED"],
             "description": "Status standardised to an upper-case known value"},
        ],
    },
    {
        "singular": "Loan", "plural": "Loans",
        "nkey": "LoanID", "dwh": "Type2",
        "cols": [
            ("LoanNumber", "NVARCHAR(20)", False),
            ("CustomerID", "INT", True),
            ("ProductType", "NVARCHAR(30)", True),
            ("PrincipalAmount", "DECIMAL(18,2)", True),
            ("InterestRate", "DECIMAL(9,4)", True),
            ("TermMonths", "INT", True),
            ("DisbursementDate", "DATE", True),
            ("OutstandingAmount", "DECIMAL(18,2)", True),
            ("Status", "NVARCHAR(20)", True),
        ],
        "not_null": ["LoanID", "LoanNumber", "CustomerID"],
        "transforms": [
            {"column": "LoanNumber", "rule": "no_whitespace",
             "description": "Loan number must be trimmed"},
            {"column": "ProductType", "rule": "in_set",
             "value": ["HOME", "AUTO", "PERSONAL", "EDUCATION", "BUSINESS"],
             "description": "Product type standardised to upper-case"},
            {"column": "PrincipalAmount", "rule": "min_value", "value": 0,
             "description": "Principal amount must not be negative"},
            {"column": "Status", "rule": "in_set",
             "value": ["ACTIVE", "CLOSED", "DEFAULTED", "PENDING"],
             "description": "Status standardised to an upper-case known value"},
        ],
    },
    {
        "singular": "Card", "plural": "Cards",
        "nkey": "CardID", "dwh": "Type1",
        "cols": [
            ("CardNumber", "NVARCHAR(25)", False),
            ("AccountID", "INT", True),
            ("CardType", "NVARCHAR(20)", True),
            ("Network", "NVARCHAR(20)", True),
            ("CreditLimit", "DECIMAL(18,2)", True),
            ("IssueDate", "DATE", True),
            ("ExpiryDate", "DATE", True),
            ("Status", "NVARCHAR(20)", True),
        ],
        "not_null": ["CardID", "CardNumber", "AccountID"],
        "transforms": [
            {"column": "CardType", "rule": "in_set",
             "value": ["DEBIT", "CREDIT", "PREPAID"],
             "description": "Card type standardised to upper-case"},
            {"column": "Network", "rule": "in_set",
             "value": ["VISA", "MASTERCARD", "RUPAY", "AMEX"],
             "description": "Card network standardised to upper-case"},
            {"column": "Status", "rule": "in_set",
             "value": ["ACTIVE", "BLOCKED", "EXPIRED"],
             "description": "Status standardised to an upper-case known value"},
        ],
    },
    {
        "singular": "Merchant", "plural": "Merchants",
        "nkey": "MerchantID", "dwh": "Type1",
        "cols": [
            ("MerchantCode", "NVARCHAR(20)", False),
            ("MerchantName", "NVARCHAR(100)", True),
            ("Category", "NVARCHAR(50)", True),
            ("City", "NVARCHAR(50)", True),
            ("Country", "NVARCHAR(50)", True),
            ("Status", "NVARCHAR(20)", True),
        ],
        "not_null": ["MerchantID", "MerchantCode"],
        "transforms": [
            {"column": "MerchantName", "rule": "no_whitespace",
             "description": "Merchant name must be trimmed"},
            {"column": "Status", "rule": "in_set",
             "value": ["ACTIVE", "INACTIVE", "SUSPENDED"],
             "description": "Status standardised to an upper-case known value"},
        ],
    },
]

FACTS = [
    {
        "singular": "CardTransaction", "plural": "CardTransactions",
        "nkey": "CardTransactionID", "dwh": "Fact",
        # measure/attribute columns that exist in SRC/PS/STG AND the fact table
        "cols": [
            ("CardTxnNumber", "NVARCHAR(25)", False),
            ("TxnDate", "DATETIME", True),
            ("Amount", "DECIMAL(18,2)", True),
            ("CurrencyCode", "NVARCHAR(3)", True),
            ("TxnType", "NVARCHAR(20)", True),
            ("Status", "NVARCHAR(20)", True),
        ],
        # natural FKs present in SRC/PS/STG, replaced by surrogate keys in fact
        "fk_cols": [
            ("CardID", "INT", True),
            ("MerchantID", "INT", True),
        ],
        # (fk_col, dim_natural_key, surrogate_col, dim_table, current_only)
        "refs": [
            ("CardID", "CardID", "CardSK", "DimCard_Type1", False),
            ("MerchantID", "MerchantID", "MerchantSK", "DimMerchant_Type1", False),
        ],
        "not_null": ["CardTransactionID", "CardTxnNumber"],
        "transforms": [
            {"column": "Amount", "rule": "min_value", "value": 0,
             "description": "Transaction amount must not be negative"},
            {"column": "CurrencyCode", "rule": "length_equals", "value": 3,
             "description": "Currency code must be a 3 letter ISO code"},
            {"column": "TxnType", "rule": "in_set",
             "value": ["PURCHASE", "WITHDRAWAL", "REFUND", "REVERSAL"],
             "description": "Transaction type standardised to upper-case"},
            {"column": "Status", "rule": "in_set",
             "value": ["APPROVED", "DECLINED", "PENDING"],
             "description": "Status standardised to an upper-case known value"},
        ],
    },
    {
        "singular": "LoanPayment", "plural": "LoanPayments",
        "nkey": "LoanPaymentID", "dwh": "Fact",
        "cols": [
            ("PaymentNumber", "NVARCHAR(25)", False),
            ("PaymentDate", "DATE", True),
            ("PaymentAmount", "DECIMAL(18,2)", True),
            ("PrincipalComponent", "DECIMAL(18,2)", True),
            ("InterestComponent", "DECIMAL(18,2)", True),
            ("PaymentMethod", "NVARCHAR(20)", True),
        ],
        "fk_cols": [
            ("LoanID", "INT", True),
        ],
        "refs": [
            ("LoanID", "LoanID", "LoanSK", "DimLoan_Type2", True),
        ],
        "not_null": ["LoanPaymentID", "PaymentNumber"],
        "transforms": [
            {"column": "PaymentAmount", "rule": "min_value", "value": 0,
             "description": "Payment amount must not be negative"},
            {"column": "PaymentMethod", "rule": "in_set",
             "value": ["CASH", "CHEQUE", "ONLINE", "AUTODEBIT"],
             "description": "Payment method standardised to upper-case"},
        ],
    },
]

ALL = DIMENSIONS + FACTS


# ==========================================================================
# small helpers
# ==========================================================================
def is_fact(e):
    return e["dwh"] == "Fact"


def src_cols(e):
    """Business columns (name,type,nullable) that live in SRC/PS/STG (no audit)."""
    cols = list(e["cols"])
    if is_fact(e):
        cols = e["fk_cols"] + cols
    return cols


def all_layer_cols(e):
    """natural key + business columns for SRC/PS (used for compare / INSERT)."""
    return [e["nkey"]] + [c[0] for c in src_cols(e)]


def dwh_compare_cols(e):
    """columns that exist on BOTH the staging table and the dim/fact table."""
    # facts drop the natural FKs (they become surrogate keys), dims keep all
    return [e["nkey"]] + [c[0] for c in e["cols"]]


def business_cols_no_key(e):
    """business columns excluding the natural key (for SCD change-detection)."""
    return [c[0] for c in e["cols"]]


def col_ddl(name, sqltype, nullable):
    return f"    [{name}] {sqltype} {'NULL' if nullable else 'NOT NULL'}"


def transform_expr(e, col):
    """SELECT expression that standardises a column during the STG load."""
    for t in e["transforms"]:
        if t["column"] == col and t["rule"] == "in_set":
            return f"UPPER(LTRIM(RTRIM([{col}])))"
    for t in e["transforms"]:
        if t["column"] == col and t["rule"] == "no_whitespace":
            return f"LTRIM(RTRIM([{col}]))"
    return f"[{col}]"


def rule_fail_condition(t):
    """SQL boolean that is TRUE when a row BREAKS this transformation rule."""
    col, rule = t["column"], t["rule"]
    if rule == "in_set":
        allowed = ", ".join("'%s'" % v for v in t["value"])
        return f"([{col}] IS NOT NULL AND UPPER(LTRIM(RTRIM([{col}]))) NOT IN ({allowed}))"
    if rule == "no_whitespace":
        return f"([{col}] IS NOT NULL AND [{col}] <> LTRIM(RTRIM([{col}])))"
    if rule == "min_value":
        return f"([{col}] IS NOT NULL AND [{col}] < {t['value']})"
    if rule == "length_equals":
        return f"([{col}] IS NOT NULL AND LEN(LTRIM(RTRIM([{col}]))) <> {t['value']})"
    if rule == "regex":  # basic email-shape check (T-SQL has no real regex)
        return f"([{col}] IS NOT NULL AND [{col}] NOT LIKE '%_@_%_._%')"
    raise ValueError(rule)


def rule_reason(t):
    return f"{t['column']} failed {t['rule']}"


# ==========================================================================
# DDL builders
# ==========================================================================
AUDIT = [("CreatedDate", "DATETIME", False), ("UpdatedDate", "DATETIME", True)]


def ddl_layer_table(e, table, extra_cols=None, pk_col=None):
    """Generic SRC/PS/STG table (natural key + business cols + audit)."""
    lines = [f"CREATE TABLE dbo.{table} ("]
    body = [col_ddl(e["nkey"], "INT", False)]
    for name, t, n in src_cols(e):
        body.append(col_ddl(name, t, n))
    for name, t, n in (extra_cols or []):
        body.append(col_ddl(name, t, n))
    for name, t, n in AUDIT:
        body.append(col_ddl(name, t, n))
    if pk_col:
        body.append(f"    CONSTRAINT [PK_{table}] PRIMARY KEY ([{pk_col}])")
    lines.append(",\n".join(body))
    lines.append(");")
    return "\n".join(lines)


def ddl_source(e):
    return ddl_layer_table(e, f"SRC_{e['plural']}", pk_col=e["nkey"])


def ddl_prestaging(e):
    return ddl_layer_table(e, f"PS_{e['plural']}", pk_col=e["nkey"])


def ddl_staging(e):
    extra = [("IsValid", "BIT", False), ("RejectionReason", "NVARCHAR(500)", True)]
    return ddl_layer_table(e, f"STG_{e['plural']}", extra_cols=extra, pk_col=e["nkey"])


def ddl_dwh(e):
    if e["dwh"] == "Type1":
        table = f"Dim{e['singular']}_Type1"
        sk = f"{e['singular']}SK"
        body = [col_ddl(sk, "INT IDENTITY(1,1)", False),
                col_ddl(e["nkey"], "INT", False)]
        for name, t, n in e["cols"]:
            body.append(col_ddl(name, t, n))
        for name, t, n in AUDIT:
            body.append(col_ddl(name, t, n))
        body.append(f"    CONSTRAINT [PK_{table}] PRIMARY KEY ([{sk}])")
        return f"CREATE TABLE dbo.{table} (\n" + ",\n".join(body) + "\n);"

    if e["dwh"] == "Type2":
        table = f"Dim{e['singular']}_Type2"
        sk = f"{e['singular']}SK"
        body = [col_ddl(sk, "INT IDENTITY(1,1)", False),
                col_ddl(e["nkey"], "INT", False)]
        for name, t, n in e["cols"]:
            body.append(col_ddl(name, t, n))
        body += [col_ddl("EffectiveDate", "DATE", False),
                 col_ddl("ExpiryDate", "DATE", True),
                 col_ddl("IsCurrent", "BIT", False),
                 col_ddl("CreatedDate", "DATETIME", False)]
        body.append(f"    CONSTRAINT [PK_{table}] PRIMARY KEY ([{sk}])")
        return f"CREATE TABLE dbo.{table} (\n" + ",\n".join(body) + "\n);"

    # Fact
    table = f"Fact{e['singular']}"
    sk = f"{e['singular']}SK"
    body = [col_ddl(sk, "INT IDENTITY(1,1)", False),
            col_ddl(e["nkey"], "INT", False)]
    for name, t, n in e["cols"]:
        body.append(col_ddl(name, t, n))
    for _fk, _nk, sk_col, _dim, _cur in e["refs"]:
        body.append(col_ddl(sk_col, "INT", True))
    body.append(col_ddl("CreatedDate", "DATETIME", False))
    body.append(f"    CONSTRAINT [PK_{table}] PRIMARY KEY ([{sk}])")
    return f"CREATE TABLE dbo.{table} (\n" + ",\n".join(body) + "\n);"


# ==========================================================================
# stored-procedure builders
# ==========================================================================
def proc_load_ps(e):
    cols = all_layer_cols(e) + ["CreatedDate", "UpdatedDate"]
    collist = ", ".join(f"[{c}]" for c in cols)
    return f"""CREATE OR ALTER PROCEDURE dbo.usp_Load_PS_{e['plural']}
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 1: direct move Source -> PreStaging (no transformation)
    DELETE FROM dbo.PS_{e['plural']};
    INSERT INTO dbo.PS_{e['plural']} ({collist})
    SELECT {collist}
    FROM {DB_SOURCE}.dbo.SRC_{e['plural']};
END;"""


def proc_load_stg(e):
    business = all_layer_cols(e)
    select_exprs = []
    for c in business:
        if c == e["nkey"]:
            select_exprs.append(f"[{c}]")
        else:
            select_exprs.append(f"{transform_expr(e, c)} AS [{c}]")

    # validation: build the IsValid + RejectionReason expressions
    fail_conditions = []
    reason_whens = []
    for col in e["not_null"]:
        fail_conditions.append(f"[{col}] IS NULL")
        reason_whens.append(f"        WHEN [{col}] IS NULL THEN '{col} is NULL'")
    for t in e["transforms"]:
        # no_whitespace is a CLEANING rule (we trim it above), not a rejection
        if t["rule"] == "no_whitespace":
            continue
        cond = rule_fail_condition(t)
        fail_conditions.append(cond)
        reason_whens.append(f"        WHEN {cond} THEN '{rule_reason(t)}'")

    is_valid = "CASE WHEN " + "\n              OR ".join(fail_conditions) + \
               "\n         THEN 0 ELSE 1 END AS [IsValid]"
    reason = "CASE\n" + "\n".join(reason_whens) + \
             "\n        ELSE NULL END AS [RejectionReason]"

    insert_cols = business + ["IsValid", "RejectionReason", "CreatedDate", "UpdatedDate"]
    collist = ", ".join(f"[{c}]" for c in insert_cols)
    select_block = ",\n           ".join(
        select_exprs + [is_valid, reason, "[CreatedDate]", "GETDATE() AS [UpdatedDate]"])

    return f"""CREATE OR ALTER PROCEDURE dbo.usp_Load_STG_{e['plural']}
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 2: PreStaging -> Staging (standardise + validate; keep rejects flagged)
    DELETE FROM dbo.STG_{e['plural']};
    INSERT INTO dbo.STG_{e['plural']} ({collist})
    SELECT {select_block}
    FROM {DB_PRESTAGING}.dbo.PS_{e['plural']};
END;"""


def proc_load_dwh_type1(e):
    table = f"Dim{e['singular']}_Type1"
    nk = e["nkey"]
    bcols = business_cols_no_key(e)
    set_list = ",\n            ".join(f"tgt.[{c}] = src.[{c}]" for c in bcols)
    ins_cols = ", ".join(f"[{c}]" for c in [nk] + bcols) + ", [CreatedDate]"
    ins_vals = ", ".join(f"src.[{c}]" for c in [nk] + bcols) + ", GETDATE()"
    sel_cols = ", ".join(f"[{c}]" for c in [nk] + bcols)
    return f"""CREATE OR ALTER PROCEDURE dbo.usp_Load_{table}
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (SCD Type-1: overwrite, one row per key)
    MERGE dbo.{table} AS tgt
    USING (SELECT {sel_cols}
           FROM {DB_STAGING}.dbo.STG_{e['plural']}
           WHERE IsValid = 1) AS src
       ON tgt.[{nk}] = src.[{nk}]
    WHEN MATCHED THEN
        UPDATE SET {set_list},
            tgt.[UpdatedDate] = GETDATE()
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ({ins_cols})
        VALUES ({ins_vals});
END;"""


def proc_load_dwh_type2(e):
    table = f"Dim{e['singular']}_Type2"
    nk = e["nkey"]
    bcols = business_cols_no_key(e)
    diff = "\n            OR ".join(
        f"ISNULL(CONVERT(NVARCHAR(4000), tgt.[{c}]), '~') "
        f"<> ISNULL(CONVERT(NVARCHAR(4000), src.[{c}]), '~')" for c in bcols)
    ins_cols = ", ".join(f"[{c}]" for c in [nk] + bcols) + \
        ", [EffectiveDate], [ExpiryDate], [IsCurrent], [CreatedDate]"
    ins_vals = ", ".join(f"src.[{c}]" for c in [nk] + bcols) + \
        ", CAST(GETDATE() AS DATE), NULL, 1, GETDATE()"
    return f"""CREATE OR ALTER PROCEDURE dbo.usp_Load_{table}
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (SCD Type-2: keep history)

    -- 1) expire the CURRENT version of any key whose attributes changed
    UPDATE tgt
        SET tgt.[ExpiryDate] = CAST(GETDATE() AS DATE),
            tgt.[IsCurrent]  = 0
    FROM dbo.{table} AS tgt
    INNER JOIN {DB_STAGING}.dbo.STG_{e['plural']} AS src
        ON src.[{nk}] = tgt.[{nk}]
    WHERE tgt.[IsCurrent] = 1
      AND src.IsValid = 1
      AND ({diff});

    -- 2) insert a new current version for new keys OR just-expired changed keys
    INSERT INTO dbo.{table} ({ins_cols})
    SELECT {ins_vals.replace('src.', 'src.')}
    FROM {DB_STAGING}.dbo.STG_{e['plural']} AS src
    WHERE src.IsValid = 1
      AND NOT EXISTS (SELECT 1 FROM dbo.{table} cur
                      WHERE cur.[{nk}] = src.[{nk}] AND cur.[IsCurrent] = 1);
END;"""


def proc_load_dwh_fact(e):
    table = f"Fact{e['singular']}"
    nk = e["nkey"]
    measures = [c[0] for c in e["cols"]]
    joins = []
    sk_selects = []
    for idx, (fk, dim_nk, sk_col, dim, cur) in enumerate(e["refs"]):
        alias = f"d{idx}"
        cond = f"{alias}.[{dim_nk}] = s.[{fk}]"
        if cur:
            cond += f" AND {alias}.[IsCurrent] = 1"
        joins.append(f"    LEFT JOIN dbo.{dim} AS {alias} ON {cond}")
        sk_selects.append(f"{alias}.[{sk_col}]")
    ins_cols = ", ".join(f"[{c}]" for c in [nk] + measures) + ", " + \
        ", ".join(f"[{r[2]}]" for r in e["refs"]) + ", [CreatedDate]"
    sel = ", ".join(f"s.[{c}]" for c in [nk] + measures) + ", " + \
        ", ".join(sk_selects) + ", GETDATE()"
    join_block = "\n".join(joins)
    return f"""CREATE OR ALTER PROCEDURE dbo.usp_Load_{table}
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (Fact: resolve surrogate keys from dimensions)
    DELETE FROM dbo.{table};
    INSERT INTO dbo.{table} ({ins_cols})
    SELECT {sel}
    FROM {DB_STAGING}.dbo.STG_{e['plural']} AS s
{join_block}
    WHERE s.IsValid = 1;
END;"""


def proc_load_dwh(e):
    if e["dwh"] == "Type1":
        return proc_load_dwh_type1(e)
    if e["dwh"] == "Type2":
        return proc_load_dwh_type2(e)
    return proc_load_dwh_fact(e)


# ==========================================================================
# seed data (deterministic - no randomness)
# ==========================================================================
N_ROWS_DIM = 6      # master/dimension entities
N_ROWS_FACT = 20    # transactional (fact) entities
DIM_KEYS = 6        # how many dimension rows exist to reference (FK range 1..6)


def rows_for(e):
    return N_ROWS_FACT if is_fact(e) else N_ROWS_DIM


def pick(lst, i):
    """Cycle through a fixed list so seed generation scales past its length."""
    return lst[(i - 1) % len(lst)]


def fk(i):
    """Cycle a foreign key over the 1..DIM_KEYS dimension rows that exist."""
    return ((i - 1) % DIM_KEYS) + 1

# realistic-ish value pools so validation rules pass on the seed
POOLS = {
    "Employees": {
        "codes": lambda i: f"EMP{i:04d}",
        "rows": lambda i: {
            "FirstName": ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Neha"][i - 1],
            "LastName": ["Sharma", "Verma", "Kumar", "Reddy", "Singh", "Gupta"][i - 1],
            "Email": f"employee{i}@bank.com",
            "Phone": f"90000000{i:02d}",
            "Designation": ["Teller", "Manager", "Analyst", "Officer", "Cashier", "Advisor"][i - 1],
            "BranchID": 100 + ((i - 1) % 5) + 1,
            "Salary": 45000 + i * 5000,
            "HireDate": f"2021-0{((i - 1) % 9) + 1}-15",
            "Status": ["Active", "Active", "OnLeave", "Active", "Inactive", "Active"][i - 1],
        },
    },
    "Loans": {
        "codes": lambda i: f"LN{i:06d}",
        "rows": lambda i: {
            "CustomerID": i,
            "ProductType": ["Home", "Auto", "Personal", "Education", "Business", "Home"][i - 1],
            "PrincipalAmount": 100000 * i,
            "InterestRate": 7.5 + i * 0.25,
            "TermMonths": 12 * i,
            "DisbursementDate": f"2023-0{((i - 1) % 9) + 1}-10",
            "OutstandingAmount": 100000 * i - 5000 * i,
            "Status": ["Active", "Active", "Closed", "Active", "Pending", "Defaulted"][i - 1],
        },
    },
    "Cards": {
        "codes": lambda i: f"4111XXXXXXXX{i:04d}",
        "rows": lambda i: {
            "AccountID": 1000 + i,
            "CardType": ["Debit", "Credit", "Debit", "Prepaid", "Credit", "Debit"][i - 1],
            "Network": ["Visa", "Mastercard", "RuPay", "Amex", "Visa", "Mastercard"][i - 1],
            "CreditLimit": 50000 * i,
            "IssueDate": f"2022-0{((i - 1) % 9) + 1}-01",
            "ExpiryDate": f"2027-0{((i - 1) % 9) + 1}-01",
            "Status": ["Active", "Active", "Blocked", "Active", "Expired", "Active"][i - 1],
        },
    },
    "Merchants": {
        "codes": lambda i: f"MER{i:04d}",
        "rows": lambda i: {
            "MerchantName": ["Big Bazaar", "Amazon", "Flipkart", "Reliance", "Croma", "Zomato"][i - 1],
            "Category": ["Retail", "Ecommerce", "Ecommerce", "Retail", "Electronics", "Food"][i - 1],
            "City": ["Delhi", "Mumbai", "Bengaluru", "Mumbai", "Pune", "Gurgaon"][i - 1],
            "Country": "India",
            "Status": ["Active", "Active", "Active", "Suspended", "Active", "Inactive"][i - 1],
        },
    },
    "CardTransactions": {
        "codes": lambda i: f"CTX{i:08d}",
        "rows": lambda i: {
            "CardID": fk(i),
            "MerchantID": fk(i),
            "TxnDate": f"2024-01-{((i - 1) % 28) + 1:02d} 12:30:00",
            "Amount": 1000 + 250 * i,
            "CurrencyCode": "INR",
            "TxnType": pick(["Purchase", "Withdrawal", "Refund", "Reversal"], i),
            "Status": pick(["Approved", "Approved", "Declined", "Pending"], i),
        },
    },
    "LoanPayments": {
        "codes": lambda i: f"LP{i:08d}",
        "rows": lambda i: {
            "LoanID": fk(i),
            "PaymentDate": f"2024-02-{((i - 1) % 28) + 1:02d}",
            "PaymentAmount": 5000 + 1000 * i,
            "PrincipalComponent": 4000 + 800 * i,
            "InterestComponent": 1000 + 200 * i,
            "PaymentMethod": pick(["Cash", "Cheque", "Online", "AutoDebit"], i),
        },
    },
}


def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def seed_for(e):
    plural = e["plural"]
    pool = POOLS[plural]
    n = rows_for(e)
    cols = all_layer_cols(e) + ["CreatedDate", "UpdatedDate"]
    lines = [f"-- ---- dbo.SRC_{plural} ({n} rows) ----",
             f"DELETE FROM dbo.SRC_{plural};"]
    for i in range(1, n + 1):
        row = {e["nkey"]: i}
        # the business/natural code column is always the first of e["cols"]
        code_col = e["cols"][0][0]
        row[code_col] = pool["codes"](i)
        row.update(pool["rows"](i))
        row["CreatedDate"] = f"2024-01-01 09:00:00"
        row["UpdatedDate"] = None
        vals = ", ".join(sql_val(row.get(c)) for c in cols)
        collist = ", ".join(f"[{c}]" for c in cols)
        lines.append(f"INSERT INTO dbo.SRC_{plural} ({collist}) VALUES ({vals});")
    return "\n".join(lines)


# ==========================================================================
# YAML config snippets
# ==========================================================================
def yaml_list(items, indent):
    return "\n".join(f"{indent}- {c}" for c in items)


def yaml_transforms(e, indent):
    out = []
    for t in e["transforms"]:
        out.append(f"{indent}- column: \"{t['column']}\"")
        out.append(f"{indent}  rule: \"{t['rule']}\"")
        if "value" in t:
            if isinstance(t["value"], list):
                vals = ", ".join(f"\"{v}\"" for v in t["value"])
                out.append(f"{indent}  value: [{vals}]")
            elif isinstance(t["value"], str):
                # single-quote strings (e.g. regex) so backslashes stay literal
                out.append(f"{indent}  value: '{t['value']}'")
            else:
                out.append(f"{indent}  value: {t['value']}")
        out.append(f"{indent}  description: \"{t['description']}\"")
    return "\n".join(out)


def cfg_src_to_ps(e):
    return f"""
  {e['plural']}:
    source_table: "dbo.SRC_{e['plural']}"
    target_table: "dbo.PS_{e['plural']}"
    load_proc: "dbo.usp_Load_PS_{e['plural']}"
    key: ["{e['nkey']}"]
    compare_columns:
{yaml_list(all_layer_cols(e), '      ')}
    not_null_columns: {e['not_null']}"""


def cfg_ps_to_stg(e):
    return f"""
  {e['plural']}:
    source_table: "dbo.PS_{e['plural']}"
    target_table: "dbo.STG_{e['plural']}"
    load_proc: "dbo.usp_Load_STG_{e['plural']}"
    key: ["{e['nkey']}"]
    compare_columns:
{yaml_list(all_layer_cols(e), '      ')}
    not_null_columns: {e['not_null']}
    transformations:
{yaml_transforms(e, '      ')}"""


def cfg_stg_to_dwh(e):
    if e["dwh"] == "Type1":
        target = f"dbo.Dim{e['singular']}_Type1"
        proc = f"dbo.usp_Load_Dim{e['singular']}_Type1"
        dim_type, tfilter = "Type1", "null"
    elif e["dwh"] == "Type2":
        target = f"dbo.Dim{e['singular']}_Type2"
        proc = f"dbo.usp_Load_Dim{e['singular']}_Type2"
        dim_type, tfilter = "Type2", '"IsCurrent = 1"'
    else:
        target = f"dbo.Fact{e['singular']}"
        proc = f"dbo.usp_Load_Fact{e['singular']}"
        dim_type, tfilter = "Fact", "null"
    return f"""
  {e['plural']}:
    source_table: "dbo.STG_{e['plural']}"
    target_table: "{target}"
    load_proc: "{proc}"
    dim_type: "{dim_type}"
    key: ["{e['nkey']}"]
    target_filter: {tfilter}
    compare_columns:
{yaml_list(dwh_compare_cols(e), '      ')}
    not_null_columns: {e['not_null']}"""


# ==========================================================================
# pytest files
# ==========================================================================
def test_src_ps(e):
    marker = e["plural"].lower()
    return f'''"""Layer 1 : Source -> PreStaging  |  {e['plural']} table."""

import pytest
from validations import validations as v

LAYER = "SourceToPreStaging"
TABLE = "{e['plural']}"


@pytest.mark.order(1)
@pytest.mark.source_to_prestaging
@pytest.mark.{marker}
@pytest.mark.basic
class Test{e['plural']}Basic:

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


@pytest.mark.order(1)
@pytest.mark.source_to_prestaging
@pytest.mark.{marker}
@pytest.mark.datamove
class Test{e['plural']}DirectMove:

    @pytest.mark.direct_move_check
    def test_direct_move(self):
        assert v.direct_move_Validation(LAYER, TABLE)
'''


def test_ps_stg(e):
    marker = e["plural"].lower()
    return f'''"""Layer 2 : PreStaging -> Staging  |  {e['plural']} table."""

import pytest
from validations import validations as v

LAYER = "PreStagingToStaging"
TABLE = "{e['plural']}"


@pytest.mark.order(2)
@pytest.mark.prestaging_to_staging
@pytest.mark.{marker}
@pytest.mark.basic
class Test{e['plural']}Basic:

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


@pytest.mark.order(2)
@pytest.mark.prestaging_to_staging
@pytest.mark.{marker}
@pytest.mark.transformation
class Test{e['plural']}Transformation:

    def test_transformation_rules(self):
        assert v.Transformation_Validation(LAYER, TABLE)

    def test_data_integrity(self):
        assert v.data_integrity_Validation(LAYER, TABLE)
'''


_BASIC_BODY = '''    @pytest.mark.metadata_check
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
        assert v.Constraint_Validation(LAYER, TABLE)'''


def test_stg_dwh(e):
    if is_fact(e):
        return _test_stg_dwh_fact(e)
    marker = e["plural"].lower()
    target = f"Dim{e['singular']}_Type1" if e["dwh"] == "Type1" \
        else f"Dim{e['singular']}_Type2"
    return f'''"""Layer 3 : Staging -> DWH  |  {e['plural']} -> {target}."""

import pytest
from validations import validations as v

LAYER = "StagingToDWH"
TABLE = "{e['plural']}"


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.{marker}
@pytest.mark.basic
class Test{e['plural']}Basic:

{_BASIC_BODY}


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.{marker}
@pytest.mark.transformation
class Test{e['plural']}DwhLoad:

    def test_data_integrity(self):
        assert v.data_integrity_Validation(LAYER, TABLE)
'''


def _test_stg_dwh_fact(e):
    """Fact test file: basic checks + the two fact-specific checks
    (foreign keys + column values), matching tests/StagingToDWH/
    test_STGDW_Transactions.py."""
    marker = e["plural"].lower()
    fact = f"Fact{e['singular']}"
    value_cols = [c[0] for c in e["cols"]]
    value_cols_py = "[" + ", ".join(f'"{c}"' for c in value_cols) + "]"
    fk_lines = "\n".join(
        f'    {{"column": "{sk}", "ref_table": "dbo.{dim}", '
        f'"ref_column": "{sk}", "allow_null": False}},'
        for _fk, _nk, sk, dim, _cur in e["refs"])
    return f'''"""Layer 3 : Staging -> DWH  |  {e['plural']} -> {fact}.

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
TABLE = "{e['plural']}"

log = get_logger()

# --- Fact-specific settings (only relevant to {fact}) --------------
SOURCE_DB = "staging"                  # Bank_Staging
TARGET_DB = "dwh"                      # Bank_DWH
STG_TABLE = "dbo.STG_{e['plural']}"
FACT_TABLE = "dbo.{fact}"
KEY = "{e['nkey']}"
VALID_FILTER = "IsValid = 1"           # only accepted staging rows reach the fact

# the non-key value columns whose data must match the staging source
VALUE_COLUMNS = {value_cols_py}

# surrogate foreign keys -> the dimension table they must point to
# allow_null=False means a NULL surrogate key is treated as a failure
FOREIGN_KEYS = [
{fk_lines}
]


def _record(name, passed, message, category):
    """Log + store the outcome so it appears in the log and the reports."""
    status = "PASS" if passed else "FAIL"
    line = f"[{{status}}] {{LAYER}} | {{TABLE}} | {{name}} | {{message}}"
    (log.info if passed else log.error)(line)
    result_store.add_result(LAYER, TABLE, name, status, message, category=category)
    return passed


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.{marker}
@pytest.mark.fact
@pytest.mark.basic
class Test{e['plural']}Basic:
    """Common reusable validations (from validations.validations)."""

{_BASIC_BODY}


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.{marker}
@pytest.mark.fact
@pytest.mark.transformation
class Test{e['plural']}Fact:
    """Fact-specific checks - logic defined here, not in validations.py."""

    def test_foreign_keys(self):
        """Every surrogate key in the fact must exist in its dimension."""
        problems = []
        for fk in FOREIGN_KEYS:
            col, ref_table, ref_col = fk["column"], fk["ref_table"], fk["ref_column"]

            # orphans: a non-null key value with no matching dimension row
            orphan_where = (f"[{{col}}] IS NOT NULL AND [{{col}}] NOT IN "
                            f"(SELECT [{{ref_col}}] FROM {{ref_table}})")
            orphans = db.get_row_count(TARGET_DB, FACT_TABLE, where=orphan_where)
            if orphans:
                problems.append(f"{{col}}: {{orphans}} orphan(s) not in {{ref_table}}")

            # nulls (only a problem when nulls are not allowed)
            if not fk["allow_null"]:
                nulls = db.get_row_count(TARGET_DB, FACT_TABLE, where=f"[{{col}}] IS NULL")
                if nulls:
                    problems.append(f"{{col}}: {{nulls}} null(s)")

        passed = not problems
        cols = ", ".join(fk["column"] for fk in FOREIGN_KEYS)
        msg = (f"all foreign keys valid ({{cols}})" if passed
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
        msg = (f"diffs={{len(result['diffs'])}}, "
               f"missing_in_target={{len(result['missing_in_target'])}}, "
               f"missing_in_source={{len(result['missing_in_source'])}}, "
               f"duplicates={{len(result['duplicates'])}}")
        assert _record("ColumnValues_Check", passed, msg, category="value_check")
'''


# ==========================================================================
# file writing
# ==========================================================================
def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n")
    print("wrote", path)


def banner(title, db=None):
    line = "-- " + "=" * 68
    out = [line, f"-- {title}"]
    if db:
        out.append(f"-- database: {db}")
    out += [line, ""]
    return "\n".join(out)


def build_ddl_file(kind, builder, db, title):
    parts = [banner(title, db), f"USE [{db}];", "GO", ""]
    for e in ALL:
        parts.append(builder(e))
        parts.append("GO\n")
    return "\n".join(parts)


def build_proc_file(builder, db, title):
    parts = [banner(title, db), f"USE [{db}];", "GO", ""]
    for e in ALL:
        parts.append(builder(e))
        parts.append("GO\n")
    return "\n".join(parts)


def main():
    # ---- DDL ----
    write("database/ddl/01_source_tables.sql",
          build_ddl_file("src", ddl_source, DB_SOURCE,
                         "NEW ENTITIES - SOURCE tables (SRC_)"))
    write("database/ddl/02_prestaging_tables.sql",
          build_ddl_file("ps", ddl_prestaging, DB_PRESTAGING,
                         "NEW ENTITIES - PRE-STAGING tables (PS_)"))
    write("database/ddl/03_staging_tables.sql",
          build_ddl_file("stg", ddl_staging, DB_STAGING,
                         "NEW ENTITIES - STAGING tables (STG_, +IsValid/RejectionReason)"))
    write("database/ddl/04_dwh_tables.sql",
          build_ddl_file("dwh", ddl_dwh, DB_DWH,
                         "NEW ENTITIES - DWH tables (Dim Type1/Type2 + Fact)"))

    # ---- load procs ----
    write("database/procs/05_load_prestaging.sql",
          build_proc_file(proc_load_ps, DB_PRESTAGING,
                          "NEW ENTITIES - Layer 1 load procs (Source -> PreStaging)"))
    write("database/procs/06_load_staging.sql",
          build_proc_file(proc_load_stg, DB_STAGING,
                          "NEW ENTITIES - Layer 2 load procs (PreStaging -> Staging)"))
    write("database/procs/07_load_dwh.sql",
          build_proc_file(proc_load_dwh, DB_DWH,
                          "NEW ENTITIES - Layer 3 load procs (Staging -> DWH)"))

    # ---- seed data ----
    seed = [banner("NEW ENTITIES - SOURCE seed data", DB_SOURCE),
            "SET NOCOUNT ON;", f"USE [{DB_SOURCE}];", "GO", ""]
    for e in ALL:
        seed.append(seed_for(e))
        seed.append("GO\n")
    write("database/data/08_source_seed_data.sql", "\n".join(seed))

    # ---- master run order ----
    order = f"""{banner("NEW ENTITIES - master run order (SQLCMD mode)")}
-- Run in SSMS with SQLCMD mode ON (Query menu -> SQLCMD Mode), or run each
-- file below in this exact order.  Assumes the 4 Bank_* databases already exist.
:setvar root "{os.path.join(ROOT, 'database').replace(chr(92), '/')}"

:r $(root)/ddl/01_source_tables.sql
:r $(root)/ddl/02_prestaging_tables.sql
:r $(root)/ddl/03_staging_tables.sql
:r $(root)/ddl/04_dwh_tables.sql
:r $(root)/procs/05_load_prestaging.sql
:r $(root)/procs/06_load_staging.sql
:r $(root)/procs/07_load_dwh.sql
:r $(root)/data/08_source_seed_data.sql
GO
PRINT 'New entities: tables + procs + seed created. Now EXEC the load procs (see README).';
GO
"""
    write("database/09_run_all_new_entities.sql", order)

    # ---- config snippets ----
    write("database/_config_additions/source_to_prestaging.additions.yaml",
          "# Append these under `tables:` in config/source_to_prestaging.yaml\n" +
          "\n".join(cfg_src_to_ps(e) for e in ALL))
    write("database/_config_additions/prestaging_to_staging.additions.yaml",
          "# Append these under `tables:` in config/prestaging_to_staging.yaml\n" +
          "\n".join(cfg_ps_to_stg(e) for e in ALL))
    write("database/_config_additions/staging_to_dwh.additions.yaml",
          "# Append these under `tables:` in config/staging_to_dwh.yaml\n" +
          "\n".join(cfg_stg_to_dwh(e) for e in ALL))

    # ---- pytest markers ----
    markers = [f"    {e['plural'].lower()}: {e['plural']} table tests" for e in ALL]
    write("database/_config_additions/pytest_markers.txt",
          "# Append these lines under `markers =` in pytest.ini\n" + "\n".join(markers))

    # ---- pytest files ----
    for e in ALL:
        write(f"tests/SourceToPreStaging/test_SRCPS_{e['plural']}.py", test_src_ps(e))
        write(f"tests/PreStagingToStaging/test_PSSTG_{e['plural']}.py", test_ps_stg(e))
        write(f"tests/StagingToDWH/test_STGDW_{e['plural']}.py", test_stg_dwh(e))

    print("\nDone. 6 entities x 4 layers generated.")


if __name__ == "__main__":
    main()
