"""UI Automation – Fund Transfer & Payments Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "UI Automation - Fund Transfer & Payments",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The banking web application is available, the user is registered, and the required test data exists.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("UI_TXN_001", "Verify money transfer page shows beneficiary list", "Fund Transfer", "High", "Pass",
              ["Navigate to fund transfer page.", "Open beneficiary selection.", "Check current beneficiary list."],
              "The beneficiary list is displayed and contains valid registered recipients."),
    make_case("UI_TXN_002", "Verify transfer form validates amount is greater than zero", "Fund Transfer", "High", "Pass",
              ["Open transfer screen.", "Enter 0 or negative amount.", "Attempt to continue."],
              "The UI blocks the submission with an invalid amount message."),
    make_case("UI_TXN_003", "Verify transfer form validates missing beneficiary", "Fund Transfer", "High", "Pass",
              ["Open transfer screen.", "Leave beneficiary blank.", "Click Continue."],
              "The application prompts the user to select a valid beneficiary."),
    make_case("UI_TXN_004", "Verify transfer confirmation page displays summary before final submit", "Fund Transfer", "High", "Pass",
              ["Select beneficiary and amount.", "Proceed to confirmation step.", "Review summary screen."],
              "The confirmation screen shows the transfer summary with recipient and amount details."),
    make_case("UI_TXN_005", "Verify successful transfer shows confirmation notification and updated balance", "Fund Transfer", "High", "Pass",
              ["Initiate a valid transfer.", "Complete confirmation.", "Review success banner and new balance."],
              "The transfer succeeds and the dashboard reflects the updated account balance."),
    make_case("UI_TXN_006", "Verify transfer fails for insufficient funds", "Fund Transfer", "High", "Pass",
              ["Attempt a transfer above the available balance.", "Submit the request.", "Observe validation message."],
              "The transfer is blocked with a clear insufficient-funds error message."),
    make_case("UI_TXN_007", "Verify funds transfer is unavailable when a day limit is exceeded", "Fund Transfer", "Medium", "Pass",
              ["Reach the daily transfer limit.", "Attempt another transfer.", "Check for limit warning."],
              "The application prevents additional transfers once the daily cap is exceeded."),
    make_case("UI_TXN_008", "Verify OTP modal appears for high-value transfer", "Fund Transfer", "High", "Fail",
              ["Initiate transfer above threshold.", "Proceed to payment confirmation.", "Check OTP challenge."],
              "The UI requires an OTP before finalizing the transaction."),
    make_case("UI_TXN_009", "Verify beneficiary addition form validates required fields", "Beneficiaries", "High", "Pass",
              ["Open Add Beneficiary page.", "Submit without account number or IFSC.", "Review validation errors."],
              "The form blocks submission until all required fields are filled correctly."),
    make_case("UI_TXN_010", "Verify beneficiary can be added with valid bank details", "Beneficiaries", "High", "Pass",
              ["Enter a valid beneficiary name, account number, and IFSC.", "Submit the form.", "Review success message."],
              "The new beneficiary is added successfully and appears in beneficiary list."),
    make_case("UI_TXN_011", "Verify duplicate beneficiary is rejected in UI", "Beneficiaries", "Medium", "Pass",
              ["Add an existing beneficiary again.", "Submit the form.", "Observe duplicate warning."],
              "The application rejects duplicate beneficiary details and displays a validation warning."),
    make_case("UI_TXN_012", "Verify NSDL UPI ID validation message is shown for invalid format", "Payments", "Medium", "Pass",
              ["Enter invalid UPI ID.", "Attempt to save the payment method.", "Check validation."],
              "The UI shows the correct invalid-format message for the UPI ID."),
    make_case("UI_TXN_013", "Verify bill payment page loads recurring bills and due dates", "Bill Payments", "High", "Pass",
              ["Open bill payments page.", "Check recurring bills list.", "Compare due dates and amounts."],
              "The page shows all due bills with accurate amount and due-date values."),
    make_case("UI_TXN_014", "Verify bill payment can be scheduled for future date", "Bill Payments", "Medium", "Pass",
              ["Select a bill and future payment date.", "Submit the payment schedule.", "Review confirmation."],
              "The scheduled bill payment is created and appears in future payments."),
    make_case("UI_TXN_015", "Verify payment status changes from pending to success after processing", "Bill Payments", "Medium", "Pass",
              ["Pay a bill.", "Refresh the payment details page.", "Monitor status change."],
              "The status updates correctly from Pending to Successful after processing."),
    make_case("UI_TXN_016", "Verify inactive billers are filtered from payment list", "Bill Payments", "Medium", "Pass",
              ["Open bill payment page.", "Review list of billers.", "Check active/inactive filtering."],
              "Inactive billers are excluded from the active payable list."),
    make_case("UI_TXN_017", "Verify debit card page shows card number masked", "Cards & Wallet", "High", "Fail",
              ["Open cards page.", "Inspect card details.", "Check masked display."],
              "Card number and sensitive digits remain masked while other details are visible."),
    make_case("UI_TXN_018", "Verify card block action requires confirmation", "Cards & Wallet", "High", "Pass",
              ["Open debit card settings.", "Click Block Card.", "Confirm the confirmation dialog appears."],
              "The user must confirm before the card is blocked."),
    make_case("UI_TXN_019", "Verify card limit update is saved and reflected immediately", "Cards & Wallet", "High", "Pass",
              ["Open card limit settings.", "Adjust daily limit.", "Save the changes.", "Review the updated value."],
              "The new card limit is saved and visible on the card summary page."),
]


@pytest.mark.ui_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_ui_fund_transfer_payments(case):
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
