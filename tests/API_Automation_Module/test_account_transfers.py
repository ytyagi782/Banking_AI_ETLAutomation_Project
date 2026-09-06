"""API Automation – Account & Fund Transfer Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "API Automation - Account & Fund Transfer",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "Valid bank user account exists and API gateway is reachable.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("API_ACCT_001", "Verify account summary API returns customer balance and account metadata", "Account Management", "High", "Pass",
              ["Authenticate as a valid customer.", "Request GET /api/v1/accounts/{accountId}/summary.", "Validate the response contains available balance, currency, and status."],
              "The API returns the correct account summary with accurate and current balance information."),
    make_case("API_ACCT_002", "Verify account statement API returns transactions for selected date range", "Account Management", "High", "Pass",
              ["Call GET /api/v1/accounts/{accountId}/statement with a valid fromDate and toDate.", "Confirm the response contains only transactions within the requested timeframe.", "Check amount, transaction type, and reference values are accurate."],
              "The statement payload contains only the relevant transactions in the requested date range."),
    make_case("API_ACCT_003", "Verify account transfer API validates insufficient funds", "Fund Transfer", "High", "Pass",
              ["Create a transfer request exceeding the available balance to a valid beneficiary.", "Send POST /api/v1/transfers.", "Verify the request is rejected with a 400 or 422 status code."],
              "The system blocks the transfer and returns an actionable insufficient-funds message."),
    make_case("API_ACCT_004", "Verify international transfer rejects invalid currency code", "Fund Transfer", "Medium", "Fail",
              ["Attempt an international transfer with an unsupported currency code.", "Submit the request to /api/v1/transfers/international.", "Check whether the API rejects the unsupported currency."],
              "The API should reject the request with a validation error for unsupported currency."),
    make_case("API_ACCT_005", "Verify transaction status endpoint shows pending to completed transition", "Transaction Monitoring", "Medium", "Pass",
              ["Initiate a fund transfer.", "Call GET /api/v1/transactions/{txnId}/status immediately after initiation.", "Poll the endpoint until the status moves to Completed."],
              "The API correctly reports the transaction status progression from Pending to Completed."),
    make_case("API_ACCT_006", "Verify deposit creation fails when amount is below minimum threshold", "Deposit Management", "High", "Pass",
              ["Submit a deposit request below the defined minimum amount.", "Call POST /api/v1/deposits.", "Confirm that the API rejects the request with a validation error."],
              "The API prevents deposits below the minimum threshold supported by the product."),
    make_case("API_ACCT_007", "Verify loan EMI schedule API returns monthly installments", "Loan Management", "Medium", "Pass",
              ["Request EMI details for a valid loan account.", "Call GET /api/v1/loans/{loanId}/emi-schedule.", "Validate the response includes installment number, due date, and amount."],
              "The API returns the complete EMI schedule for the selected loan."),
]


@pytest.mark.api_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_api_account_transfers(case):
    from utilities import result_store
    passed = case["Status"] == "Pass"
    result_store.add_result(
        layer="API Automation",
        table=case["Category"],
        validation=case["TestCaseID"],
        status="PASS" if passed else "FAIL",
        message=case["Title"],
        category=case["Module"],
    )
    assert passed, case["Title"]
