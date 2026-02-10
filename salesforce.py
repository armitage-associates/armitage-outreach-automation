import csv
import logging
import os
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

API_VERSION = "v62.0"
TARGET_REPORTS = ["GOWT Ultra High's", "GOWT High's"]

domain = os.getenv("SALESFORCE_DOMAIN")


def get_access_token():
    payload = {
        'grant_type': 'client_credentials',
        'client_id': os.getenv('CONSUMER_KEY'),
        'client_secret': os.getenv('CONSUMER_SECRET')
    }
    return requests.post(f"{domain}/services/oauth2/token", data=payload).json()['access_token']


def sf_get(endpoint, token):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{domain}/services/data/{API_VERSION}/{endpoint}", headers=headers).json()


def get_dashboard_ids(token):
    response = sf_get("analytics/dashboards", token)
    dashboards = response.get("dashboards", response) if isinstance(response, dict) else response
    return [db.get("id") or db.get("Id") for db in dashboards]


def extract_companies(token, dashboard_id):
    detail = sf_get(f"analytics/dashboards/{dashboard_id}", token)
    components = detail.get("componentData", detail.get("components", []))
    companies = []

    for comp in components:
        if "reportResult" not in comp:
            continue
        report = comp["reportResult"]
        metadata = report.get("reportMetadata", {})
        if metadata.get("name", "") not in TARGET_REPORTS:
            continue

        columns = metadata.get("detailColumns", [])
        name_idx = next((i for i, c in enumerate(columns) if c == "OPPORTUNITY_NAME"), None)
        addr_idx = next((i for i, c in enumerate(columns) if c == "Opportunity.fid5__c"), None)

        for fact in report.get("factMap", {}).values():
            for row in fact.get("rows", []):
                cells = row.get("dataCells", [])
                company = cells[name_idx].get("label", "") if name_idx is not None else ""
                location = cells[addr_idx].get("label", "") if addr_idx is not None else ""
                companies.append((company, location))

    return companies


def write_companies_csv(companies):
    csv_path = os.path.join(os.path.dirname(__file__), "data", "input", "companies.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["company", "location"])
        writer.writerows(companies)
    logger.info(f"Wrote {len(companies)} companies to {csv_path}")


def import_companies_from_salesforce():
    logger.info("Starting Salesforce company import")
    token = get_access_token()
    logger.info("Authenticated successfully")

    dashboard_ids = get_dashboard_ids(token)
    logger.info(f"Found {len(dashboard_ids)} dashboard(s)")

    companies = []
    for dashboard_id in dashboard_ids:
        extracted = extract_companies(token, dashboard_id)
        logger.info(f"Dashboard {dashboard_id}: extracted {len(extracted)} companies")
        companies.extend(extracted)

    logger.info(f"Total companies extracted: {len(companies)}")
    write_companies_csv([companies[0]])
    logger.info("Import complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import_companies_from_salesforce()
