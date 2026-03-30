"""Bulk update all Opportunities with null Transaction_type__c to type 3."""
import urllib.parse
import requests
import os
from salesforce import get_access_token, sf_get, API_VERSION

domain = os.getenv("SALESFORCE_DOMAIN")
BATCH_SIZE = 200
NEW_VALUE = "3. Growth equity (<$20mn cheque)"


def get_all_opportunity_ids(token):
    """Fetch all Opportunity IDs where Transaction_type__c is null, handling pagination."""
    soql = "SELECT Id FROM Opportunity WHERE Transaction_type__c = null"
    endpoint = f"query/?q={urllib.parse.quote(soql)}"

    all_ids = []
    while endpoint:
        result = sf_get(endpoint, token)
        for record in result.get("records", []):
            all_ids.append(record["Id"])
        next_url = result.get("nextRecordsUrl")
        if next_url:
            # nextRecordsUrl is like /services/data/v62.0/query/01g...
            endpoint = next_url.replace(f"/services/data/{API_VERSION}/", "")
        else:
            endpoint = None

    return all_ids


def batch_update(token, ids, value):
    """Update records in batches of 200 using sObject Collections API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    total = len(ids)
    updated = 0
    failed = 0

    for i in range(0, total, BATCH_SIZE):
        batch = ids[i:i + BATCH_SIZE]
        records = [
            {"attributes": {"type": "Opportunity"}, "Id": oid, "Transaction_type__c": value}
            for oid in batch
        ]
        payload = {"records": records}

        url = f"{domain}/services/data/{API_VERSION}/composite/sobjects"
        resp = requests.patch(url, headers=headers, json=payload)
        results = resp.json()

        batch_ok = sum(1 for r in results if r.get("success"))
        batch_fail = sum(1 for r in results if not r.get("success"))
        updated += batch_ok
        failed += batch_fail

        if batch_fail > 0:
            errors = [r for r in results if not r.get("success")]
            print(f"  Batch {i // BATCH_SIZE + 1}: {batch_ok} ok, {batch_fail} failed. Errors: {errors[:3]}")
        else:
            print(f"  Batch {i // BATCH_SIZE + 1}: {batch_ok}/{len(batch)} updated")

    return updated, failed


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    token = get_access_token()

    print("Fetching all Opportunity IDs with null Transaction_type__c...")
    ids = get_all_opportunity_ids(token)
    print(f"Found {len(ids)} records to update.")

    print(f"\nUpdating all to: '{NEW_VALUE}'")
    updated, failed = batch_update(token, ids, NEW_VALUE)
    print(f"\nDone: {updated} updated, {failed} failed.")
