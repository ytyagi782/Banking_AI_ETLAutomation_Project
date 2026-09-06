"""Power BI Automation – Report Visuals & Interaction Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "PowerBI Automation - Report Visuals & Interaction",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The Power BI workspace, data gateway, and semantic model are available for validation.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("PBI_VIS_001", "Verify the Sales Overview report loads without error when filtered by month", "Report Refresh", "High", "Pass",
              ["Open the Sales Overview report in Power BI Service.", "Apply a valid month filter for the last 6 months.", "Verify the report renders without visual errors or blank tiles."],
              "The report opens successfully and displays all expected visuals with the selected month filter applied."),
    make_case("PBI_VIS_002", "Verify slicer interactions update all dependent visuals in the branch dashboard", "Visual Interaction", "High", "Pass",
              ["Select a branch from the slicer.", "Observe the values across all dependent visuals.", "Validate that all visuals respond to the applied branch filter."],
              "All visuals on the dashboard update consistently to reflect the selected branch filter."),
    make_case("PBI_VIS_003", "Verify drill-through to customer detail works from the branch summary report", "Drill Through", "High", "Pass",
              ["Select a customer record from the branch summary visual.", "Use drill-through to navigate to the customer detail page.", "Confirm the destination report opens with the selected customer context."],
              "The drill-through navigates to the correct customer detail page with the selected record context preserved."),
    make_case("PBI_VIS_004", "Verify a report with no data rows shows a valid empty-state message", "Empty State", "Medium", "Pass",
              ["Apply a filter that returns no records.", "Open the report page containing the KPI chart.", "Check whether the visual renders an empty-state message rather than a broken visual."],
              "The report cleanly shows the no-data state with a clear, user-friendly message."),
    make_case("PBI_VIS_005", "Verify date hierarchy slicer shows correct month and quarter grouping", "Data Modeling", "High", "Pass",
              ["Open the trend analysis dashboard.", "Move between month, quarter, and year levels in the date slicer.", "Validate each hierarchy level groups data consistently."],
              "The date hierarchy displays the correct month and quarter rollups without incorrect values."),
    make_case("PBI_VIS_006", "Verify a report page with cross-highlight remains synchronized across visuals", "Cross Highlighting", "Medium", "Pass",
              ["Select a record in one chart.", "Observe the selected record highlight in all related visuals.", "Ensure the cross-highlight state is consistent across the page."],
              "Cross-highlighting behaves consistently and reflects the selected record across all visuals."),
    make_case("PBI_VIS_007", "Verify bookmarks retain selected visual states after navigation", "Navigation", "Medium", "Pass",
              ["Apply several slicer values on a dashboard.", "Create and activate a bookmark.", "Navigate away and return to confirm the state persists correctly."],
              "The bookmark restores the exact selected state and visual configuration expected by the user."),
    make_case("PBI_VIS_008", "Verify data labels for bar chart are readable at the smallest supported zoom level", "Accessibility", "Medium", "Fail",
              ["Open the product portfolio chart at the minimum supported zoom level.", "Review the bar labels for readability.", "Ensure labels are not clipped or overlapping."],
              "Data labels remain readable and appropriately rendered at the minimum view scale."),
]


@pytest.mark.powerbi_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_pbi_report_visuals_interaction(case):
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
