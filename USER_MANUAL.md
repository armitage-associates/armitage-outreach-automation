# Armitage GOWT Intelligence - User Manual

## What This System Does

This system monitors LinkedIn activity for companies in your GOWT pipeline. It runs automatically and delivers results to two Excel files on OneDrive.

**GOWT High companies (~24)** — scraped monthly for LinkedIn posts from the past 30 days. Each company gets its own tab in `GOWT_high.xlsx`.

**GOWT Medium companies (~273)** — scraped quarterly for LinkedIn posts from the past 90 days. All companies appear in a single tab in `GOWT_mid_low.xlsx`.

**FTE tracking (~853 companies)** — scraped quarterly for LinkedIn employee counts. Shows quarter-over-quarter headcount changes in `GOWT_mid_low.xlsx`.

---

## When It Runs

| What | When | Output |
|------|------|--------|
| High company LinkedIn news | 28th of every month | `GOWT_high.xlsx` on OneDrive |
| Medium company LinkedIn news | Days 1-5 of Jan/Apr/Jul/Oct | `GOWT_mid_low.xlsx` on OneDrive |
| FTE employee counts | 6th of Jan/Apr/Jul/Oct | `GOWT_mid_low.xlsx` on OneDrive |

All times are midnight AEST. Results appear on OneDrive within a few hours of the scheduled time.

---

## Where to Find Results

Both Excel files are uploaded to the **GOWT Data Scrape** folder in OneDrive (Arlen Cram's account).

### GOWT_high.xlsx

- One tab per company (24 tabs)
- Each tab shows LinkedIn posts: Date Posted, Title, Post Text
- Replaced entirely each month with fresh data

### GOWT_mid_low.xlsx

- **FTE Tracking** sheet — employee counts by quarter with change percentages
- **{Quarter} News** sheet (e.g. "Q3 2026 News") — LinkedIn posts for all Medium companies
- FTE columns accumulate over time; News sheet is replaced each quarter

---

## How Companies Are Selected

Companies are pulled from Salesforce each time the scrape runs. The filter is:

- **Stage** = "8. Good opportunity wrong timing"
- **GOWT Priority** = "High" or "Medium"
- **Transaction type** ≠ "8. Portfolio company bolt-on"

If a company is added to or removed from the GOWT pipeline in Salesforce, the next scrape will pick up the change automatically.

---

## External Services

| Service | What it does |
|---------|-------------|
| **Salesforce** | Source of company list |
| **BrightData** | Scrapes LinkedIn pages for posts and employee counts |
| **OneDrive** | Stores the Excel files |

No AI analysis, no news scraping, no email delivery. Just LinkedIn data straight to Excel.

---

## Things That Can Break

### 1. BrightData account expired
**Symptom:** No LinkedIn data in the Excel files.
**Fix:** Log into https://brightdata.com/cp and check your account status / billing.

### 2. Salesforce credentials changed
**Symptom:** Workflow fails at the import step.
**Fix:** Update `CONSUMER_KEY` and `CONSUMER_SECRET` in GitHub > Settings > Secrets.

### 3. OneDrive token expired
**Symptom:** Excel files not appearing on OneDrive (but still committed to git).
**Fix:** Re-run the OAuth auth flow to get a new refresh token. Update `ONEDRIVE_REFRESH_TOKEN` in GitHub Secrets.

### 4. GitHub Actions stopped running
**Symptom:** No updates for a month+.
**Fix:** GitHub disables scheduled workflows after 60 days of repo inactivity. Make any commit to re-enable, or trigger manually from the Actions tab.

---

## How to Trigger a Run Manually

1. Go to the GitHub repository
2. Click the **Actions** tab
3. Select the workflow you want to run (e.g. "Monthly GOWT High Scrape")
4. Click **Run workflow**
5. Optionally enter a month/quarter label, or leave blank to auto-detect

---

## How to Check If a Run Succeeded

1. Go to GitHub > **Actions** tab
2. Click the most recent workflow run
3. Green checkmark = success, red X = failure
4. If failed, click the failed job to see the error message

---

## API Keys / Secrets

All credentials are stored as GitHub Secrets (never visible in code). To update:

1. GitHub > **Settings** > **Secrets and variables** > **Actions**
2. Click the pencil icon next to the secret
3. Paste the new value and click **Update secret**

| Secret | Service | Where to get a new one |
|--------|---------|----------------------|
| `BRIGHTDATA_API_KEY` | BrightData | https://brightdata.com/cp |
| `CONSUMER_KEY` | Salesforce | Salesforce connected app settings |
| `CONSUMER_SECRET` | Salesforce | Salesforce connected app settings |
| `ONEDRIVE_REFRESH_TOKEN` | OneDrive | Re-run OAuth device code flow |
