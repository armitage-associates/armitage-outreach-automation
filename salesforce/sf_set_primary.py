"""Set IsPrimary on the earliest OpportunityContactRole for Opportunities missing a primary contact."""
import urllib.parse
import requests
import os
from dotenv import load_dotenv
from salesforce import get_access_token, sf_get, API_VERSION

load_dotenv()

domain = os.getenv("SALESFORCE_DOMAIN")
BATCH_SIZE = 200


def get_opps_missing_primary(token):
    """Get all Opportunity IDs that have contacts but no primary."""
    soql = """SELECT Id FROM Opportunity
    WHERE Id IN (SELECT OpportunityId FROM OpportunityContactRole)
    AND Id NOT IN (SELECT OpportunityId FROM OpportunityContactRole WHERE IsPrimary = true)"""
    endpoint = f"query/?q={urllib.parse.quote(soql)}"

    opp_ids = []
    while endpoint:
        result = sf_get(endpoint, token)
        for rec in result.get("records", []):
            opp_ids.append(rec["Id"])
        next_url = result.get("nextRecordsUrl")
        endpoint = next_url.replace(f"/services/data/{API_VERSION}/", "") if next_url else None

    return opp_ids


def get_earliest_contact_role(token, opp_ids):
    """For each Opportunity, get the earliest-created OpportunityContactRole ID."""
    # Query in chunks to avoid SOQL length limits
    chunk_size = 200
    ocr_to_update = []

    for i in range(0, len(opp_ids), chunk_size):
        chunk = opp_ids[i:i + chunk_size]
        ids_clause = ",".join(f"'{oid}'" for oid in chunk)
        soql = f"""SELECT Id, OpportunityId, Contact.Name, CreatedDate
        FROM OpportunityContactRole
        WHERE OpportunityId IN ({ids_clause})
        ORDER BY CreatedDate ASC"""
        endpoint = f"query/?q={urllib.parse.quote(soql)}"

        # Collect all contact roles, then pick earliest per opportunity
        opp_to_roles = {}
        while endpoint:
            result = sf_get(endpoint, token)
            for rec in result.get("records", []):
                oid = rec["OpportunityId"]
                if oid not in opp_to_roles:
                    # First one is earliest due to ORDER BY CreatedDate ASC
                    opp_to_roles[oid] = rec["Id"]
            next_url = result.get("nextRecordsUrl")
            endpoint = next_url.replace(f"/services/data/{API_VERSION}/", "") if next_url else None

        ocr_to_update.extend(opp_to_roles.values())
        print(f"  Chunk {i // chunk_size + 1}: found {len(opp_to_roles)} contact roles to update")

    return ocr_to_update


def batch_set_primary(token, ocr_ids):
    """Set IsPrimary=true on contact roles in batches."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    total = len(ocr_ids)
    updated = 0
    failed = 0

    for i in range(0, total, BATCH_SIZE):
        batch = ocr_ids[i:i + BATCH_SIZE]
        records = [
            {"attributes": {"type": "OpportunityContactRole"}, "Id": crid, "IsPrimary": True}
            for crid in batch
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
            print(f"  Batch {i // BATCH_SIZE + 1}: {batch_ok} ok, {batch_fail} failed. Sample error: {errors[0]}")
        else:
            print(f"  Batch {i // BATCH_SIZE + 1}: {batch_ok}/{len(batch)} updated")

    return updated, failed


if __name__ == "__main__":
    token = get_access_token()

    print("Finding Opportunities with contacts but no primary...")
    opp_ids = get_opps_missing_primary(token)
    print(f"Found {len(opp_ids)} Opportunities.\n")

    print("Identifying earliest contact role for each...")
    ocr_ids = get_earliest_contact_role(token, opp_ids)
    print(f"\n{len(ocr_ids)} contact roles to set as primary.\n")

    print("Setting IsPrimary=true...")
    updated, failed = batch_set_primary(token, ocr_ids)
    print(f"\nDone: {updated} updated, {failed} failed.")
