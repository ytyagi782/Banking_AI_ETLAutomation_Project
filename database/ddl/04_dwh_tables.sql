-- ====================================================================
-- NEW ENTITIES - DWH tables (Dim Type1/Type2 + Fact)
-- database: Bank_DWH
-- ====================================================================

USE [Bank_DWH];
GO

CREATE TABLE dbo.DimEmployee_Type2 (
    [EmployeeSK] INT IDENTITY(1,1) NOT NULL,
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
    [EffectiveDate] DATE NOT NULL,
    [ExpiryDate] DATE NULL,
    [IsCurrent] BIT NOT NULL,
    [CreatedDate] DATETIME NOT NULL,
    CONSTRAINT [PK_DimEmployee_Type2] PRIMARY KEY ([EmployeeSK])
);
GO

CREATE TABLE dbo.DimLoan_Type2 (
    [LoanSK] INT IDENTITY(1,1) NOT NULL,
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
    [EffectiveDate] DATE NOT NULL,
    [ExpiryDate] DATE NULL,
    [IsCurrent] BIT NOT NULL,
    [CreatedDate] DATETIME NOT NULL,
    CONSTRAINT [PK_DimLoan_Type2] PRIMARY KEY ([LoanSK])
);
GO

CREATE TABLE dbo.DimCard_Type1 (
    [CardSK] INT IDENTITY(1,1) NOT NULL,
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
    CONSTRAINT [PK_DimCard_Type1] PRIMARY KEY ([CardSK])
);
GO

CREATE TABLE dbo.DimMerchant_Type1 (
    [MerchantSK] INT IDENTITY(1,1) NOT NULL,
    [MerchantID] INT NOT NULL,
    [MerchantCode] NVARCHAR(20) NOT NULL,
    [MerchantName] NVARCHAR(100) NULL,
    [Category] NVARCHAR(50) NULL,
    [City] NVARCHAR(50) NULL,
    [Country] NVARCHAR(50) NULL,
    [Status] NVARCHAR(20) NULL,
    [CreatedDate] DATETIME NOT NULL,
    [UpdatedDate] DATETIME NULL,
    CONSTRAINT [PK_DimMerchant_Type1] PRIMARY KEY ([MerchantSK])
);
GO

CREATE TABLE dbo.FactCardTransaction (
    [CardTransactionSK] INT IDENTITY(1,1) NOT NULL,
    [CardTransactionID] INT NOT NULL,
    [CardTxnNumber] NVARCHAR(25) NOT NULL,
    [TxnDate] DATETIME NULL,
    [Amount] DECIMAL(18,2) NULL,
    [CurrencyCode] NVARCHAR(3) NULL,
    [TxnType] NVARCHAR(20) NULL,
    [Status] NVARCHAR(20) NULL,
    [CardSK] INT NULL,
    [MerchantSK] INT NULL,
    [CreatedDate] DATETIME NOT NULL,
    CONSTRAINT [PK_FactCardTransaction] PRIMARY KEY ([CardTransactionSK])
);
GO

CREATE TABLE dbo.FactLoanPayment (
    [LoanPaymentSK] INT IDENTITY(1,1) NOT NULL,
    [LoanPaymentID] INT NOT NULL,
    [PaymentNumber] NVARCHAR(25) NOT NULL,
    [PaymentDate] DATE NULL,
    [PaymentAmount] DECIMAL(18,2) NULL,
    [PrincipalComponent] DECIMAL(18,2) NULL,
    [InterestComponent] DECIMAL(18,2) NULL,
    [PaymentMethod] NVARCHAR(20) NULL,
    [LoanSK] INT NULL,
    [CreatedDate] DATETIME NOT NULL,
    CONSTRAINT [PK_FactLoanPayment] PRIMARY KEY ([LoanPaymentSK])
);
GO
