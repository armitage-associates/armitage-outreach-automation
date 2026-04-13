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
| `Growth_News__c`, `Growth_Actions__c`, `P__c` | Populated by the monthly scraper pipeline |

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

`.github/workflows/run-schedule.yml` — monthly scraper pipeline (unrelated to Origination Charts, predates this work).

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

- `main.py`, `scraper.py`, `company/*`, `scrapers/*`, `utils/*` — the monthly outreach automation pipeline, unrelated to Origination Charts
- `salesforce.py` — shared Salesforce client; has the OAuth flow and helpers that the Origination Charts scripts import
- `data/origination_dashboard_backup.json` — pre-any-edits snapshot of the Origination weekly dashboard

### Two relevant Excel files

- `data/armitage_origination_metrics.xlsx` — source of truth for the funnel waterfall logic (Sheet2 has the cumulative formulas; Raw Data has the ~7400 opportunities)
- `data/piechart_metrics.xlsx` — source of truth for the 4 pie charts (Pivot sheet has the breakdowns; Deal list export has ~7375 rows)

Both Excel files were frozen snapshots. Numbers in our live dashboards will drift as Salesforce data changes, but the **logic** matches exactly.
