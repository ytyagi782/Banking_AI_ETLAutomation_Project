-- ====================================================================
-- NEW ENTITIES - Layer 1 load procs (Source -> PreStaging)
-- database: Bank_PreStaging
-- ====================================================================

USE [Bank_PreStaging];
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_PS_Employees
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 1: direct move Source -> PreStaging (no transformation)
    DELETE FROM dbo.PS_Employees;
    INSERT INTO dbo.PS_Employees ([EmployeeID], [EmployeeCode], [FirstName], [LastName], [Email], [Phone], [Designation], [BranchID], [Salary], [HireDate], [Status], [CreatedDate], [UpdatedDate])
    SELECT [EmployeeID], [EmployeeCode], [FirstName], [LastName], [Email], [Phone], [Designation], [BranchID], [Salary], [HireDate], [Status], [CreatedDate], [UpdatedDate]
    FROM Bank_Source.dbo.SRC_Employees;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_PS_Loans
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 1: direct move Source -> PreStaging (no transformation)
    DELETE FROM dbo.PS_Loans;
    INSERT INTO dbo.PS_Loans ([LoanID], [LoanNumber], [CustomerID], [ProductType], [PrincipalAmount], [InterestRate], [TermMonths], [DisbursementDate], [OutstandingAmount], [Status], [CreatedDate], [UpdatedDate])
    SELECT [LoanID], [LoanNumber], [CustomerID], [ProductType], [PrincipalAmount], [InterestRate], [TermMonths], [DisbursementDate], [OutstandingAmount], [Status], [CreatedDate], [UpdatedDate]
    FROM Bank_Source.dbo.SRC_Loans;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_PS_Cards
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 1: direct move Source -> PreStaging (no transformation)
    DELETE FROM dbo.PS_Cards;
    INSERT INTO dbo.PS_Cards ([CardID], [CardNumber], [AccountID], [CardType], [Network], [CreditLimit], [IssueDate], [ExpiryDate], [Status], [CreatedDate], [UpdatedDate])
    SELECT [CardID], [CardNumber], [AccountID], [CardType], [Network], [CreditLimit], [IssueDate], [ExpiryDate], [Status], [CreatedDate], [UpdatedDate]
    FROM Bank_Source.dbo.SRC_Cards;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_PS_Merchants
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 1: direct move Source -> PreStaging (no transformation)
    DELETE FROM dbo.PS_Merchants;
    INSERT INTO dbo.PS_Merchants ([MerchantID], [MerchantCode], [MerchantName], [Category], [City], [Country], [Status], [CreatedDate], [UpdatedDate])
    SELECT [MerchantID], [MerchantCode], [MerchantName], [Category], [City], [Country], [Status], [CreatedDate], [UpdatedDate]
    FROM Bank_Source.dbo.SRC_Merchants;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_PS_CardTransactions
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 1: direct move Source -> PreStaging (no transformation)
    DELETE FROM dbo.PS_CardTransactions;
    INSERT INTO dbo.PS_CardTransactions ([CardTransactionID], [CardID], [MerchantID], [CardTxnNumber], [TxnDate], [Amount], [CurrencyCode], [TxnType], [Status], [CreatedDate], [UpdatedDate])
    SELECT [CardTransactionID], [CardID], [MerchantID], [CardTxnNumber], [TxnDate], [Amount], [CurrencyCode], [TxnType], [Status], [CreatedDate], [UpdatedDate]
    FROM Bank_Source.dbo.SRC_CardTransactions;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_Load_PS_LoanPayments
AS
BEGIN
    SET NOCOUNT ON;
    -- Layer 1: direct move Source -> PreStaging (no transformation)
    DELETE FROM dbo.PS_LoanPayments;
    INSERT INTO dbo.PS_LoanPayments ([LoanPaymentID], [LoanID], [PaymentNumber], [PaymentDate], [PaymentAmount], [PrincipalComponent], [InterestComponent], [PaymentMethod], [CreatedDate], [UpdatedDate])
    SELECT [LoanPaymentID], [LoanID], [PaymentNumber], [PaymentDate], [PaymentAmount], [PrincipalComponent], [InterestComponent], [PaymentMethod], [CreatedDate], [UpdatedDate]
    FROM Bank_Source.dbo.SRC_LoanPayments;
END;
GO
