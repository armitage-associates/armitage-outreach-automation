"""Discover Opportunity StageName picklist values and counts for funnel chart."""
import urllib.parse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from salesforce import get_access_token, sf_get


def get_stage_picklist(token):
    """Get all StageName picklist values from the Opportunity object schema."""
    result = sf_get("sobjects/Opportunity/describe", token)
    for field in result.get("fields", []):
        if field["name"] == "StageName":
            print("=== StageName Picklist Values ===")
            for pv in field.get("picklistValues", []):
                active = "ACTIVE" if pv.get("active") else "INACTIVE"
                print(f"  {pv['value']:40s}  [{active}]")
            return field
    return None


def get_stage_counts(token):
    """Count Opportunities per StageName (all-time)."""
    soql = "SELECT StageName, COUNT(Id) cnt FROM Opportunity GROUP BY StageName ORDER BY COUNT(Id) DESC"
    endpoint = f"query/?q={urllib.parse.quote(soql)}"
    result = sf_get(endpoint, token)

    print("\n=== Opportunity Counts by Stage (All-Time) ===")
    total = 0
    for record in result.get("records", []):
        stage = record.get("StageName", "(blank)")
        count = record.get("cnt", 0)
        total += count
        print(f"  {stage:40s}  {count:>6,}")
    print(f"  {'TOTAL':40s}  {total:>6,}")
    return result.get("records", [])


def get_cumulative_funnel(token):
    """Compute cumulative funnel counts.

    Stages go from 6 (Origination) down to 0 (Complete).
    Cumulative means: for each stage, count all opps at that stage or further.
    """
    # The funnel stages in order (top to bottom)
    funnel_stages = [
        ("Businesses contacted",  ["6. Origination", "5. Low", "4. Medium", "3. High", "2. EOI", "1. Term sheet", "0. Complete"]),
        ("Initial contact",       ["5. Low", "4. Medium", "3. High", "2. EOI", "1. Term sheet", "0. Complete"]),
        ("Initial discussions",   ["4. Medium", "3. High", "2. EOI", "1. Term sheet", "0. Complete"]),
        ("Initial DD",            ["3. High", "2. EOI", "1. Term sheet", "0. Complete"]),
        ("Indicative offers made",["2. EOI", "1. Term sheet", "0. Complete"]),
        ("Term sheets signed",    ["1. Term sheet", "0. Complete"]),
        ("Investments made",      ["0. Complete"]),
    ]

    # Get counts per stage
    soql = "SELECT StageName, COUNT(Id) cnt FROM Opportunity GROUP BY StageName"
    endpoint = f"query/?q={urllib.parse.quote(soql)}"
    result = sf_get(endpoint, token)

    stage_counts = {}
    for record in result.get("records", []):
        stage_counts[record.get("StageName", "")] = record.get("cnt", 0)

    # Also get total including killed/GOWT for "Businesses contacted"
    total_all = sum(stage_counts.values())

    print("\n=== Cumulative Funnel (current stage based) ===")
    for label, included_stages in funnel_stages:
        count = sum(stage_counts.get(s, 0) for s in included_stages)
        print(f"  {label:30s}  {count:>6,}")

    print(f"\n  Total (incl. Killed/GOWT):   {total_all:>6,}")
    print(f"  - 7. Killed:                 {stage_counts.get('7. Killed', 0):>6,}")
    print(f"  - 8. GOWT:                   {stage_counts.get('8. Good opportunity wrong timing', 0):>6,}")

    # Check if OpportunityFieldHistory is available for true "ever reached" tracking
    print("\n=== Checking OpportunityFieldHistory ===")
    try:
        history_soql = (
            "SELECT OpportunityId, OldValue, NewValue "
            "FROM OpportunityFieldHistory "
            "WHERE Field = 'StageName' "
            "LIMIT 5"
        )
        history_endpoint = f"query/?q={urllib.parse.quote(history_soql)}"
        history_result = sf_get(history_endpoint, token)
        records = history_result.get("records", [])
        if records:
            print(f"  OpportunityFieldHistory IS available ({len(records)} sample records found)")
            for r in records[:3]:
                print(f"    {r.get('OldValue')} -> {r.get('NewValue')}")
        else:
            print("  OpportunityFieldHistory exists but no StageName history records found")
    except Exception as e:
        print(f"  OpportunityFieldHistory NOT available: {e}")


if __name__ == "__main__":
    token = get_access_token()
    get_stage_picklist(token)
    get_stage_counts(token)
    get_cumulative_funnel(token)
