# Armitage Outreach Automation - User Manual

## What This System Does

This system automatically researches companies in your Salesforce pipeline and delivers growth intelligence reports. Every month, it:

1. Pulls your target companies from Salesforce (from the "GOWT Ultra High's" and "GOWT High's" dashboard reports)
2. Searches for recent news about each company (last 30 days)
3. Scrapes each company's LinkedIn page for recent posts
4. Scrapes the primary contact's personal LinkedIn for recent posts
5. Uses AI to identify growth signals, write a suggested LinkedIn outreach message, and recommend action items
6. Pushes the results back into Salesforce (on each Opportunity record)
7. Emails a digest report to each Opportunity owner with their assigned companies

---

## How It Runs

The system runs automatically via GitHub Actions on the **25th of every month** at midnight UTC (10am AEST).

You can also trigger it manually:
1. Go to your GitHub repository
2. Click the **Actions** tab
3. Click **Run Main Script** on the left
4. Click the green **Run workflow** button

To cancel a running pipeline:
1. Go to the **Actions** tab
2. Click the running workflow
3. Click **Cancel workflow** in the top right

---

## What You Receive

Each Salesforce Opportunity owner receives one email containing a digest of all their assigned companies. Each company section includes:

- **News & Articles** - Recent news from Australian business media
- **LinkedIn Posts** - Recent company LinkedIn activity flagged as growth signals
- **Contact Activity** - The primary contact's personal LinkedIn posts
- **Potential Actions** - 5-7 recommended next steps for analysts
- **Suggested LinkedIn Reachout** - A ready-to-send connection message

The same information is also written directly into Salesforce on each Opportunity record (in the Growth News, Growth Actions, and Contact Activity fields).

---

## How Long It Takes

The full pipeline for ~60 companies takes approximately **4-5 hours**. This is because:
- Each company takes ~2-3 minutes to scrape and analyse
- There is a 2-minute cooldown between companies to avoid API rate limits
- The work is split across 3 sequential jobs

---

## External Services Used

The system depends on several external services. If any one fails, the system continues with whatever data it can get (it does not stop entirely).

| Service | What It Does | Website |
|---------|-------------|---------|
| **Salesforce** | Source of companies and destination for results | salesforce.com |
| **Perplexity AI** | Searches for recent news articles | perplexity.ai |
| **BrightData** | Scrapes LinkedIn company and contact pages | brightdata.com |
| **OpenAI** | Analyses data and writes summaries/messages | openai.com |
| **Firmable** | Looks up company details (HQ, industry, LinkedIn ID) | firmable.com |
| **SerpAPI** | Google search to find company websites and contact LinkedIn profiles | serpapi.com |
| **Gmail SMTP** | Sends the email digests | gmail.com |

---

## Things That Can Break (and How to Fix Them)

### 1. BrightData: "Customer is not active"

**What it looks like:**
```
API error 400: Customer is not active
```

**What it means:** Your BrightData account has expired, run out of credit, or been suspended.

**How to fix:**
1. Log into https://brightdata.com/cp
2. Check your account status and billing
3. Add funds or reactivate your plan

**Impact if not fixed:** No LinkedIn posts will be scraped. News articles and AI analysis still work.

---

### 2. Salesforce: Authentication failure

**What it looks like:**
```
Salesforce authentication failed
```
or
```
INVALID_SESSION_ID
```

**What it means:** Your Salesforce credentials or security token have expired or changed.

**How to fix:**
1. Go to your GitHub repository > **Settings** > **Secrets and variables** > **Actions**
2. Update these secrets with current values:
   - `SALESFORCE_PASSWORD`
   - `SALESFORCE_SECURITY_TOKEN`
   - `CONSUMER_KEY` / `CONSUMER_SECRET` (if the connected app was recreated)
3. To get a new security token: In Salesforce, go to **Settings** > **Reset My Security Token**

**Impact if not fixed:** No companies are imported and the pipeline does nothing.

---

### 3. OpenAI: Rate limit or API key invalid

**What it looks like:**
```
openai.RateLimitError: Rate limit reached
```
or
```
openai.AuthenticationError: Incorrect API key
```

**What it means:** Your OpenAI API key is wrong, expired, or you've hit your usage limit.

**How to fix:**
1. Go to https://platform.openai.com/api-keys
2. Check your key is still active and your account has credit
3. If needed, generate a new key and update the `OPENAI_API_KEY` secret in GitHub

**Impact if not fixed:** No AI summaries, reachout messages, or action items are generated. Raw news and LinkedIn data is still collected.

---

### 4. Perplexity: API key invalid or quota exceeded

**What it looks like:**
```
401 Unauthorized
```
or
```
429 Too Many Requests
```

**What it means:** Your Perplexity API key is wrong or you've used up your monthly quota.

**How to fix:**
1. Go to https://www.perplexity.ai/settings/api
2. Check your API key and usage limits
3. If needed, generate a new key and update `PERPLEXITY_API_KEY` in GitHub Secrets

**Impact if not fixed:** No news articles are found. LinkedIn scraping and AI analysis of LinkedIn posts still work.

---

### 5. Gmail: Authentication failed

**What it looks like:**
```
SMTPAuthenticationError: Username and Password not accepted
```

**What it means:** Your Gmail app password is wrong or has been revoked.

**How to fix:**
1. Go to https://myaccount.google.com/apppasswords
2. Generate a new app password (you need 2-Step Verification enabled first)
3. Update the `SMTP_PASSWORD` secret in GitHub

**Impact if not fixed:** No email digests are sent. Data is still pushed to Salesforce.

---

### 6. Firmable: API key invalid

**What it looks like:**
```
Firmable API error: 401
```

**What it means:** Your Firmable API key is wrong or the account is inactive.

**How to fix:**
1. Log into Firmable and check your API key
2. Update `FIRMABLE_API_KEY` in GitHub Secrets

**Impact if not fixed:** Company enrichment data (HQ, industry, LinkedIn ID) will be missing. The system continues but LinkedIn scraping may be less accurate without the LinkedIn company ID.

---

### 7. SerpAPI: API key invalid or quota exceeded

**What it looks like:**
```
SerpAPI error: Invalid API key
```

**What it means:** Your SerpAPI key is wrong or you've used all your monthly searches.

**How to fix:**
1. Go to https://serpapi.com/manage-api-key
2. Check your key and remaining searches
3. If needed, update `SERP_API_KEY` in GitHub Secrets

**Impact if not fixed:** The system cannot find company websites or contact LinkedIn profiles. Most companies will be skipped entirely.

---

### 8. GitHub Actions: Workflow did not run on the 25th

**What it means:** GitHub scheduled workflows can sometimes be delayed or skipped if the repository has had no recent activity (pushes or commits) in the last 60 days.

**How to fix:**
- Make sure the repository has at least one commit or push within any 60-day window
- You can always run it manually from the Actions tab as a backup

---

### 9. GitHub Actions: Job timed out

**What it looks like:**
```
The job running on runner ... has exceeded the maximum execution time of 350 minutes
```

**What it means:** A scrape job took longer than 5 hours 50 minutes (usually because BrightData was slow to respond).

**How to fix:**
- This is usually a temporary issue. Trigger the workflow again manually.
- If it keeps happening, BrightData may be experiencing delays. Check their status page.

---

### 10. A company shows "No results" or missing data

**What it means:** The company may be too small or too new to have recent news or LinkedIn activity, or the company name in Salesforce doesn't match what's publicly available.

**How to fix:**
- Check that the company name in Salesforce matches how it appears on their website and LinkedIn
- Some companies genuinely have no recent activity - this is normal

---

## How to Update API Keys

All API keys and passwords are stored as GitHub Secrets (they are never visible in the code).

To update a secret:
1. Go to your GitHub repository
2. Click **Settings** (top menu bar)
3. Click **Secrets and variables** > **Actions** (left sidebar)
4. Find the secret you need to update
5. Click the pencil icon to edit
6. Paste the new value and click **Update secret**

The secrets you may need to update:

| Secret Name | Service | Where to Get a New One |
|------------|---------|----------------------|
| `OPENAI_API_KEY` | OpenAI | https://platform.openai.com/api-keys |
| `PERPLEXITY_API_KEY` | Perplexity | https://www.perplexity.ai/settings/api |
| `FIRMABLE_API_KEY` | Firmable | Firmable dashboard |
| `SERP_API_KEY` | SerpAPI | https://serpapi.com/manage-api-key |
| `BRIGHTDATA_API_KEY` | BrightData | https://brightdata.com/cp |
| `SALESFORCE_PASSWORD` | Salesforce | Your Salesforce login password |
| `SALESFORCE_SECURITY_TOKEN` | Salesforce | Salesforce > Settings > Reset My Security Token |
| `CONSUMER_KEY` | Salesforce | Salesforce connected app settings |
| `CONSUMER_SECRET` | Salesforce | Salesforce connected app settings |
| `ACCESS_TOKEN` | Salesforce | Salesforce connected app settings |
| `SMTP_USER` | Gmail | Your Gmail address |
| `SMTP_PASSWORD` | Gmail | https://myaccount.google.com/apppasswords |
| `SENDER_EMAIL` | Gmail | Your Gmail address (usually same as SMTP_USER) |

---

## How to Check If a Run Succeeded

1. Go to your GitHub repository > **Actions** tab
2. Click the most recent workflow run
3. You'll see the jobs: **import**, **scrape-1**, **scrape-2**, **scrape-3**, **deliver**
4. Green checkmark = success, red X = failure, yellow circle = in progress, grey circle = skipped

If a job failed:
1. Click on the failed job
2. Expand the failed step to see the error message
3. Refer to the troubleshooting section above

---

## How to Test With a Single Company

If you want to test the system with just one company before running the full pipeline:

1. Go to the workflow file (`.github/workflows/run-schedule.yml`)
2. Set `TEST_COMPANY` to a company name (e.g., `TEST_COMPANY: Smartsoft`)
3. Set the `test-single` job's `if:` to `true`
4. Set the `import` job's `if:` to `false`
5. Push the changes or trigger manually

This will only scrape that one company and skip the full pipeline.

---

## Quick Reference: Monthly Checklist

Before the 25th each month, verify:

- [ ] All API accounts are active and have credit/quota remaining
- [ ] Salesforce credentials haven't changed
- [ ] Gmail app password hasn't been revoked
- [ ] The GitHub repository has had recent activity (within last 60 days)
- [ ] Check the Actions tab after the 25th to confirm the run completed successfully
