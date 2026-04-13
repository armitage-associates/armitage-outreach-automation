"""Daily update of the 4 Origination Charts pie chart reports' CreatedDate filter.

Rolls the standardDateFilter forward each day so the default view always shows
the last 365 days. Users can still override the date range on the run page.

Run daily via GitHub Actions alongside sf_funnel_update.py.
"""
import logging
import os
import sys
from datetime import date, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from salesforce import get_access_token

logger = logging.getLogger(__name__)

API_VERSION = "v62.0"
DOMAIN = os.getenv("SALESFORCE_DOMAIN")

REPORT_IDS = [
    ("00OOl0000065kZqMAI", "Dealflow by Source (LTM)"),
    ("00OOl0000065lSfMAI", "Dealflow by Industry (LTM)"),
    ("00OOl0000065mN7MAI", "Dead Deals by Status (LTM)"),
    ("00OOl0000065mOjMAI", "Dead Deals by Reason (LTM)"),
]


def update_report_date_range(token, report_id, start_date, end_date):
    """PATCH a report's standardDateFilter to the given range."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "reportMetadata": {
            "standardDateFilter": {
                "column": "CREATED_DATE",
                "durationValue": "CUSTOM",
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
            }
        }
    }
    resp = requests.patch(
        f"{DOMAIN}/services/data/{API_VERSION}/analytics/reports/{report_id}",
        headers=headers,
        json=payload,
    )
    return resp.status_code == 200


def update_all_reports():
    """Roll all 4 pie chart reports to the last 365 days."""
    logger.info("Starting daily report date range update")
    token = get_access_token()

    today = date.today()
    year_ago = today - timedelta(days=365)
    logger.info(f"Rolling window: {year_ago} to {today}")

    success = 0
    for report_id, name in REPORT_IDS:
        if update_report_date_range(token, report_id, year_ago, today):
            logger.info(f"  {name}: updated")
            success += 1
        else:
            logger.error(f"  {name}: FAILED")

    logger.info(f"Done: {success}/{len(REPORT_IDS)} reports updated")
    return success == len(REPORT_IDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    update_all_reports()
