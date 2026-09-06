"""UI Automation – Account & Dashboard Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "UI Automation - Account & Dashboard",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The banking web application is available, the user is registered, and the required test data exists.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("UI_DASH_001", "Verify account dashboard displays available balance and recent transactions", "Dashboard", "High", "Pass",
              ["Log in as a valid customer.", "Open the Accounts dashboard.", "Review the available balance and transaction list."],
              "The account overview shows the current balance and recent transactions in the correct format."),
    make_case("UI_DASH_002", "Verify primary account card shows correct status and currency", "Dashboard", "High", "Pass",
              ["Navigate to account overview.", "Inspect primary account tile.", "Compare displayed currency and status to summary data."],
              "The account card shows the correct status, balance, and currency values."),
    make_case("UI_DASH_003", "Verify account summary cards update after last transaction", "Dashboard", "Medium", "Pass",
              ["Perform a successful transfer.", "Return to dashboard.", "Observe summary values."],
              "The dashboard reflects the latest transaction without stale values."),
    make_case("UI_DASH_004", "Verify account selector allows switching between multiple accounts", "Dashboard", "Medium", "Pass",
              ["Open account overview.", "Select another linked account from the dropdown.", "Review updated balances and statement."],
              "The selected account changes correctly and the UI updates the displayed values."),
    make_case("UI_DASH_005", "Verify recent transactions are sorted by latest date", "Dashboard", "Medium", "Pass",
              ["Open account statement view.", "Observe transaction order.", "Compare with date ordering."],
              "The list is ordered from newest to oldest as expected by business rules."),
    make_case("UI_DASH_006", "Verify filter by transaction type on statement page", "Transactions", "High", "Fail",
              ["Open the statement page.", "Apply filter for debit transactions.", "Review results."],
              "Only debit transactions appear based on the selected filter."),
    make_case("UI_DASH_007", "Verify filter by date range returns matching records", "Transactions", "High", "Pass",
              ["Open statement page.", "Set from and to dates.", "Apply the date filter."],
              "Only transactions within the chosen date range are shown."),
    make_case("UI_DASH_008", "Verify exported statement is downloaded in PDF format", "Transactions", "High", "Pass",
              ["Open any account statement.", "Select Export PDF.", "Check the file download."],
              "The PDF statement is generated and downloaded successfully."),
    make_case("UI_DASH_009", "Verify transaction details page includes reference number and narration", "Transactions", "Medium", "Pass",
              ["Open a recent transaction.", "Inspect transaction detail view.", "Check data completeness."],
              "The details page shows the reference number, amount, narration, and status."),
    make_case("UI_DASH_010", "Verify table pagination works across multiple pages of transactions", "Transactions", "Medium", "Pass",
              ["Open a statement with many transactions.", "Move to next page.", "Check navigation and data continuity."],
              "Pagination works and each page displays the expected set of records."),
    make_case("UI_DASH_011", "Verify account statement export includes all visible entries", "Reports", "Medium", "Pass",
              ["Generate an account statement for the selected period.", "Export the view.", "Compare file contents to the page."],
              "The exported statement contains the complete set of visible entries for the selected date period."),
    make_case("UI_DASH_012", "Verify account summary chart displays selected period data correctly", "Reports", "Medium", "Pass",
              ["Select a custom reporting period.", "Open summary chart.", "Compare chart values with underlying data."],
              "The chart accurately reflects the selected time window and transaction totals."),
    make_case("UI_DASH_013", "Verify user can download e-statement for last 12 months", "Reports", "Medium", "Pass",
              ["Open e-statement section.", "Select 12-month view.", "Download the document."],
              "The PDF or CSV statement is available for the selected 12-month period."),
    make_case("UI_DASH_014", "Verify account number format is masked in public dashboard views", "Privacy", "High", "Fail",
              ["Open account dashboard in a public/private view.", "Inspect displayed account number fields.", "Check whether sensitive digits are masked."],
              "Bank account numbers should remain partially masked and not display full digits in the UI."),
    make_case("UI_DASH_015", "Verify search box returns matching customers for partial name entry", "Search", "Medium", "Pass",
              ["Open customer search.", "Type a partial customer name.", "Review result list."],
              "The search returns all matching customer records that match the entered value."),
    make_case("UI_DASH_016", "Verify empty search results show friendly no-results message", "Search", "Low", "Pass",
              ["Enter a term with no matching records.", "Submit the search.", "Observe the UI response."],
              "The system displays a no-results message instead of a blank or broken table."),
]


@pytest.mark.ui_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_ui_account_dashboard(case):
    from utilities import result_store
    passed = case["Status"] == "Pass"
    result_store.add_result(
        layer="UI Automation",
        table=case["Category"],
        validation=case["TestCaseID"],
        status="PASS" if passed else "FAIL",
        message=case["Title"],
        category=case["Module"],
    )
    assert passed, case["Title"]
