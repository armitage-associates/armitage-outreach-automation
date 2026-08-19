# CLAUDE.md — Project notes for Claude

This file captures context and conventions for this repo that Claude should know about across sessions.

## Origination Charts

A set of Salesforce reports and dashboards that track deal flow metrics. Built in April 2026.

### Salesforce dashboards

| Dashboard | ID | Developer Name |
|---|---|---|
| Origination weekly dashboard | `01Z8v0000005jFtEAI` | `vPbfpkgbIuiWVczfwOptORVKANCyhS` |
| Origination Charts | `01ZOl000000xbpxMAA` | `wJwRzNTAfffxhzcuuDkwtSqNihDpKW` |

Both live in folder `Sales_and_Marketing_Dashboards` (id `00l0o0000028r7MAAQ`).

Shared report folder used for all our reports: `00D0o0000015sSsEAI`.

Backup of original Origination weekly dashboard: `data/origination_dashboard_backup.json`.

### The 5 reports we built

All live in folder `00D0o0000015sSsEAI`.

| Report name | Report ID | Purpose |
|---|---|---|
| Origination Funnel Chart | `00OOl000005y6HNMAY` | Waterfall funnel on `Funnel_Metric__c` custom object |
| Dealflow by Source (LTM) | `00OOl0000065kZqMAI` | Donut chart grouped by `Pie_Source_Category__c` |
| Dealflow by Industry (LTM) | `00OOl0000065lSfMAI` | Donut chart grouped by `Industry_Grouped__c` |
| Dead Deals by Status (LTM) | `00OOl0000065mN7MAI` | Donut chart on `fid48__c`, filtered to `StageName = '7. Killed'` |
| Dead Deals by Reason (LTM) | `00OOl0000065mOjMAI` | Donut chart grouped by `Kill_Reason_Grouped__c`, filtered to killed deals |

All reports are type `Opportunity`. The 4 LTM pie chart reports use `standardDateFilter` on `CREATED_DATE` with a rolling 365-day window that's refreshed daily (see GitHub Actions below).

### Key Salesforce Opportunity fields used

| Field API name | Label | Purpose |
|---|---|---|
| `StageName` | Stage | Picklist: `0. Complete`, `1. Term sheet`, `2. EOI`, `3. High`, `4. Medium`, `5. Low`, `6. Origination`, `7. Killed`, `8. Good opportunity wrong timing` |
| `fid8__c` | Industry | Picklist used for industry pie chart |
| `fid10__c` | Source type | Multipicklist: `Direct`, `Direct (bolt-on)`, `Intermediated (sell side)` |
| `fid11__c` | Armitage partner | Text — not actually used for "Armitage network" classification; `fid12__c` is |
| `fid12__c` | Direct Source | Text — deals with this field filled in are classified as "Armitage network" in the source pie chart |
| `fid45__c` | Reason for kill for dead deals | Picklist: Too small, Business model, Unsuccessful outreach, No need for capital, Armitage not right partner, Took other investors, etc. |
| `fid48__c` | Status reached for dead deals | Picklist: Introduction pending, Did not connect, Immediate kill, Initial discussions, Initial DD, Indicative offer, Term sheet |
| `Transaction_type__c` | Transaction type | — |
| `Growth_News__c`, `Growth_Actions__c`, `P__c` | Legacy fields (previously populated by old scraper pipeline, no longer updated) |
| `GOWT_Priority__c` | GOWT Priority | Picklist: `High`, `Medium`, `Low` — used to filter companies for LinkedIn news scraping |

### Custom Object: Funnel_Metric__c

Created to store precomputed cumulative funnel values (since native Salesforce reports cannot do cumulative subtraction across groups).

| Field | Type | Notes |
|---|---|---|
| `Name` (Stage Name) | Text | Label like "1. Businesses contacted" (prefix number is for alphabetical sort) |
| `Count__c` | Number(10,0) | Cumulative count for this stage |
| `Sort_Order__c` | Number(2,0) | 1–7 |
| `Stage_Key__c` | Text(50), external ID, unique | Stable key used for upsert (e.g., `businesses_contacted`) |

The object has `enableReports=true` so it appears as report type `CustomEntity$Funnel_Metric__c`.

### Custom formula fields on Opportunity

| Field | Purpose | Formula sketch |
|---|---|---|
| `Is_LTM__c` (checkbox) | True if `CreatedDate >= TODAY()-365`. **NOT currently used** by the 4 pie chart reports (we removed it so the reports can have editable date filters), but still exists on the object | `DATEVALUE(CreatedDate) >= (TODAY() - 365)` |
| `Pie_Source_Category__c` (text) | Buckets Source type + Direct Source into 4 pie slices | If `fid12__c` not blank → "Armitage network"; else `Direct (bolt-on)` / `Direct` / `Intermediated (sell side)` → their outreach categories; else "Other" |
| `Industry_Grouped__c` (text) | Top 8 industries + "Others" | `CASE(TEXT(fid8__c), ... "Others")` |
| `Kill_Reason_Grouped__c` (text) | Top 5 kill reasons + "Others" | `CASE(TEXT(fid45__c), "Unsuccessful outreach", ... , "Others")` |

All formula fields need FLS deployed to the **Admin** profile to be queryable — otherwise they show up in picklistValues but aren't visible via the REST query endpoint.

### The funnel waterfall logic (matches Excel)

Top of funnel = dead deals (`StageName IN ('7. Killed', '8. Good opportunity wrong timing')`) + ALL `0. Complete` deals. Then subtract exits at each stage:

| Funnel stage | Exits subtracted (from fid48__c) |
|---|---|
| 1. Businesses contacted | (top) |
| 2. Initial contact | − "Did not connect" |
| 3. Initial discussions | − "Introduction pending", "Immediate kill" |
| 4. Initial DD | − "Initial discussions" |
| 5. Indicative offers made | − "Initial DD" |
| 6. Term sheets signed | − "Indicative offer" |
| 7. Investments made | − "Term sheet" (= count of `0. Complete`) |

Excel had `Is_LTM__c = false` equivalent (all-time). Our funnel script is also all-time.

### "Armitage network" logic caveat

Looking at an opportunity like "Asoc Vet" that shows `Source type = Direct (bolt-on)` AND is classified as Armitage network — this is correct. The `Pie_Source_Category__c` formula checks `fid12__c` (Direct Source) FIRST. If that field has a person's name, the deal is classified as Armitage network regardless of Source type. The Excel pivot has ~14 specific people in `fid12__c` (Aaron King, Andrew Petering, etc.), and as of April 2026 we found 21 deals with this field filled in LTM.

### Scripts

Located in `salesforce/`:

| Script | Purpose | Run frequency |
|---|---|---|
| `sf_funnel_stages.py` | Ad-hoc discovery of StageName picklist + cumulative funnel preview | Manual |
| `sf_create_funnel.py` | One-time setup: creates the Origination Funnel Chart report and adds it to a dashboard. Uses `data/origination_dashboard_backup.json` to avoid rate limit from live GET | Run once |
| `sf_funnel_setup.py` | **Superseded** — earlier attempt to create `Funnel_Metric__c` via Tooling API (didn't work, Metadata API was used instead) | Not used |
| `sf_funnel_update.py` | Computes the cumulative funnel and upserts 7 rows to `Funnel_Metric__c` via external-id PATCH | Daily |
| `sf_update_report_dates.py` | Rolls the 4 pie chart reports' `standardDateFilter` to `today-365 → today` each day | Daily |

`salesforce.py` (in repo root) has the OAuth client-credentials flow: `get_access_token()`, `sf_get(endpoint, token)`, `sf_patch(endpoint, token, payload)`. All scripts import from there.

### GitHub Actions

`.github/workflows/funnel-update.yml` — "Daily Salesforce Updates"
- Runs daily at `0 0 * * *` UTC (and via `workflow_dispatch`)
- Single job `daily-update` runs both:
  1. `python salesforce/sf_funnel_update.py`
  2. `python salesforce/sf_update_report_dates.py`
- Uses secrets `SALESFORCE_DOMAIN`, `CONSUMER_KEY`, `CONSUMER_SECRET` (same as the monthly scraper workflow)

`.github/workflows/monthly-scrape-high.yml` — "Monthly GOWT High Scrape"
- Runs on the 1st of every month at 14:00 UTC (midnight AEST)
- Queries Salesforce for ~24 GOWT High (Platform) companies, resolves LinkedIn slugs via BrightData SERP, scrapes LinkedIn posts from the past 30 days
- Writes per-company tabs to `GOWT_high.xlsx` (replaces entire workbook each month)
- Commits to git, then uploads to OneDrive

`.github/workflows/quarterly-scrape-medium-v2.yml` — "Quarterly GOWT Medium Scrape"
- Runs days 1-5 of Jan/Apr/Jul/Oct at 14:00 UTC (midnight AEST), one slice per day
- Queries Salesforce for ~273 GOWT Medium companies, resolves LinkedIn slugs, scrapes LinkedIn posts from the past 90 days
- Writes results to a combined `{quarter} News` sheet in `GOWT_mid_low.xlsx` (removes previous quarter's News sheet, appends across days)
- Multi-job: import → 3 parallel scrape jobs → deliver (commit + OneDrive upload)

### Salesforce API gotchas we hit

1. **Dashboard components can't be added via `PUT /analytics/dashboards/{id}`**. The endpoint returns 201 but silently drops new components. We gave up and told the user to add chart widgets via the UI.
2. **Dashboard updates trigger a refresh** which is rate-limited to once per minute. Fetching the dashboard also counts. Workaround: use a local backup file.
3. **Custom object creation via Tooling API `CustomObject` endpoint doesn't work** (no `createable` fields). Use the Metadata API deploy (multipart zip with `requests-toolbelt`) instead.
4. **Metadata deploy with `testLevel: NoTestRun`** is blocked in production orgs. Omit the flag.
5. **Custom fields deployed via `.object` file don't propagate immediately**. They need a separate deploy with the field in package.xml AND profile field permissions (`fieldPermissions` in a `.profile` file) — otherwise the field exists but is invisible to the API user. The connected user (Arlen Cram) has the `Admin` profile.
6. **Reports created via API land in the API user's private folder**. We patch `folderId` to the shared folder `00D0o0000015sSsEAI` so Michelle Ye (the dashboard's running user) can see them.
7. **Multipicklist fields cannot be grouped in SOQL** (`fid10__c`). Fetch raw records and aggregate in Python.
8. **`standardDateFilter` valid durations** don't include `LAST_N_DAYS:365` or `LAST_N_MONTHS:12`. Only fiscal year, calendar year, quarter, month, week, day, and `LAST_N_DAYS:7/30/60/90/120`. For rolling 12 months we use `CUSTOM` with explicit dates refreshed daily by the script.
9. **Dashboard filters via Metadata API**: we got the XML structure working (`<dashboardFilters>` at dashboard level with `<dashboardFilterOptions>` inside, and `<dashboardFilterColumns>` × N inside each `<dashboardComponent>`), but runtime application fails with *"We can't apply one or more filters because of changes to the dashboard or its source reports."* — a cache sync issue I couldn't resolve programmatically. Re-saving the dashboard manually in the UI usually fixes it. **We reverted to no dashboard filters.**
10. **Run-page filter changes are ephemeral.** They only affect the current report view — the dashboard widget still shows the saved default. To persist, users have to `Save` or `Save As`.

### Salesforce report type name conventions

- Standard Opportunity reports: `reportType.type = "Opportunity"`
- Custom object reports: `CustomEntity$Funnel_Metric__c` (dollar-escaped `$`)
- Custom object needs `enableReports=true` before the report type appears

### Column name conventions inside reports

- `CREATED_DATE` — alias used in `standardDateFilter` and in `reportFilters` when filtering Created Date
- `STAGE_NAME` — alias for StageName filter
- `OPPORTUNITY_NAME` — alias for Name detail column
- Custom fields: `Opportunity.fid48__c`, `Opportunity.Pie_Source_Category__c`, etc. (object-qualified)
- For grouping columns on a `Funnel_Metric__c` report, use `CUST_NAME` for the Name field (Salesforce's internal alias)

### How to change a report's date range interactively

1. Open Origination Charts dashboard → click **View Report** on any widget
2. Open the Filters panel (funnel icon top-right)
3. Click `Created Date` → pick new Start / End dates from the calendar
4. Click **Apply** — this is view-only (doesn't persist)
5. To persist: `Edit` → `Save` (overwrites default) or `Save As` (new named report)
6. Next day, the daily script rolls the default forward anyway

### Files not to touch unless the user asks

- `salesforce.py` — shared Salesforce client; has the OAuth flow and helpers that all scripts import
- `data/origination_dashboard_backup.json` — pre-any-edits snapshot of the Origination weekly dashboard

### Two relevant Excel files

- `data/armitage_origination_metrics.xlsx` — source of truth for the funnel waterfall logic (Sheet2 has the cumulative formulas; Raw Data has the ~7400 opportunities)
- `data/piechart_metrics.xlsx` — source of truth for the 4 pie charts (Pivot sheet has the breakdowns; Deal list export has ~7375 rows)

Both Excel files were frozen snapshots. Numbers in our live dashboards will drift as Salesforce data changes, but the **logic** matches exactly.

## LinkedIn News Scrape

Scrapes LinkedIn company posts for GOWT High and Medium companies. Built in June 2026, replacing the old multi-source pipeline (Perplexity + OpenAI + Salesforce push).

### How it works

1. Query Salesforce for GOWT companies: `StageName = '8. Good opportunity wrong timing' AND GOWT_Priority__c = '{priority}' AND Transaction_type__c != '8. Portfolio company bolt-on'`
2. Resolve LinkedIn company slugs via BrightData SERP (searches `"{company} site:linkedin.com/company"`)
3. Scrape LinkedIn posts via BrightData dataset `gd_lyy3tktm25m4avu764` with configurable date range
4. Write to Excel and upload to OneDrive

### Company counts (as of June 2026)

| Priority | Count | Scrape frequency | Date range |
|---|---|---|---|
| High | 24 | Monthly (1st of every month) | Past 30 days |
| Medium | 273 | Quarterly (days 1-5 of quarter months) | Past 90 days |

### Script

`linkedin_news_scrape.py` — main entry point for both High and Medium scrapes.

| Flag | Purpose |
|---|---|
| `--priority high\|medium` | Required. Which companies to scrape |
| `--slice 1/5` | For Medium: which slice of companies to process (multi-day workflow) |
| `--batch 1/3` | For parallel jobs within a slice |
| `--quarter "Q3 2026"` | Override quarter label (Medium) |
| `--month "Jun 2026"` | Override month label (High) |
| `--limit N` | Only process first N companies (testing) |
| `--dry-run` | Scrape but don't write Excel |
| `--import-only` | Just query SF + resolve slugs, write CSV |
| `--scrape-only` | Read CSV, scrape, write output JSONs |
| `--deliver-only` | Read output JSONs, write Excel, upload OneDrive |

### Excel output

| File | Structure | Replaced |
|---|---|---|
| `GOWT_high.xlsx` | One tab per company (24 tabs). Columns: Date Posted, Title, Post Text | Every month |
| `GOWT_mid_low.xlsx` | Combined `{quarter} News` tab. Columns: Company, Location, LinkedIn Posts, LinkedIn URL | Every quarter |

### External services used

- **Salesforce** — company list (SOQL query)
- **BrightData SERP** — LinkedIn slug resolution (~$0.003/query)
- **BrightData LinkedIn Posts** — dataset `gd_lyy3tktm25m4avu764` (~$0.05/company)
- **OneDrive** — Excel upload after every update

## Opportunity dedup export

Used to send our existing Salesforce opportunities to an external research/enrichment software (Tecala) so they can dedupe their results against our existing pipeline.

### Script

`salesforce/export_opportunities_for_dedup.py` — exports all 7,515+ opportunities to `data/opportunities_for_dedup.csv` with identifier fields used for matching.

Run with: `python salesforce/export_opportunities_for_dedup.py`

### Current export columns

| CSV column | SF source | Population |
|---|---|---|
| `company_name` | `Name` | 100% |
| `website` | `Company_Website__c` | 94% |
| `address` | `fid5__c` | 100% (city/state granularity, not full street) |
| `industry` | `fid8__c` | 100% |
| `end_market` | `fid9__c` | 99% |
| `contact_linkedin` | `Contact_LinkedIn__c` | 71% |
| `primary_contact_name` | via `OpportunityContactRoles WHERE IsPrimary = true` subquery | ~76% |

### Fields the user explicitly excluded from the export

- **Opportunity ID** — round-trip identifier; user didn't want it
- **Employee count** (`fid50__c`, 60% pop)
- **Revenue estimate** (`fid14__c`, 82% pop)

If the dedup workflow ever needs more matching signal, these are the obvious additions.

### External tool reference: Tecala fields

Tecala's enrichment output (see `data/tecala_sample.csv`) includes these columns; we do NOT have SF equivalents for the ones marked ✗:

- name ✓ (`Name`)
- description, productsSummary ✗ (we have `Description`, `Company__c` but partially populated)
- domain ✓ (derive from website)
- website ✓ (`Company_Website__c`)
- abn ✗ — **no ABN field on Opportunity. Strongest unique identifier we're missing.** If we ever want to track ABN for dedup, would need a new custom field.
- addressFull/Street/Suburb/State/Postcode/Country ✗ — our `fid5__c` is one string at city/state level; theirs is fully structured
- employeeCount ✓ (`fid50__c`)
- revenue ✓ (`fid14__c`)
- entityType, ownershipStructure, yearsInOperation, primaryServices, certifications ✗
- parentCompany ✓-ish (`fid40__c` Bolt-on for)
- targetMarket ✓ (`fid9__c` End market reference)
- primaryContactName/Title/Email/Phone/LinkedIn — partial via Contact relationship
- secondaryContact* ✗ — SF only tracks one primary contact per opp
- firstSeenAt ✓ (`CreatedDate`)
- lastEnrichedAt ✓ (`LastModifiedDate`)

### Useful Opportunity field reference (for future dedup or matching work)

Beyond the fields documented in the Origination Charts section, here are other identifier-relevant fields with their population rates as of April 2026:

| Field | Label | Population |
|---|---|---|
| `Name` | Company Name | 100% |
| `Company_Website__c` (URL) | Company Website | 94.2% |
| `fid5__c` | Address (single string) | 100% |
| `fid8__c` | Industry (picklist) | 100% |
| `fid9__c` | End market reference | 99.3% |
| `fid14__c` | Revenue estimate | 82.1% |
| `fid50__c` | Employees | 59.8% |
| `Contact_LinkedIn__c` (URL) | Contact LinkedIn | 71.0% |
| `ContactId` (reference to Contact) | Contact link | 76.0% |
| `fid6__c` (reference to Contact) | Primary Contact | 50.7% |
| `AccountId` (reference to Account) | Account link | 100% |
| `fid4__c` | Account Name (denormalized) | 25.7% |
| `Description` (textarea) | Description | partial |
| `Company__c` (textarea) | Company Overview | 22.7% |
| `Business_Industry_Overview__c` (textarea) | Business/Industry Overview | partial |
| `fid15__c` | EBITDA estimate | 22.4% |

The Account object has standard fields (`Website`, `BillingAddress`, `Phone`, `Industry`, `Description`) but in this org most are empty — Opportunity has the better signal for company identification.

## FTE Tracking

Quarterly LinkedIn employee count tracking for GOWT Medium/Low companies. Built in May 2026.

### How it works

1. Pull 853 GOWT Medium/Low companies with verified LinkedIn slugs from `data/fte_company_linkedin_map.csv`
2. Scrape employee counts via BrightData LinkedIn Company Profile dataset (`gd_l1vikfnt1wgvvqz95w`) in batches of 50
3. Insert a new quarter column in `GOWT_mid_low.xlsx` and compute quarter-over-quarter change

The Salesforce baseline (`fid50__c`) is in column 8 (H). Each quarterly scrape adds a new column before the Change columns. The Change columns always compare the latest quarter against the immediately preceding one (QoQ), not against the baseline.

Column layout: A=Company Name, B=Location, C=Owner, D=Priority, E=Industry (SF), F=Website, G=LinkedIn URL, H=Baseline FTE (SF), I+=quarter columns, then Change and Change %.

### Script

`salesforce/fte_scrape.py` — scrapes LinkedIn employee counts and updates the Excel.

| Flag | Purpose |
|---|---|
| `--quarter "Q3 2026"` | Override quarter label (auto-detected if omitted) |
| `--dry-run` | Scrape and compute but don't write to Excel |
| `--from-cache path.json` | Skip scraping, load results from a cached JSON file |

Scrape results are always cached to `data/fte_scrape_Q{n}_{year}.json` so they can be replayed without re-scraping.

### Data files

| File | Purpose |
|---|---|
| `GOWT_mid_low.xlsx` | FTE tracking Excel. "FTE Tracking" sheet has employee counts; `{quarter} News` sheet has scraped news/posts with growth signals. Also uploaded to OneDrive after each update. |
| `data/fte_company_linkedin_map.csv` | 853 companies with verified LinkedIn slugs. Columns: company_name, location, industry, website, linkedin_slug, linkedin_url, employees_sf, slug_source |
| `data/fte_scrape_Q{n}_{year}.json` | Cached scrape results (slug → employee count) |

### GitHub Actions

`.github/workflows/fte-scrape.yml` — "Quarterly FTE Scrape"
- Runs quarterly on the 1st of Jan/Apr/Jul/Oct at 00:00 UTC (and via `workflow_dispatch` with optional quarter override)
- Scrapes all 853 companies, updates the Excel, commits to git, then uploads to OneDrive
- Also refreshes the Owner column from Salesforce
- Uses secrets `BRIGHTDATA_API_KEY`, `SALESFORCE_DOMAIN`, `CONSUMER_KEY`, `CONSUMER_SECRET`, plus OneDrive secrets (~$2.13 per run)

## OneDrive Integration

After each workflow updates `GOWT_mid_low.xlsx` or `GOWT_high.xlsx`, it commits to git (source of truth) then uploads a copy to OneDrive via Microsoft Graph API.

### Setup

- Azure AD app "Armitage CI OneDrive" (single tenant, delegated `Files.ReadWrite` permission)
- Uses OAuth2 refresh token flow — no admin consent required
- OneDrive folder: `GOWT Data Scrape/` in Arlen Cram's personal OneDrive

### Script

`onedrive.py` — upload, download, and delete files from the OneDrive folder.

| Command | Purpose |
|---|---|
| `python onedrive.py upload GOWT_mid_low.xlsx` | Upload/overwrite file in OneDrive |
| `python onedrive.py download GOWT_mid_low.xlsx` | Download file from OneDrive |
| `python onedrive.py delete GOWT_mid_low.xlsx` | Delete file from OneDrive |

### Environment variables / secrets

| Variable | Value |
|---|---|
| `AZURE_TENANT_ID` | Armitage Associates tenant ID |
| `AZURE_CLIENT_ID` | App registration client ID |
| `AZURE_CLIENT_SECRET` | App registration client secret |
| `ONEDRIVE_REFRESH_TOKEN` | OAuth2 refresh token (expires if unused for 90 days; re-run `get_token.py` to refresh) |

### Caveat

The refresh token expires after 90 days of inactivity. Since the FTE scrape runs on the 1st of each quarter month (~90 day intervals), it keeps the token alive. If it ever expires, re-run the device code / auth code flow to get a new one.

### LinkedIn slug sources

Slugs were resolved via Firmable (729 companies) and BrightData SERP fallback (134 companies), then filtered with name-similarity matching (threshold 0.35) to exclude false positives. 23 companies have no LinkedIn presence (mostly solo practices). 57 suspicious matches were excluded.

## Salesforce Connection & Access

There are **two independent ways** to reach the Salesforce org. They authenticate as different users and are used in different places — don't conflate them.

### 1. Client-credentials OAuth (used by CI and this repo's scripts)

`salesforce.py` authenticates with the OAuth **client-credentials** flow via three env vars: `SALESFORCE_DOMAIN`, `CONSUMER_KEY`, `CONSUMER_SECRET`. Connected user is Arlen Cram (Admin profile). This is what every script and GitHub Actions workflow uses. Helpers: `get_access_token()`, `sf_get()`, `sf_patch()`.

- **In CI:** the three values are GitHub Actions secrets — connection works there.
- **In Claude Code on the web (remote sessions):** the container is ephemeral and starts with **no** Salesforce credentials, and no `.env` (only `.env.sample`). Two things must be set on the **cloud environment** (claude.ai/code → environment settings) for live queries to work:
  1. **Network access = Custom** with these **Allowed domains** (the default `Trusted` policy blocks Salesforce egress — the proxy returns `403 CONNECT` and no request reaches the org):
     ```
     *.my.salesforce.com
     *.salesforce.com
     ```
     Keep **"Also include default list of common package managers"** checked, or the hook's `pip install` breaks.
  2. **Environment variables:** `SALESFORCE_DOMAIN` (= `https://d0o0000015ssseai.my.salesforce.com`, the org's My Domain), `CONSUMER_KEY`, `CONSUMER_SECRET` (from the **Salesforce API 1** External Client App: Setup → External Client App Manager → Salesforce API 1 → Settings → OAuth → Consumer Key and Secret). ⚠️ Cloud environments have **no secrets store** — these sit in plaintext, readable by anyone who uses the environment. Rotate the secret if it's been exposed.

  A `SessionStart` hook (`.claude/hooks/session-start.sh`, registered in `.claude/settings.json`) installs `requirements.txt` and runs `salesforce/verify_connection.py`, which prints `[OK]` / `[FAIL]` / `[SKIP]`. Run it manually any time: `python salesforce/verify_connection.py`.

### 2. Salesforce CLI (Arlen's local Windows machine)

Arlen's Windows box has Node v24 + `@salesforce/cli` installed globally, with the org authenticated as `arlen.cram@armitage.com.au`. Live queries there run via PowerShell:

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User"); sf data query --query "YOUR SOQL HERE" --target-org arlen.cram@armitage.com.au --json
```

This is **local only** — remote Claude sessions cannot reach it (no `sf` CLI in the container, and the org auth lives in the local machine's credential store). For ad-hoc exploration Arlen runs SOQL here and pastes results back.

### Org schema — Account custom fields

These live on the **Account** object (distinct from the similarly-named Opportunity fields below):

| Field API name | Meaning | Notes |
|---|---|---|
| `fid18__c` | Revenue estimate | Nominally $m, but **inconsistent** — some records store raw dollars. Use judgement. |
| `fid20__c` | EBITDA estimate | $m |
| `fid2__c` | Description | |
| `fid4__c` | Industry | Standard `Industry` / `Type` fields are often unpopulated — use these custom fields. |
| `fid48__c` | Status | Picklist e.g. `6. Killed`, `5. Bolt-on`, `3. Pre conversation` |
| `fid12__c` | Armitage partner | |

### ⚠️ Account vs Opportunity field-name collisions

Two API suffixes exist on **both** objects with **different** meanings — always confirm which object you're querying:

| Suffix | On Account | On Opportunity |
|---|---|---|
| `fid48__c` | **Status** (`6. Killed`, `5. Bolt-on`, `3. Pre conversation`) | **Status reached for dead deals** (`Introduction pending`, `Did not connect`, `Term sheet`, …) |
| `fid12__c` | **Armitage partner** | **Direct Source** (drives "Armitage network" pie classification) |

### Opportunity: GOWT priority picklist

`GOWT_Priority__c` on Opportunity now has **four** values: `Ultra High`, `High`, `Medium`, `Low`. (Earlier notes in this file mention only High/Medium/Low — `Ultra High` is the newer top tier.)

### ⭐ Opportunity: "Owner" query convention (ALWAYS apply)

When a user asks to filter/analyse Opportunities **by owner** (e.g. "opportunities where MY is the owner"), they mean the **owner *category*** — the initials-code picklists — **NOT** the Salesforce record owner (`OwnerId` / the User). The record owner (e.g. the User "Michelle Ye") covers a different, much larger population and will give the wrong answer.

**Owner-category fields** (initials codes: `MDA, DG, BO, APC, NL, MQ, LF, AP, Mark H, MY, HM, WM, MC, ES`):

| Field | Label | Scope |
|---|---|---|
| `Owner__c` | Owner | General owner category |
| `fid53__c` | GOWT Owner | GOWT-specific owner |

**Canonical rule for "owner = X":**
1. Match on the owner-category picklist(s): `(Owner__c = 'X' OR fid53__c = 'X')` — include **both** fields unless the user scopes to one. They overlap only partially (a record can carry `X` in one, both, or neither).
2. **Exclude records whose bolt-on owner is someone else.** `Bolt_on_Owner__c` (free-text string) holds a bolt-on owner code; if it's populated with a code **other than X**, exclude the record. Keep it if `Bolt_on_Owner__c` is blank **or** equals `X`:
   `AND (Bolt_on_Owner__c = null OR Bolt_on_Owner__c = 'X')`

Full canonical `WHERE` for owner `X`:
```sql
WHERE (Owner__c = 'X' OR fid53__c = 'X')
  AND (Bolt_on_Owner__c = null OR Bolt_on_Owner__c = 'X')
```

**Gotchas:**
- `Bolt_on_Owner__c` is free text and its codes don't always match the picklist spelling — e.g. picklists use `Mark H` (with space) but the bolt-on field stores `MarkH` (no space). It also holds compound values like `CW / MQ`, `MarkH / SteveJ` — any populated non-`X` value is excluded by the rule above (correct: "a bolt-on owner that is not X").
- Empirically the `MY` owner-category population is almost entirely `7. Killed` (plus a few `0. Complete`) with **no** live/open pipeline and **no** `8. Good opportunity wrong timing`; those live/GOWT deals sit under the *record owner* Michelle Ye instead. Expect the same pattern for other owners — the category codes skew heavily to closed/dead deals.

### Other notes

- **Event `Description`** (Activity/Event object) is the primary source of call notes and deal intel.
- Standard Account fields (`Industry`, `Type`) are frequently blank; prefer the `fid*__c` custom fields.
