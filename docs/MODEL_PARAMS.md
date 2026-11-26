# GeoCapp — Model Parameters (source of truth: `data/meta.json`)

> Priority 3, Phase 1 — the model is now **configuration-driven**.
> This document defines the meaning of each parameter and lists what
> deliberately remains in the code. The docstring of `geocapital/scoring.py`
> and the `_doc` key of `meta.json` point here.

Component and profile identifiers (`dynamisme`, `stabilite`, `solvabilite`,
`institutions`, `ouverture`; `Prudent`, `Équilibré`, `Audacieux`) are the
literal keys used in the code and in `data/meta.json`, so they are kept
as-is. In English they correspond to dynamism, stability, solvency,
institutions and openness, and to the Prudent, Balanced and Bold profiles.

## 1. General principle

| Topic | Location |
|---|---|
| Numeric calibration values | `data/meta.json` → `financial_params` + `scoring_model` |
| Schema validation | `geocapital/scoring.py` → `validate_model_params()` |
| Memoized reading | `geocapital/scoring.py` → `model()` (key = content signature; `reset_model_cache()` to force a reload) |
| Formulas (never numbers) | `geocapital/scoring.py` |
| FR labels of components, verdict copy, icons | `geocapital/scoring.py` → `COMPONENT_LABELS`, `VERDICT_STYLES`, `_PROFILE_DESCRIPTIONS` (EN i18n via `data/i18n/en/*.json`) |
| Configuration errors | `scoring.ConfigError("meta.<section>.<key>: <problem>")` — **never swallowed**: an invalid configuration stops the app with a precise message, not a silent fallback |

A parameter exists **only in `meta.json`**: the historical constants of the
scoring module (`RISK_FREE_RATE`, `MATURE_ERP`, `BETA`,
`EQUITY_BOND_VOL_RATIO`, `PROFILES`, `RATING_SCORES`, `DEFAULT_SPREADS`)
are read-only views onto the configuration (PEP 562 `__getattr__`).

## 2. `financial_params` (required return, Damodaran method)

`Ke = risk_free_rate + beta × mature_ERP + country_premium`,
with `country_premium = max(rating_spread, (cds − offset)/100) × vol_ratio`.

| Parameter | Value | Meaning |
|---|---|---|
| `risk_free_rate` | 4.2 (%) | US 10-year Treasury yield, early 2025 |
| `mature_erp` | 4.5 (%) | Equity risk premium of a mature market |
| `beta` | 1.0 | Broad-market beta (equity-sensitive) |
| `equity_bond_vol_ratio` | 1.5 | Equity / bond volatility ratio: converts a bond spread into an equity premium |

## 3. `scoring_model.profiles` — weights of the five components per profile

The weights sum to 1 for each profile (strict check).

| Profile | dynamisme | stabilite | solvabilite | institutions | ouverture |
|---|---|---|---|---|---|
| `Prudent` | 0.15 | 0.30 | 0.30 | 0.15 | 0.10 |
| `Équilibré` | 0.25 | 0.20 | 0.25 | 0.15 | 0.15 |
| `Audacieux` | 0.35 | 0.10 | 0.20 | 0.10 | 0.25 |

An unknown profile falls back to `Équilibré` (a display choice, tested).

## 4. `scoring_model.components` — internal component curves

### 4.1 `dynamisme`
| Parameter | Value | Meaning |
|---|---|---|
| `weights.growth` | 0.55 | Weight of GDP growth |
| `weights.unemployment` | 0.20 | Weight of unemployment (inverted) |
| `weights.outlook` | 0.25 | Weight of the qualitative "outlook" (50 if missing, see 4.6) |
| `growth_range` | [-2.0, 5.0] | Growth: linear score 0–100 (−2% → 0; 5% → 100) |
| `unemployment_range` | [2.0, 20.0] | Inverted unemployment (2% → 100; 20% → 0) |

### 4.2 `stabilite`
| Parameter | Value | Meaning |
|---|---|---|
| `weights.inflation` | 0.45 | Weight of the gap between inflation and its target |
| `weights.policy_rate` | 0.15 | Weight of the real policy rate (bands) |
| `weights.currency` | 0.40 | Weight of currency stability (qualitative) |
| `inflation_target` | 2.0 (%) | Target: score = 100 − 4 × \|inflation − target\| |
| `inflation_sensitivity` | 4.0 | Slope of the inflation penalty |
| `real_rate_bands` | [[−1, 2, 95], [−3, 4, 72], [−8, 6, 40]] | Real policy rate (nominal − inflation), lower bound inclusive / upper bound exclusive → score if within the band |
| `real_rate_outside_score` | 8.0 | Default score when outside every band |

### 4.3 `solvabilite`
| Parameter | Value | Meaning |
|---|---|---|
| `weights.debt` | 0.30 | Weight of debt/GDP (inverted over `debt_range`) |
| `weights.rating` | 0.40 | Weight of the rating score (§ 8) |
| `weights.cds` | 0.30 | Weight of the CDS score (§ 6) |
| `debt_range` | [20.0, 180.0] | Inverted debt/GDP (20% → 100; 180% → 0) |

### 4.4 `institutions`
`weights.governance` 0.60 (qualitative), `weights.resilience` 0.40 (qualitative).

### 4.5 `ouverture`
`weights.business` 0.60 (qualitative), `weights.openness` 0.40 (qualitative).

### 4.6 `missing_qualitative_score`
| Parameter | Value | Meaning |
|---|---|---|
| `missing_qualitative_score` | 50.0 | Default qualitative score (0–100) when the datum is missing or null — not a judgment, but the neutral value of the corpus |

## 5. `scoring_model.risk` — perceived risk and volatility

`risk = 100 − (0.40 × stability + 0.35 × solvency + 0.25 × institutions)`;
`volatility = base + slope × risk`.

| Parameter | Value | Meaning |
|---|---|---|
| `weights.stabilite/solvabilite/institutions` | 0.40/0.35/0.25 | Only the "defensive" components feed the risk (dynamism and openness are excluded: a dynamic but fragile country is still risky) |
| `volatility_base` | 10.0 | Lower annual volatility (risk 0) |
| `volatility_slope` | 0.48 | Volatility added per risk point (risk 90 → 53.2%) |
| `bands` | [30, 50, 70] | Risk label thresholds: < 30 "Low", < 50 "Moderate", < 70 "High", otherwise "Very high" (`risk_label`) |

## 6. `scoring_model.cds_score` — CDS curve (bp) → score

| Parameter | Value | Meaning |
|---|---|---|
| `none_score` | 5.0 | Score if no quoted CDS exists (an absent market signal is a bad sign) |
| `floor_pb` | 20.0 | At ≤ 20 bp, score = 100 |
| `log10_ceiling_ratio` | 50.0 | Three reference decades: log score within [floor, floor × 50] |
| `spread` | 95.0 | Score 100 − 95 × logarithmic position (floor of 5 at floor × ratio, then clamped) |

## 7. `scoring_model.crp` — country risk premium (Damodaran)

| Parameter | Value | Meaning |
|---|---|---|
| `cds_offset_pb` | 25.0 | Basis points before the CDS is considered informative (market noise) |
| `cds_divisor` | 100.0 | bp → %: (cds − 25)/100 |

The retained source is `max(crp_cds, crp_rating)`; if no quoted CDS exists,
the rating spread is used (the French label stored in the code is
`Notation (CDS non coté)`, i.e. "Rating (CDS not quoted)"); otherwise
`max(...)`.

## 8. `scoring_model.ratings` — rating tables

| Parameter | Meaning |
|---|---|
| `scores` | Score 0–100 per rating (AAA 100 … RD 1; **NR = 20**, an unrated country sits near the bottom) |
| `spreads` | Bond spread (%) per rating, Damodaran reference early 2025; used for the country premium |
| `default_score` | 20.0 — used if the country's rating is not in `scores` |
| `default_spread` | 15.5 — used if the country's rating is not in `spreads` |

Check: `scores` and `spreads` must cover **exactly** the same ratings.

## 9. `scoring_model.verdicts` — decision thresholds

| Parameter | Value | Meaning |
|---|---|---|
| `invest_min` | 76.0 | ≥ 76 → "Invest" |
| `caution_min` | 62.0 | 62–75.9 → "Invest with caution" |
| `wait_min` | 45.0 | 45–61.9 → "Wait" |
| `wait_rescue_score` | 38.0 | 38–44.9 can be rescued if `wait_rescue_dynamisme` is reached |
| `wait_rescue_dynamisme` | 55.0 | Rescue condition: dynamism ≥ 55 → "Wait" (otherwise "Avoid") |
| `blocking_ratings` | ["NR", "D", "RD"] | A country that is **unrated or in default** **with no quoted CDS** cannot rank above "Wait" (no market price: no signal, no "Invest"). If a CDS is quoted, the market signal is used. |

Check: strict order `wait_rescue_score ≤ wait_min ≤ caution_min ≤ invest_min`.

## 10. Conversion details

| Rule | Definition |
|---|---|
| `linear(value, low, high, reverse)` | (value − low)/(high − low) × 100, clamped to 0–100, inverted if `reverse` |
| `clamp` | The tighter of the two bounds always applies |
| Score rounding | 1 decimal (`round(score, 1)`); sub-components rounded to 0.1 |
| Ke/CRP rounding | 2 decimals (Ke), 2 decimals (CRP) |

## 11. What deliberately stays hard-coded (and why)

These items are deliberately **outside the calibration**:

1. **`indicator_status`** (green/orange/red status on the dashboard) —
   these are qualitative display heuristics, not parameters used in the
   formulas; for example: growth ≥ 3% / ≥ 1%; inflation 0.5–3.5%;
   debt ≤ 60/100%; unemployment ≤ 6/10%; CDS ≤ 100/300 bp; real rate > 4
   or > 10–20% nominal → caution/risk. Changing these thresholds
   therefore affects **no** score, verdict or Ke — moving them to the
   metadata would be justified in a dedicated increment, with the same
   regression tests.
2. **`correlation`** (portfolio correlation matrix) — the correlations
   (0.80 within a group, 0.55 developed/emerging, 0.30
   developed/frontier, etc.) reflect the structure of the groups
   (`developed`, `emerging`, `gulf`, `frontier`) referenced by the
   `group_key` field of the country profiles. Moving them will be best
   done alongside the arrival of new groups (Priority 6, additional
   countries).
3. **Display**: `COMPONENT_LABELS`, `VERDICT_STYLES` (tone, icon,
   verdict sentence), `_PROFILE_DESCRIPTIONS` — these are FR labels;
   the EN port is done through `data/i18n/en/*.json` (overlays), not
   through the numeric calibration.
4. **Rounding** in the formulas (1 decimal for scores, 2 decimals for
   Ke): display conventions, not calibration choices.

## 12. History

- 2026-10-25: migration of all coefficients from the code to
  `data/meta.json` (`scoring_model`). **No figure changed**: regressions
  proven by `tests/test_scoring_config.py` (baseline frozen before the
  refactor, identical to within 0.1).
- Earlier definitions: see `docs/DATA_AUDIT.md` (data freshness) and the
  Sources & method page of the app (educational content).
