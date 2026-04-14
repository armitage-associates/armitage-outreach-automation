"""Export all Opportunity records with identifier/enrichment fields to CSV.

Used for deduplication and enrichment against external research tool (Tecala).

Usage:
    python salesforce/export_opportunities_for_dedup.py

Output: data/opportunities_for_dedup.csv

On every run, this script:
  1. Fetches ALL Opportunity records from Salesforce (with contact subqueries)
  2. Applies cleanups:
     - Strips invisible unicode (zero-width space, NBSP, ÿ, control chars)
     - Blanks out third-party directory URLs (pitchbook, ABR, yellowpages, etc.)
     - Blanks out placeholder values ("na", "n/a", "-", etc.) in contact/URL fields
     - Preserves numeric 0 values (unlike `x or ""`)
  3. Writes the CSV with a stable 21-column schema
  4. Runs integrity checks:
     - Row count matches Salesforce
     - Schema matches (21 expected columns in correct order)
     - No invisible chars remain
     - No placeholder values remain
     - Emails contain @
     - URLs start with http(s)://
     - Spot-checks 50 random records against live SF data

If any check fails the script exits with code 1 so callers (e.g. a scheduled
job) can detect the failure.

Fields:
  Company core: company_name, salesforce_account_id, website, address,
                industry, end_market, description, company_overview,
                employee_count, revenue_estimate, parent_company
  Primary contact: name, title, email, phone, linkedin
  Secondary contact: name, title, email, phone, linkedin
"""
import csv
import logging
import os
import random
import re
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


EXPECTED_COLUMNS = [
    "company_name", "salesforce_account_id", "website", "address", "industry",
    "end_market", "description", "company_overview", "employee_count",
    "revenue_estimate", "parent_company",
    "primary_contact_name", "primary_contact_title", "primary_contact_email",
    "primary_contact_phone", "primary_contact_linkedin",
    "secondary_contact_name", "secondary_contact_title", "secondary_contact_email",
    "secondary_contact_phone", "secondary_contact_linkedin",
]

_PHONE_CHARS_RE = re.compile(r"^[\d\+\-\(\)\s\.]+$")
_INVISIBLE_CHARS = ("\u200B", "\u200C", "\u200D", "\uFEFF", "\u00A0", "\u00FF", "\u0000")


def verify_csv(output_path, spot_check_size=50):
    """Run integrity checks on the exported CSV against live Salesforce.

    Returns a tuple (passed: bool, issues: list[str]).
    """
    issues = []
    warnings = []

    # Load CSV
    with open(output_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    csv_total = len(rows)

    # --- Check 1: Row count matches Salesforce ---
    token = get_access_token()
    sf_count = sf_get(
        f"query/?q={urllib.parse.quote('SELECT COUNT(Id) cnt FROM Opportunity')}",
        token,
    )["records"][0]["cnt"]

    if csv_total != sf_count:
        issues.append(f"Row count mismatch: CSV has {csv_total:,}, SF has {sf_count:,}")
    else:
        logger.info(f"  [1/8] Row count: {csv_total:,} ✓")

    # --- Check 2: Column schema ---
    actual_cols = list(rows[0].keys()) if rows else []
    if actual_cols != EXPECTED_COLUMNS:
        issues.append(
            f"Column schema mismatch.\n"
            f"  Expected: {EXPECTED_COLUMNS}\n"
            f"  Actual:   {actual_cols}"
        )
    else:
        logger.info(f"  [2/8] Schema: {len(actual_cols)} columns in correct order ✓")

    # --- Check 3: No invisible/control characters ---
    invisible_rows = 0
    for r in rows:
        for val in r.values():
            if val and any(c in val for c in _INVISIBLE_CHARS):
                invisible_rows += 1
                break
    if invisible_rows:
        issues.append(f"{invisible_rows} rows contain invisible/control characters")
    else:
        logger.info("  [3/8] No invisible unicode chars ✓")

    # --- Check 4: No placeholder values in contact/URL fields ---
    placeholder_hits = 0
    contact_url_cols = [
        "website", "primary_contact_name", "primary_contact_email",
        "primary_contact_phone", "primary_contact_linkedin",
        "secondary_contact_name", "secondary_contact_email",
        "secondary_contact_phone", "secondary_contact_linkedin",
    ]
    for r in rows:
        for col in contact_url_cols:
            v = (r.get(col) or "").strip().lower()
            if v in PLACEHOLDER_VALUES:
                placeholder_hits += 1
                break
    if placeholder_hits:
        issues.append(f"{placeholder_hits} rows still contain placeholder values")
    else:
        logger.info("  [4/8] No placeholder values ✓")

    # --- Check 5: Emails contain @ ---
    bad_emails = 0
    for r in rows:
        for col in ("primary_contact_email", "secondary_contact_email"):
            e = (r.get(col) or "").strip()
            if e and "@" not in e:
                bad_emails += 1
    if bad_emails:
        issues.append(f"{bad_emails} email values don't contain '@'")
    else:
        logger.info("  [5/8] All non-empty emails contain @ ✓")

    # --- Check 6: URLs start with http(s):// ---
    bad_urls = 0
    for r in rows:
        for col in ("website", "primary_contact_linkedin", "secondary_contact_linkedin"):
            u = (r.get(col) or "").strip()
            if u and not (u.startswith("http://") or u.startswith("https://")):
                bad_urls += 1
    if bad_urls:
        warnings.append(f"{bad_urls} URLs don't start with http(s):// (may be source data issue)")
    else:
        logger.info("  [6/8] All non-empty URLs start with http(s):// ✓")

    # --- Check 7: Phone numbers are reasonable format ---
    # Warn only — vanity numbers like "1300 GOBARKER" are legitimate.
    bad_phones = 0
    for r in rows:
        for col in ("primary_contact_phone", "secondary_contact_phone"):
            p = (r.get(col) or "").strip()
            if p and not _PHONE_CHARS_RE.match(p):
                bad_phones += 1
    if bad_phones:
        warnings.append(
            f"{bad_phones} phone values have unusual format (vanity numbers, "
            "trailing punctuation — may be source data issue)"
        )
    else:
        logger.info("  [7/8] Phone formats look clean ✓")

    # --- Check 8: Spot-check random records against live SF ---
    if rows and csv_total == sf_count:
        random.seed(42)
        sample = random.sample(rows, min(spot_check_size, csv_total))
        account_ids = [r["salesforce_account_id"] for r in sample]
        id_clause = ",".join(f"'{aid}'" for aid in set(account_ids))
        soql = (
            f"SELECT Id, Name, AccountId, Company_Website__c, fid5__c, fid8__c, fid9__c, "
            f"fid50__c, fid14__c, fid40__c, Description, Company__c, Contact_LinkedIn__c, "
            f"(SELECT IsPrimary, Contact.Name, Contact.Title, Contact.Email, Contact.Phone, "
            f"Contact.MobilePhone, Contact.fidliurl__c FROM OpportunityContactRoles "
            f"ORDER BY IsPrimary DESC, CreatedDate ASC) "
            f"FROM Opportunity WHERE AccountId IN ({id_clause})"
        )
        result = sf_get(f"query/?q={urllib.parse.quote(soql)}", token)
        sf_by_acc = {}
        for rec in result.get("records", []):
            sf_by_acc.setdefault(rec["AccountId"], []).append(rec)

        extractors = _row_extractors()
        mismatches = 0
        for csv_row in sample:
            aid = csv_row["salesforce_account_id"]
            sf_recs = sf_by_acc.get(aid, [])
            sf = None
            for rec in sf_recs:
                if _sanitize_text(rec.get("Name") or "") == csv_row["company_name"]:
                    sf = rec
                    break
            if not sf:
                mismatches += 1
                continue
            for col, fn in extractors:
                expected = str(fn(sf) or "")
                actual = csv_row.get(col) or ""
                if expected != actual:
                    mismatches += 1
                    break

        if mismatches:
            issues.append(
                f"{mismatches}/{len(sample)} spot-checked records don't match live SF data"
            )
        else:
            logger.info(
                f"  [8/8] Spot-check: {len(sample)} random records × "
                f"{len(extractors)} fields = {len(sample) * len(extractors)} comparisons ✓"
            )
    else:
        logger.info("  [8/8] Spot-check: skipped (prior check failed)")

    # Print warnings as informational
    for w in warnings:
        logger.warning(f"  WARNING: {w}")

    passed = not issues
    return passed, issues


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    output = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "opportunities_for_dedup.csv",
    )

    logger.info("=== Exporting Salesforce opportunities for dedup ===")
    count = export_csv(output)
    if count is None:
        logger.error("Export failed.")
        sys.exit(1)

    logger.info("=== Running integrity checks ===")
    passed, issues = verify_csv(output)

    if passed:
        logger.info(f"=== All checks passed. {count:,} rows written to {output} ===")
        sys.exit(0)
    else:
        logger.error("=== Integrity checks FAILED ===")
        for issue in issues:
            logger.error(f"  ✗ {issue}")
        sys.exit(1)
