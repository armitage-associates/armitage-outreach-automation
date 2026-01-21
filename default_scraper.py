import os
import json
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from company_url.serp_company_url import get_company_url
from firmable import get_company_info

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

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

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
                                "description": "Publish date of the article strictly in 'DD Month YYYY' format"
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
    return datetime.strptime(article["date"], "%d %B %Y")

def pull_news(company_name, location):
    logger.info("Starting news pull for company=%s, location=%s", company_name, location)

    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%d %B %Y")

    try:
        company_url = get_company_url(company_name, location)
        logger.debug("Resolved company URL: %s", company_url)

        company_info = get_company_info(
            company_url,
            True if "linkedin" in company_url else False
        )
        logger.debug("Retrieved company info: %s", company_info)

        system_prompt = (
            "You are a Senior Market Researcher. "
            "Your job is to research and find news articles of the company "
            "for the given time period, based on user requirement. "
            "You must output strictly valid JSON matching the provided schema."
        )

        user_prompt = (
            f"The company you will be finding news articles for is {company_name}. "
            f"{company_name} is located at {company_info['hq_location']}, "
            f"they are primarily in the {company_info['industry'].lower()} industries. "
            f"Find news articles indicating growth (awards, expansion, new hires, "
            f"partnerships, patents, financial success, etc) for {company_name}, "
            f"prioritize the company website at {company_info['website']}, "
            f"but also look into other reliable news sources. "
            f"Focus strictly on events after {one_year_ago}."
        )

        logger.info("Sending request to Perplexity model")

        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=article_schema,
            extra_body={"return_citations": True}
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

        return data

    except Exception:
        logger.exception("Failed to pull news for %s", company_name)
        raise  # re-raise so callers can handle it

# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    data = pull_news("Axcelerate", "Sydney")
    print(json.dumps(data, indent=2))