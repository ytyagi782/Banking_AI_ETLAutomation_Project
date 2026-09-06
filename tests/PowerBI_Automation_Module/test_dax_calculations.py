"""Power BI Automation – DAX & Calculations Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "PowerBI Automation - DAX & Calculations",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The Power BI workspace, data gateway, and semantic model are available for validation.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("PBI_DAX_001", "Verify dashboard tile totals match the underlying semantic model values", "Data Accuracy", "High", "Pass",
              ["Open the executive dashboard in the workspace.", "Read the total revenue tile value.", "Cross-check the value against the underlying semantic model result for the same date slice."],
              "The visual tile value matches the semantic model result accurately without discrepancy."),
    make_case("PBI_DAX_002", "Verify alternate currency conversion values are accurate in the Treasury dashboard", "DAX / Calculations", "High", "Pass",
              ["Open the Treasury dashboard.", "Switch currency context from INR to USD and EUR.", "Cross-check conversion metrics against the approved business rules."],
              "Currency conversion values are calculated accurately for each selected reporting currency."),
    make_case("PBI_DAX_003", "Verify DAX measure for net profit excludes reversed transactions per policy", "DAX / Calculations", "High", "Pass",
              ["Apply the reversal filter to the financial performance report.", "Check the net profit measure.", "Validate that reversed transactions are excluded according to policy."],
              "The net profit measure excludes reversed transactions and reflects policy-compliant values."),
    make_case("PBI_DAX_004", "Verify the KPI card uses the latest date slice and not stale data", "KPI Validation", "High", "Pass",
              ["Open the KPI summary page.", "Change the report date filter to the latest completed month.", "Compare the KPI card value with the corresponding source data."],
              "The KPI card reflects the latest selected date slice and not stale or previously cached data."),
    make_case("PBI_DAX_005", "Verify table sorting by amount descending matches the dataset order", "Sorting", "Medium", "Pass",
              ["Open the transaction summary table.", "Sort by amount in descending order.", "Cross-check that the table order matches the semantic model logic."],
              "The table displays the sorted amount order correctly according to the expected business logic."),
    make_case("PBI_DAX_006", "Verify YoY growth measure handles missing prior-year data gracefully", "DAX / Calculations", "Medium", "Fail",
              ["Open the year-over-year growth report.", "Select a period where prior-year data does not exist.", "Validate the measure shows BLANK or 0% instead of an error."],
              "The YoY growth measure should handle missing prior-year data without producing errors or misleading values."),
]


@pytest.mark.powerbi_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_pbi_dax_calculations(case):
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
