"""Create an Origination Pipeline Funnel report and add it to the weekly dashboard."""
import json
import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from salesforce import get_access_token, sf_get

API_VERSION = "v62.0"
DOMAIN = os.getenv("SALESFORCE_DOMAIN")
DASHBOARD_ID = "01Z8v0000005jFtEAI"

# Stages to exclude from the funnel
EXCLUDED_STAGES = ["7. Killed", "8. Good opportunity wrong timing"]


def sf_post(endpoint, token, payload):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.post(f"{DOMAIN}/services/data/{API_VERSION}/{endpoint}", headers=headers, json=payload)


def sf_put(endpoint, token, payload):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.put(f"{DOMAIN}/services/data/{API_VERSION}/{endpoint}", headers=headers, json=payload)


def create_funnel_report(token):
    """Create a Summary report on Opportunities grouped by StageName, excluding killed stages."""
    report_metadata = {
        "reportMetadata": {
            "name": "Origination Pipeline Funnel",
            "reportFormat": "SUMMARY",
            "reportType": {"type": "Opportunity"},
            "groupingsDown": [
                {"name": "STAGE_NAME", "sortOrder": "Desc", "dateGranularity": "None"}
            ],
            "aggregates": ["RowCount"],
            "reportBooleanFilter": None,
            "reportFilters": [
                {
                    "column": "STAGE_NAME",
                    "operator": "notEqual",
                    "value": ",".join(EXCLUDED_STAGES),
                    "filterType": "fieldValue",
                    "isRunPageEditable": False
                }
            ],
            "standardDateFilter": {
                "column": "CREATED_DATE",
                "durationValue": "CUSTOM",
                "startDate": None,
                "endDate": None
            },
            "detailColumns": ["OPPORTUNITY_NAME", "CLOSE_DATE"]
        }
    }

    print("Creating report 'Origination Pipeline Funnel'...")
    resp = sf_post("analytics/reports", token, report_metadata)

    if resp.status_code in (200, 201):
        result = resp.json()
        report_id = result.get("reportMetadata", {}).get("id")
        print(f"  Report created: {report_id}")
        return report_id
    else:
        print(f"  Failed to create report: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        return None


def add_funnel_to_dashboard(token, report_id):
    """Add the funnel report as a horizontal bar chart component to the dashboard."""
    # Use backup to avoid triggering a dashboard refresh (rate limited)
    backup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "origination_dashboard_backup.json")
    if os.path.exists(backup_path):
        print(f"\nLoading dashboard from backup (to avoid refresh rate limit)...")
        with open(backup_path) as f:
            detail = json.load(f)
    else:
        print(f"\nFetching dashboard {DASHBOARD_ID}...")
        detail = sf_get(f"analytics/dashboards/{DASHBOARD_ID}", token)
    meta = detail.get("dashboardMetadata", {})

    components = meta.get("components", [])
    layout = meta.get("layout", {})
    layout_components = layout.get("components", [])
    print(f"  Current components: {len(components)}, layout entries: {len(layout_components)}")

    # Find the max row used so we can place the new component below everything
    max_row_end = 0
    for lc in layout_components:
        row_end = lc.get("row", 0) + lc.get("rowspan", 0)
        if row_end > max_row_end:
            max_row_end = row_end
    print(f"  Layout grid ends at row {max_row_end}")

    # Build new funnel component (matching existing component schema)
    new_component = {
        "reportId": report_id,
        "type": "Report",
        "header": "Origination Pipeline Funnel (All-Time)",
        "footer": None,
        "title": None,
        "chartTheme": None,
        "properties": {
            "aggregates": [{"name": "RowCount"}],
            "autoSelectColumns": False,
            "drillUrl": None,
            "filterColumns": [],
            "groupings": [
                {
                    "name": "STAGE_NAME",
                    "sortOrder": "Desc",
                    "sortAggregate": None,
                    "inheritedReportSort": None
                }
            ],
            "maxRows": None,
            "reportFormat": "SUMMARY",
            "sort": None,
            "useReportChart": False,
            "visualizationType": "Bar",
            "visualizationProperties": {
                "aggregateVisualizationInfos": [
                    {"axis": "Y", "visualizationType": "Bar"}
                ],
                "axisRange": {"max": None, "min": None, "rangeType": "auto"},
                "decimalPrecision": -1,
                "displayUnits": "auto",
                "groupByType": "grouped",
                "legendPosition": "Bottom",
                "showValues": True
            }
        }
    }

    # Append component
    components.append(new_component)
    meta["components"] = components

    # Append layout entry — full width (12 cols), placed below existing content
    layout_components.append({
        "colspan": 9,
        "column": 0,
        "row": max_row_end,
        "rowspan": 14
    })
    layout["components"] = layout_components
    meta["layout"] = layout

    # PUT the updated dashboard
    update_payload = {"dashboardMetadata": meta}
    print(f"  Adding funnel component at row {max_row_end}...")
    resp = sf_put(f"analytics/dashboards/{DASHBOARD_ID}", token, update_payload)

    if resp.status_code in (200, 201):
        result = resp.json()
        new_meta = result.get("dashboardMetadata", {})
        new_count = len(new_meta.get("components", []))
        print(f"  Dashboard updated! Components now: {new_count}")
        return True
    else:
        print(f"  Failed to update dashboard: {resp.status_code}")
        print(f"  Response: {resp.text[:1000]}")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    token = get_access_token()

    # Step 1: Create the report (or reuse existing one)
    existing_report_id = "00OOl000005y2gnMAA"  # Previously created
    report_id = existing_report_id
    if not report_id:
        report_id = create_funnel_report(token)
        if not report_id:
            print("\nFailed to create report. Aborting.")
            sys.exit(1)
    else:
        print(f"Using existing report: {report_id}")

    # Step 2: Add to dashboard
    success = add_funnel_to_dashboard(token, report_id)
    if success:
        print(f"\nDone! The funnel chart has been added to the Origination weekly dashboard.")
        print(f"Report ID: {report_id}")
        print(f"Dashboard: {DOMAIN}/lightning/o/Dashboard/home (or navigate to the dashboard)")
    else:
        print(f"\nReport was created ({report_id}) but failed to add to dashboard.")
        print("You can add it manually: Dashboard > Edit > Add Component > select 'Origination Pipeline Funnel'")
