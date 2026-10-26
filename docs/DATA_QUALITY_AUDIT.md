# GeoCapital — Data Quality Audit (Priority 7, increment 7.1)

> **Review-first matrix** generated on 2026-10-25 from production data, with no changes to data, formulas, parameters, or app behavior.
> Machine-readable companion: `data/audit/data_quality_audit.json`.
> `app.data_as_of` = **2026-10-25** — ⚠ data_as_of = the app-level declared verification date; it does NOT prove every underlying observation is current.

## 1. Method

- **Read-only** inspection of: `data/countries/*.json`, `data/meta.json`, `geocapital/data.py`, `geocapital/scoring.py`, `geocapital/freshness.py`, plus the traceable documents (`docs/DATA_AUDIT.md`, `docs/DATA_REFRESH_PLAN.md`, `docs/REFRESH_REVIEW.md`, `docs/MODEL_PARAMS.md`).
- **Statuses**: `verified` — complete per-observation provenance + documented cross-check (Lebanon-inflation only). ; `stale` — dated observation beyond the current uniform threshold (year < current − 1) — a display signal, not a judgment. ; `estimated` — source explicitly estimated/modelled (real `source` text, or the ILO-modelled series known from the refresh mapping). ; `conflicting` — at least two official sources in disagreement — manual arbitration required (exhaustive list in DOCUMENTED_CONFLICTS). ; `missing` — block or value absent; documented absences (unquoted CDS) are distinguished via flags. ; `unverified` — documented extension: recent or undated observation with no per-observation provenance (no URL, obs_status or retrieved).
- The sixth status `unverified` is a **transparent extension**, motivated by the metadata reality (no per-observation provenance outside Lebanon-inflation). It is documented here and in the JSON.
- **Conflicts**: only those already documented (REFRESH_REVIEW entries 1–3 + annex, DATA_REFRESH_PLAN §8).
- **Provenance**: absent field ≠ missing value; the absence of `source_url`/`obs_status`/`retrieved` is recorded as a metadata gap (K5).
- **Scoring influence**: read from the code and `scoring_model` (exact sub-weights); no assumed weights; « display only » is stated explicitly when a key enters no formula (reserves, equity index, currency).

## 2. Coverage

- Production countries: **10** (`usa`, `france`, `japan`, `china`, `saudi`, `uae`, `morocco`, `south_africa`, `lebanon`, `syria`).
- Keys: 10 data indicators + `crp` (computed) + 6 qualitative keys → **170 country-indicator pairs** (100 data + 10 computed + 60 qualitative).
- Status counts: `conflicting` **3**, `estimated` **5**, `missing` **2**, `stale` **88**, `unverified` **61**, `verified` **11**.

## 3. Freshness: one uniform rule today, per-type thresholds PROPOSED (separate review)

Current rule: `stale ⇔ obs_year < current year − 1 (freshness.py, display only — score and verdict unchanged)`.

| Type | Keys | Current rule adequate? | Proposal (not applied) | Rationale |
|---|---|---|---|---|
| `annual_macro` | `gdp_growth`, `inflation`, `unemployment`, `debt_gdp` | ✓ adequate | keep the uniform rule: ⚠ if observation year < current year − 1 | national accounts, CPI, unemployment and debt are published as annual vintages; the current uniform threshold matches that granularity. |
| `policy_rate` | `policy_rate` | ✗ to differentiate | ⚠ if the decision is older than ~3 months; require the exact decision date (not « 2024 »). | the policy rate is the most volatile datum in the corpus; an annual vintage hides dated revisions. |
| `rating` | `rating` | ✗ to differentiate | re-verify agency matrices every ~6 months (actions/outlooks); deliberate NR (LBN/SYR) preserved unless contradicted by evidence. | interim agency actions (outlooks) are more frequent than the annual cycle. |
| `cds` | `cds` | ✗ to differentiate | if quoted: keep a quote date; if unquoted: documented absence treated as a deliberate signal (never « stale »). | near-daily series; the absence of a market remains the model's chosen signal. |
| `market_levels` | `reserves`, `equity_index`, `currency` | ✗ to differentiate | monthly reserves (⚠ once the published quarter has passed); 1-year performance recomputed at least quarterly. | reserves are published monthly; rolling performances have no meaningful annual vintage. |
| `qualitative` | `qualitative:*` | ✗ to differentiate | dated annual review (a `reviewed` field to introduce), never automatically « stale ». | editorial assessments are not observations; their age is not a market vintage. |

> No change to `geocapital/freshness.py` or displayed labels: this section is a proposal for review, aligned with data natures (annual macro ≈ OK; rates/ratings/CDS/levels/qualitative → differentiation needed).

## 4. Prioritized findings (methodology)

Findings are ordered **lexicographically**: (tier 1) potential impact on the final score/verdict → (tier 2) staleness + provenance → (tier 3) cross-country definition incompatibility → (tier 4) confidence that a defensible correction is possible. **No numeric sensitivity is simulated**: the model exposes no elasticities (counterfactuals would require changing data, forbidden here). Findings K1–K4 (tier 1) concern the model's heaviest paths (currency_stability ×0.40 of stabilite; rating/CDS → solvabilite + Ke + verdict capping; unemployment/GDP → dynamisme).

### K1 — Real-rate temporal mixing (Lebanon) — known, not corrected (tier 1; countries: `lebanon`)

- **Finding**: policy_rate 20.0 % (vintage 2024, source « Banque du Liban ») is combined with inflation 14.6 % (2025, WDI, applied in 6.1) → real_rate = 5.4, inside the [−8, 6] band → rate_s = 40. This vintage mixing is a property of the data, not a model rule; it is recorded here as a known issue without changing the calculation.
- **Impact**: stabilite (inflation w 0.45, policy w 0.15, currency w 0.40) → risk (w 0.40) → verdicts.
- **Evidence required**: current BDL policy rate (BDL site/bulletin) with the exact decision date.
- **Recommended path**: batch B2 (policy-rate refresh) — not a formula change.

### K2 — NR rating and unquoted CDS (Lebanon, Syria) (tier 1; countries: `lebanon`, `syria`)

- **Finding**: rating = NR and cds = None for both countries → rating_score = 20, cds_score = none_score = 5, CRP falls back to the rating spread (15.5 × 1.5), and the verdict is capped at « Attendre » regardless of the score (blocking_ratings). This is a deliberate model signal, but it rests on 2024 vintages.
- **Impact**: solvabilite (w 0.40/0.30) → risk; Ke/CRP; verdict capping.
- **Evidence required**: dated agency matrices; sourced confirmation that no quoted CDS market exists.
- **Recommended path**: batch B4.

### K3 — Unemployment values in conflict (Lebanon 30, Syria 50) (tier 1; countries: `lebanon`, `syria`)

- **Finding**: No citable national survey; diverging ILO modelled series (LBN 11.0 in 2023, WDI 2024/25 null; SYR 13.6 in 2025); crisis levels (30/50) without a traceable citation. Documented conflicts — no default arbitration.
- **Impact**: dynamisme (w 0.20) + the « Attendre » rescue path (dynamisme ≥ 55 threshold).
- **Evidence required**: docs/DATA_REFRESH_PLAN.md §8.2 / §8.3 (ILOSTAT + national surveys + post-transition).
- **Recommended path**: batch B5 — evidence first.

### K4 — Lebanon GDP 2024: three institutional vintages (tier 1; countries: `lebanon`)

- **Finding**: Production −6.5 (IMF) vs WDI+LEM −7.1 vs WEO Oct 2026 −5.2. The file stays at −6.5; conflict documented.
- **Impact**: dynamisme (w 0.55) — the largest dynamisme influence in the corpus.
- **Evidence required**: docs/DATA_REFRESH_PLAN.md §8.1 (IMF internal reconciliation + national-accounts base).
- **Recommended path**: batch B5.

### K5 — Per-observation provenance nearly absent (tier 2; countries: `*`)

- **Finding**: Out of 100 data pairs, ONLY lebanon-inflation carries source_url/obs_status/retrieved (the pattern set in 6.1). meta.sources is a dataset-level registry, not per observation. Absent fields (verification impossible) are distinguished from missing values.
- **Impact**: capacity to re-verify and refresh repeatedly; the displayed freshness flag is currently the only signal.
- **Evidence required**: backfill URL + obs_status + retrieved at each future application batch (the 6.1 pattern).
- **Recommended path**: batch B1 (metadata), transversal.

### K6 — Real-rate band specification vs code mismatch (documentation only) (tier 4; countries: `*`)

- **Finding**: docs/MODEL_PARAMS.md §4.2 describes the bands as « inclusive-low / exclusive-high » while the code compares low ≤ real ≤ high (inclusive on both ends). The difference only appears at exact band edges (e.g. real = 4.0 → code 72, strict doc reading 40). No country sits on an edge today; this is a documentation/test alignment finding, with no formula change in this increment.
- **Impact**: no current score effect; a future vintage could land on an edge.
- **Evidence required**: decide the documentary convention (align the doc to the code, or the reverse via a dedicated increment).
- **Recommended path**: keep on the documentation watch-list.

## 5. Matrix — data by country (10 × 10)

Columns: key | value | period (observation ≠ retrieved — rarely distinct today) | status | confidence | scoring influence | source | URL | recommended batch.

### `usa`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 2.8 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | FMI, WEO | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 2.9 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | Bureau of Labor Statistics | — | batch B3 |
| `debt_gdp` | 123 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | FMI, WEO | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 4.33 (%) | déc. 2024 | `stale` (precise_month) | high | stabilite (sub-weight 0.15; risk w 0.4) | Federal Reserve | — | batch B2 |
| `unemployment` | 4.1 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | Bureau of Labor Statistics | — | batch B5 |
| `reserves` | 250 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | FMI / Trésor | — | batch B3/B4 |
| `rating` | AA+ () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 40 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | S&P Dow Jones Indices | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Fed / BRI | — | batch B4 (display) |

### `france`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 1.1 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | INSEE / FMI | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 2 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | INSEE | — | batch B3 |
| `debt_gdp` | 112 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | INSEE / FMI | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 3 (%) | déc. 2024 | `stale` (precise_month) | high | stabilite (sub-weight 0.15; risk w 0.4) | BCE | — | batch B2 |
| `unemployment` | 7.4 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | INSEE | — | batch B5 |
| `reserves` | 265 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | Banque de France / FMI | — | batch B3/B4 |
| `rating` | AA- () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 35 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Euronext | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | BCE / BRI | — | batch B4 (display) |

### `japan`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 0.3 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | Cabinet Office / FMI | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 2.7 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | Statistics Bureau | — | batch B3 |
| `debt_gdp` | 255 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | FMI, WEO | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 0.5 (%) | janv. 2025 | `unverified` (provenance_absent) | medium | stabilite (sub-weight 0.15; risk w 0.4) | Bank of Japan | — | batch B2 |
| `unemployment` | 2.5 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | Statistics Bureau | — | batch B5 |
| `reserves` | 1230 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | Ministère des Finances / FMI | — | batch B3/B4 |
| `rating` | A+ () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 30 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Nikkei / JPX | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | BOJ / BRI | — | batch B4 (display) |

- ⚠ `japan.policy_rate` — observation (vintage 2025) neither verified in this audit nor accompanied by source_url/obs_status/retrieved.

### `china`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 5 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | Bureau national de la statistique / FMI | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 0.2 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | Bureau national de la statistique | — | batch B3 |
| `debt_gdp` | 88 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | FMI, WEO | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 3.1 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.15; risk w 0.4) | PBoC (LPR 1 an) | — | batch B2 |
| `unemployment` | 5.1 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | Bureau national de la statistique | — | batch B5 |
| `reserves` | 3200 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | PBoC / FMI | — | batch B3/B4 |
| `rating` | A+ () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 75 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Shanghai Stock Exchange | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | PBoC / BRI | — | batch B4 (display) |

- ⚠ `china.debt_gdp` — vintage 2024 < current−1 threshold (freshness.is_stale); no per-source verification in this audit.
  - Government coverage: `general_government` (documented in the file note)

### `saudi`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 1.3 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | FMI, WEO | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 1.7 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | GASTAT / FMI | — | batch B3 |
| `debt_gdp` | 30 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | FMI, WEO | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 5 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.15; risk w 0.4) | SAMA | — | batch B2 |
| `unemployment` | 3.5 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | GASTAT | — | batch B5 |
| `reserves` | 420 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | SAMA / FMI | — | batch B3/B4 |
| `rating` | A+ () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 60 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Saudi Exchange | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | SAMA | — | batch B4 (display) |

### `uae`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 4 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | FMI, WEO | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 2 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | FMI / autorités émiraties | — | batch B3 |
| `debt_gdp` | 30 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | FMI, WEO | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 4.4 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.15; risk w 0.4) | CBUAE | — | batch B2 |
| `unemployment` | 2.7 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | FMI / autorités | — | batch B5 |
| `reserves` | 240 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | CBUAE / FMI | — | batch B3/B4 |
| `rating` | AA () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 45 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Dubai Financial Market | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | CBUAE | — | batch B4 (display) |

### `morocco`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 3.2 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | FMI, WEO | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 1.7 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | Bank Al-Maghrib | — | batch B3 |
| `debt_gdp` | 69 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | FMI, WEO | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 2.25 (%) | déc. 2024 | `stale` (precise_month) | high | stabilite (sub-weight 0.15; risk w 0.4) | Bank Al-Maghrib | — | batch B2 |
| `unemployment` | 13.3 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | HCP | — | batch B5 |
| `reserves` | 36 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | Bank Al-Maghrib / FMI | — | batch B3/B4 |
| `rating` | BB+ () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 100 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Bourse de Casablanca | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Bank Al-Maghrib | — | batch B4 (display) |

### `south_africa`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | 0.6 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.55) | Statistics South Africa / FMI | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 4.4 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.45; risk w 0.4) | Statistics South Africa | — | batch B3 |
| `debt_gdp` | 75 (%) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | FMI, WEO | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 7.75 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.15; risk w 0.4) | SARB | — | batch B2 |
| `unemployment` | 32.1 (%) | 2024 | `stale` (no per-observation provenance) | high | dynamisme (sub-weight 0.2) | Statistics South Africa | — | batch B5 |
| `reserves` | 62 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | SARB / FMI | — | batch B3/B4 |
| `rating` | BB- () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | 180 (pb) | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.3; risk w 0.35) | CMA / marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Johannesburg Stock Exchange | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | SARB / BRI | — | batch B4 (display) |

### `lebanon`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | -6.5 (%) | 2024 | `conflicting` (conflict_documented) | high | dynamisme (sub-weight 0.55) | FMI / estimations | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 14.6 (%) | 2025 | `verified` (IMF WEO cross-check == 14.6 (docs/REFRESH_REVIEW.md entry 2)) | high | stabilite (sub-weight 0.45; risk w 0.4) | Banque mondiale (WDI, série FP.CPI.TOTL.ZG) / FMI (WEO) | yes | batch B3 |
| `debt_gdp` | 150 (%) | 2024 | `estimated` (source_labelled_estimate) | medium | solvabilite (sub-weight 0.3; risk w 0.35) | Estimation FMI | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 20 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.15; risk w 0.4) | Banque du Liban | — | batch B2 |
| `unemployment` | 30 (%) | 2024 | `conflicting` (conflict_documented) | high | dynamisme (sub-weight 0.2) | Estimation OIT / Banque mondiale | — | batch B5 |
| `reserves` | 10 (Mds $) | 2024 | `stale` (no per-observation provenance) | high | display only | FMI / BDL | — | batch B3/B4 |
| `rating` | D () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P Global Ratings | — | batch B4 |
| `cds` | — (pb) | 2024 | `missing` (documented_absence) | high | solvabilite (sub-weight 0.3; risk w 0.35) | Marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Beyrouth Stock Exchange | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | BDL / marché parallèle | — | batch B4 (display) |

- ⚠ `lebanon.gdp_growth` — IMF WEO −5.2 (2024) vs World Bank WDI+LEM −7.1 vs production −6.5 (IMF) — docs/REFRESH_REVIEW.md entry 1 (seek_better_source).
- ⚠ `lebanon.debt_gdp` — the `source` field carries an explicit estimate/modelling mention (real text).
- ⚠ `lebanon.unemployment` — Production 30 (2024) vs ILO modelled 11.0 (2023; WDI 2024/25 null) vs MPO April 2026 ≈22.8 — docs/REFRESH_REVIEW.md annex + docs/DATA_REFRESH_PLAN.md §8.2.
- ⚠ `lebanon.cds` — value=None with a documented « non coté » block — the absence is a signal handled by the model, not a data-entry gap.

### `syria`

| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |
|---|---|---|---|---|---|---|---|---|
| `gdp_growth` | -1.2 (%) | 2024 | `estimated` (source_labelled_estimate) | medium | dynamisme (sub-weight 0.55) | Estimation Banque mondiale / FMI | — | batch B3 (others) / batch B5 (Lebanon) |
| `inflation` | 60 (%) | 2024 | `estimated` (source_labelled_estimate) | medium | stabilite (sub-weight 0.45; risk w 0.4) | Estimation | — | batch B3 |
| `debt_gdp` | 130 (%) | 2024 | `estimated` (source_labelled_estimate) | medium | solvabilite (sub-weight 0.3; risk w 0.35) | Estimation | — | batch B3 (re-check central vs general before any substitution) |
| `policy_rate` | 10 (%) | 2024 | `stale` (no per-observation provenance) | high | stabilite (sub-weight 0.15; risk w 0.4) | Banque centrale de Syrie | — | batch B2 |
| `unemployment` | 50 (%) | 2024 | `conflicting` (conflict_documented) | high | dynamisme (sub-weight 0.2) | Estimation OIT | — | batch B5 |
| `reserves` | 1 (Mds $) | 2024 | `estimated` (source_labelled_estimate) | medium | display only | Estimation | — | batch B3/B4 |
| `rating` | NR () | 2024 | `stale` (no per-observation provenance) | high | solvabilite (sub-weight 0.4; risk w 0.35) | S&P / Moody's / Fitch | — | batch B4 |
| `cds` | — (pb) | 2024 | `missing` (documented_absence) | high | solvabilite (sub-weight 0.3; risk w 0.35) | Marché | — | batch B4 |
| `equity_index` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | DSE | — | batch B4 (display) |
| `currency` | — () | 2024 | `stale` (scalar_value_absent_by_design) | high | display only | Banque centrale / marché parallèle | — | batch B4 (display) |

- ⚠ `syria.gdp_growth` — the `source` field carries an explicit estimate/modelling mention (real text).
- ⚠ `syria.inflation` — the `source` field carries an explicit estimate/modelling mention (real text).
- ⚠ `syria.debt_gdp` — the `source` field carries an explicit estimate/modelling mention (real text).
- ⚠ `syria.unemployment` — Production 50 (« Estimation OIT », citation never traceable) vs ILO modelled 13.6 (2025) vs EUAA COI ≈24 (2024) — docs/REFRESH_REVIEW.md entry 3 + docs/DATA_REFRESH_PLAN.md §8.3.
- ⚠ `syria.reserves` — the `source` field carries an explicit estimate/modelling mention (real text).
- ⚠ `syria.cds` — value=None with a documented « non coté » block — the absence is a signal handled by the model, not a data-entry gap.

## 6. Matrix — qualitative keys (6 per country)

Each assessment is an editorial score with no review date — status `unverified`, low confidence (a structural limit, not a data-entry error).

| Country | outlook | currency_stability | governance | resilience | business | openness |
|---|---|---|---|---|---|---|
| `usa` | 65 | 92 | 74 | 80 | 82 | 70 |
| `france` | 50 | 85 | 78 | 75 | 68 | 80 |
| `japan` | 55 | 70 | 82 | 78 | 72 | 70 |
| `china` | 60 | 62 | 55 | 70 | 52 | 55 |
| `saudi` | 65 | 80 | 48 | 62 | 62 | 60 |
| `uae` | 80 | 88 | 55 | 65 | 78 | 85 |
| `morocco` | 75 | 65 | 53 | 60 | 60 | 72 |
| `south_africa` | 50 | 50 | 58 | 58 | 48 | 65 |
| `lebanon` | 20 | 8 | 25 | 25 | 30 | 70 |
| `syria` | 25 | 2 | 8 | 10 | 8 | 20 |

Sub-weights: outlook 0.25 (dynamisme); **currency_stability 0.40 (stabilite — tied with inflation for the heaviest weight)**; governance 0.60 + resilience 0.40 (institutions — the third component entering risk, w 0.25); business 0.60 + openness 0.40 (ouverture, excluded from risk).

## 7. Derived — country risk premium

| Country | CRP | Basis | Usage note |
|---|---|---|---|
| `usa` | 0.83 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `france` | 1.2 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `japan` | 1.42 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `china` | 1.42 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `saudi` | 1.42 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `uae` | 1.05 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `morocco` | 3.9 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `south_africa` | 5.25 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation); freshness remains that of the rating/cds inputs. |
| `lebanon` | 22.5 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation (cds non coté)); freshness remains that of the rating/cds inputs. |
| `syria` | 23.25 % | Damodaran (max rating-spread/CDS spread) × 1.5 | deterministic recomputation vs scoring.country_risk_premium (basis: notation (cds non coté)); freshness remains that of the rating/cds inputs. |

## 8. Proposed action batches (none applied)

| Batch | Name | Keys | Risk | Note |
|---|---|---|---|---|
| B1 | provenance backfill (metadata) | transversal | low | URL + obs_status + retrieved per value, alongside future application batches; no value changes. |
| B2 | policy rates (10 countries) | `policy_rate` | medium — also mitigates K1 | exact decision date required; refreshes rate_s (band). |
| B3 | annual macro (documented batch) | `gdp_growth`, `inflation`, `unemployment`, `debt_gdp` | medium | definition-first; central vs general explicit; Lebanon-GDP and LBN/SYR-unemployment excluded → B5. |
| B4 | market signals | `rating`, `cds`, `equity_index`, `currency`, `reserves` | medium | display + Ke; deliberate NR preserved; net vs gross made explicit. |
| B5 | documented conflicts | `lebanon:gdp_growth`, `lebanon:unemployment`, `syria:unemployment` | high — human review required | only after the §8 DATA_REFRESH_PLAN evidence; no automatic arbitration (no « newest wins »). |
| B6 | qualitative: grid and dating | qualitative:* | medium | publish the qualitative scoring grid + a review date per assessment. |

## 9. Limitations

- Without per-observation URLs or publication dates, per-source verification is not reproducible at scale in this audit (finding K5).
- No numeric sensitivity simulated — the model exposes no derivable elasticities without a counterfactual (forbidden here).
- Qualitative keys are never « stale » under the current code; the « not an observation » distinction is assumed here, reported without correction.
- Currency and equity-index data (2024 performance) sit outside the model; whether to bring them into scoring is a separate architecture decision.
- Brazil (candidate 6.3) is excluded from the matrix: no production coverage.

