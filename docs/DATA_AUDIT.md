# GeoCapital — Data Audit Baseline (Priority 1, Phase 1 foundations)

Date of audit / retrieval baseline: **2026-10-25** (`app.data_as_of` in
`data/meta.json`). This document records **what is currently in the
database, where it came from, how old it is, and what needs refreshing** —
*no indicator value has been changed yet*.

## 1. Vocabulary (display contract, implemented in Slice 1)

| Term | Definition | Where it lives |
|---|---|---|
| Observation date | The period the data covers (e.g. `"2024"`, `"déc. 2024"`) | `indicators.*.date` in each `data/countries/*.json` |
| Retrieval date (`data_as_of`) | The date GeoCapital verified the datum against its source | `app.data_as_of` in `data/meta.json` |
| Stale / "to refresh" | Observation year **< current year − 1** (in 2026: anything before 2025) | `geocapital/freshness.py` (display layer only — never affects scores) |

Stale indicators carry a `⚠` marker on their dashboard card in FR and EN,
next to the usual "source · date" footer. Undated values (`calcul`, CDS
computation) are never marked stale.

## 2. Current vintage — every observation is dated 2024

Audit of all 10 countries (50 indicator records with dates under
`data/countries/*.json`):

| Country | All quantitative indicator dates |
|---|---|
| China, Lebanon, Saudi Arabia, South Africa, Syria, UAE | `2024` for every indicator |
| France, Morocco, USA | `2024`, except `policy_rate`: `déc. 2024` |
| Japan | `2024`, except `policy_rate`: `janv. 2025` |

**Conclusion at 2026-10-25:** the entire quantitative dataset is
2024-vintage (≥ 1.5 years old). Under the freshness rule above, every
`2024` observation is marked `⚠` and every profile now surfaces:
- a "Data as of 2026-10-25 / Données au 2026-10-25" retrieval line,
- a legend explaining the `⚠` marker,
- the oldest observation year underlying the composite verdict
  (`fresh.verdict_dates`).

No country profile or verdict can be presented as "current" as long as
its indicators are 2024-vintage; the display layer states this
explicitly in both languages.

## 3. Refresh plan (to be executed, source-led — no invented values)

Each replacement must: (a) match a checkable source, (b) keep the
previous FR value recoverable in Git history, (c) update the indicator
`date` to the observation period, (d) note the retrieval context in
`docs/` and FR/EN narratives where wording depends on the level.

Ordered by priority:

1. **Syria and Lebanon (careful reassessment).**
   Both profiles carry structural missing data (no active sovereign
   rating, no quoted CDS — treated as deliberate risk signals). Verify
   against IMF Article IV / WEO databases, World Bank, BDL (Banque du
   Liban) and SAMA-equivalent publications before touching any value.
   Lebanon and Syria narratives (2024) also pre-date major regime-level
   changes; narrative updates must cite dated sources, not press memory.
2. **Policy rates** (US Fed, ECB/Banque de France reference, BOJ, PBoC
   LPR, Banque du Maroc, CBUAE, SAMA, SARB, Banque du Liban, Banque
   centrale de Syrie) — most volatile + most stale (déc. 2024/janv.
   2025), available from central-bank official pages.
3. **GDP growth / inflation / unemployment / debt** — IMF WEO October
   2025 vintage (findable via imf.org), used as a single authoritative
   batch; record vintage explicitly per indicator.
4. **Sovereign ratings / CDS / equity markets / currencies** — agency
   rating matrices (S&P, Moody's, Fitch) and market references from
   retrievable public pages; where a live quote cannot be verified
   (CDS for small markets), retain the older value **and keep the ⚠
   stale label** rather than fabricate.

## 4. Standing limitations

- The dataset stays "educational reference", not real time; the
  Sources & Method page says so and remains authoritative on limits.
- Observation dates are per-indicator; the composite verdict inherits
  the oldest vintage — displayed on the dashboard and KE block.
- FR decimal formatting in numeric strings (e.g. `2,8 %`) is a
  `data.py` display issue tracked in `docs/PRODUCT_GAP_AUDIT.md`
  (top gap #1); provenance display does not duplicate it.
- Retrieval date is a single app-level stamp; per-indicator retrieval
  dates will attach as each refresh batch lands (fields to be added at
  that time — `retrieved: <ISO date> — <source>`), not before.

## 5. Applied change #1 — Lebanon inflation (Priority 6, increment 6.1)

Applied on 2026-10-25, per the review decision recorded in
`docs/REFRESH_REVIEW.md` (entry 2, `approve_candidate` — the only
production application authorized in this increment). This supersedes
the intro statement "*no indicator value has been changed yet*" and
respects §4's pre-declared per-indicator `retrieved` field approach.

**File:** `data/countries/lebanon.json` · **Indicator key:**
`indicators.inflation` · **Country id:** `lebanon` (ISO3 LBN).

| Field | Before (2024 vintage) | After (applied) |
|---|---|---|
| Value / unit | `45.0` / `%` | `14.6` / `%` |
| Observation period (`date`) | `"2024"` | `"2025"` |
| Source | Administration centrale de la statistique / FMI | Banque mondiale (WDI, série `FP.CPI.TOTL.ZG`) / FMI (WEO) |
| Source URL | — | `https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=LB` |
| Obs status | — | `actual` (WDI `obs_status` empty = real observation; neither estimate nor forecast) |
| Retrieved | — | `2026-10-25` (**retrieval date, not observation date** — the observation period remains `"2025"`) |

Provenance and corroboration (full evidence in
`docs/REFRESH_REVIEW.md`, entry 2):

- The value is the 2025 annual-average CPI inflation (WDI
  `FP.CPI.TOTL.ZG`, database lastupdated 2026-10-08), definitionally
  identical to the existing indicator (annual-average consumer price
  inflation, %).
- Independent cross-check: IMF WEO (PCPIPCH, Oct 2026 vintage) shows
  exactly **14.6** for 2025 and **45.2** for 2024 — the *existing* 45.0
  is thereby corroborated, and the substitution is a new observation
  year, not a competing estimate.
- Limitations: the disinflation rests on a still-fragile exchange-rate
  stabilization; the note field was rewritten accordingly, and the
  replacement is explicit (schema has no per-indicator history —
  confirmed by audit: no production file carries `history_value` /
  `previous` fields; the prior FR narrative remains recoverable in
  Git history).

Effect on model outputs (formulas, thresholds and weights **unchanged**
— verified by the frozen-baseline suite): Lebanon component
`stabilite` 4.4 → 31.5 (inflation sub-score 100 − |14.6 − 2.0| × 4 =
49.6; policy_rate 20.0 − inflation 14.6 = real rate 5.4 now inside the
[−8, 6] band → 40; currency unchanged at 8.0). Scores 12.8/14.8/17.8 →
20.9/20.2/20.5 (Prudent/Équilibré/Audacieux), verdict **Éviter
unchanged** on all three profiles, risk 89.2 → 78.4, volatility
52.8 → 47.6, ke and crp unchanged (rating/CDS-based). The
`tests/test_scoring_config.py` baseline contains the approved exception
only in its `lebanon` rows.

**Reproducing the pre-application baseline (no working-tree changes).
** The original frozen rows are preserved here and in the increment
report rather than in Git history, because
`tests/test_scoring_config.py` is untracked. The *data* side is fully
reproducible from Git, since `data/countries/lebanon.json` is tracked:

1. `git show HEAD:data/countries/lebanon.json` — returns the
   pre-application file (inflation block: `45.0` / `%` / `2024` /
   "Administration centrale de la statistique / FMI"), read-only;
2. load that JSON into a dict and call
   `scoring.overall_score(country, profile)` with the current code —
   formulas unchanged, this yields exactly the original rows:
   12.8/14.8/17.8 → "Éviter" ×3, risk 89.2, volatility 52.8, ke 31.20,
   `stabilite` 4.4 (verified during increment 6.2 review);
3. reapply this increment's block (§ above) to return to the current
   state — or simply leave the working tree untouched and discard the
   in-memory dict.

Scratch copies (`/tmp/geocapital_baseline.json` etc.) are regenerated
at each increment and are not the durable record; this subsection and
`docs/REFRESH_REVIEW.md` (entry 2) are.

Also stale now: §2's table ("every observation is dated 2024") — one
record (Lebanon `inflation`, `"2025"`) has moved on. The remaining
49 records are still 2024-vintage; §2 applies to them until each
refresh batch lands.

## 6. Prepared candidate — Brazil expansion file (not registered)

A proposed Brazil country file was prepared at
`data/candidates/brazil.json` (status `proposed_for_review`), based on
the sources verified in `docs/REFRESH_REVIEW.md` (entries 4–8):

| Indicator | Value | Period | Source (verified) | Note |
|---|---|---|---|---|
| `gdp_growth` | 2.3 % | 2025 (annual) | IBGE — Contas Nacionais (release 2026-03-03) | Triple agreement with IMF WEO (2.3) and WDI (2.29) |
| `inflation` | 4.26 % | 2025 (IPCA, Dec→Dec cumulative) | IBGE — IPCA fascículo dez. 2025 | National source preferred; the unsettled WDI 5.02 divergence (entry 5) is not used |
| `unemployment` | 5.6 % | 2025 (PNAD annual average) | IBGE — PNAD Contínua annual release 2026-01-30 | Cross-checked against ILO-modeled 5.97; direct result 5.1 % (Dec quarter) documented in notes |
| `debt_gdp` | 78.6 % | déc. 2025 | BCB — DBGG general-government gross debt (SGS 13762) | Central-government WDI 81.86 (2024) rejected: incompatible definition (entry 7); 2024 value 76.27 % |
| `reserves` | 358.2 Md$ | 31/12/2025 | BCB — Relatório de Gestão das Reservas (mars 2026), "conceito caixa" | Cross-check WB/IFS 358.5 (accrual), 0.08 % apart; concept (total incl. gold) explicit in note |

Not part of production: Brazil is not in
`data/countries/`, the country registry, navigation, comparator or
scoring coverage (verified: `geocapital/data.py` loads only
`data/countries/*`). Market indicators (`policy_rate`, `rating`, `cds`,
`crp`, `equity_index`, `currency`) and editorial content are explicitly
listed as `open_items` in the candidate file — no values or metadata
were invented. Registration awaits a separate user-authorized
increment.
