# "SalesForce integration" thread — reconstructed instructions

> **Provenance / confidence.** These instructions were reconstructed on 2026-11-04 from
> the only two things visible to another session: (1) the **one artifact** that thread
> published ("Origination Funnel", read in full) and (2) its **one-line post-turn
> summary** (a Feb-2026 task-count analysis). The thread itself is a Remote Control /
> bridge session on a user computer that was offline, so its full transcript could **not**
> be read. Items marked **[confirmed]** are grounded in the artifact; items marked
> **[to confirm]** are inferred from this repo's conventions and should be checked
> against the real thread once it is reachable (bring the host computer online, then
> `claude --teleport session_01RGme4NcL6c8ZgGdMDtAQbS`).

## What that thread was for

A live-Salesforce analysis workspace (Sonnet 4.6, high effort, **no git repo**, auto-PR
off) used for ad-hoc origination questions and for recreating Armitage's origination
funnel chart as a shareable artifact. Two concrete work products are evidenced:

1. **The origination funnel chart** — rebuilt as an SVG artifact in house style. **[confirmed]**
2. **Monthly task-count-by-company analysis** — e.g. Feb 2026: Petro Industrial 95 (killed),
   next highest Associated Scale Services 21. **[confirmed it ran; method below is [to confirm]]**

## 1. Origination funnel chart (house style) — build instructions **[confirmed]**

Reproduce the funnel as a standalone SVG (matches the PowerPoint/Excel funnel used in
IC decks). Exact spec taken from the published artifact:

- **Title:** `Origination funnel, <start> – <end>` (the artifact used *2016 – Oct 2026*),
  13.5px bold, colour `#1A3F77`.
- **Palette / type:** bars `#1A3F77` (navy); labels `#5A5A5A` (grey); font
  `Calibri, 'Segoe UI', Arial, sans-serif`.
- **7 stages, top → bottom:** Businesses contacted · Initial contact · Initial discussion ·
  Initial due diligence · Indicative offers made · Term sheets signed · Investments made.
- **Layout:** stage labels right-aligned to x=145; bars start at x=150, max width 285px
  mapped to the top value; bar height 30px, row pitch 38px; scale = `285 / <top value>`
  px per unit. Value label sits **inside** the bar (white, bold) when the bar is wide
  enough, otherwise **outside** to the right in navy (the artifact flips to outside at
  stage 4 downward).
- **Footnote (bottom-right):** `<N> portfolio companies` / `<M> bolt-on acquisitions`
  (artifact: 20 / 51).
- **Values in the published artifact (2016 – Oct 2026):**
  7,482 → 5,624 → 3,045 → 326 → 150 → 112 → 72.

This is the **cumulative survivorship funnel** documented in `CLAUDE.md`
(§ Dynamic origination funnel report): each stage is the count of deals that reached *at
least* that depth, so the series declines monotonically and stage 7 = count of
`0. Complete`. The numbers come from the same `fid48__c` / `StageName` waterfall as
`salesforce/sf_funnel_update.py` — pull them live rather than hard-coding. **[to confirm:
whether the thread computed values live or pasted them from the Excel snapshot]**

## 2. Monthly task-count-by-company analysis **[to confirm]**

Produces, for a given month, a ranking of companies by number of Activity records (Tasks),
flagging the deal's stage (e.g. "killed"). Reconstructed method:

- Query `Task` where `ActivityDate` falls in the target month, group by the related
  Opportunity/Account, count, and order descending.
- Annotate each with the Opportunity `StageName` (so "Petro Industrial 95 (killed)" reads
  as 95 tasks on a now-`7. Killed` opportunity).
- Confirm against the real thread whether it counted `Task`, `Event`, or both, and whether
  it grouped by Account or Opportunity.

## Standing conventions this thread should inherit

All work here must follow the repo's `CLAUDE.md`, in particular:
- **Salesforce connection & access** (client-credentials OAuth via `salesforce.py`).
- **Owner query convention** (`Owner__c` / `fid53__c`, not `OwnerId`; drop non-target bolt-on owners).
- **Opportunity analysis minimum standard** (exclude bolt-ons where `fid40__c` populated;
  Completed / GOWT+ / Killed buckets; classify by description).
- **Killing an opportunity** (three-field kill + always ask for `fid48__c`).

## Open items to finish these instructions

- [ ] Read the real transcript (teleport once the host computer is online) and replace all
      **[to confirm]** sections with the thread's actual method.
- [ ] Confirm whether the funnel artifact pulls live figures or a frozen snapshot.
- [ ] Capture any other analyses the thread ran that left no artifact/summary.
