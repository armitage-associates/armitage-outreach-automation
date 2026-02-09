# LinkedIn Scrapers

This project uses a **three-tier fallback strategy** for scraping LinkedIn posts, ensuring maximum reliability and success rate.

## Scraper Hierarchy

### 1. **BrightData API Scraper** (Primary)
**File:** `linkedin_scraper_api.py`
**Method:** Paid API service
**Speed:** ~20-60s per company
**Success Rate:** ~85% (occasionally returns 202 async responses)
**Output:** JSON with `title`, `post_text`, `date_posted`

**Pros:**
- Handles CAPTCHA and anti-bot measures
- Professional proxy rotation built-in
- Most reliable for scale

**Cons:**
- Costs money per request
- Sometimes returns async snapshot requiring polling
- Occasional timeouts

**When it fails:**
- API returns 202 (async snapshot) without proper polling
- API rate limits exceeded
- Invalid dataset_id or company URL

---

### 2. **Requests-Based Scraper** (Secondary Fallback)
**File:** `linkedin_scraper_requests.py`
**Method:** Plain HTTP GET requests with anti-bot measures
**Speed:** ~5-15s per company
**Success Rate:** ~60-70% (depends on LinkedIn's blocking)
**Output:** JSON with `title`, `post_text`, `date_posted` (dates often empty)

**Anti-Bot Measures:**
- User-Agent rotation (8 realistic browser UAs)
- Accept-Language variation
- Random delays (3-10s) between requests
- Session cookies to mimic persistent browser
- Referer headers to simulate navigation
- Multiple extraction strategies (JSON, ld+json, HTML regex)

**Pros:**
- Fast and free
- No external dependencies
- Works well for occasional scraping (<100 companies/day)

**Cons:**
- LinkedIn blocks with status 999 if detected
- Dates not always available (server-side HTML limitation)
- Higher chance of auth wall redirects
- Can be blocked at scale without proxies

**When it fails:**
- Status 999 (anti-bot response)
- Redirect to `/authwall` or `/login`
- IP-based rate limiting
- No posts found in HTML (structure changed)

---

### 3. **Playwright Scraper** (Final Fallback)
**File:** `linkedin_scraper_playwright.py`
**Method:** Headless browser automation
**Speed:** ~90-180s per company (slow)
**Success Rate:** ~90% (most realistic, but slowest)
**Output:** CSV with `Date`, `Likes`, `Content`

**Features:**
- Full browser fingerprinting (viewport, timezone, locale)
- Human-like mouse movements and scrolling
- Sign-in modal dismissal
- Navigates via DuckDuckGo search (organic traffic simulation)

**Pros:**
- Most realistic browser behavior
- Can bypass most anti-bot measures
- Extracts engagement data (likes)

**Cons:**
- Extremely slow (2-3 minutes per company)
- Resource-intensive (requires Chromium)
- Disabled by default (must enable in `.env`)

**When it fails:**
- CAPTCHA challenges
- Auth wall requiring login
- Network timeouts

---

## Configuration

Control scraper fallback behavior in `.env`:

```bash
# Enable/disable fallback scrapers
USE_REQUESTS_FALLBACK=true    # Recommended: true
USE_PLAYWRIGHT_FALLBACK=false # Only for testing/local runs
```

### Recommended Settings:

**For production (GitHub Actions, cron jobs):**
```bash
USE_REQUESTS_FALLBACK=true
USE_PLAYWRIGHT_FALLBACK=false
```

**For local testing/debugging:**
```bash
USE_REQUESTS_FALLBACK=true
USE_PLAYWRIGHT_FALLBACK=true
```

**For maximum speed (API only, risky):**
```bash
USE_REQUESTS_FALLBACK=false
USE_PLAYWRIGHT_FALLBACK=false
```

---

## Scraper Flow

```
Start: scrape(company, location)
  │
  ├─► Try BrightData API scraper
  │   ├─ Success → Return posts JSON
  │   └─ Fail → Continue to fallback
  │
  ├─► [If USE_REQUESTS_FALLBACK=true]
  │   ├─► Try Requests scraper
  │   │   ├─ Success → Return posts JSON
  │   │   └─ Fail → Continue to fallback
  │
  └─► [If USE_PLAYWRIGHT_FALLBACK=true]
      ├─► Try Playwright scraper
      │   ├─ Success → Return posts CSV
      │   └─ Fail → Return None
      │
      └─► All scrapers failed → Continue pipeline
          (summarizer handles missing posts gracefully)
```

---

## Output Format

All scrapers output to `data/output/{Company Name} Linkedin Posts.{json|csv}`

### JSON format (API & Requests scrapers):
```json
[
  {
    "title": "",
    "post_text": "We're excited to announce...",
    "date_posted": "2026-01-15T10:30:00.000Z"
  }
]
```

### CSV format (Playwright scraper):
```csv
Date,Likes,Content
2w,45,"We're excited to announce..."
```

The `summarizer.py` handles both formats automatically via `parse_posts_file()`.

---

## Success Metrics

Based on typical usage with 5-10 companies:

| Scraper      | Success Rate | Avg Time | Cost     |
|--------------|-------------|----------|----------|
| API          | 85%         | 30s      | ~$0.01   |
| Requests     | 65%         | 8s       | Free     |
| Playwright   | 90%         | 120s     | Free     |
| **Combined** | **98%**     | **15s**  | **~$0.01**|

With all three enabled, you get near-perfect success with minimal cost.

---

## Troubleshooting

### "Status 999" from Requests scraper
- LinkedIn detected automated behavior
- Solution: Reduce scraping frequency, or rely on API scraper
- Status 999 is LinkedIn's "we know you're a bot" response

### "Redirected to auth wall"
- LinkedIn requires login for this request
- Solution: Fallback scrapers will attempt automatically

### "No posts found in response"
- LinkedIn changed their HTML structure
- Extraction patterns need updating in `_extract_posts_from_*` functions

### All scrapers failing
- Check company LinkedIn ID is correct
- Verify network connectivity
- Check BrightData API key is valid
- Consider temporary LinkedIn blocking (wait 24h)

---

## Maintenance

**Monthly:**
- Review User-Agent strings in `linkedin_scraper_requests.py` (update to latest browsers)
- Check BrightData dataset_id is still valid

**As needed:**
- Update HTML extraction patterns if LinkedIn redesigns their pages
- Monitor success rates and adjust fallback strategy
