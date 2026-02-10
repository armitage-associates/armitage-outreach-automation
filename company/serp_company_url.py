import os
import logging
import serpapi
from dotenv import load_dotenv
from urllib.parse import urlparse

# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("SERP_API_KEY")

def clean_domain(url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return urlparse(url).netloc.replace('www.', '').lower()

def get_company_url(name, location):
    """
    Get company website URL using SERP API Google search.

    Returns:
        str: Company domain on success
        None: On any failure (API error, no results, etc.)
    """
    params = {
        "engine": "google",
        "location": "Australia",
        "google_domain": "google.com.au",
        "hl": "en",
        "gl": "au",
        "q": f"{name} {location} Company Page",
        "api_key": API_KEY
    }

    try:
        client = serpapi.Client(api_key=params["api_key"])
        results = client.search(params)

        if not results.get("organic_results"):
            logger.warning(f"No search results found for {name} in {location}")
            return None

        link = results["organic_results"][0].get("link")
        if not link:
            logger.warning(f"First result has no link for {name} in {location}")
            return None

        domain = clean_domain(link)
        logger.info(f"Found company URL for {name}: {domain}")
        return domain

    except Exception as e:
        logger.exception(f"SERP API error for {name} in {location}: {e}")
        return None

if __name__ == "__main__":
  print(get_company_url("LAB Group", "Melbourne"))