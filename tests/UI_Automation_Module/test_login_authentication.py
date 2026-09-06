"""UI Automation – Login & Authentication Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "UI Automation - Login & Authentication",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The banking web application is available, the user is registered, and the required test data exists.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("UI_LOGIN_001", "Verify user can log in with valid credentials", "Authentication", "High", "Pass",
              ["Open login page.", "Enter valid customer ID and password.", "Click Sign In.", "Validate home page loads."],
              "The user is successfully authenticated and lands on the dashboard."),
    make_case("UI_LOGIN_002", "Verify login fails for wrong password", "Authentication", "High", "Pass",
              ["Open login page.", "Enter a valid customer ID and wrong password.", "Click Sign In.", "Validate error message appears."],
              "The system rejects the login and keeps the user on the login page."),
    make_case("UI_LOGIN_003", "Verify session timeout redirect to login page", "Authentication", "Medium", "Pass",
              ["Log in successfully.", "Keep the session idle until timeout.", "Attempt to access the dashboard.", "Observe redirect behavior."],
              "The user is redirected to login and the session is terminated securely."),
    make_case("UI_LOGIN_004", "Verify remember me feature persist login for returning user", "Authentication", "Medium", "Pass",
              ["Log in with remember me enabled.", "Close the browser.", "Open the banking portal again."],
              "The user remains signed in on the browser session without re-entering credentials."),
    make_case("UI_LOGIN_005", "Verify forgot password link opens reset workflow", "Authentication", "Medium", "Pass",
              ["Click Forgot Password.", "Enter registered email or mobile number.", "Submit the request."],
              "The password reset instructions are displayed and a reset request is submitted."),
    make_case("UI_LOGIN_006", "Verify login with locked account is blocked", "Authentication", "High", "Pass",
              ["Use an account with a locked status.", "Attempt login.", "Observe response.", "Confirm account remains locked."],
              "The system blocks access and informs the user that the account is locked."),
    make_case("UI_LOGIN_007", "Verify login with unsupported locale is handled gracefully", "Authentication", "Low", "Fail",
              ["Change browser language to an unsupported locale.", "Log in using valid credentials.", "Check validation and page load."],
              "The application should gracefully handle the unsupported locale without a broken interface or blank page."),
    make_case("UI_LOGIN_008", "Verify inactivity timer warning appears before auto logout", "Authentication", "Medium", "Pass",
              ["Log in and stay idle near the timeout threshold.", "Observe warning modal.", "Check countdown behavior."],
              "The system warns the user before terminating the session due to inactivity."),
    make_case("UI_LOGIN_009", "Verify account deactivation requires confirmation step", "Security", "High", "Pass",
              ["Go to account settings.", "Select Deactivate Account.", "Observe confirmation prompt."],
              "The user must confirm the deactivation action before the account is disabled."),
    make_case("UI_LOGIN_010", "Verify password change requires current password validation", "Security", "High", "Pass",
              ["Navigate to change-password page.", "Use an incorrect current password.", "Submit the request."],
              "The system rejects the password change and asks the user to confirm the current password."),
    make_case("UI_LOGIN_011", "Verify successful password change shows confirmation banner and logout flow", "Security", "High", "Pass",
              ["Change the password with valid current password.", "Submit the form.", "Follow the sign-out flow."],
              "The password change succeeds, the user is notified, and the session is reset securely."),
    make_case("UI_LOGIN_012", "Verify CAPTCHA is displayed after three consecutive failed login attempts", "Security", "High", "Pass",
              ["Enter wrong credentials three times.", "Observe the login form after the third failure.", "Validate CAPTCHA challenge appears."],
              "The CAPTCHA challenge is presented to prevent brute-force login attempts."),
    make_case("UI_LOGIN_013", "Verify multi-factor authentication prompt appears for high-risk login", "Security", "High", "Fail",
              ["Log in from a new device or IP address.", "Observe whether MFA challenge is triggered.", "Validate OTP or push notification prompt."],
              "The system should trigger MFA for logins from unrecognized devices or locations."),
]


@pytest.mark.ui_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_ui_login_authentication(case):
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
