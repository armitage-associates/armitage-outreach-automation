"""Export all Opportunity records with identifier/enrichment fields to CSV.

Used for deduplication and enrichment against external research tool (Tecala).

Fields chosen to maximize matching signal and enrich their database:
  Company core: company_name, salesforce_account_id, website, address,
                industry, end_market, description, company_overview,
                employee_count, revenue_estimate, parent_company
  Primary contact: name, title, email, phone, linkedin
  Secondary contact: name, title, email, phone, linkedin
"""
import csv
import logging
import os
import sys
import urllib.parse
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from salesforce import get_access_token, sf_get

logger = logging.getLogger(__name__)

# Domains that are directories/registries/profile pages, not actual company
# websites. Websites matching these are blanked out in the export so Tecala's
# dedup matcher doesn't get confused by shared-directory domains.
DIRECTORY_DOMAINS = {
    # Business registries
    "abr.business.gov.au", "abr.gov.au", "asic.gov.au",
    "publishednotices.asic.gov.au", "business.gov.au",
    "find-and-update.company-information.service.gov.uk", "gov.uk",
    # Local business directories
    "yellowpages.com.au", "yellowpages.co.nz",
    "whitepages.com.au", "whitepages.com",
    "truelocal.com.au", "localsearch.com.au", "localsearch.com",
    "companyhub.nz", "thecompanycheck.com",
    # Business intelligence databases
    "pitchbook.com", "crunchbase.com", "rocketreach.co",
    "zoominfo.com", "dnb.com", "owler.com", "tracxn.com",
    "datanyze.com", "corporationwiki.com", "opencorporates.com",
    "bloomberg.com",
    # Industry regulators / registers
    "training.gov.au", "teqsa.gov.au", "tga.gov.au",
    "ndiscommission.gov.au", "buy.nsw.gov.au",
    "medicalsearch.com.au", "australianfintech.com.au",
    # Social / review / job sites
    "linkedin.com", "au.linkedin.com", "uk.linkedin.com", "nz.linkedin.com",
    "facebook.com", "twitter.com", "x.com",
    "instagram.com", "youtube.com", "tiktok.com",
    "trustpilot.com", "glassdoor.com", "glassdoor.com.au",
    "yelp.com", "yelp.com.au",
    "seek.com.au", "indeed.com",
    # Startup / industry directories
    "f6s.com", "startupdaily.net", "techboard.com.au", "anthill.com.au",
    # News / encyclopedias
    "wikipedia.org", "en.wikipedia.org", "smh.com.au", "afr.com",
    "techcrunch.com", "businessinsider.com", "reuters.com",
    # Maps / misc
    "mapquest.com", "whereis.com", "google.com", "goo.gl",
}

# Catch-all for government domains (most are regulators/registries, not real
# company websites unless the "company" literally is a gov body)
GOV_SUFFIXES = (".gov.au", ".gov.nz", ".gov.uk", ".gov")


def _sanitize_text(value):
    """Strip invisible/control/garbage chars from text fields.

    - Removes zero-width spaces (U+200B, U+200C, U+200D, U+FEFF)
    - Removes Latin-1 garbage char ÿ (U+00FF) from encoding artifacts
    - Removes all other C0 control chars except tab
    - Replaces non-breaking space (U+00A0) with regular space
    - Collapses runs of whitespace and trims
    """
    if not value:
        return ""
    if not isinstance(value, str):
        return value
    for ch in ("\u200B", "\u200C", "\u200D", "\uFEFF", "\u00FF", "\u0000"):
        value = value.replace(ch, "")
    value = "".join(c for c in value if ord(c) >= 32 or c == "\t")
    value = value.replace("\u00A0", " ")
    return " ".join(value.split())


# Values that are placeholders, not real data. Blanked out in contact/URL fields
# so Tecala doesn't try to match/dial/email them.
PLACEHOLDER_VALUES = {
    "na", "n/a", "n / a", "none", "-", "--", "---",
    "tbd", "tbc", "unknown", "null", "nil",
    ".", "?", "??",
}


def _blank_if_placeholder(value):
    """Return empty string if value is a common placeholder, else return as-is."""
    if not value:
        return ""
    if value.strip().lower() in PLACEHOLDER_VALUES:
        return ""
    return value


def _clean_website(url):
    """Return the URL if it looks like a real company website, else empty string."""
    if not url:
        return ""
    try:
        parsed = urlparse(url if "://" in url else "http://" + url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
    except Exception:
        return url

    if host in DIRECTORY_DOMAINS:
        return ""
    if any(host.endswith(s) for s in GOV_SUFFIXES):
        return ""
    lower = url.lower()
    if "/profile/" in lower or "/profiles/" in lower or "/listing" in lower or "/company-profile" in lower:
        return ""
    return url


def _get_contact_by_priority(rec, *, primary):
    """Return the primary or first-secondary contact from OpportunityContactRoles.

    Primary = IsPrimary=true
    Secondary = first non-primary (ordered by CreatedDate ascending from the subquery)
    """
    rels = rec.get("OpportunityContactRoles") or {}
    for r in rels.get("records", []) or []:
        if r.get("IsPrimary") == primary:
            return r.get("Contact") or {}
        if not primary and not r.get("IsPrimary"):
            return r.get("Contact") or {}
    return {}


def _primary_contact(rec):
    return _get_contact_by_priority(rec, primary=True)


def _secondary_contact(rec):
    rels = rec.get("OpportunityContactRoles") or {}
    for r in rels.get("records", []) or []:
        if not r.get("IsPrimary"):
            return r.get("Contact") or {}
    return {}


def _phone(contact):
    return contact.get("Phone") or contact.get("MobilePhone") or ""


def _num(value):
    """Preserve 0.0 unlike `value or ""`. Return "" for None, else str(value)."""
    return "" if value is None else str(value)


def _row_extractors():
    """(csv_column_name, extractor) tuples defining the output CSV.

    All text values are sanitized via _sanitize_text() to strip invisible/control
    unicode. Contact and URL fields also go through _blank_if_placeholder() to
    remove "na" / "n/a" / "-" / etc. placeholder values. Numeric fields use
    _num() to preserve 0 values.
    """
    S = _sanitize_text
    BP = _blank_if_placeholder
    return [
        ("company_name", lambda r: S(r.get("Name"))),
        ("salesforce_account_id", lambda r: r.get("AccountId") or ""),
        ("website", lambda r: _clean_website(BP(S(r.get("Company_Website__c"))))),
        ("address", lambda r: S(r.get("fid5__c"))),
        ("industry", lambda r: S(r.get("fid8__c"))),
        ("end_market", lambda r: S(r.get("fid9__c"))),
        ("description", lambda r: S(r.get("Description"))),
        ("company_overview", lambda r: S(r.get("Company__c"))),
        ("employee_count", lambda r: _num(r.get("fid50__c"))),
        ("revenue_estimate", lambda r: _num(r.get("fid14__c"))),
        ("parent_company", lambda r: S(r.get("fid40__c"))),
        ("primary_contact_name", lambda r: BP(S((_primary_contact(r) or {}).get("Name")))),
        ("primary_contact_title", lambda r: BP(S((_primary_contact(r) or {}).get("Title")))),
        ("primary_contact_email", lambda r: BP(S((_primary_contact(r) or {}).get("Email")))),
        ("primary_contact_phone", lambda r: BP(S(_phone(_primary_contact(r) or {})))),
        ("primary_contact_linkedin", lambda r: BP(S(r.get("Contact_LinkedIn__c")))),
        ("secondary_contact_name", lambda r: BP(S((_secondary_contact(r) or {}).get("Name")))),
        ("secondary_contact_title", lambda r: BP(S((_secondary_contact(r) or {}).get("Title")))),
        ("secondary_contact_email", lambda r: BP(S((_secondary_contact(r) or {}).get("Email")))),
        ("secondary_contact_phone", lambda r: BP(S(_phone(_secondary_contact(r) or {})))),
        ("secondary_contact_linkedin", lambda r: BP(S((_secondary_contact(r) or {}).get("fidliurl__c")))),
    ]


def export_csv(output_path):
    token = get_access_token()

    opp_fields = [
        "Name", "AccountId", "Company_Website__c",
        "fid5__c", "fid8__c", "fid9__c",
        "Description", "Company__c",
        "fid50__c", "fid14__c", "fid40__c",
        "Contact_LinkedIn__c",
    ]
    select_clause = ", ".join(opp_fields)
    soql = (
        f"SELECT {select_clause}, "
        "(SELECT IsPrimary, Contact.Name, Contact.Title, Contact.Email, "
        "Contact.Phone, Contact.MobilePhone, Contact.fidliurl__c "
        "FROM OpportunityContactRoles ORDER BY IsPrimary DESC, CreatedDate ASC) "
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

    extractors = _row_extractors()
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([col for col, _ in extractors])
        for rec in records:
            writer.writerow([fn(rec) for _, fn in extractors])

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
