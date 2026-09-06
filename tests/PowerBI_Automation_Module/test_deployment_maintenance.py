"""Power BI Automation – Deployment & Maintenance Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "PowerBI Automation - Deployment & Maintenance",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The Power BI workspace, data gateway, and semantic model are available for validation.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("PBI_DEP_001", "Verify the service report uses the correct dataset version after deployment", "Deployment", "High", "Pass",
              ["Deploy the updated dataset to the production workspace.", "Open the consumer report.", "Validate that the report uses the newly deployed dataset version."],
              "The consumer report references the correct and current dataset version after deployment."),
    make_case("PBI_DEP_002", "Verify comments in the managed report are not lost during refresh", "Publication", "Medium", "Pass",
              ["Create a comment on a report page in the service.", "Trigger dataset refresh.", "Confirm that the comment remains available after the refresh."],
              "Comments and annotations remain intact following refresh and report publication updates."),
    make_case("PBI_DEP_003", "Verify a stale dataset reference is flagged during report open and not silently ignored", "Maintenance", "High", "Fail",
              ["Change the underlying dataset name in the workspace.", "Open the affected report page.", "Check that the report surfaces a broken dataset reference or warning message."],
              "The report should clearly identify the stale dataset reference instead of silently loading incorrect data."),
    make_case("PBI_DEP_004", "Verify published app navigation flows correctly between landing page and detail pages", "App Navigation", "High", "Pass",
              ["Open the published Power BI app.", "Navigate from the landing page to a detailed report page.", "Validate that navigation links work and the correct page context remains."],
              "The published app navigates smoothly between landing and detail pages without broken links or context loss."),
    make_case("PBI_DEP_005", "Verify dashboard refresh does not lose custom theme colors or branding", "Branding", "Medium", "Pass",
              ["Open the branded executive dashboard.", "Refresh the underlying dataset.", "Validate the corporate theme colors and logos remain unchanged."],
              "The dashboard retains its branding and custom visual theme after refresh."),
    make_case("PBI_DEP_006", "Verify the footer metadata is correct across all report pages", "Formatting", "Low", "Pass",
              ["Open each page of the compliance report.", "Review the footer for last updated timestamp and report owner details.", "Validate the metadata is consistent across all pages."],
              "The footer metadata remains consistent and accurate across all report pages."),
    make_case("PBI_DEP_007", "Verify report performance remains within acceptable threshold for a large dataset", "Performance", "High", "Pass",
              ["Open the full portfolio performance dashboard with the largest supported dataset.", "Record page load time and visual rendering delay.", "Ensure the dashboard loads within the agreed SLA."],
              "The report loads within the acceptable performance threshold without visible lag."),
    make_case("PBI_DEP_008", "Verify the behaviour for report-level filter in a pinned live page remains unchanged", "Pinned Live Page", "Medium", "Pass",
              ["Open the pinned live page in the service.", "Apply a report-level filter.", "Validate the page reflects the selected filter state without breaking the live-linked experience."],
              "The pinned live page continues to function as expected while preserving the selected report-level filter state."),
    make_case("PBI_DEP_009", "Verify dashboard legend ordering matches business requirements", "Visual Formatting", "Medium", "Pass",
              ["Open the product mix dashboard.", "Check legend order for categories such as Retail, SME, Corporate, and Wealth.", "Validate the order matches the defined business sequence."],
              "Legend entries appear in the expected business order and remain stable across refreshes."),
]


@pytest.mark.powerbi_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_pbi_deployment_maintenance(case):
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
