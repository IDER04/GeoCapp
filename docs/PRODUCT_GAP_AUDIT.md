# GeoCapital — Product Gap Audit (FR/EN, MVP 1.0)

Date: 2026-10-25 · Scope: 8 product sections, functional gaps prioritized
(funcional completeness > visual polish). Verification for this audit:
unittest suite **96/96 OK** (81 existing + 15 localization tests), FR renders
of all 8 pages via Streamlit AppTest, full EN pass in a real browser
(language switch, all 8 sections, non-USA country profile included).

---

## Global constraints (by design in this phase)

- `geocapital/data.py` and `geocapital/scoring.py` are **read-only**:
  all EN localization goes through display-time overlays
  (`data/i18n/en/*.json` + `geocapital/i18n.py`); no data file edited.
- AI payloads stay **FR-grounded** (deterministic facts language);
  only display names are localized.
- i18n guarantee: numeric values, IDs (`id`, `iso3`, `group_key`),
  quiz answer indices and URLs are never passed through translation
  (enforced by `tests/test_localize.py`).

---

## Prioritized functional gaps (top 3, cross-section)

### 1. FR number and unit formatting leaks in EN surfaces
Root cause: `data.py::format_number`, `indicator_display` and
`indicator_summary` (untouchable) hard-code French locale and units —
decimal commas (`2,8 %`), space-thousands (`3 200 Mds $`), and FR units
(`% du PIB`, `Mds $`, `pb`) that reach EN indicator cards, comparator
table and CSV. Values are correct; only the typography is FR.
Also `indicator_summary` falls back to the French literal **« Non coté »**
for an unquoted CDS (Lebanon, Syria) in both languages, and country_page
pipes fixed `4,20 %` / `4,50 %` KPI values (RE risk-free / ERP) from FR
string literals.
Fix direction (next phase, no scoring/data edit needed in views):
render numbers through an i18n-aware formatter in `ui.py`, and map the
unit strings via `display_label()` at display time.

### 2. Analyst answers are not localized end-to-end
The analyst page UI (selectors, placeholders, legend) is translated,
but the conversation payloads (`geocapital/analyst.py`) are FR-only:
validated facts FR labels (`pays`, `poids`, `volatilite`), FR canned
phrases, and `FALLBACK_QUESTION` in FR even in EN mode. This is the
accepted "facts language deterministic" compromise, but it means an EN
user reads FR fact blocks and (without an AI key) a FR fallback question.
Fix direction: EN mirror of the fact templates with FR kept for AI prompts.

### 3. Non-numeric cell fallbacks in the comparator
`comparison_frame` fills missing cells with FR literals (e.g. `Non coté`,
`NR` is acceptable) and the on-screen table displays composed summary
strings without translation, while the CSV export only strips the row
labels. Combined with gap 1, EN comparator cells are a mix of EN labels
(US point of the labels is fixed) and FR-formatted values.
Fix direction: post-process summary strings cell by cell (regex on
known unit suffixes) before both display and CSV.

---

## Section-by-section

### 1. Living map (◉)
- Working: 10-country selection, score per investor profile (3 profiles),
  metric selector (attractiveness / controlled risk / growth / currency
  stability) with internal FR state keys + localized labels, group
  filtering FR *and* EN (via `group_key()` reverse-map over overlays),
  chips grid, top-3 reading grid, risk/return map, legal caption.
- Verified EN: names, group chips, verdicts, metric labels, sidebar.
- Gaps (priority order):
  1. Map annex captions ("grey countries not rated") come from STRINGS
     — OK; only number typography inherits gap #1.
  2. Verdict thresholds show scoring-derived wording already localized.

### 2. Country profile (▤)
- Working: selector with localized names, hero (region/group/headline/
  official name/verdict), narrative tabs — timeline (5–7 dates),
  institutions, relations (allies/rivals/dependencies), strengths/
  risks/opportunities, full EN quiz (options + explanation, answer index
  preserved), dashboard of 11 indicators (labels localized, CRP card
  special-cased with i18n note + "Damodaran · {source}"), Ke formula
  explanation, AI explainers (FR-grounded payloads).
- Verified EN: USA & Morocco (non-USA), incl. Morocco protectorate
  timeline fully EN.
- Gaps (priority order):
  1. KPI fixed strings `4,20 %` / `4,50 %` show FR decimals in EN
     (part of gap #1; trivially fixable in views with an i18n format).
  2. Indicator card units (`% du PIB`, `Mds $`) FR in EN (gap #1).
  3. Score-reason lines are localized labels but interpolate numeric
     values FR-formatted (comma decimals) — gap #1 again.

### 3. Comparator (⇄)
- Working: 2–3 country multiselect with localized names, radar chart
  (localized components), required-return comparison, full dashboard
  table with localized row labels, FR-vs-EN "reading" paragraph,
  CSV export with translated header ("Indicator") and translated row
  values, no-signal handling per profile.
- Verified EN: table headers, reading paragraph, CSV column header.
- Gaps (priority order): see top gaps #1 and #3 (value typography,
  `Non coté`, CSV values not localized beyond labels).

### 4. News decoder (⌁)
- Working: country + recent-event selectors (localized names), event
  overlays (10 events EN incl. accent-free rewording), 4-step causal
  chain (event → economy → finance → winners/losers), concept cards
  ("In the Treasury market, this is called…"), winners/losers lists,
  learn-more link, historical echo card with localized country name.
- Verified EN: Sept 18 2024 Fed event end-to-end, no FR leaks.
- Gaps (priority order):
  1. Event dates are data strings (`"2024-09-18"`) formatted FR side;
     EN shows ISO/source as-is — acceptable but could be localized.
  2. Source line ("Source: Federal Reserve") relies on the EN `source`
     field — complete today, void-check only narrative paths.

### 5. Analyst (✎)
- Working: page header/captions EN, intent selector (6 topics) with
  localized labels, entity selectors with localized country/event
  names, legend (validated facts / AI interpretation / hypothesis),
  conversation cleared per question, graceful no-AI-key captions.
- Gaps (priority order): top gap #2 (FR fact payloads, FR
  FALLBACK_QUESTION). Nothing else functional found.

### 6. Portfolio (◫)
- Working: €100k fictional allocation with per-country inputs, 3
  EN presets (Defensive/Balanced/Offensive), weighted Ke, estimated
  volatility, diversification gain, HHI/effective countries,
  normalized allocation chart with localized names, EN diagnosis
  paragraph, risk-contribution chart, reset, AI commentary (FR payload).
- Verified EN end-to-end, no FR leaks.
- Gaps (priority order):
  1. AI commentary FR (accepted design, listed under gap #2).
  2. Volatility/return figures inherit FR decimal commas — gap #1.

### 7. Progress (✦)
- Working: explored-country tracking, quiz-success counters, badges,
  mental map grid grouped by the 4 groups with EN headers
  (DEVELOPED/EMERGING/GULF/FRONTIER), per-country actions
  (Open/Revisit/quiz), next-step suggestion (localized copy),
  "Understanding ≠ liking" caveat, progress reset.
- Verified EN end-to-end, no FR leaks.
- Gaps (priority order):
  1. Nothing functional found; internal group values stay FR by design
     (translated at display, filter works in both languages).

### 8. Sources & method (◎)
- Working: 3-step story (past/present/decision), score-component table,
  3-profile weighting table, Ke formula with EN methodology text
  (`meta.json` overlay: score/ke/missing/disclaimer), missing-data
  rule (Lebanon/Syria treated as information), AI role table, 7 sources
  list EN, update line, limits & warning.
- Verified EN end-to-end, no FR leaks.
- Gaps (priority order):
  1. Fixed percentages in EN methodology text (`4.20 %`) match the
     hardcoded KPIs — consistent, but both should derive from scoring
     constants to avoid drift.

---

## Test & data guarantees added in this phase

- `tests/test_localize.py` — 15 tests: overlay completeness per country,
  events, meta; identity of numerics/IDs/quiz answers under
  localization; scoring results identical FR vs EN; FR fallback on
  empty translations; EN accent hygiene (no `é à ç œ…`) on all overlays.
- Overlays: 10 countries + `events.json` + `meta.json` (incl. `group`,
  indicator `source` ×100, CRP note via `ind.crp.note`,
  comparator CSV header via `comp.csv.indicator`).
- STRINGS parity: 497 keys in FR **and** EN (`test_i18n.TestParity`).

## Known verification limitation

Streamlit AppTest cannot replay the language radio in EN sessions
(`ValueError: 'Équilibré' is not in list` — harness quirk with formatted
labels, not an app bug). EN verification was therefore done in a real
browser against the running Streamlit server (all 8 pages + 2 country
profiles + comparator table + portfolio panel).
