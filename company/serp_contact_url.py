import os
import logging
import requests
from dotenv import load_dotenv
from urllib.parse import quote_plus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("BRIGHTDATA_API_KEY")


def get_contact_linkedin_url(contact_name, company_name):
    """
    Search Google for a person's LinkedIn profile URL using Bright Data SERP API.

    Args:
        contact_name: Full name of the contact (e.g. "Nick Gannoulis")
        company_name: Company name for disambiguation (e.g. "OnQ Software")

    Returns:
        str: LinkedIn profile URL on success
        None: On any failure
    """
    query = f"{contact_name} {company_name} LinkedIn"

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
            logger.warning(f"No search results for contact {contact_name} at {company_name}")
            return None

        for result in organic[:5]:
            link = result.get("link", "")
            if "linkedin.com/in/" in link:
                logger.info(f"Found LinkedIn URL for {contact_name}: {link}")
                return link

        logger.warning(f"No LinkedIn profile URL found in top results for {contact_name}")
        return None

    except Exception as e:
        logger.exception(f"Bright Data SERP API error searching for {contact_name}: {e}")
        return None


if __name__ == "__main__":
    print(get_contact_linkedin_url("Nick Gannoulis", "OnQ Software"))
