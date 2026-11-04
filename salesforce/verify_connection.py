"""Verify the Salesforce client-credentials connection.

Used by the SessionStart hook (and runnable manually) to confirm that this
environment can authenticate to Salesforce and run a query.

Usage:
    python salesforce/verify_connection.py

Exit codes:
    0  connection OK
    1  credentials present but auth/query failed
    3  credentials not configured (skipped)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import salesforce as sf  # noqa: E402

REQUIRED = ["SALESFORCE_DOMAIN", "CONSUMER_KEY", "CONSUMER_SECRET"]
SKIP = 3


def main():
    missing = [v for v in REQUIRED if not os.getenv(v)]
    if missing:
        print(f"[SKIP] Salesforce credentials not set: {', '.join(missing)}")
        print("       Add them as environment secrets in the Claude Code web environment settings.")
        return SKIP

    try:
        token = sf.get_access_token()
    except Exception as e:
        print(f"[FAIL] Could not obtain access token: {e}")
        return 1

    if not token:
        print("[FAIL] Empty access token returned.")
        return 1

    try:
        res = sf.sf_get("query/?q=SELECT+COUNT()+FROM+Opportunity", token)
        count = res.get("totalSize")
        print(f"[OK] Connected to {sf.domain} - Opportunity count: {count}")
        return 0
    except Exception as e:
        print(f"[FAIL] Token acquired but query failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
