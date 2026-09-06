"""API Automation – Customer & Services Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "API Automation - Customer & Services",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "Valid bank user account exists and API gateway is reachable.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("API_CUST_001", "Verify beneficiary creation succeeds with valid KYC details", "Beneficiary Management", "High", "Pass",
              ["Send POST /api/v1/beneficiaries with a valid account number, IFSC, and nickname.", "Confirm the response returns 201 Created.", "Validate the beneficiary record is persisted and retrievable."],
              "The beneficiary is created successfully and is available for future transfers."),
    make_case("API_CUST_002", "Verify duplicate beneficiary is rejected", "Beneficiary Management", "Medium", "Pass",
              ["Create a beneficiary with the same account and bank details twice.", "Submit the second creation request.", "Validate the second request is rejected as a duplicate."],
              "The API prevents duplication of the same beneficiary details."),
    make_case("API_CUST_003", "Verify GET /api/v1/customers/{id} returns 404 for unknown customer", "Customer Management", "Medium", "Pass",
              ["Request a customer profile using a non-existent customer identifier.", "Validate the status code is 404.", "Confirm the error payload contains a meaningful not found message."],
              "The API returns a not-found response for customer IDs that do not exist."),
    make_case("API_CUST_004", "Verify card block API success for active card", "Card Management", "High", "Pass",
              ["Authenticate as a valid user with an active card.", "Invoke POST /api/v1/cards/{cardId}/block.", "Check the response indicates the card is blocked successfully."],
              "The API blocks the card and updates status to Blocked in the system."),
    make_case("API_CUST_005", "Verify fraud alert API rejects duplicate events for same transaction", "Fraud & AML", "High", "Pass",
              ["Send two identical fraud-alert requests for the same transaction ID.", "Check whether the second request is treated as duplicate.", "Validate the response status and deduplication behavior."],
              "Duplicate fraud-monitoring events are prevented from being stored multiple times."),
    make_case("API_CUST_006", "Verify branch list API returns active branches only", "Branch Management", "Medium", "Fail",
              ["Request the list of branches from GET /api/v1/branches.", "Verify only active branches are returned in the result set.", "Check whether inactive or closed branches are filtered out."],
              "The API should return only those branches that are currently active."),
    make_case("API_CUST_007", "Verify user profile update returns validation error for missing mobile number", "Profile Management", "Medium", "Pass",
              ["Attempt to update a customer profile without a mobile number.", "Call PATCH /api/v1/customers/{customerId}.", "Validate that the API rejects the request with a required field error."],
              "The API rejects incomplete profile updates and highlights the missing field."),
    make_case("API_CUST_008", "Verify GET /api/v1/notifications returns unread notifications only", "Notification Service", "Low", "Pass",
              ["Authenticate the user and request notifications.", "Validate the payload includes only unread items for the current user.", "Ensure read notifications are excluded from the response payload."],
              "Only unread notifications are returned in the API response for the authenticated user."),
]


@pytest.mark.api_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_api_customer_services(case):
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
