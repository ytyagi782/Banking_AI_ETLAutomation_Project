-- ====================================================================
-- NEW ENTITIES - Layer 2 load procs (PreStaging -> Staging)
-- database: Bank_Staging
-- ====================================================================

USE [Bank_Staging];
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_STG_Employees
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 2: PreStaging -> Staging (standardise + validate; keep rejects flagged)
    DELETE FROM dbo.STG_Employees;
    INSERT INTO dbo.STG_Employees ([EmployeeID], [EmployeeCode], [FirstName], [LastName], [Email], [Phone], [Designation], [BranchID], [Salary], [HireDate], [Status], [IsValid], [RejectionReason], [CreatedDate], [UpdatedDate])
    SELECT [EmployeeID],
           [EmployeeCode] AS [EmployeeCode],
           LTRIM(RTRIM([FirstName])) AS [FirstName],
           LTRIM(RTRIM([LastName])) AS [LastName],
           [Email] AS [Email],
           [Phone] AS [Phone],
           [Designation] AS [Designation],
           [BranchID] AS [BranchID],
           [Salary] AS [Salary],
           [HireDate] AS [HireDate],
           UPPER(LTRIM(RTRIM([Status]))) AS [Status],
           CASE WHEN [EmployeeID] IS NULL
              OR [EmployeeCode] IS NULL
              OR ([Email] IS NOT NULL AND [Email] NOT LIKE '%_@_%_._%')
              OR ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'INACTIVE', 'ONLEAVE', 'RESIGNED'))
         THEN 0 ELSE 1 END AS [IsValid],
           CASE
        WHEN [EmployeeID] IS NULL THEN 'EmployeeID is NULL'
        WHEN [EmployeeCode] IS NULL THEN 'EmployeeCode is NULL'
        WHEN ([Email] IS NOT NULL AND [Email] NOT LIKE '%_@_%_._%') THEN 'Email failed regex'
        WHEN ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'INACTIVE', 'ONLEAVE', 'RESIGNED')) THEN 'Status failed in_set'
        ELSE NULL END AS [RejectionReason],
           [CreatedDate],
           GETDATE() AS [UpdatedDate]
    FROM Bank_PreStaging.dbo.PS_Employees;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_STG_Loans
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 2: PreStaging -> Staging (standardise + validate; keep rejects flagged)
    DELETE FROM dbo.STG_Loans;
    INSERT INTO dbo.STG_Loans ([LoanID], [LoanNumber], [CustomerID], [ProductType], [PrincipalAmount], [InterestRate], [TermMonths], [DisbursementDate], [OutstandingAmount], [Status], [IsValid], [RejectionReason], [CreatedDate], [UpdatedDate])
    SELECT [LoanID],
           LTRIM(RTRIM([LoanNumber])) AS [LoanNumber],
           [CustomerID] AS [CustomerID],
           UPPER(LTRIM(RTRIM([ProductType]))) AS [ProductType],
           [PrincipalAmount] AS [PrincipalAmount],
           [InterestRate] AS [InterestRate],
           [TermMonths] AS [TermMonths],
           [DisbursementDate] AS [DisbursementDate],
           [OutstandingAmount] AS [OutstandingAmount],
           UPPER(LTRIM(RTRIM([Status]))) AS [Status],
           CASE WHEN [LoanID] IS NULL
              OR [LoanNumber] IS NULL
              OR [CustomerID] IS NULL
              OR ([ProductType] IS NOT NULL AND UPPER(LTRIM(RTRIM([ProductType]))) NOT IN ('HOME', 'AUTO', 'PERSONAL', 'EDUCATION', 'BUSINESS'))
              OR ([PrincipalAmount] IS NOT NULL AND [PrincipalAmount] < 0)
              OR ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'CLOSED', 'DEFAULTED', 'PENDING'))
         THEN 0 ELSE 1 END AS [IsValid],
           CASE
        WHEN [LoanID] IS NULL THEN 'LoanID is NULL'
        WHEN [LoanNumber] IS NULL THEN 'LoanNumber is NULL'
        WHEN [CustomerID] IS NULL THEN 'CustomerID is NULL'
        WHEN ([ProductType] IS NOT NULL AND UPPER(LTRIM(RTRIM([ProductType]))) NOT IN ('HOME', 'AUTO', 'PERSONAL', 'EDUCATION', 'BUSINESS')) THEN 'ProductType failed in_set'
        WHEN ([PrincipalAmount] IS NOT NULL AND [PrincipalAmount] < 0) THEN 'PrincipalAmount failed min_value'
        WHEN ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'CLOSED', 'DEFAULTED', 'PENDING')) THEN 'Status failed in_set'
        ELSE NULL END AS [RejectionReason],
           [CreatedDate],
           GETDATE() AS [UpdatedDate]
    FROM Bank_PreStaging.dbo.PS_Loans;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_STG_Cards
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 2: PreStaging -> Staging (standardise + validate; keep rejects flagged)
    DELETE FROM dbo.STG_Cards;
    INSERT INTO dbo.STG_Cards ([CardID], [CardNumber], [AccountID], [CardType], [Network], [CreditLimit], [IssueDate], [ExpiryDate], [Status], [IsValid], [RejectionReason], [CreatedDate], [UpdatedDate])
    SELECT [CardID],
           [CardNumber] AS [CardNumber],
           [AccountID] AS [AccountID],
           UPPER(LTRIM(RTRIM([CardType]))) AS [CardType],
           UPPER(LTRIM(RTRIM([Network]))) AS [Network],
           [CreditLimit] AS [CreditLimit],
           [IssueDate] AS [IssueDate],
           [ExpiryDate] AS [ExpiryDate],
           UPPER(LTRIM(RTRIM([Status]))) AS [Status],
           CASE WHEN [CardID] IS NULL
              OR [CardNumber] IS NULL
              OR [AccountID] IS NULL
              OR ([CardType] IS NOT NULL AND UPPER(LTRIM(RTRIM([CardType]))) NOT IN ('DEBIT', 'CREDIT', 'PREPAID'))
              OR ([Network] IS NOT NULL AND UPPER(LTRIM(RTRIM([Network]))) NOT IN ('VISA', 'MASTERCARD', 'RUPAY', 'AMEX'))
              OR ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'BLOCKED', 'EXPIRED'))
         THEN 0 ELSE 1 END AS [IsValid],
           CASE
        WHEN [CardID] IS NULL THEN 'CardID is NULL'
        WHEN [CardNumber] IS NULL THEN 'CardNumber is NULL'
        WHEN [AccountID] IS NULL THEN 'AccountID is NULL'
        WHEN ([CardType] IS NOT NULL AND UPPER(LTRIM(RTRIM([CardType]))) NOT IN ('DEBIT', 'CREDIT', 'PREPAID')) THEN 'CardType failed in_set'
        WHEN ([Network] IS NOT NULL AND UPPER(LTRIM(RTRIM([Network]))) NOT IN ('VISA', 'MASTERCARD', 'RUPAY', 'AMEX')) THEN 'Network failed in_set'
        WHEN ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'BLOCKED', 'EXPIRED')) THEN 'Status failed in_set'
        ELSE NULL END AS [RejectionReason],
           [CreatedDate],
           GETDATE() AS [UpdatedDate]
    FROM Bank_PreStaging.dbo.PS_Cards;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_STG_Merchants
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 2: PreStaging -> Staging (standardise + validate; keep rejects flagged)
    DELETE FROM dbo.STG_Merchants;
    INSERT INTO dbo.STG_Merchants ([MerchantID], [MerchantCode], [MerchantName], [Category], [City], [Country], [Status], [IsValid], [RejectionReason], [CreatedDate], [UpdatedDate])
    SELECT [MerchantID],
           [MerchantCode] AS [MerchantCode],
           LTRIM(RTRIM([MerchantName])) AS [MerchantName],
           [Category] AS [Category],
           [City] AS [City],
           [Country] AS [Country],
           UPPER(LTRIM(RTRIM([Status]))) AS [Status],
           CASE WHEN [MerchantID] IS NULL
              OR [MerchantCode] IS NULL
              OR ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'))
         THEN 0 ELSE 1 END AS [IsValid],
           CASE
        WHEN [MerchantID] IS NULL THEN 'MerchantID is NULL'
        WHEN [MerchantCode] IS NULL THEN 'MerchantCode is NULL'
        WHEN ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')) THEN 'Status failed in_set'
        ELSE NULL END AS [RejectionReason],
           [CreatedDate],
           GETDATE() AS [UpdatedDate]
    FROM Bank_PreStaging.dbo.PS_Merchants;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_STG_CardTransactions
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 2: PreStaging -> Staging (standardise + validate; keep rejects flagged)
    DELETE FROM dbo.STG_CardTransactions;
    INSERT INTO dbo.STG_CardTransactions ([CardTransactionID], [CardID], [MerchantID], [CardTxnNumber], [TxnDate], [Amount], [CurrencyCode], [TxnType], [Status], [IsValid], [RejectionReason], [CreatedDate], [UpdatedDate])
    SELECT [CardTransactionID],
           [CardID] AS [CardID],
           [MerchantID] AS [MerchantID],
           [CardTxnNumber] AS [CardTxnNumber],
           [TxnDate] AS [TxnDate],
           [Amount] AS [Amount],
           [CurrencyCode] AS [CurrencyCode],
           UPPER(LTRIM(RTRIM([TxnType]))) AS [TxnType],
           UPPER(LTRIM(RTRIM([Status]))) AS [Status],
           CASE WHEN [CardTransactionID] IS NULL
              OR [CardTxnNumber] IS NULL
              OR ([Amount] IS NOT NULL AND [Amount] < 0)
              OR ([CurrencyCode] IS NOT NULL AND LEN(LTRIM(RTRIM([CurrencyCode]))) <> 3)
              OR ([TxnType] IS NOT NULL AND UPPER(LTRIM(RTRIM([TxnType]))) NOT IN ('PURCHASE', 'WITHDRAWAL', 'REFUND', 'REVERSAL'))
              OR ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('APPROVED', 'DECLINED', 'PENDING'))
         THEN 0 ELSE 1 END AS [IsValid],
           CASE
        WHEN [CardTransactionID] IS NULL THEN 'CardTransactionID is NULL'
        WHEN [CardTxnNumber] IS NULL THEN 'CardTxnNumber is NULL'
        WHEN ([Amount] IS NOT NULL AND [Amount] < 0) THEN 'Amount failed min_value'
        WHEN ([CurrencyCode] IS NOT NULL AND LEN(LTRIM(RTRIM([CurrencyCode]))) <> 3) THEN 'CurrencyCode failed length_equals'
        WHEN ([TxnType] IS NOT NULL AND UPPER(LTRIM(RTRIM([TxnType]))) NOT IN ('PURCHASE', 'WITHDRAWAL', 'REFUND', 'REVERSAL')) THEN 'TxnType failed in_set'
        WHEN ([Status] IS NOT NULL AND UPPER(LTRIM(RTRIM([Status]))) NOT IN ('APPROVED', 'DECLINED', 'PENDING')) THEN 'Status failed in_set'
        ELSE NULL END AS [RejectionReason],
           [CreatedDate],
           GETDATE() AS [UpdatedDate]
    FROM Bank_PreStaging.dbo.PS_CardTransactions;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_STG_LoanPayments
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 2: PreStaging -> Staging (standardise + validate; keep rejects flagged)
    DELETE FROM dbo.STG_LoanPayments;
    INSERT INTO dbo.STG_LoanPayments ([LoanPaymentID], [LoanID], [PaymentNumber], [PaymentDate], [PaymentAmount], [PrincipalComponent], [InterestComponent], [PaymentMethod], [IsValid], [RejectionReason], [CreatedDate], [UpdatedDate])
    SELECT [LoanPaymentID],
           [LoanID] AS [LoanID],
           [PaymentNumber] AS [PaymentNumber],
           [PaymentDate] AS [PaymentDate],
           [PaymentAmount] AS [PaymentAmount],
           [PrincipalComponent] AS [PrincipalComponent],
           [InterestComponent] AS [InterestComponent],
           UPPER(LTRIM(RTRIM([PaymentMethod]))) AS [PaymentMethod],
           CASE WHEN [LoanPaymentID] IS NULL
              OR [PaymentNumber] IS NULL
              OR ([PaymentAmount] IS NOT NULL AND [PaymentAmount] < 0)
              OR ([PaymentMethod] IS NOT NULL AND UPPER(LTRIM(RTRIM([PaymentMethod]))) NOT IN ('CASH', 'CHEQUE', 'ONLINE', 'AUTODEBIT'))
         THEN 0 ELSE 1 END AS [IsValid],
           CASE
        WHEN [LoanPaymentID] IS NULL THEN 'LoanPaymentID is NULL'
        WHEN [PaymentNumber] IS NULL THEN 'PaymentNumber is NULL'
        WHEN ([PaymentAmount] IS NOT NULL AND [PaymentAmount] < 0) THEN 'PaymentAmount failed min_value'
        WHEN ([PaymentMethod] IS NOT NULL AND UPPER(LTRIM(RTRIM([PaymentMethod]))) NOT IN ('CASH', 'CHEQUE', 'ONLINE', 'AUTODEBIT')) THEN 'PaymentMethod failed in_set'
        ELSE NULL END AS [RejectionReason],
           [CreatedDate],
           GETDATE() AS [UpdatedDate]
    FROM Bank_PreStaging.dbo.PS_LoanPayments;
END;
GO
