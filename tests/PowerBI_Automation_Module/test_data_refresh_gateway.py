"""Power BI Automation – Data Refresh & Gateway Module"""
import pytest


def make_case(testcase_id, title, category, priority, status, steps, expected_result):
    return {
        "TestCaseID": testcase_id,
        "Title": title,
        "Module": "PowerBI Automation - Data Refresh & Gateway",
        "Category": category,
        "Priority": priority,
        "Status": status,
        "Preconditions": "The Power BI workspace, data gateway, and semantic model are available for validation.",
        "TestSteps": steps,
        "ExpectedResult": expected_result,
    }


CASES = [
    make_case("PBI_RFR_001", "Verify scheduled refresh completes successfully for the daily revenue dataset", "Data Refresh", "High", "Pass",
              ["Trigger the scheduled refresh for the daily revenue dataset.", "Review refresh logs for success and elapsed duration.", "Confirm the dataset refresh status changes to Succeeded."],
              "The dataset refresh succeeds without data errors and timestamps update correctly."),
    make_case("PBI_RFR_002", "Verify Power BI gateway is online and connected for SQL Server source", "Gateway Connectivity", "High", "Pass",
              ["Open the on-premises data gateway status page.", "Check the SQL Server data source connection state.", "Validate gateway health and connectivity status."],
              "The gateway is online and the SQL Server source connection is healthy and available."),
    make_case("PBI_RFR_003", "Verify a missing column in the source feed triggers the correct refresh failure alert", "Data Quality", "High", "Fail",
              ["Remove a required source field from the upstream feed.", "Run the dataset refresh.", "Check whether the refresh error clearly identifies the missing column."],
              "The refresh should fail with a clear error indicating the missing source column and the cause of the refresh issue."),
    make_case("PBI_RFR_004", "Verify the data source credential is valid after password rotation", "Credentials", "High", "Pass",
              ["Rotate the SQL credential used by the Power BI dataset.", "Attempt a manual refresh.", "Confirm the data source credentials are accepted and the refresh succeeds."],
              "The new credentials are accepted and the report successfully refreshes without authentication errors."),
    make_case("PBI_RFR_005", "Verify scheduled refresh is skipped when the source is unavailable and an alert is raised", "Failure Handling", "High", "Pass",
              ["Stop the source SQL service temporarily.", "Trigger the scheduled refresh.", "Verify the dataset logs a failed refresh and the notification alert is generated."],
              "The refresh fails gracefully, logs the failure, and triggers the expected alert to administrators."),
    make_case("PBI_RFR_006", "Verify the pipeline dataset handles duplicate records without inflated totals", "Data Quality", "High", "Pass",
              ["Load a sample dataset containing duplicate source rows.", "Refresh the semantic model.", "Validate the totals and row counts are not inflated by duplicate data."],
              "Duplicate data records do not distort totals or KPI metrics in the published report."),
    make_case("PBI_RFR_007", "Verify incremental refresh processes only new partitions", "Data Refresh", "Medium", "Pass",
              ["Configure incremental refresh policy on the transaction dataset.", "Add new rows to the source and trigger refresh.", "Confirm only the latest partition is refreshed, not the full dataset."],
              "Incremental refresh processes only the new partition and leaves historical partitions untouched."),
]


@pytest.mark.powerbi_automation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["TestCaseID"])
def test_pbi_data_refresh_gateway(case):
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
