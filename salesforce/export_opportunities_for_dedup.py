"""Export all Opportunity records with identifier fields to CSV.

Used for deduplication against external research tool.
Fields chosen to maximize matching signal against the external tool's schema:
  - company_name, website, address, industry (core)
  - employee_count, revenue_estimate, end_market (size/segmentation)
  - contact_linkedin, primary_contact_name (contact-based matching)
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

# (sf_field_path, csv_column_name, extractor_fn)
# extractor takes the record dict and returns the value
def _direct(field):
    return lambda rec: rec.get(field) or ""

def _primary_contact_name(rec):
    rels = rec.get("OpportunityContactRoles")
    if not rels:
        return ""
    for r in rels.get("records", []):
        if r.get("IsPrimary"):
            return (r.get("Contact") or {}).get("Name") or ""
    return ""

FIELDS = [
    ("Name", "company_name", _direct("Name")),
    ("Company_Website__c", "website", _direct("Company_Website__c")),
    ("fid5__c", "address", _direct("fid5__c")),
    ("fid8__c", "industry", _direct("fid8__c")),
    ("fid9__c", "end_market", _direct("fid9__c")),
    ("Contact_LinkedIn__c", "contact_linkedin", _direct("Contact_LinkedIn__c")),
    (None, "primary_contact_name", _primary_contact_name),
]


def export_csv(output_path):
    token = get_access_token()

    select_fields = [f for f, _, _ in FIELDS if f]
    select_clause = ", ".join(select_fields)
    soql = (
        f"SELECT {select_clause}, "
        "(SELECT IsPrimary, Contact.Name FROM OpportunityContactRoles WHERE IsPrimary = true LIMIT 1) "
        "FROM Opportunity ORDER BY Name"
    )

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
        writer.writerow([col for _, col, _ in FIELDS])
        for rec in records:
            writer.writerow([fn(rec) for _, _, fn in FIELDS])

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
