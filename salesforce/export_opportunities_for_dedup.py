"""Export all Opportunity records with Tier 1 identifier fields to CSV.

Used for deduplication against external research tool.
Fields: Opportunity ID, Company Name, Website, Address, Industry
"""
import csv
import logging
import os
import sys
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from salesforce import get_access_token, sf_get

logger = logging.getLogger(__name__)

FIELDS = [
    ("Name", "company_name"),
    ("Company_Website__c", "website"),
    ("fid5__c", "address"),
    ("fid8__c", "industry"),
]


def export_csv(output_path):
    token = get_access_token()

    select_clause = ", ".join(f for f, _ in FIELDS)
    soql = f"SELECT {select_clause} FROM Opportunity ORDER BY Name"

    records = []
    endpoint = f"query/?q={urllib.parse.quote(soql)}"
    while endpoint:
        result = sf_get(endpoint, token)
        if isinstance(result, list):
            logger.error(f"Query error: {result}")
            return
        records.extend(result.get("records", []))
        if result.get("done", True):
            break
        next_rec = result.get("nextRecordsUrl", "")
        endpoint = next_rec.split("/services/data/v62.0/")[-1] if next_rec else None

    logger.info(f"Fetched {len(records):,} opportunities")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([csv_col for _, csv_col in FIELDS])
        for rec in records:
            writer.writerow([rec.get(sf_field) or "" for sf_field, _ in FIELDS])

    logger.info(f"Wrote {len(records):,} rows to {output_path}")
    return len(records)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    output = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "opportunities_for_dedup.csv",
    )
    export_csv(output)
