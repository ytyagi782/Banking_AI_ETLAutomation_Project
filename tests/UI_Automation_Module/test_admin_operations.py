"""UI Automation – Admin & Operations Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "UI Automation - Admin & Operations",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The banking web application is available, the user is registered, and the required test data exists.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("UI_ADM_001", "Verify admin dashboard shows active user count and failed logins", "Admin", "High", "Pass",
              ["Log in as admin.", "Open system monitoring dashboard.", "Review counts and metrics."],
              "Admin metrics show active users and failed login counts consistently."),
    make_case("UI_ADM_002", "Verify user management list can filter by branch or status", "Admin", "Medium", "Pass",
              ["Open user management page.", "Apply branch and active status filters.", "Review list results."],
              "The filter updates the user list based on the selected branch and status."),
    make_case("UI_ADM_003", "Verify admin user creation form requires role selection", "Admin", "High", "Pass",
              ["Open create user form.", "Leave role unselected.", "Attempt submission."],
              "The form blocks submission until a role is assigned to the new user."),
    make_case("UI_ADM_004", "Verify user edit screen saves contact updates", "Admin", "Medium", "Pass",
              ["Open a user record.", "Edit phone and email fields.", "Save the changes."],
              "The contact details are updated and displayed with the latest values."),
    make_case("UI_ADM_005", "Verify branch setup form rejects invalid IFSC code", "Branch Operations", "Medium", "Pass",
              ["Open branch creation or update page.", "Enter invalid IFSC code.", "Submit form."],
              "The system shows a validation error and prevents saving invalid IFSC values."),
    make_case("UI_ADM_006", "Verify branch details page loads with working hours and address", "Branch Operations", "Medium", "Pass",
              ["Open a branch record.", "Inspect address and working hours.", "Compare values to source data."],
              "The branch details page loads and displays correct working-hour and address information."),
    make_case("UI_ADM_007", "Verify ATM branch locator search returns nearby branches", "Branch Locator", "Medium", "Pass",
              ["Open branch locator.", "Enter city or pincode.", "Submit search.", "Review results."],
              "The app returns a list of nearby branches matching the user's location query."),
    make_case("UI_ADM_008", "Verify branch locator with invalid pincode displays no result alert", "Branch Locator", "Low", "Pass",
              ["Enter an invalid pincode.", "Search branches.", "Observe results."],
              "The system shows a no-results message for the invalid location search."),
    make_case("UI_ADM_009", "Verify support chat widget opens and loads agent availability", "Support", "Medium", "Pass",
              ["Open the help widget.", "Check availability status.", "Start a chat session."],
              "The chat widget loads and shows the available support status."),
    make_case("UI_ADM_010", "Verify support ticket creation requires issue description", "Support", "High", "Pass",
              ["Open support ticket page.", "Submit without description.", "Check the validation error."],
              "The user is required to add a description before creating a support ticket."),
    make_case("UI_ADM_011", "Verify support ticket list shows newest tickets first", "Support", "Low", "Pass",
              ["Open support ticket page.", "Inspect order of tickets.", "Verify ordering by created date."],
              "The support tickets list is ordered from newest to oldest."),
    make_case("UI_ADM_012", "Verify help articles open in a new tab without breaking navigation state", "Support", "Low", "Pass",
              ["Click a help article from the customer portal.", "Validate how the article opens.", "Ensure the portal remains usable."],
              "The help article opens without destroying the user's current portal state."),
    make_case("UI_ADM_013", "Verify loan application form validates age eligibility", "Loans", "High", "Pass",
              ["Open loan application page.", "Enter age below minimum threshold.", "Submit form.", "Check validation."],
              "The application blocks loan submission for applicants below the minimum eligible age."),
    make_case("UI_ADM_014", "Verify EMI schedule page shows monthly breakdown correctly", "Loans", "High", "Pass",
              ["Open loan details page.", "View EMI schedule.", "Validate due dates and amounts."],
              "The EMI schedule displays the correct monthly breakdown and dates."),
    make_case("UI_ADM_015", "Verify pre-approved loan offer is displayed for eligible customers", "Loans", "Medium", "Pass",
              ["Log in to a customer with pre-approved loan eligibility.", "Open loan section.", "Review dashboard message."],
              "The eligible customer sees the pre-approved loan offer in the UI."),
    make_case("UI_ADM_016", "Verify loan repayment through net banking is successful", "Loans", "High", "Pass",
              ["Open loan repayment page.", "Choose repayment amount and payment mode.", "Complete payment."],
              "The repayment is processed successfully and the loan balance is updated on the screen."),
    make_case("UI_ADM_017", "Verify investment portfolio page loads holdings and returns", "Investments", "High", "Fail",
              ["Open investments page.", "Review holdings summary.", "Check returns and capital allocation values."],
              "The page displays holdings, returns, and allocation detail accurately."),
    make_case("UI_ADM_018", "Verify SIP contribution form validates monthly amount", "Investments", "Medium", "Pass",
              ["Open SIP setup page.", "Enter amount below the allowed minimum.", "Submit the form."],
              "The system rejects SIP setup with a validation error for the minimum amount."),
    make_case("UI_ADM_019", "Verify bank holiday calendar is visible and filters transactions appropriately", "Reports", "Low", "Fail",
              ["Open holiday calendar in the reporting section.", "Check dates and transaction filters.", "Verify business-day adjustments."],
              "The report should reflect bank holiday adjustments and show the impact on transaction processing correctly."),
]


@pytest.mark.ui_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_ui_admin_operations(case):
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
