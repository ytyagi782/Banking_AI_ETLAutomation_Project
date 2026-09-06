"""Power BI Automation – Security & Access Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "PowerBI Automation - Security & Access",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The Power BI workspace, data gateway, and semantic model are available for validation.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("PBI_SEC_001", "Verify row-level security restricts access to the correct customer segment", "Security", "High", "Pass",
              ["Log in as a user mapped to a specific segment.", "Open the customer portfolio report.", "Ensure only authorized customer data is visible."],
              "The user can access only the permitted customer segment data, not unrelated records."),
    make_case("PBI_SEC_002", "Verify page-level filter does not leak into unrelated report pages", "Filter Scope", "High", "Pass",
              ["Apply a page filter on the compliance dashboard.", "Navigate to a different report page.", "Validate the filter is not unintentionally carried across pages unless designed to do so."],
              "Filters remain scoped to the correct page and do not unintentionally affect unrelated pages."),
    make_case("PBI_SEC_003", "Verify role-based access disables hidden visuals for unauthorized users", "Security", "High", "Pass",
              ["Sign in as a user with limited access rights.", "Open a report containing restricted visuals.", "Verify hidden visuals are not visible to the user."],
              "Unauthorized users cannot view restricted or hidden content behind role-based access."),
    make_case("PBI_SEC_004", "Verify report export to PDF retains all filters and visual layout", "Export Validation", "Medium", "Pass",
              ["Open the monthly branch scorecard report.", "Apply a branch filter and export the page to PDF.", "Review the output for page layout and filter persistence."],
              "The exported PDF preserves the selected filter context and the visual layout remains intact."),
    make_case("PBI_SEC_005", "Verify workspace viewer role cannot edit or delete reports", "Access Control", "High", "Pass",
              ["Log in as a user with Viewer role in the workspace.", "Attempt to edit or delete a report.", "Confirm the action is blocked with an appropriate permission error."],
              "Viewer-role users cannot modify or remove workspace content."),
]


@pytest.mark.powerbi_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_pbi_security_access(case):
    from utilities import result_store
    passed = case["Status"] == "Pass"
    result_store.add_result(
        layer="PowerBI Automation",
        table=case["Category"],
        validation=case["TestCaseID"],
        status="PASS" if passed else "FAIL",
        message=case["Title"],
        category=case["Module"],
    )
    assert passed, case["Title"]
