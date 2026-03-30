"""Compute origination pipeline funnel metrics and upsert to Funnel_Metric__c.

Replicates the Excel funnel logic:
  - Dead deals: uses fid48__c ("Status reached for dead deals") to know how far they got
  - Complete deals: StageName = "0. Complete" with no fid48__c
  - Cumulative waterfall: each stage = total minus deals that exited before reaching it

Run daily via GitHub Actions to keep the Salesforce dashboard chart up to date.
"""
import json
import logging
import os
import sys
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from salesforce import get_access_token, sf_get

logger = logging.getLogger(__name__)

API_VERSION = "v62.0"
DOMAIN = os.getenv("SALESFORCE_DOMAIN")

# Funnel stages in order, with the fid48__c values that EXIT before reaching the next stage
# "Did not connect" means the deal never made it past "Businesses contacted"
# "Introduction pending" + "Immediate kill" means they were contacted but didn't reach discussions
FUNNEL_STAGES = [
    {
        "key": "businesses_contacted",
        "label": "1. Businesses contacted",
        "sort": 1,
        "exits_before": [],  # Top of funnel = all deals
    },
    {
        "key": "initial_contact",
        "label": "2. Initial contact",
        "sort": 2,
        "exits_before": ["Did not connect"],
    },
    {
        "key": "initial_discussions",
        "label": "3. Initial discussions",
        "sort": 3,
        "exits_before": ["Introduction pending", "Immediate kill"],
    },
    {
        "key": "initial_dd",
        "label": "4. Initial DD",
        "sort": 4,
        "exits_before": ["Initial discussions"],
    },
    {
        "key": "indicative_offers",
        "label": "5. Indicative offers made",
        "sort": 5,
        "exits_before": ["Initial DD"],
    },
    {
        "key": "term_sheets",
        "label": "6. Term sheets signed",
        "sort": 6,
        "exits_before": ["Indicative offer"],
    },
    {
        "key": "investments",
        "label": "7. Investments made",
        "sort": 7,
        "exits_before": ["Term sheet"],
    },
]


def get_dead_deal_counts(token):
    """Count dead deals by fid48__c (status reached for dead deals)."""
    soql = (
        "SELECT fid48__c, COUNT(Id) cnt "
        "FROM Opportunity "
        "WHERE fid48__c != null "
        "GROUP BY fid48__c"
    )
    endpoint = f"query/?q={urllib.parse.quote(soql)}"
    result = sf_get(endpoint, token)

    counts = {}
    for record in result.get("records", []):
        stage = record.get("fid48__c", "")
        counts[stage] = record.get("cnt", 0)
    return counts


def get_complete_count(token):
    """Count completed deals (StageName = '0. Complete' with no dead-deal status)."""
    soql = (
        "SELECT COUNT(Id) cnt "
        "FROM Opportunity "
        "WHERE StageName = '0. Complete' AND fid48__c = null"
    )
    endpoint = f"query/?q={urllib.parse.quote(soql)}"
    result = sf_get(endpoint, token)
    records = result.get("records", [])
    return records[0].get("cnt", 0) if records else 0


def compute_funnel(dead_counts, complete_count):
    """Compute cumulative funnel using waterfall subtraction."""
    total = sum(dead_counts.values()) + complete_count
    funnel = []
    running = total

    for stage in FUNNEL_STAGES:
        if stage["exits_before"]:
            exits = sum(dead_counts.get(v, 0) for v in stage["exits_before"])
            running -= exits

        funnel.append({
            "key": stage["key"],
            "label": stage["label"],
            "sort": stage["sort"],
            "count": running,
        })

    return funnel


def upsert_funnel_metrics(token, funnel):
    """Upsert funnel metrics to Funnel_Metric__c using Stage_Key__c as external ID."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    success = 0
    for stage in funnel:
        payload = {
            "Name": stage["label"],
            "Count__c": stage["count"],
            "Sort_Order__c": stage["sort"],
        }
        resp = requests.patch(
            f"{DOMAIN}/services/data/{API_VERSION}/sobjects/Funnel_Metric__c/Stage_Key__c/{stage['key']}",
            headers=headers,
            json=payload,
        )
        if resp.status_code in (200, 201, 204):
            action = "created" if resp.status_code == 201 else "updated"
            logger.info(f"  {stage['label']:30s} {stage['count']:>6,}  ({action})")
            success += 1
        else:
            logger.error(f"  Failed {stage['label']}: {resp.status_code} {resp.text[:200]}")

    return success


def update_funnel():
    """Main entry point: compute and upsert funnel metrics."""
    logger.info("Starting funnel metrics update")
    token = get_access_token()

    logger.info("Querying dead deal counts (fid48__c)...")
    dead_counts = get_dead_deal_counts(token)
    logger.info(f"  Dead deals by stage: {json.dumps(dead_counts, indent=2)}")

    logger.info("Querying complete deal count...")
    complete_count = get_complete_count(token)
    logger.info(f"  Complete deals: {complete_count}")

    logger.info("Computing cumulative funnel...")
    funnel = compute_funnel(dead_counts, complete_count)

    logger.info("Upserting to Funnel_Metric__c...")
    success = upsert_funnel_metrics(token, funnel)
    logger.info(f"Done: {success}/{len(funnel)} stages updated")

    # Print summary
    print("\n=== Funnel Metrics ===")
    for stage in funnel:
        print(f"  {stage['label']:30s}  {stage['count']:>6,}")

    return funnel


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    update_funnel()
