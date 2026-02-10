import logging
from .serp_company_url import get_company_url
from .firmable_data import get_company_info

# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def get_info(company_name, company_location):
    """
    Aggregate company information from multiple sources.

    Returns:
        dict: Company info with all available fields on success
        None: Only if critical data (company URL) cannot be obtained
    """
    # Get company URL from SERP
    company_url = get_company_url(company_name, company_location)

    if not company_url:
        logger.error(f"Could not find company URL for {company_name} in {company_location}")
        return None

    # Get detailed company info from Firmable
    company_info = get_company_info(company_url)

    # If Firmable fails, create a minimal info dict so workflow can continue
    if not company_info:
        logger.warning(f"Could not get Firmable data for {company_name}, using minimal info")
        company_info = {
            "hq_location": None,
            "linkedin": None,
            "industry": "Unknown"
        }

    # Always add these fields
    company_info['website'] = company_url
    company_info['name'] = company_name
    company_info['city'] = company_location

    logger.info(f"Successfully aggregated info for {company_name}")
    return company_info


if __name__ == "__main__":
    print(get_info("UrbanX", "Brisbane"))