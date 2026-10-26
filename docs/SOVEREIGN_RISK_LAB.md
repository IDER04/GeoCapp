# Sovereign Risk Lab — methodology, assumptions, limitations

> Priority 8, phase 2. Companion of the in-app page **Lab risque souverain /
> Sovereign Risk Lab** (`views/risk_lab_page.py`, calculations in
> `geocapital/risk_lab.py`). This document explains the new calculations,
> their assumptions, and their limits. Nothing here changes production data,
> scoring formulas, or scoring parameters.

## 1. Scope

The lab deepens the sovereign-risk reading across three blocks, for every
production country of the existing registry (`data/countries/`, 10 countries —
Brazil remains an isolated candidate and is not covered):

| Block | Metrics |
|---|---|
| Fiscal sustainability | public debt/GDP (observed); fiscal/primary balance (unavailable); interest payments / revenue (unavailable) |
| External vulnerability | FX reserves (observed); current-account balance, external debt (total & short-term), reserves in months of imports (all unavailable) |
| Macro-financial conditions | GDP growth, inflation, policy rate (observed); real rate (derived) |

Every metric card shows: value, unit, observation period (distinct from the
retrieval date `app.data_as_of`), source when known, and a
freshness/uncertainty status.

## 2. Metric inventory (A–E classification)

Classification of every metric the lab displays, verified against the
production files (`data/countries/*.json`), the loaders (`geocapital/data.py`)
and the code paths of `geocapital/risk_lab.py`:

| Metric | Class | Status / source when unlocked |
|---|---|---|
| Public debt/GDP | **A** | Available in all 10 countries (`debt_gdp`, %, sourced, e.g. Lebanon 150 % 2024 estimated) |
| FX reserves | **A** | Available in all 10 countries (`reserves`, $bn; Lebanon = NET, documented) |
| GDP growth | **A** | Available in all 10 countries |
| Inflation | **A** | Available in all 10 countries (Lebanon updated 2025, WDI/FMI) |
| Policy rate | **A** | Available in all 10 countries |
| Real interest rate | **B** | Derived `policy_rate − inflation` — same convention as the engine, existing bands; mixed vintages flagged (Lebanon, Japan) |
| Fiscal / primary balance | **C** | Absent from the v1 schema — one new external source: IMF WEO (revenue-expenditure, % of GDP) or national treasury |
| Interest payments / revenue | **D** | Absent — needs TWO same-vintage inputs: interest paid AND total revenue (IMF GFS or voted budget) |
| Current-account balance | **C** | Absent — one new external source: IMF BOP (% of GDP) |
| External debt (total) | **C** | Absent — one new external source: World Bank IDS (% of GDP) |
| External debt (short-term) | **C** | Absent — same source: World Bank IDS (≤ 1 year) |
| Reserves in months of imports | **D** | Not computed — needs reserves AND imports compatible in period and currency (e.g. WDI TM.VAL.MRCH.CD); an `imports` field alone must not create a coverage |

No metric is classified « intentionally unavailable » (E) beyond these:
every unavailable metric is genuinely absent from the production schema —
verified field by field; no alias, nested object, or loader path carries the
value. The lab reads the schema's aliases if a future file adds the field
(automatic read-through, tested).

## 3. Calculations

### 3.1 Real rate (the only derived calculation)

```
real_rate = policy_rate − inflation
```

- Same convention as the scoring engine (`scoring.component_scores`);
  no formula is duplicated with different semantics and none is modified.
- The result is read against the **existing** real-rate bands from
  `data/meta.json::scoring_model.components.stabilite.real_rate_bands`
  (score `real_rate_outside_score` when outside all bands). The lab
  re-displays these bands; it never redefines or recalibrates them.
- The lab's outputs have **no effect** on the country score or verdict;
  they are a reading aid.

### 3.2 Vintage-alignment warning

`real_rate` combines the vintage of `policy_rate` with the vintage of
`inflation`. When the two observation years differ, the page shows an
explicit warning and the value must be read as an order of magnitude:

- **Lebanon**: policy rate 20.0 % (vintage 2024) × inflation 14.6 %
  (vintage 2025) → real 5.4 %, inside the [−8, 6] band (score 40). This is
  the known real-rate temporal-alignment issue (K1 of
  `docs/DATA_QUALITY_AUDIT.md`), flagged, not corrected.
- **Japan**: policy rate « janv. 2025 » × inflation 2024 — also flagged.

### 3.3 Debt reading (not a DSA)

The debt card positions the observed debt/GDP ratio relative to the
**existing** solvency band `scoring_model.components.solvabilite.debt_range`
(20–180 % of GDP). Indicative reading only: the actual score remains
computed by the unchanged engine.

**No complete debt-sustainability analysis is presented.** A DSA requires at
minimum the fiscal (or primary) balance, the interest burden relative to
revenue, and a growth trajectory. The fiscal balance and interest/revenue
are absent from the v1 schema, so the page explains the limitation instead
and lists, for each missing input, why it matters and which source would
unblock it (IMF WEO / GFS, World Bank IDS, national treasury).

### 3.4 Reserves and months of imports

- Reserves are displayed as sourced in the country file ($bn). Mind the
  gross vs **net** distinction: Lebanon's reserves are net and documented
  as such in the file note.
- **Reserves in months of imports are not computed today**: the coverage
  requires an imports figure compatible with the reserves (same period and
  currency). An `imports` field alone does not create a coverage value —
  the metric stays « unavailable » rather than inventing a ratio.

## 4. Data-quality handling (presentation rules)

- **Missing ≠ zero**: an indicator absent from the schema is displayed as
  « unavailable » with its unit, why it matters, and the source required.
  It is never replaced by zero, a neutral value, or an estimate.
- **Professional presentation**: indicator cards lead with the value, unit,
  reference period and the analytical commentary of the country file. No
  maintenance wording (« to be refreshed ») and no warning icons on cards.
  Status chips reflect a clearly defined **data status**, not freshness:
  « Sourced observation » (neutral), « Estimated » (source-declared
  estimate — never presented as confirmed), « Diverging sources ».
- **Statuses are reused, not duplicated**: freshness, estimated and
  conflicting statuses come from the audit module
  (`data_quality_audit.status_for`). Chip mapping: conflicting → red,
  estimated → orange, otherwise neutral. Staleness alone does not style a
  card.
- **« Data details » expander**: one indicator-by-indicator table (period,
  source, validation status — including per-observation staleness when the
  vintage is genuinely older than the freshness threshold) plus the
  `data_as_of` caveat. Blanket freshness claims are avoided: each row
  describes its own observation.
- **Single-instance warnings**: the mixed-vintages warning appears once
  (real-rate panel); the DSA limitation is one callout pointing to the
  « Indicators not covered » section (no duplicated bullet list).
- **Comparison table**: discreet superscript markers restricted to
  interpretation-changing statuses — `e` (estimate), `d` (diverging
  sources), `m` (mixed vintages) — with a one-line legend; staleness alone
  is never marked.

## 5. Cross-country comparison

A 2–4 country comparison table lists all lab metrics with per-cell warnings
(⚠ stale/estimated/conflict/mixed vintages); unavailable cells stay visible
as « n.d. ». One bar chart (metric selector: debt, real rate, reserves)
covers only countries that actually have the metric.

## 6. Tests

`tests/test_risk_lab.py` (31 tests): engine-consistent real-rate math; band
reading from `scoring.model()`; Lebanon/Japan vintage-mismatch flags;
missing-data handling (unavailable ≠ zero; alias read-through if a future
file carries the field; imports alone do not create a coverage); DSA gating;
audit-status reuse (data-status chips: conflict → red, estimated → orange,
freshness alone → neutral); FR/EN key presence and translated summaries
without raw keys or unsubstituted placeholders; 12-metric × 10-country
coverage; production files byte-identical after lab calls; the page renders
without exception in FR and EN; the raw-key regression (user-reported
symptoms « nav.risk_lab » / « RL.title »); and the professional-presentation
regression: no maintenance wording or ⚠ icons on any rendered surface,
estimated/conflicting/mixed-vintage statuses stay visible (Lebanon), the
vintage warning appears exactly once, the « Data details » expander lists
per-indicator provenance, and the comparison legend is present.

Known out-of-scope quirk: Streamlit's AppTest library cannot re-read the
state of the map page's profile radio when its options are formatted in
English (pre-existing library limitation, unrelated to the lab); the lab's
render test navigates directly to the page.
