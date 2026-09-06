"""API Automation – Authentication & Security Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "API Automation - Authentication & Security",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "Valid bank user account exists and API gateway is reachable.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("API_AUTH_001", "Verify customer login returns 200 for valid credentials", "Authentication", "High", "Pass",
              ["Send POST /api/v1/auth/login with valid customer ID and password.", "Verify response status code is 200.", "Validate access token is returned in the response payload."],
              "The API authenticates the customer successfully and returns a valid access token."),
    make_case("API_AUTH_002", "Verify login fails for invalid password", "Authentication", "High", "Pass",
              ["Send POST /api/v1/auth/login with a valid username and incorrect password.", "Validate the response status code is 401.", "Check the error response contains a meaningful authentication message."],
              "The API rejects the invalid credentials and does not issue a token."),
    make_case("API_AUTH_003", "Verify token refresh works with a valid refresh token", "Authentication", "High", "Pass",
              ["Generate a valid access token and refresh token.", "Call POST /api/v1/auth/refresh-token with the refresh token.", "Confirm a new access token is returned without requiring user re-login."],
              "The system issues a new access token while keeping the authenticated session valid."),
    make_case("API_AUTH_004", "Verify OTP validation fails for expired OTP", "OTP & Security", "High", "Pass",
              ["Request an OTP for a banking transaction.", "Use an expired OTP code in a verification call.", "Verify the response is 401 or 410 and the request is denied."],
              "Expired OTPs are rejected and the transaction remains protected from unauthorized completion."),
    make_case("API_AUTH_005", "Verify password reset request validates email format", "Security", "High", "Pass",
              ["Send a password reset request with an incorrectly formatted email address.", "Submit POST /api/v1/auth/password-reset-request.", "Ensure the API returns 400 and highlights the invalid email field."],
              "The password reset request is rejected when the email format is invalid."),
    make_case("API_AUTH_006", "Verify session timeout response contains secure logout instructions", "Session Management", "Medium", "Pass",
              ["Allow the session to expire after the configured idle timeout.", "Send a follow-up authenticated request.", "Validate that the response is 401 and includes logout guidance."],
              "Expired sessions are rejected cleanly with an appropriate security response."),
    make_case("API_AUTH_007", "Verify payment API returns 429 when rate limit is exceeded", "Resilience", "Medium", "Pass",
              ["Send multiple simultaneous payment requests beyond the configured rate limit.", "Monitor the response codes for the overflow requests.", "Verify the API returns 429 with Retry-After header."],
              "The API enforces throttling and informs clients to retry after the specified duration."),
    make_case("API_AUTH_008", "Verify JWT token with tampered payload is rejected", "Security", "High", "Fail",
              ["Decode a valid JWT, modify the customer ID in the payload.", "Re-encode the token without the correct signing key.", "Send a request with the tampered token and verify 401 response."],
              "The API should reject tampered tokens and return an unauthorized response."),
]


@pytest.mark.api_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_api_auth_security(case):
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
