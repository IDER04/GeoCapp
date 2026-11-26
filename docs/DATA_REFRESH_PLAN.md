# GeoCapp — Data Refresh Plan (Phase 1, increment 1)

> Priority 6. Implementation: `geocapital/refresh.py` · First run:
> candidate report `docs/REFRESH_CANDIDATES_BRA_LBN_SYR.md`
> (+ `.json`) — Brazil, Lebanon, Syria.
>
> **Status: review before application.** No production file
> (`data/countries/*.json`) was modified by this increment.

## 1. Objective and principles

Improve the **freshness** and **traceability** of the data without
tampering with the scoring model, without silently overwriting a value,
and without inventing figures, dates or URLs. Three principles:

1. **Review-first**: the API provides *candidates*; nothing is applied
   automatically. Each candidate carries a recommendation
   (`safe` / `manual` / `reject` / `gap`), an explanation and its
   request URL.
2. **Matching by definition, not by name**: a World Bank (WB) series is
   mapped only if its definition genuinely covers that of the country
   profile; partial overlaps are documented (`match: "partial"`) and
   routed to manual review or rejection.
3. **Provenance**: each observation distinguishes
   - the **observation period** (e.g. 2024 — never treated as the
     current year),
   - the source's **publication/update date**
     (`meta.lastupdated` of the response, when available),
   - the **retrieval date** (timestamped when the generator runs),
   - the WDI **observation status** (`obs_status`).

## 2. Observation status semantics (WDI)

| `obs_status` | Meaning | Handling |
|---|---|---|
| `` (empty) or `A` | actual observation | accepted as `actual` |
| `E` | official estimate | accepted, flagged `estimate` (cross-checking recommended) |
| `F` | forecast | **excluded** from `latest_actual()` — a forecast does not replace an observation; explicitly rejected if proposed |
| `NA` | not available | ignored |

## 3. Indicator mapping (WB WDI v2 only)

Source: World Bank Indicators API, v2
(`https://api.worldbank.org/v2/...`, free, no key). Market indicators
with no single free official equivalent (`policy_rate`, `rating`, `cds`,
`crp`, `equity_index`, `currency`) are **not** mapped — manual sources
are mandatory.

| GeoCapp indicator | WB series | Match | Definition note |
|---|---|---|---|
| `gdp_growth` | `NY.GDP.MKTP.KD.ZG` | `exact` | Real GDP, annual growth % |
| `inflation` | `FP.CPI.TOTL.ZG` | `exact` | Consumer price index, annual average % (not an end-of-year point) |
| `unemployment` | `SL.UEM.TOTL.ZS` | `partial` | ILO **modeled** series — can diverge strongly from crisis estimates (Lebanon, Syria) |
| `debt_gdp` | `GC.DOD.TOTL.GD.ZS` | `partial` | **Central government** debt ≠ general public-sector debt (understates it); series often discontinued in earlier years |
| `reserves` | `FI.RES.TOTL.CD` | `exact_for_total` | **Total** reserves (gold included), US$; defined conversion US$ → US$ billions (×10⁻⁹). ⚠️ if the profile documents **net** reserves → incompatible definition, rejected |

## 4. Recommendation rules (summary)

- `gap` — retrieval impossible or no usable row: the existing value is
  kept and the gap is documented (to be followed up on the freshness
  side, Priority 2).
- `reject` — observation *older* than the existing one; forecast;
  outdated central-government debt series; net ≠ total reserves.
- `manual` — more recent vintage; same vintage with a diverging value;
  new country (expansion); divergence of more than 10 points on modeled
  unemployment. Nothing is applied without human judgment.
- `safe` — reserved for future, explicitly approved automation.
  **No "safe" candidate was produced in this increment**: under
  review-first, every value change goes through a person first.

## 5. First run — Lebanon, Syria, Brazil (2026-10-25)

Results: **15 candidates → 0 safe · 8 manual · 6 reject · 1 gap**.

Key findings (details in the report):

- **Lebanon**: GDP −7.08% (2024, WB) vs −6.5% (profile, IMF) →
  provenance review; 2025 inflation = 14.6% (easing) → review; ILO
  modeled unemployment 2023 = 11.0% vs crisis estimate of 30% → the
  modeled series is not aligned with the breakdown and was rejected in
  favor of the existing value; GROSS reserves US$33.3 bn vs NET reserves
  US$10 bn (BDL/IMF) → **incompatible definition, rejected**; central
  government debt discontinued in 1999 → rejected.
- **Syria**: WDI coverage is severely incomplete (GDP ends 2022, CPI
  ends 2019, debt retrieval failed, reserves end 2010, a single modeled
  unemployment value for 2025 = 13.6%) → mostly gaps, to be filled
  elsewhere.
- **Brazil**: all series are fresh (2024–2025) and complete; these are
  **expansion** candidates (no production file), so all are "manual" by
  construction.

### Official sources to use for the gaps (Lebanon / Syria)

- **IMF — WEO and Article IV**: GDP, inflation, debt and reserves for
  Lebanon and Syria (staff estimates, "general public sector"
  definition for debt). `imf.org/weo`, Article IV country reports.
- **Banque du Liban (BDL)**: policy rate, net and free reserves, monetary
  base. `bdl.gov.lb` ("BDL Bulletin" series).
- **Central Bank of Syria**: policy rate, reserves (scattered
  information); the Syrian *Central Bureau of Statistics* for CPI when
  it publishes.
- **World Bank**: `SL.UEM.TOTL.ZS` (ILO modeled unemployment) — to be
  cross-checked against "crisis" estimates (ILO, national studies)
  before any substitution.

These non-WB retrievals are not part of increment 1 (no connector); they
go through a documented manual entry with URL + date, then the same
review process.

## 6. Full workflow (target)

1. `refresh.candidate_pack(cid)` / `pack_for_new_country(snapshot)` →
   candidates for one country (WB API, timeout, no key).
2. `build_candidate()` → recommendation + explanation + metadata.
3. `generate_report()` → `docs/REFRESH_CANDIDATES_*.md` + `.json`
   (writes **only** under `docs/`).
4. Human review: decide each `manual`, accept/reject the `reject`
   entries, trace each `gap` to its official source.
5. Future increment (not implemented): controlled writing of approved
   candidates into `data/countries/*.json` — keeping the `source`,
   `note` and vintage fields and `data_as_of` from `meta.json`, then
   running the test suite + checking the frozen reference scoring.

## 7. Known limitations

- Covers only WB WDI v2; no IMF/BDL/Central Bank of Syria connector
  (probable next increment).
- A fine-grained "publication date" is not exposed per observation by
  the API (only the database update date is) — hence the traced
  `lastupdated` field, distinct from the observation period.
- `per_page=60` comfortably covers annual series; a series paginated
  beyond that would require a loop (not needed at this stage).
- WDI values are sometimes revised after the fact: a `manual` candidate
  must always be cross-checked against a second source before being
  applied.
- The `per_page` counter, network errors and malformed JSON are
  converted into a traceable `gap`, never into a value replaced by an
  internal estimate.

## 8. Follow-up — remaining evidence for the three unresolved cases (2026-10-25)

Following the review in `docs/REFRESH_REVIEW.md`, none of the three cases
below can be decided by default: any application remains blocked until
this evidence is gathered. **None of these three values was modified in
production in this increment.**

### 8.1 Lebanon — `gdp_growth` 2024 (IMF vs World Bank gap)

Three official vintages coexist for 2024: the profile (−6.5%, source
"IMF / estimates"), the World Bank (WDI and LEM: −7.1%), and the IMF WEO
of October 2026 (−5.2%). Evidence to gather before any choice:

- **IMF internal reconciliation**: identify what lies behind the
  existing value ("IMF / estimates") and compare it with the WEO
  DataMapper (`NGDP_RPCH`): different vintages, chronological revisions,
  and any Lebanon Article IV country note explaining the gap;
- **National accounts basis**: determine whether −7.1 vs −5.2 stems from
  a base revision of Lebanon's national accounts or from different staff
  assumptions (aftermath of the 2024 conflict, GDP entry and exit
  points);
- **Precise LEM citation**: Spring 2025 LEM edition (revision
  −5.7 → −7.1) — pin down the exact page and vintage to trace the
  chronology of revisions.

Without this, `seek_better_source` remains in force (applying −7.1
would amount to settling a 1.9-point disagreement between institutions).

### 8.2 Lebanon — `unemployment` (triple divergence)

Three values coexist in the official sources consulted: profile 30%
(2024) · ILO modeled 11.0% (2023; 2024/25 are **null** in WDI) · MPO
April 2026 ~22.8% (2024). Evidence to gather:

- **ILOSTAT ILOEST Lebanon**: download the Lebanon series and check the
  exact reference year of the 11.0% as well as the methodological note
  (modeled estimate, no recent survey);
- **Recent national surveys**: look for any post-2019 publication from
  the CAS and the OLM (Lebanese labor market observatory) confirming or
  contradicting the profile's ~30%;
- **LEM/MPO**: locate the exact page of the 22.8% (2024) in the April
  2026 MPO sheet, with definition, period and status (estimated vs
  observed).

Without an underlying survey, none of the three values can justifiably
replace another — hence `seek_better_source` is maintained.

### 8.3 Syria — `unemployment` 2025

Three values centered on the December 2024 break: profile 50% (2024,
"ILO estimate", citation never traceable) · ILO modeled 13.6% (2025) ·
EUAA COI 24% (2024). Evidence to gather:

- **ILOSTAT ILOEST Syria**: full series + ILO methodological note
  ("lack of recent labour market data") — the 13.6% value is a model
  output, not an observation;
- **First surveys by the Syrian government after December 2024**: any
  usable post-transition survey (Echo, REACH, OCHA, Syrian ONS if
  resumed) — a direct survey, if published, would be the first in
  years;
- **Post-conflict WB/IMF publications**: the IMF has excluded Syria from
  the WEO since 2011; any reinclusion would signal new data available
  to exploit;
- **Citation of the existing 50%**: find the exact publication behind
  the crisis estimate (UNOCHA/EUAA/RNIS fact sheets 2023–24) to date and
  qualify this level before any decision.

Post-conflict modeled values (13.6%) must **not** be applied without a
corroborating survey: they rest on a model with no visibility on the
transition.
