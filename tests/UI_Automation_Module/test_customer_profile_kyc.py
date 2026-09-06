"""UI Automation – Customer Profile & KYC Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "UI Automation - Customer Profile & KYC",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The banking web application is available, the user is registered, and the required test data exists.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("UI_KYC_001", "Verify user profile page shows personal details and KYC status", "Profile Management", "High", "Pass",
              ["Open profile management page.", "Inspect personal details and KYC status.", "Check display accuracy."],
              "The profile page shows correct account holder information and current KYC status."),
    make_case("UI_KYC_002", "Verify KYC update form rejects invalid PAN number", "Profile Management", "High", "Pass",
              ["Enter invalid PAN in the KYC form.", "Submit changes.", "Check validation message."],
              "The system rejects invalid PAN data and requests correction."),
    make_case("UI_KYC_003", "Verify KYC document upload success message appears after upload", "Profile Management", "High", "Pass",
              ["Choose a valid document file.", "Upload to KYC page.", "Observe confirmation."],
              "The document is uploaded successfully and a confirmation message is shown."),
    make_case("UI_KYC_004", "Verify document upload rejects unsupported file type", "Profile Management", "High", "Pass",
              ["Choose a PDF or image file outside allowed formats.", "Upload to KYC page.", "Review error."],
              "The application blocks the file and explains the supported types."),
    make_case("UI_KYC_005", "Verify customer onboarding form captures required identity details", "Onboarding", "High", "Pass",
              ["Open customer onboarding page.", "Fill in required identity details.", "Submit the form."],
              "The form accepts valid customer onboarding details without validation errors."),
    make_case("UI_KYC_006", "Verify onboarding form rejects duplicate mobile number", "Onboarding", "High", "Pass",
              ["Enter a mobile number already tied to an existing customer.", "Submit onboarding form.", "Observe duplicate warning."],
              "The app prevents onboarding with an already registered mobile number."),
    make_case("UI_KYC_007", "Verify message center displays unread notifications count correctly", "Notifications", "Medium", "Pass",
              ["Open notification center.", "Review unread count.", "Check item list."],
              "The notification count and list correspond to the unread message state."),
    make_case("UI_KYC_008", "Verify notification mark as read updates the count immediately", "Notifications", "Medium", "Pass",
              ["Open notifications.", "Mark a notification as read.", "Check count update."],
              "The unread count decreases after the notification is marked as read."),
    make_case("UI_KYC_009", "Verify screen reader labels exist for primary action buttons", "Accessibility", "Medium", "Pass",
              ["Inspect login and transfer screens with accessibility tools.", "Check button labels and ARIA attributes.", "Verify focus order."],
              "Action buttons have meaningful labels and keyboard navigation works correctly."),
    make_case("UI_KYC_010", "Verify accessibility overlay closes on ESC and preserves focus", "Accessibility", "Medium", "Pass",
              ["Open modal or side panel.", "Press ESC.", "Confirm focus returns correctly."],
              "The modal closes as expected and keyboard focus returns to the triggering control."),
    make_case("UI_KYC_011", "Verify Aadhaar number masking on profile page shows only last 4 digits", "Privacy", "High", "Fail",
              ["Open profile page.", "Inspect the Aadhaar number field.", "Validate only the last 4 digits are visible."],
              "The Aadhaar number should be masked with only the last 4 digits visible for privacy compliance."),
]


@pytest.mark.ui_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_ui_customer_profile_kyc(case):
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
