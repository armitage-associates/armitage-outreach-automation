import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from company_url.serp_company_url import get_company_url
from firmable import get_company_info
from perplexity import Perplexity

# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,  # change to DEBUG for more verbosity
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Setup
# -------------------------------------------------------------------
load_dotenv()

client = Perplexity()

article_schema = {
    "type": "json_schema",
    "json_schema": {
        "schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "articles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "date": {
                                "type": "string",
                                "description": "Publish date of the article strictly in 'DD/MM/YYYY' format"
                            },
                            "summary": {"type": "string"},
                            "growth_type": {"type": "string"},
                            "source_url": {"type": "string"}
                        },
                        "required": ["headline", "date", "summary", "growth_type", "source_url"]
                    }
                }
            },
            "required": ["company", "articles"]
        }
    }
}

def parse_date(article):
    """
    Parses the date string in DD/MM/YYYY format. 
    If parsing fails, returns datetime.min so the article is sorted last.
    """
    date_str = article.get("date", "")
    try:
        # Changed from "%d %B %Y" to "%d/%m/%Y"
        return datetime.strptime(date_str, "%d/%m/%Y")
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date: '{date_str}'. Sorting to end.")
        return datetime.min

def pull_news_perplexity(company_name, location, timeframe):
    start_date = None 
    now = datetime.now()

    if timeframe == "year":
        start_date = (now - timedelta(days=365)).strftime("%-m/%-d/%Y")
    elif timeframe == "month":
        start_date = (now - timedelta(days=30)).strftime("%-m/%-d/%Y")
    elif timeframe == "week":
        start_date = (now - timedelta(days=7)).strftime("%-m/%-d/%Y")
    elif timeframe == "day":
        start_date = (now - timedelta(days=1)).strftime("%-m/%-d/%Y")

    logger.info(f"Starting news pull for company={company_name}, location={location} after {start_date}")

    try:
        company_url = get_company_url(company_name, location)
        logger.debug("Resolved company URL: %s", company_url)

        company_info = get_company_info(
            company_url,
            True if "linkedin" in company_url else False
        )

        logger.debug("Retrieved company info: %s", company_info)

        hq_sentence = (
                        f"{company_name} is currently headquartered at {company_info['hq_location']}. "
                        if company_info.get("hq_location")
                        else ""
                    )

        user_prompt = (
            f"The company you will be finding news articles for is {company_name} located in {location}. "
            f"{hq_sentence}"
            f"They are primarily in the {company_info['industry'].lower()} industries. "
            f"Find news articles indicating growth (awards, expansion, new hires, "
            f"partnerships, patents, financial success, etc) for {company_name}. "
            "Only return news for this specific company and location, do not confuse it with other companies with similar names."
        )

        logger.info(f"User prompt: {user_prompt}")

        logger.info("Sending request to Perplexity model")
        domains = [company_url, 
                   "afr.com", 
                   "insidesmallbusiness.com.au", 
                   "dynamicbusiness.com",
                   "smartcompany.com.au",
                   "startupdaily.net",
                   "businessnews.com.au",
                  ]
        
        for domain in domains:
            logger.info(f"Scraping {domain}")

        response = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ],
                        model="sonar-pro",
                        web_search_options={
                            "search_domain_filter": domains,
                            "search_after_date": start_date,
                            "user_location": {
                                                "country": "AU",
                                                "city": location,
                                             }
                        },
                        response_format=article_schema
                    )

        content = response.choices[0].message.content
        data = json.loads(content)

        data["articles"] = sorted(
            data["articles"],
            key=parse_date,
            reverse=True
        )

        logger.info(
            "Successfully retrieved %d articles for %s",
            len(data["articles"]),
            company_name
        )

        if data:
            # 1. Create the 'data' directory if it doesn't exist
            os.makedirs("data", exist_ok=True)
            
            # 2. Construct the filename (e.g., "data/LAB Group.json")
            # Using .get("company") ensures we use the exact name returned by the AI
            filename = f"data/{data.get('company', company_name)}.json"
            
            # 3. Save the result
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Result saved to {filename}")

        return data

    except Exception:
        logger.exception("Failed to pull news for %s", company_name)
        raise  # re-raise so callers can handle it

# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    # batch scrape
    # companies_list = [
    #     ("Partmax", "Melbourne"),
    #     ("GRC Solutions", "Sydney"),
    #     ("Smartsoft", "Adelaide"),
    #     ("OnQ Software", "Melbourne"),
    #     ("LAB Group", "Melbourne"),
    #     ("Axcelerate", "Brisbane"),
    #     ("Pharmako Biotechnologies", "Sydney"),
    #     ("iD4me", "Melbourne")
    # ]

    # for name, location in companies_list:
    #     pull_news_perplexity(name, location, "year")

    # single scrape
    pull_news_perplexity("iD4me", "Melbourne", "year")