-- ====================================================================
-- NEW ENTITIES - Layer 3 load procs (Staging -> DWH)
-- database: Bank_DWH
-- ====================================================================

USE [Bank_DWH];
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_DimEmployee_Type2
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (SCD Type-2: keep history)

    -- 1) expire the CURRENT version of any key whose attributes changed
    UPDATE tgt
        SET tgt.[ExpiryDate] = CAST(GETDATE() AS DATE),
            tgt.[IsCurrent]  = 0
    FROM dbo.DimEmployee_Type2 AS tgt
    INNER JOIN Bank_Staging.dbo.STG_Employees AS src
        ON src.[EmployeeID] = tgt.[EmployeeID]
    WHERE tgt.[IsCurrent] = 1
      AND src.IsValid = 1
      AND (ISNULL(CONVERT(NVARCHAR(4000), tgt.[EmployeeCode]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[EmployeeCode]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[FirstName]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[FirstName]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[LastName]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[LastName]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[Email]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[Email]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[Phone]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[Phone]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[Designation]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[Designation]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[BranchID]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[BranchID]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[Salary]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[Salary]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[HireDate]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[HireDate]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[Status]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[Status]), '~'));

    -- 2) insert a new current version for new keys OR just-expired changed keys
    INSERT INTO dbo.DimEmployee_Type2 ([EmployeeID], [EmployeeCode], [FirstName], [LastName], [Email], [Phone], [Designation], [BranchID], [Salary], [HireDate], [Status], [EffectiveDate], [ExpiryDate], [IsCurrent], [CreatedDate])
    SELECT src.[EmployeeID], src.[EmployeeCode], src.[FirstName], src.[LastName], src.[Email], src.[Phone], src.[Designation], src.[BranchID], src.[Salary], src.[HireDate], src.[Status], CAST(GETDATE() AS DATE), NULL, 1, GETDATE()
    FROM Bank_Staging.dbo.STG_Employees AS src
    WHERE src.IsValid = 1
      AND NOT EXISTS (SELECT 1 FROM dbo.DimEmployee_Type2 cur
                      WHERE cur.[EmployeeID] = src.[EmployeeID] AND cur.[IsCurrent] = 1);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_DimLoan_Type2
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (SCD Type-2: keep history)

    -- 1) expire the CURRENT version of any key whose attributes changed
    UPDATE tgt
        SET tgt.[ExpiryDate] = CAST(GETDATE() AS DATE),
            tgt.[IsCurrent]  = 0
    FROM dbo.DimLoan_Type2 AS tgt
    INNER JOIN Bank_Staging.dbo.STG_Loans AS src
        ON src.[LoanID] = tgt.[LoanID]
    WHERE tgt.[IsCurrent] = 1
      AND src.IsValid = 1
      AND (ISNULL(CONVERT(NVARCHAR(4000), tgt.[LoanNumber]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[LoanNumber]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[CustomerID]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[CustomerID]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[ProductType]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[ProductType]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[PrincipalAmount]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[PrincipalAmount]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[InterestRate]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[InterestRate]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[TermMonths]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[TermMonths]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[DisbursementDate]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[DisbursementDate]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[OutstandingAmount]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[OutstandingAmount]), '~')
            OR ISNULL(CONVERT(NVARCHAR(4000), tgt.[Status]), '~') <> ISNULL(CONVERT(NVARCHAR(4000), src.[Status]), '~'));

    -- 2) insert a new current version for new keys OR just-expired changed keys
    INSERT INTO dbo.DimLoan_Type2 ([LoanID], [LoanNumber], [CustomerID], [ProductType], [PrincipalAmount], [InterestRate], [TermMonths], [DisbursementDate], [OutstandingAmount], [Status], [EffectiveDate], [ExpiryDate], [IsCurrent], [CreatedDate])
    SELECT src.[LoanID], src.[LoanNumber], src.[CustomerID], src.[ProductType], src.[PrincipalAmount], src.[InterestRate], src.[TermMonths], src.[DisbursementDate], src.[OutstandingAmount], src.[Status], CAST(GETDATE() AS DATE), NULL, 1, GETDATE()
    FROM Bank_Staging.dbo.STG_Loans AS src
    WHERE src.IsValid = 1
      AND NOT EXISTS (SELECT 1 FROM dbo.DimLoan_Type2 cur
                      WHERE cur.[LoanID] = src.[LoanID] AND cur.[IsCurrent] = 1);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_DimCard_Type1
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (SCD Type-1: overwrite, one row per key)
    MERGE dbo.DimCard_Type1 AS tgt
    USING (SELECT [CardID], [CardNumber], [AccountID], [CardType], [Network], [CreditLimit], [IssueDate], [ExpiryDate], [Status]
           FROM Bank_Staging.dbo.STG_Cards
           WHERE IsValid = 1) AS src
       ON tgt.[CardID] = src.[CardID]
    WHEN MATCHED THEN
        UPDATE SET tgt.[CardNumber] = src.[CardNumber],
            tgt.[AccountID] = src.[AccountID],
            tgt.[CardType] = src.[CardType],
            tgt.[Network] = src.[Network],
            tgt.[CreditLimit] = src.[CreditLimit],
            tgt.[IssueDate] = src.[IssueDate],
            tgt.[ExpiryDate] = src.[ExpiryDate],
            tgt.[Status] = src.[Status],
            tgt.[UpdatedDate] = GETDATE()
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([CardID], [CardNumber], [AccountID], [CardType], [Network], [CreditLimit], [IssueDate], [ExpiryDate], [Status], [CreatedDate])
        VALUES (src.[CardID], src.[CardNumber], src.[AccountID], src.[CardType], src.[Network], src.[CreditLimit], src.[IssueDate], src.[ExpiryDate], src.[Status], GETDATE());
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_DimMerchant_Type1
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (SCD Type-1: overwrite, one row per key)
    MERGE dbo.DimMerchant_Type1 AS tgt
    USING (SELECT [MerchantID], [MerchantCode], [MerchantName], [Category], [City], [Country], [Status]
           FROM Bank_Staging.dbo.STG_Merchants
           WHERE IsValid = 1) AS src
       ON tgt.[MerchantID] = src.[MerchantID]
    WHEN MATCHED THEN
        UPDATE SET tgt.[MerchantCode] = src.[MerchantCode],
            tgt.[MerchantName] = src.[MerchantName],
            tgt.[Category] = src.[Category],
            tgt.[City] = src.[City],
            tgt.[Country] = src.[Country],
            tgt.[Status] = src.[Status],
            tgt.[UpdatedDate] = GETDATE()
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([MerchantID], [MerchantCode], [MerchantName], [Category], [City], [Country], [Status], [CreatedDate])
        VALUES (src.[MerchantID], src.[MerchantCode], src.[MerchantName], src.[Category], src.[City], src.[Country], src.[Status], GETDATE());
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_FactCardTransaction
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (Fact: resolve surrogate keys from dimensions)
    DELETE FROM dbo.FactCardTransaction;
    INSERT INTO dbo.FactCardTransaction ([CardTransactionID], [CardTxnNumber], [TxnDate], [Amount], [CurrencyCode], [TxnType], [Status], [CardSK], [MerchantSK], [CreatedDate])
    SELECT s.[CardTransactionID], s.[CardTxnNumber], s.[TxnDate], s.[Amount], s.[CurrencyCode], s.[TxnType], s.[Status], d0.[CardSK], d1.[MerchantSK], GETDATE()
    FROM Bank_Staging.dbo.STG_CardTransactions AS s
    LEFT JOIN dbo.DimCard_Type1 AS d0 ON d0.[CardID] = s.[CardID]
    LEFT JOIN dbo.DimMerchant_Type1 AS d1 ON d1.[MerchantID] = s.[MerchantID]
    WHERE s.IsValid = 1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_FactLoanPayment
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 3: Staging -> DWH  (Fact: resolve surrogate keys from dimensions)
    DELETE FROM dbo.FactLoanPayment;
    INSERT INTO dbo.FactLoanPayment ([LoanPaymentID], [PaymentNumber], [PaymentDate], [PaymentAmount], [PrincipalComponent], [InterestComponent], [PaymentMethod], [LoanSK], [CreatedDate])
    SELECT s.[LoanPaymentID], s.[PaymentNumber], s.[PaymentDate], s.[PaymentAmount], s.[PrincipalComponent], s.[InterestComponent], s.[PaymentMethod], d0.[LoanSK], GETDATE()
    FROM Bank_Staging.dbo.STG_LoanPayments AS s
    LEFT JOIN dbo.DimLoan_Type2 AS d0 ON d0.[LoanID] = s.[LoanID] AND d0.[IsCurrent] = 1
    WHERE s.IsValid = 1;
END;
GO
