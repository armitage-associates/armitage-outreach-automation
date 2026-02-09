import os
import re
import json
import time
import random
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Pool of realistic user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

# Accept-Language variations
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en-AU,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
    "en-US,en;q=0.9,es;q=0.8",
]


def scrape_news_linkedin(company_info):
    """
    Scrape LinkedIn posts for a company using plain GET requests with anti-bot measures.

    Anti-bot measures:
    - User-Agent rotation from realistic browser pool
    - Accept-Language variation
    - Random delays (3-10s) to mimic human behavior
    - Session cookies to appear like a persistent browser
    - Referer header to simulate navigation
    - Multiple extraction strategies (JSON, ld+json, HTML)

    Args:
        company_info (dict): Company information containing:
            - name: Company name
            - linkedin: LinkedIn company ID/slug

    Returns:
        str: Path to output JSON file on success
        None: On any failure
    """
    company_name = company_info.get("name", "Unknown")
    linkedin_id = company_info.get("linkedin")

    if not linkedin_id:
        logger.warning(f"No LinkedIn ID for {company_name}, skipping")
        return None

    url = f"https://www.linkedin.com/company/{linkedin_id}"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "data", "output")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{company_name} Linkedin Posts.json")

    # Create a session to maintain cookies (acts like a real browser)
    session = requests.Session()

    # Rotate user agent and language
    user_agent = random.choice(USER_AGENTS)
    accept_language = random.choice(ACCEPT_LANGUAGES)

    # Build realistic headers
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": accept_language,
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    # Add Referer on subsequent requests (simulate navigation from LinkedIn homepage)
    if random.random() < 0.7:
        headers["Referer"] = "https://www.linkedin.com/"

    try:
        # Random delay to simulate human behavior (3-10s)
        delay = random.uniform(3, 10)
        logger.info(f"Waiting {delay:.1f}s before request (anti-bot measure)...")
        time.sleep(delay)

        logger.info(f"GET {url} (UA: {user_agent[:60]}...)")
        resp = session.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
        )

        logger.info(f"Status: {resp.status_code}, Final URL: {resp.url}, Length: {len(resp.text)}")

        # Status 999 = LinkedIn anti-bot response
        if resp.status_code == 999:
            logger.error("Received status 999 (LinkedIn anti-bot). Scraper blocked.")
            return None

        # Check for auth walls or blocks
        if "authwall" in resp.url or "login" in resp.url or "checkpoint" in resp.url:
            logger.error(f"Redirected to auth wall or checkpoint: {resp.url}")
            return None

        resp.raise_for_status()
        html = resp.text

        posts = []

        # Strategy 1: Extract from <code> elements containing JSON state
        # LinkedIn embeds serialized data in <code> tags
        code_blocks = re.findall(
            r'<code[^>]*><!--(.+?)--></code>', html, re.DOTALL
        )
        logger.info(f"Found {len(code_blocks)} embedded <code> blocks")

        for block in code_blocks:
            try:
                data = json.loads(block)
                _extract_posts_from_data(data, posts)
            except (json.JSONDecodeError, TypeError):
                continue

        # Strategy 2: Extract from application/ld+json
        ld_blocks = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        logger.info(f"Found {len(ld_blocks)} ld+json blocks")

        for block in ld_blocks:
            try:
                data = json.loads(block)
                _extract_posts_from_ld(data, posts)
            except (json.JSONDecodeError, TypeError):
                continue

        # Strategy 3: Regex fallback for post text in HTML
        if not posts:
            logger.info("Trying HTML element extraction...")
            _extract_posts_from_html(html, posts)

        # Deduplicate by post_text
        seen = set()
        unique_posts = []
        for p in posts:
            text = p.get("post_text", "")[:100]
            if text and text not in seen:
                seen.add(text)
                unique_posts.append(p)

        if not unique_posts:
            logger.error("No posts found in response")
            return None

        logger.info(f"Extracted {len(unique_posts)} unique posts")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_posts, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved to {output_file}")
        return output_file

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None
    except Exception as e:
        logger.exception(f"Scraper failed: {e}")
        return None
    finally:
        session.close()


def _extract_posts_from_data(data, posts):
    """Recursively search nested JSON data for post-like objects."""
    if isinstance(data, dict):
        # Look for objects with commentary/text fields typical of LinkedIn posts
        text = (
            data.get("commentary", {}).get("text", {}).get("text")
            if isinstance(data.get("commentary"), dict)
            else None
        )
        if not text:
            text = data.get("post_text") or data.get("text") or data.get("commentary")
            if isinstance(text, dict):
                text = text.get("text")

        if text and isinstance(text, str) and len(text) > 20:
            # Extract date with multiple fallback strategies
            date_posted = (
                data.get("date_posted")
                or data.get("postedAt")
                or data.get("publishedAt")
                or data.get("createdAt")
            )

            # Handle nested created object
            if not date_posted and isinstance(data.get("created"), dict):
                date_posted = data.get("created", {}).get("time", "")
            elif not date_posted:
                date_posted = data.get("created", "")

            post = {
                "title": data.get("title", ""),
                "post_text": text.strip(),
                "date_posted": date_posted,
            }
            posts.append(post)
            return

        for v in data.values():
            _extract_posts_from_data(v, posts)

    elif isinstance(data, list):
        for item in data:
            _extract_posts_from_data(item, posts)


def _extract_posts_from_ld(data, posts):
    """Extract posts from JSON-LD structured data."""
    if isinstance(data, list):
        for item in data:
            _extract_posts_from_ld(item, posts)
        return

    if not isinstance(data, dict):
        return

    # SocialMediaPosting or Article types
    obj_type = data.get("@type", "")
    if "Posting" in obj_type or "Article" in obj_type:
        text = data.get("articleBody") or data.get("text") or data.get("description", "")
        if text:
            posts.append({
                "title": data.get("headline", data.get("name", "")),
                "post_text": text.strip(),
                "date_posted": data.get("datePublished", data.get("dateCreated", "")),
            })

    # Check nested items
    for key in ("mainEntity", "hasPart", "itemListElement"):
        nested = data.get(key)
        if nested:
            _extract_posts_from_ld(nested, posts)


def _extract_posts_from_html(html, posts):
    """Extract post content directly from HTML elements."""
    # LinkedIn renders post text in specific data-test-id elements
    patterns = [
        r'data-test-id="main-feed-activity-card__commentary"[^>]*>(.*?)</(?:p|div)>',
        r'class="feed-shared-update-v2__description[^"]*"[^>]*>(.*?)</div>',
        r'class="update-components-text[^"]*"[^>]*>(.*?)</div>',
        r'class="break-words[^"]*"[^>]*>(.*?)</(?:p|div|span)>',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        for match in matches:
            # Strip HTML tags and clean up
            clean = re.sub(r"<[^>]+>", "", match).strip()
            # Remove excessive whitespace
            clean = re.sub(r'\s+', ' ', clean)
            if clean and len(clean) > 20:
                posts.append({
                    "title": "",
                    "post_text": clean,
                    "date_posted": "",
                })


if __name__ == "__main__":
    company_info = {
        "hq_location": "11 Camford Street, Milton, QLD, 4064, AU",
        "linkedin": "axcelerate-student-training-rto-management-systems",
        "industry": "E-learning and online education",
        "website": "axcelerate.com.au",
        "name": "Axcelerate",
        "city": "Queensland",
    }

    result = scrape_news_linkedin(company_info)
    if result:
        print(f"Successfully scraped posts to: {result}")
    else:
        print("Scraping failed")
