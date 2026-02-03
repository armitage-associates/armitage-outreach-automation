# Armitage News Scraper

Automated growth intelligence pipeline that discovers, analyzes, and delivers company growth signals. The system scrapes news articles and LinkedIn posts for target companies, identifies growth indicators using AI, generates personalized LinkedIn reachout messages, and distributes formatted reports via email.

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
 LinkedIn Post Scraping (Playwright) ──> data/output/{company} Linkedin Posts.csv
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
│   └── linkedin_scraper.py          # LinkedIn post scraping via Playwright (guest access)
├── data/
│   ├── input/companies.csv          # Target companies list
│   └── output/                      # Generated JSON reports and CSV files
└── cron.txt                         # Cron schedule definition
```

## Setup

### Prerequisites

- Python 3.12+
- Playwright browsers (`playwright install --with-deps chromium`)

### Installation

```bash
pip install -r requirements.txt
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
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o-mini) |
| `PERPLEXITY_API_KEY` | Perplexity AI API key (sonar-pro) |
| `FIRMABLE_API_KEY` | Firmable API key for company enrichment |
| `SERP_API_KEY` | SerpAPI key for Google Search |
| `SALESFORCE_DOMAIN` | Salesforce instance URL (e.g., `https://yourorg.my.salesforce.com`) |
| `SALESFORCE_USERNAME` | Salesforce login email |
| `SALESFORCE_PASSWORD` | Salesforce password |
| `SALESFORCE_SECURITY_TOKEN` | Salesforce security token |
| `CONSUMER_KEY` | Salesforce Connected App consumer key (OAuth) |
| `CONSUMER_SECRET` | Salesforce Connected App consumer secret (OAuth) |
| `SMTP_USER` | SMTP username (email address) |
| `SMTP_PASSWORD` | SMTP password (app password for Gmail) |
| `SENDER_EMAIL` | Sender email (defaults to `SMTP_USER`) |
| `ALERT_EMAIL` | Alert recipient for errors (comma-separated) |

### Input

Add target companies to `data/input/companies.csv`:

```csv
company,location
Partmax,Melbourne
GRC Solutions,Sydney
```

## Usage

### Run the full pipeline

```bash
python main.py
```

This will:
1. Read companies from `data/input/companies.csv`
2. Retrieve company info (website URL, LinkedIn ID, industry)
3. Scrape news articles via Perplexity AI
4. Scrape LinkedIn posts via Playwright (no login required — uses guest access with anti-detection)
5. Analyze posts with OpenAI, filter for growth signals, and generate a reachout message
6. Send a digest email to configured recipients

### Run individual components

```bash
# Scrape all companies
python scraper.py

# Summarize LinkedIn posts for a single company
python summarizer.py

# Send digest email from existing output data
python email_client.py recipient@example.com

# Sync data to Salesforce
python salesforce.py
```

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
      "date": "20/01/2026 - 5d"
    }
  ],
  "message": "AI-generated LinkedIn reachout message...",
  "linkedin_url": "https://www.linkedin.com/company/..."
}
```

## Scheduling

The pipeline is configured to run weekly via a system cron job. The schedule is defined in `cron.txt`:

```
0 12 * * 0  # Every Sunday at noon
```

To install the cron job:

```bash
crontab cron.txt
```

To verify it was installed:

```bash
crontab -l
```

The cron job uses the project's virtual environment Python interpreter and logs output to `cron.log` in the project directory. Check this file to debug any issues with scheduled runs:

```bash
tail -f cron.log
```

## Tools & APIs

| Tool | Purpose |
|---|---|
| [OpenAI](https://openai.com/) | Post analysis and reachout message generation (GPT-4o-mini) |
| [Perplexity AI](https://perplexity.ai/) | News article discovery (sonar-pro) |
| [SerpAPI](https://serpapi.com/) | Google Search for company URLs |
| [Firmable](https://firmable.com/) | Company data enrichment |
| [Playwright](https://playwright.dev/) | LinkedIn browser automation |
| [Salesforce](https://salesforce.com/) | CRM data sync |
