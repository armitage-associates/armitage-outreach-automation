import os
import json
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def scrape_news_linkedin(company_info):
    """
    Scrape LinkedIn posts for a company using BrightData's API.

    Args:
        company_info (dict): Company information containing:
            - name: Company name
            - linkedin: LinkedIn company ID/slug
            - city: Company city (optional, for logging)

    Returns:
        str: Path to output JSON file on success
        None: On any failure (missing linkedin ID, API error, etc.)
    """
    company_name = company_info.get('name', 'Unknown')
    linkedin_id = company_info.get('linkedin')

    if not linkedin_id:
        logger.warning(f"No LinkedIn ID available for {company_name}, skipping LinkedIn scrape")
        return None

    # Get API key from environment
    api_key = os.getenv('BRIGHTDATA_API_KEY')
    if not api_key:
        logger.error("BRIGHTDATA_API_KEY not found in environment variables")
        return None

    # Build LinkedIn company URL
    company_url = f"https://www.linkedin.com/company/{linkedin_id}"

    # Calculate date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Format dates as ISO 8601 strings
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    logger.info(f"Scraping LinkedIn posts for {company_name} from {start_date_str} to {end_date_str}")

    # Prepare output directory and file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "data", "output")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{company_name} Linkedin Posts.json")

    # Prepare API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps({
        "input": [{
            "url": company_url,
            "start_date": start_date_str,
            "end_date": end_date_str
        }],
    })

    try:
        logger.info(f"Making API request to BrightData for {company_name}...")
        response = requests.post(
            "https://api.brightdata.com/datasets/v3/scrape?dataset_id=gd_lyy3tktm25m4avu764&custom_output_fields=title%2Cpost_text%2Cdate_posted&notify=false&type=discover_new&discover_by=company_url",
            headers=headers,
            data=data,
            timeout=100
        )

        # Check for HTTP errors
        response.raise_for_status()

        # BrightData returns NDJSON (multiple JSON objects on separate lines)
        response_text = response.text.strip()

        logger.info(f"Response length: {len(response_text)} characters")
        logger.info(f"Number of lines: {len(response_text.split(chr(10)))}")

        # Each line is a separate post object - collect them all
        posts_data = []
        for line_num, line in enumerate(response_text.split('\n'), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Each line is a post object (dict with title, post_text, date_posted)
                if isinstance(obj, dict) and 'post_text' in obj:
                    posts_data.append(obj)
                    logger.info(f"Line {line_num}: Added post")
                else:
                    logger.debug(f"Line {line_num}: Skipping - not a post object")
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num} - Failed to parse: {e}")
                continue

        if not posts_data:
            logger.error("No posts found in response")
            return None

        logger.info(f"Collected {len(posts_data)} posts total")

        # Save to JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(posts_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully saved {len(posts_data)} posts to {output_file}")
        return output_file

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {company_name}: {e}")
        return None
    except Exception as e:
        logger.exception(f"LinkedIn API scraper failed for {company_name}: {e}")
        return None


if __name__ == "__main__":
    # Test with sample company info
    company_info = {
        'hq_location': '11 Camford Street, Milton, QLD, 4064, AU',
        'linkedin': 'axcelerate-student-training-rto-management-systems',
        'industry': 'E-learning and online education',
        'website': 'axcelerate.com.au',
        'name': 'Axcelerate',
        'city': 'Queensland'
    }

    result = scrape_news_linkedin(company_info)
    if result:
        print(f"Successfully scraped posts to: {result}")
    else:
        print("Scraping failed")