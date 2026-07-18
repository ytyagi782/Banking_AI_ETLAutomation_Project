-- ====================================================================
-- NEW ENTITIES - SOURCE tables (SRC_)
-- database: Bank_Source
-- ====================================================================

USE [Bank_Source];
GO

CREATE TABLE dbo.SRC_Employees (
    [EmployeeID] INT NOT NULL,
    [EmployeeCode] NVARCHAR(20) NOT NULL,
    [FirstName] NVARCHAR(50) NULL,
    [LastName] NVARCHAR(50) NULL,
    [Email] NVARCHAR(100) NULL,
    [Phone] NVARCHAR(20) NULL,
    [Designation] NVARCHAR(50) NULL,
    [BranchID] INT NULL,
    [Salary] DECIMAL(18,2) NULL,
    [HireDate] DATE NULL,
    [Status] NVARCHAR(20) NULL,
    [CreatedDate] DATETIME NOT NULL,
    [UpdatedDate] DATETIME NULL,
    CONSTRAINT [PK_SRC_Employees] PRIMARY KEY ([EmployeeID])
);
GO

CREATE TABLE dbo.SRC_Loans (
    [LoanID] INT NOT NULL,
    [LoanNumber] NVARCHAR(20) NOT NULL,
    [CustomerID] INT NULL,
    [ProductType] NVARCHAR(30) NULL,
    [PrincipalAmount] DECIMAL(18,2) NULL,
    [InterestRate] DECIMAL(9,4) NULL,
    [TermMonths] INT NULL,
    [DisbursementDate] DATE NULL,
    [OutstandingAmount] DECIMAL(18,2) NULL,
    [Status] NVARCHAR(20) NULL,
    [CreatedDate] DATETIME NOT NULL,
    [UpdatedDate] DATETIME NULL,
    CONSTRAINT [PK_SRC_Loans] PRIMARY KEY ([LoanID])
);
GO

CREATE TABLE dbo.SRC_Cards (
    [CardID] INT NOT NULL,
    [CardNumber] NVARCHAR(25) NOT NULL,
    [AccountID] INT NULL,
    [CardType] NVARCHAR(20) NULL,
    [Network] NVARCHAR(20) NULL,
    [CreditLimit] DECIMAL(18,2) NULL,
    [IssueDate] DATE NULL,
    [ExpiryDate] DATE NULL,
    [Status] NVARCHAR(20) NULL,
    [CreatedDate] DATETIME NOT NULL,
    [UpdatedDate] DATETIME NULL,
    CONSTRAINT [PK_SRC_Cards] PRIMARY KEY ([CardID])
);
GO

CREATE TABLE dbo.SRC_Merchants (
    [MerchantID] INT NOT NULL,
    [MerchantCode] NVARCHAR(20) NOT NULL,
    [MerchantName] NVARCHAR(100) NULL,
    [Category] NVARCHAR(50) NULL,
    [City] NVARCHAR(50) NULL,
    [Country] NVARCHAR(50) NULL,
    [Status] NVARCHAR(20) NULL,
    [CreatedDate] DATETIME NOT NULL,
    [UpdatedDate] DATETIME NULL,
    CONSTRAINT [PK_SRC_Merchants] PRIMARY KEY ([MerchantID])
);
GO

CREATE TABLE dbo.SRC_CardTransactions (
    [CardTransactionID] INT NOT NULL,
    [CardID] INT NULL,
    [MerchantID] INT NULL,
    [CardTxnNumber] NVARCHAR(25) NOT NULL,
    [TxnDate] DATETIME NULL,
    [Amount] DECIMAL(18,2) NULL,
    [CurrencyCode] NVARCHAR(3) NULL,
    [TxnType] NVARCHAR(20) NULL,
    [Status] NVARCHAR(20) NULL,
    [CreatedDate] DATETIME NOT NULL,
    [UpdatedDate] DATETIME NULL,
    CONSTRAINT [PK_SRC_CardTransactions] PRIMARY KEY ([CardTransactionID])
);
GO

CREATE TABLE dbo.SRC_LoanPayments (
    [LoanPaymentID] INT NOT NULL,
    [LoanID] INT NULL,
    [PaymentNumber] NVARCHAR(25) NOT NULL,
    [PaymentDate] DATE NULL,
    [PaymentAmount] DECIMAL(18,2) NULL,
    [PrincipalComponent] DECIMAL(18,2) NULL,
    [InterestComponent] DECIMAL(18,2) NULL,
    [PaymentMethod] NVARCHAR(20) NULL,
    [CreatedDate] DATETIME NOT NULL,
    [UpdatedDate] DATETIME NULL,
    CONSTRAINT [PK_SRC_LoanPayments] PRIMARY KEY ([LoanPaymentID])
);
GO
