import os
import logging
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse, quote_plus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("BRIGHTDATA_API_KEY")


def clean_domain(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return urlparse(url).netloc.replace('www.', '').lower()


def get_company_url(name, location):
    """
    Get company website URL using Bright Data SERP API Google search.

    Returns:
        str: Company domain on success
        None: On any failure (API error, no results, etc.)
    """
    query = f"{name} {location} Company Page"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "zone": "serp_api1",
        "url": f"https://www.google.com/search?q={quote_plus(query)}&gl=au&hl=en&brd_json=1",
        "format": "raw",
    }

    try:
        resp = requests.post(
            "https://api.brightdata.com/request",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if not resp.ok:
            logger.error(f"Bright Data SERP API error {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        organic = data.get("organic", [])

        if not organic:
            logger.warning(f"No search results found for {name} in {location}")
            return None

        link = organic[0].get("link")
        if not link:
            logger.warning(f"First result has no link for {name} in {location}")
            return None

        domain = clean_domain(link)
        logger.info(f"Found company URL for {name}: {domain}")
        return domain

    except Exception as e:
        logger.exception(f"Bright Data SERP API error for {name} in {location}: {e}")
        return None


if __name__ == "__main__":
    print(get_company_url("LAB Group", "Melbourne"))