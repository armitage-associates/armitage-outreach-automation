"""
Populate Contact_LinkedIn__c on Opportunities using Bright Data SERP API.
Pushes every 50 found URLs with retry logic for network errors.
"""
import os
import json
import time
import urllib.parse
import requests
import logging
from dotenv import load_dotenv
from salesforce import get_access_token, sf_get, API_VERSION
from company.brightdata_contact_url import get_contact_linkedin_url

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

domain = os.getenv("SALESFORCE_DOMAIN")
BATCH_SIZE = 200
PUSH_EVERY = 50
MAX_RETRIES = 3


def get_token_with_retry():
    """Get Salesforce access token with retry on network errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return get_access_token()
        except Exception as e:
            logger.warning(f"Token refresh failed (attempt {attempt + 1}): {e}")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("Failed to get access token after retries")


def get_opps_with_primary_contact(token):
    """Get Opportunities with a primary contact but no LinkedIn URL."""
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
    """Batch update Contact_LinkedIn__c on Opportunities with retry."""
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

        for attempt in range(MAX_RETRIES):
            try:
                url = f"{domain}/services/data/{API_VERSION}/composite/sobjects"
                resp = requests.patch(url, headers=headers, json=payload, timeout=30)
                results = resp.json()

                batch_ok = sum(1 for r in results if r.get("success"))
                batch_fail = sum(1 for r in results if not r.get("success"))
                updated += batch_ok
                failed += batch_fail

                if batch_fail > 0:
                    errors = [r for r in results if not r.get("success")]
                    logger.warning(f"Batch: {batch_ok} ok, {batch_fail} failed. Sample: {errors[0]}")
                else:
                    logger.info(f"Batch: {batch_ok}/{len(batch)} pushed to Salesforce")
                break
            except Exception as e:
                logger.warning(f"Batch push failed (attempt {attempt + 1}): {e}")
                time.sleep(10 * (attempt + 1))
                if attempt == MAX_RETRIES - 1:
                    failed += len(batch)
                else:
                    token = get_token_with_retry()
                    headers["Authorization"] = f"Bearer {token}"

    return updated, failed


CACHE_FILE = os.path.join(os.path.dirname(__file__), "data", "linkedin_cache.json")


def load_cache():
    """Load previously scraped LinkedIn URLs from cache file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_to_cache(cache):
    """Save LinkedIn URL cache to file."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


if __name__ == "__main__":
    import json as json_mod
    token = get_token_with_retry()

    print("=== Finding Opportunities with missing LinkedIn URLs ===")
    opps = get_opps_with_primary_contact(token)
    print(f"Found {len(opps)} Opportunities to process.\n")

    # Load cache of previously scraped URLs
    cache = load_cache()
    print(f"Loaded {len(cache)} cached LinkedIn URLs.\n")

    pending = []
    not_found = 0
    total_updated = 0
    total_failed = 0
    cache_hits = 0

    for i, opp in enumerate(opps):
        opp_id = opp["opp_id"]

        # Check cache first
        if opp_id in cache:
            linkedin_url = cache[opp_id]
            cache_hits += 1
        else:
            linkedin_url = get_contact_linkedin_url(opp["contact_name"], opp["opp_name"])
            # Save to cache regardless of result
            cache[opp_id] = linkedin_url
            if (i + 1) % 10 == 0:
                save_to_cache(cache)

        if linkedin_url:
            pending.append({"opp_id": opp_id, "url": linkedin_url})
        else:
            not_found += 1

        # Push every PUSH_EVERY found URLs
        if len(pending) >= PUSH_EVERY:
            token = get_token_with_retry()
            updated, failed = batch_update_linkedin(token, pending)
            total_updated += updated
            total_failed += failed
            pending = []

        if (i + 1) % 100 == 0:
            save_to_cache(cache)
            print(f"  Progress: {i + 1}/{len(opps)} searched | {total_updated} pushed | {not_found} not found | {cache_hits} cache hits")

    # Push remaining
    if pending:
        token = get_token_with_retry()
        updated, failed = batch_update_linkedin(token, pending)
        total_updated += updated
        total_failed += failed

    # Final cache save
    save_to_cache(cache)

    print(f"\nDone: {total_updated} pushed, {total_failed} failed, {not_found} not found, {cache_hits} cache hits.")
    print(f"Cache saved to {CACHE_FILE} ({len(cache)} entries).")
