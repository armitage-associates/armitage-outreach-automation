# Armitage GOWT Intelligence

LinkedIn news monitoring and FTE tracking for GOWT portfolio companies. Scrapes company LinkedIn posts and employee counts, writes results to Excel, and uploads to OneDrive.

## How It Works

```
   Salesforce                BrightData               Excel + OneDrive
┌──────────────┐         ┌────────────────┐         ┌──────────────────┐
│ Query GOWT   │──────►  │ SERP: resolve  │──────►  │ GOWT_high.xlsx   │
│ High/Medium  │         │ LinkedIn slugs │         │ (per-company tabs)│
│ companies    │         │                │         │                  │
│              │         │ LinkedIn API:  │──────►  │ GOWT_mid_low.xlsx│
│              │         │ scrape posts   │         │ (combined tab)   │
└──────────────┘         │                │         │                  │
                         │ LinkedIn API:  │──────►  │ GOWT_mid_low.xlsx│
                         │ employee counts│         │ (FTE Tracking)   │
                         └────────────────┘         └──────────────────┘
```

## Workflows

| Workflow | Schedule | What it does |
|----------|----------|-------------|
| **Monthly High Scrape** | 28th of every month, midnight AEST | Scrapes LinkedIn posts (past 30 days) for ~24 GOWT High companies. Writes per-company tabs to `GOWT_high.xlsx`. |
| **Quarterly Medium Scrape** | Days 1-5 of Jan/Apr/Jul/Oct, midnight AEST | Scrapes LinkedIn posts (past 90 days) for ~273 GOWT Medium companies. Writes combined tab to `GOWT_mid_low.xlsx`. |
| **Quarterly FTE Scrape** | 6th of Jan/Apr/Jul/Oct, midnight AEST | Scrapes LinkedIn employee counts for 853 companies. Adds new quarter column to `GOWT_mid_low.xlsx` with QoQ change. |
| **Daily Funnel Update** | Daily (currently manual) | Updates Salesforce origination funnel metrics and report date ranges. |
| **OneDrive Keepalive** | Manual (~every 2 months) | Pings OneDrive to keep OAuth refresh token alive. |

All workflows commit to git and upload to OneDrive after each Excel update.

## Project Structure

```
├── linkedin_news_scrape.py               # LinkedIn news scrape (High monthly + Medium quarterly)
├── salesforce.py                         # Salesforce OAuth + REST API client
├── onedrive.py                           # OneDrive upload/download/delete
├── salesforce/
│   ├── fte_scrape.py                     # Quarterly FTE tracking (LinkedIn employee counts)
│   ├── sf_funnel_update.py               # Origination funnel metric upsert
│   ├── sf_update_report_dates.py         # Report date range roll
│   ├── sf_query.py                       # Ad-hoc SOQL query tool
│   ├── export_opportunities_for_dedup.py # Dedup export for Tecala
│   └── ...                               # Other Salesforce utilities
├── data/
│   ├── fte_company_linkedin_map.csv      # LinkedIn slug mapping (853 companies)
│   └── fte_scrape_Q*.json               # Cached FTE scrape results
├── GOWT_high.xlsx                        # High company LinkedIn news (monthly)
├── GOWT_mid_low.xlsx                     # Medium FTE tracking + quarterly news
├── .github/workflows/
│   ├── monthly-scrape-high.yml           # Monthly GOWT High scrape
│   ├── quarterly-scrape-medium-v2.yml    # Quarterly GOWT Medium scrape
│   ├── fte-scrape.yml                    # Quarterly FTE tracking
│   ├── funnel-update.yml                 # Daily origination funnel
│   └── onedrive-keepalive.yml            # OneDrive token refresh
└── requirements.txt
```

## Setup

### Prerequisites

- Python 3.12+
- GitHub repository with Actions enabled

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Set these environment variables (or add to `.env`):

**Required:**

| Variable | Service | Purpose |
|----------|---------|---------|
| `BRIGHTDATA_API_KEY` | BrightData | LinkedIn posts, employee counts, SERP search |
| `SALESFORCE_DOMAIN` | Salesforce | Instance URL |
| `CONSUMER_KEY` | Salesforce | OAuth client credentials |
| `CONSUMER_SECRET` | Salesforce | OAuth client credentials |

**OneDrive upload:**

| Variable | Purpose |
|----------|---------|
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | App registration client ID |
| `AZURE_CLIENT_SECRET` | App registration client secret |
| `ONEDRIVE_REFRESH_TOKEN` | OAuth2 refresh token (expires after 90 days of inactivity) |

## Usage

### LinkedIn News Scrape

```bash
# Full run — High companies (monthly)
python linkedin_news_scrape.py --priority high

# Full run — Medium companies (quarterly)
python linkedin_news_scrape.py --priority medium

# Test with 2 companies, don't write Excel
python linkedin_news_scrape.py --priority high --limit 2 --dry-run

# Multi-job workflow (used by GitHub Actions)
python linkedin_news_scrape.py --priority medium --import-only --slice 1/5
python linkedin_news_scrape.py --priority medium --scrape-only --batch 1/11
python linkedin_news_scrape.py --priority medium --deliver-only
```

### FTE Tracking

```bash
# Auto-detect quarter, scrape and update Excel
python salesforce/fte_scrape.py

# Specify quarter
python salesforce/fte_scrape.py --quarter "Q3 2026"

# Replay from cached results
python salesforce/fte_scrape.py --from-cache data/fte_scrape_Q2_2026.json
```

## Excel Output

### GOWT_high.xlsx (monthly)

24 tabs, one per company. Each tab:

| Date Posted | Title | Post Text |
|-------------|-------|-----------|
| 2026-06-15 | ... | ... |

Entire workbook replaced each month.

### GOWT_mid_low.xlsx

**FTE Tracking sheet** — employee counts with quarterly columns and QoQ change.

**{Quarter} News sheet** — combined LinkedIn posts for all Medium companies:

| Company | Location | LinkedIn Posts | LinkedIn URL |
|---------|----------|---------------|-------------|
| ... | ... | [date] post text | ... |

News sheet replaced each quarter.

## External Services

| Service | Purpose | Cost estimate |
|---------|---------|--------------|
| BrightData SERP | Resolve LinkedIn company slugs | ~$0.003/query |
| BrightData LinkedIn Posts | Scrape company posts | ~$0.05/company |
| BrightData LinkedIn Company Profile | Employee counts (FTE) | ~$0.0025/company |
| Salesforce | Company list (SOQL queries) | Included |
| OneDrive | Excel file backup | Included |

## Troubleshooting

### BrightData: "Customer is not active"
Account has expired or run out of credit. Log into https://brightdata.com/cp to check.

### Salesforce: Authentication failure
Update `CONSUMER_KEY` and `CONSUMER_SECRET` in GitHub Secrets.

### OneDrive: Refresh token expired
The token expires after 90 days of inactivity. Re-run the auth flow to get a new one. The keepalive workflow prevents this if run every ~2 months.

### GitHub Actions: Workflow did not run
GitHub skips scheduled workflows if the repo has no activity for 60 days. Make a commit or trigger manually.

## License

Proprietary — Armitage Associates
