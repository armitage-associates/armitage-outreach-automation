# Armitage News Scraper

Automated growth intelligence pipeline that discovers, analyzes, and delivers company growth signals. The system scrapes news articles and LinkedIn posts for target companies, identifies growth indicators using AI, generates personalized LinkedIn reachout messages, and distributes formatted reports via email.

## 🚀 Key Features

- **Dual LinkedIn Scraping**: BrightData API (primary) with Playwright fallback for reliability
- **AI-Powered Analysis**: OpenAI GPT-4 identifies growth signals from posts
- **Automated Delivery**: Email digests and Salesforce CRM integration
- **GitHub Actions**: Run on cloud infrastructure, no server required
- **Smart Fallbacks**: API-first approach with browser automation backup

## Architecture

```
companies.csv
      |
      v
 Company Info Retrieval (SERP + Firmable APIs)
      |
      v
 News Scraping (Perplexity AI) ──> data/output/{company}.json
      |
      v
 LinkedIn Post Scraping
   ├─> BrightData API (primary) ──> data/output/{company} Linkedin Posts.json
   └─> Playwright (fallback)    ──> data/output/{company} Linkedin Posts.csv
      |
      v
 AI Analysis & Summarization (OpenAI)
   - Filter posts for growth indicators
   - Generate LinkedIn reachout message
   - Merge into company JSON
      |
      v
 Delivery
   - Email digest (SMTP)
   - Salesforce CRM sync
```

## Growth Indicators Detected

- Awards and recognition
- Business expansion
- New hires / team growth
- Partnerships and collaborations
- Patents and innovations
- Financial success / funding
- Product launches
- Market expansion
- Client acquisitions

## Project Structure

```
├── main.py                          # Entry point, runs full pipeline
├── scraper.py                       # Orchestrates scraping per company
├── summarizer.py                    # AI post analysis + reachout message generation
├── email_client.py                  # HTML email formatting and SMTP delivery
├── salesforce.py                    # Salesforce CRM integration
├── company/
│   ├── get_company_info.py          # Aggregates company data from APIs
│   ├── serp_company_url.py          # Google Search via SerpAPI
│   └── firmable_data.py             # Firmable API for company enrichment
├── scrapers/
│   ├── perplexity_scraper.py        # News scraping via Perplexity AI
│   ├── linkedin_scraper_api.py      # LinkedIn API scraper (BrightData) - PRIMARY
│   └── linkedin_scraper_playwright.py # LinkedIn browser automation - FALLBACK
├── data/
│   ├── input/companies.csv          # Target companies list
│   └── output/                      # Generated JSON reports and CSV/JSON files
├── .github/
│   └── workflows/
│       ├── run-on-push.yml          # GitHub Actions: runs on push
│       └── scraper.yml              # GitHub Actions: scheduled daily
└── cron.txt                         # Cron schedule definition
```

## Setup

### Prerequisites

- Python 3.12+
- Playwright browsers (only if using fallback scraper)

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd armitage-automation

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (optional, only for fallback)
playwright install --with-deps chromium
```

### Configuration

Copy the sample env file and fill in your credentials:

```bash
cp .env.sample .env
```

Required environment variables:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o-mini) for post analysis |
| `PERPLEXITY_API_KEY` | Perplexity AI API key (sonar-pro) for news scraping |
| `FIRMABLE_API_KEY` | Firmable API key for company enrichment |
| `SERP_API_KEY` | SerpAPI key for Google Search |
| `BRIGHTDATA_API_KEY` | **BrightData API key for LinkedIn scraping (primary method)** |
| `SALESFORCE_DOMAIN` | Salesforce instance URL (e.g., `https://yourorg.my.salesforce.com`) |
| `SALESFORCE_USERNAME` | Salesforce login email |
| `SALESFORCE_PASSWORD` | Salesforce password |
| `SALESFORCE_SECURITY_TOKEN` | Salesforce security token |
| `CONSUMER_KEY` | Salesforce Connected App consumer key (OAuth) |
| `CONSUMER_SECRET` | Salesforce Connected App consumer secret (OAuth) |
| `ACCESS_TOKEN` | Salesforce access token |
| `SMTP_USER` | SMTP username (email address) |
| `SMTP_PASSWORD` | SMTP password (app password for Gmail) |
| `SENDER_EMAIL` | Sender email (defaults to `SMTP_USER`) |
| `EMAIL_RECIPIENTS` | Email recipients (comma-separated) |
| `USE_PLAYWRIGHT_FALLBACK` | **Optional:** Enable Playwright browser fallback (default: `false`). Set to `true` for local testing. |

### Input

Add target companies to `data/input/companies.csv`:

```csv
company,location
OnQ Software,Melbourne
Axcelerate,Brisbane
GRC Solutions,Sydney
```

## Usage

### Local Execution

#### Run the full pipeline (API-only mode - Default)

```bash
python main.py
```

This will:
1. Read companies from `data/input/companies.csv`
2. Retrieve company info (website URL, LinkedIn ID, industry)
3. Scrape news articles via Perplexity AI
4. **Scrape LinkedIn posts via BrightData API only**
5. Analyze posts with OpenAI, filter for growth signals, and generate a reachout message
6. Send a digest email to configured recipients

#### Enable Playwright fallback (Local testing only)

```bash
# One-time command with fallback enabled
USE_PLAYWRIGHT_FALLBACK=true python main.py

# Or update .env file
# Set: USE_PLAYWRIGHT_FALLBACK=true
```

This enables browser automation as a fallback if the API fails. **Use only for local testing.**

#### Run individual components

```bash
# Scrape all companies
python scraper.py

# Test API scraper
python scrapers/linkedin_scraper_api.py

# Test Playwright scraper (fallback)
python scrapers/linkedin_scraper_playwright.py

# Summarize LinkedIn posts for a single company
python summarizer.py

# Send digest email from existing output data
python email_client.py recipient@example.com

# Sync data to Salesforce
python salesforce.py
```

### GitHub Actions (Cloud Execution)

The project includes GitHub Actions workflows for automated execution:

#### Setup GitHub Actions

1. **Push code to GitHub**:
   ```bash
   git add .
   git commit -m "Setup automation"
   git push origin main
   ```

2. **Add secrets** to your GitHub repository:
   - Go to: Settings → Secrets and variables → Actions
   - Add all environment variables from `.env` as repository secrets

3. **Workflows will run**:
   - **On push**: Every time you push code (`.github/workflows/run-on-push.yml`)
   - **Scheduled**: Daily at 9 AM UTC (`.github/workflows/scraper.yml`)
   - **Manual**: Click "Run workflow" in Actions tab

#### Benefits of GitHub Actions

✅ No server required - runs on GitHub infrastructure
✅ Free tier: 2,000 minutes/month
✅ API-based scraping works perfectly (no browser overhead)
✅ Automatic artifact storage (30-day retention)
✅ Email notifications on failure

For detailed setup instructions, see [`.github/GITHUB_ACTIONS_SETUP.md`](.github/GITHUB_ACTIONS_SETUP.md)

## Output

Each company produces a JSON file in `data/output/` with the following structure:

```json
{
  "company": "Company Name",
  "articles": [
    {
      "headline": "...",
      "date": "DD/MM/YYYY",
      "summary": "...",
      "growth_type": "expansion",
      "source_url": "https://..."
    }
  ],
  "posts": [
    {
      "summary": "...",
      "growth_type": "new_hires",
      "date": "06/02/2026 - 1d"
    }
  ],
  "message": "AI-generated LinkedIn reachout message...",
  "linkedin_url": "https://www.linkedin.com/company/...",
  "potential_actions": [
    "Schedule introductory call",
    "Research competitive landscape"
  ]
}
```

## LinkedIn Scraping Strategy

### Primary: BrightData API (`linkedin_scraper_api.py`)
- ✅ Fast and reliable
- ✅ No browser required
- ✅ Perfect for CI/CD environments
- ✅ Returns structured JSON data
- 📊 Scrapes last 30 days of posts

### Fallback: Playwright (`linkedin_scraper_playwright.py`)
- 🔄 Automatic fallback if API fails
- 🎭 Advanced anti-detection (randomized fingerprints)
- 🌐 Guest access (no login required)
- 📄 Returns CSV data (auto-converted to JSON by summarizer)

The system automatically tries the API first and falls back to Playwright only if needed.

## Scheduling

### Local Cron (Linux/Mac)

The pipeline can run weekly via cron. Schedule defined in `cron.txt`:

```
0 12 * * 0  # Every Sunday at noon
```

Install the cron job:

```bash
crontab cron.txt
```

Verify installation:

```bash
crontab -l
```

Check logs:

```bash
tail -f cron.log
```

### GitHub Actions (Recommended)

Use GitHub Actions for cloud-based scheduling:
- No server maintenance
- Automatic notifications
- Version-controlled configuration
- Free tier available

See `.github/workflows/scraper.yml` for configuration.

## Tools & APIs

| Tool | Purpose | Required |
|---|---|---|
| [OpenAI](https://openai.com/) | Post analysis and reachout generation (GPT-4o-mini) | Yes |
| [Perplexity AI](https://perplexity.ai/) | News article discovery (sonar-pro) | Yes |
| [BrightData](https://brightdata.com/) | LinkedIn API scraping (primary method) | Yes |
| [SerpAPI](https://serpapi.com/) | Google Search for company URLs | Yes |
| [Firmable](https://firmable.com/) | Company data enrichment | Yes |
| [Playwright](https://playwright.dev/) | LinkedIn browser automation (fallback) | Optional |
| [Salesforce](https://salesforce.com/) | CRM data sync | Optional |

## Troubleshooting

### OpenAI "insufficient_quota" Error

If you get quota errors but have credits:
1. Go to: https://platform.openai.com/settings/organization/limits
2. Check "Monthly budget" - it might be set too low (e.g., $0.01)
3. Increase to $5-10
4. Verify payment method is active

### BrightData API Not Working

- Check API key in `.env` is correct
- Verify you have credits in BrightData account
- System will automatically fall back to Playwright

### GitHub Actions Failing

- Ensure all secrets are set in repository settings
- Check workflow logs in Actions tab
- Verify API keys are valid and have credits

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Proprietary - Armitage Associates

## Support

For issues or questions, contact the development team or check logs:
- Local: `cron.log`
- GitHub Actions: Actions tab → Workflow run → View logs
