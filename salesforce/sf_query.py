"""Quick script to retrieve Opportunities with no Transaction type from Salesforce."""
import json
import urllib.parse
from salesforce import get_access_token, sf_get

def describe_opportunity_fields(token):
    """Get all field names on the Opportunity object to find the right API names."""
    result = sf_get("sobjects/Opportunity/describe", token)
    fields = result.get("fields", [])
    # Print fields that look relevant to the screenshot columns
    keywords = ["transaction", "status", "reason", "kill", "stage", "close", "discussion"]
    print("=== Relevant Opportunity fields ===")
    for f in fields:
        name_lower = f["name"].lower()
        label_lower = f["label"].lower()
        if any(kw in name_lower or kw in label_lower for kw in keywords):
            print(f"  {f['name']:40s} label='{f['label']}'  type={f['type']}")
    return fields

def query_opportunities(token, fields_map):
    """Query opportunities with no Transaction type."""
    # Build SOQL using the discovered field names
    select_fields = ", ".join([
        "Name",
        fields_map["transaction_type"],
        "StageName",
        fields_map["status"],
        fields_map["reason_kill"],
        "CloseDate",
    ])
    soql = (
        f"SELECT {select_fields} FROM Opportunity "
        f"WHERE {fields_map['transaction_type']} = null "
        f"ORDER BY {fields_map['transaction_type']} ASC NULLS FIRST "
        f"LIMIT 100"
    )
    print(f"\n=== SOQL ===\n{soql}\n")
    endpoint = f"query/?q={urllib.parse.quote(soql)}"
    result = sf_get(endpoint, token)

    records = result.get("records", [])
    print(f"=== Results: {result.get('totalSize', '?')} records ===")
    for i, r in enumerate(records, 1):
        print(f"{i:3d}. {r.get('Name', ''):40s} | "
              f"Stage: {r.get('StageName', ''):30s} | "
              f"Status: {str(r.get(fields_map['status'], '')):20s} | "
              f"Reason: {str(r.get(fields_map['reason_kill'], '')):40s} | "
              f"Close: {r.get('CloseDate', '')}")
    return records

if __name__ == "__main__":
    token = get_access_token()

    # Step 1: Discover field names
    fields = describe_opportunity_fields(token)

    # After seeing the output, fill in the field map and run the query
    # For now, let's just discover fields first
    print("\n\nRun again with --query after confirming field names above.")

    fields_map = {
        "transaction_type": "Transaction_type__c",
        "status": "fid31__c",
        "reason_kill": "fid45__c",
    }
    query_opportunities(token, fields_map)
