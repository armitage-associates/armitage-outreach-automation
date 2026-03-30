"""
1. Create a 'Contact LinkedIn' custom field on Opportunity via Salesforce Metadata API.
2. Populate it for all Opportunities that have a primary contact, using SERP API to find LinkedIn URLs.
"""
import os
import time
import urllib.parse
import requests
import logging
from dotenv import load_dotenv
from salesforce import get_access_token, sf_get, sf_patch, API_VERSION
from company.brightdata_contact_url import get_contact_linkedin_url

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

domain = os.getenv("SALESFORCE_DOMAIN")
BATCH_SIZE = 200


def create_contact_linkedin_field(token):
    """Create Contact_LinkedIn__c URL field on Opportunity via Tooling API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Check if field already exists
    result = sf_get("sobjects/Opportunity/describe", token)
    existing = [f["name"] for f in result["fields"]]
    if "Contact_LinkedIn__c" in existing:
        logger.info("Field Contact_LinkedIn__c already exists, skipping creation.")
        return True

    # Use Tooling API to create custom field
    payload = {
        "FullName": "Opportunity.Contact_LinkedIn__c",
        "Metadata": {
            "label": "Contact LinkedIn",
            "type": "Url",
            "description": "LinkedIn profile URL for the primary contact",
        },
    }

    url = f"{domain}/services/data/{API_VERSION}/tooling/sobjects/CustomField"
    resp = requests.post(url, headers=headers, json=payload)

    if resp.status_code == 201:
        logger.info(f"Created Contact_LinkedIn__c field: {resp.json()}")
        return True
    else:
        logger.error(f"Failed to create field: {resp.status_code} {resp.text}")
        return False


def get_opps_with_primary_contact(token):
    """Get Opportunities with a primary contact (name + company), that don't already have a LinkedIn URL."""
    soql = """SELECT OpportunityId, Opportunity.Name, Contact.Name
    FROM OpportunityContactRole
    WHERE IsPrimary = true
    AND Opportunity.Contact_LinkedIn__c = null
    ORDER BY Opportunity.Name"""

    endpoint = f"query/?q={urllib.parse.quote(soql)}"
    records = []
    while endpoint:
        result = sf_get(endpoint, token)
        records.extend(result.get("records", []))
        next_url = result.get("nextRecordsUrl")
        endpoint = next_url.replace(f"/services/data/{API_VERSION}/", "") if next_url else None

    opps = []
    for rec in records:
        opp_id = rec.get("OpportunityId")
        opp_name = rec.get("Opportunity", {}).get("Name") or ""
        contact_name = rec.get("Contact", {}).get("Name") or ""
        if opp_id and contact_name:
            opps.append({"opp_id": opp_id, "opp_name": opp_name, "contact_name": contact_name})

    return opps


def batch_update_linkedin(token, updates):
    """Batch update Contact_LinkedIn__c on Opportunities."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    updated = 0
    failed = 0

    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        records = [
            {"attributes": {"type": "Opportunity"}, "Id": u["opp_id"], "Contact_LinkedIn__c": u["url"]}
            for u in batch
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
            logger.warning(f"Batch {i // BATCH_SIZE + 1}: {batch_ok} ok, {batch_fail} failed. Sample: {errors[0]}")
        else:
            logger.info(f"Batch {i // BATCH_SIZE + 1}: {batch_ok}/{len(batch)} updated")

    return updated, failed


if __name__ == "__main__":
    token = get_access_token()

    # Step 1: Create the field
    print("=== Step 1: Create Contact_LinkedIn__c field ===")
    if not create_contact_linkedin_field(token):
        print("Failed to create field. Exiting.")
        exit(1)

    # Re-authenticate in case of delay
    time.sleep(3)
    token = get_access_token()

    # Step 2: Get all opps with primary contacts but no LinkedIn URL
    print("\n=== Step 2: Find Opportunities to populate ===")
    opps = get_opps_with_primary_contact(token)
    print(f"Found {len(opps)} Opportunities with primary contacts needing LinkedIn URLs.\n")

    # Step 3: Search for LinkedIn URLs via SERP API
    print("=== Step 3: Search for LinkedIn URLs ===")
    updates = []
    not_found = 0
    for i, opp in enumerate(opps):
        linkedin_url = get_contact_linkedin_url(opp["contact_name"], opp["opp_name"])
        if linkedin_url:
            updates.append({"opp_id": opp["opp_id"], "url": linkedin_url})
        else:
            not_found += 1

        if (i + 1) % 50 == 0:
            print(f"  Searched {i + 1}/{len(opps)} — found: {len(updates)}, not found: {not_found}")

    print(f"\nSearch complete: {len(updates)} found, {not_found} not found.\n")

    # Step 4: Batch update Salesforce
    if updates:
        print("=== Step 4: Update Salesforce ===")
        updated, failed = batch_update_linkedin(token, updates)
        print(f"\nDone: {updated} updated, {failed} failed, {not_found} no LinkedIn URL found.")
    else:
        print("No LinkedIn URLs found to update.")
