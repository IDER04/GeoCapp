# GeoCapp — Review of the 8 "manual" candidates (Priority 6, increment 1)

> Review date: 2026-10-25 · Scope: the **8 candidates classified as
> `manual`** in `docs/REFRESH_CANDIDATES_BRA_LBN_SYR.md`.
> **Status: review document.** No production data
> (`data/countries/*.json`, `data/meta.json`) was modified;
> `data_as_of` remains `2026-10-25`.

## Method and evidence used

The candidates were **not** validated on the report alone; the official
sources were consulted directly:

- **World Bank Indicators API v2** (observations + series metadata:
  definition, source institution) — including verification that LBN
  `SL.UEM` 2024/2025 are **null** (gaps);
- **IMF official statistics API (WEO DataMapper)** — `NGDP_RPCH` (real
  GDP growth) and `PCPIPCH` (inflation) for LBN and BRA; Syria is
  **excluded** there ("Data are excluded from 2011 onward because of the
  uncertain political situation", WEO statistical appendix);
- **BCB API (SGS)** series `13762` — "Dívida bruta do governo geral
  (% PIB)", 2008 methodology (gross debt of the **general government**);
- **National publications**: IBGE (GDP 2025 = 2.3%, IPCA 2025 = 4.26%,
  PNAD Contínua — unemployment (desocupação) 2025 = 5.6% annual);
  Banco Central (Relatório de Gestão das Reservas 2026: US$358.23 bn
  at 31/12/2025);
- **World Bank country monitoring**: Lebanon Economic Monitor (releases
  of 19/06/2025 and 22/01/2026), MPO/Lebanon data sheet (April 2026);
- **ILO**: ILOSTAT + ILO Syria employment fact sheet (July 2025), EUAA
  COI Syria report (July 2025).

Conservative standards applied: a more recent value is **not** approved
by default; each proposal must be cross-checked against a second
official source and be comparable in definition, unit and period. If the
evidence is contradictory or remains insufficient → `seek_better_source`.

Recommendation codes: `approve_candidate` (candidate validated as is,
future application after a signal from the user), `retain_existing`
(keep the production value), `seek_better_source` (neither the existing
value nor the proposal can be assessed — a better source is needed).

---

## Decision table (8 `manual` candidates)

| # | Country | Indicator | Recommendation |
|---|---------|-----------|----------------|
| 1 | Lebanon | Real GDP 2024 | **`seek_better_source`** |
| 2 | Lebanon | Inflation | **`approve_candidate`** |
| 3 | Syria | Unemployment | **`seek_better_source`** |
| 4 | Brazil | Real GDP 2025 | **`approve_candidate`** |
| 5 | Brazil | Inflation 2025 | **`seek_better_source`** |
| 6 | Brazil | Unemployment 2025 | **`approve_candidate`** |
| 7 | Brazil | Debt/GDP | **`seek_better_source`** |
| 8 | Brazil | Reserves 2025 | **`approve_candidate`** |

Count: **4 × `approve_candidate` · 0 × `retain_existing` ·
4 × `seek_better_source`.** None of these candidates should be applied
without an explicit signal from the user; the 4 approvals concern
Lebanon's inflation and three Brazil candidates (GDP, unemployment,
reserves) — see the detail for each entry.

---

### 1) Lebanon — `gdp_growth` (real GDP, %, 2024)

- **Existing**: −6.5% · 2024 · unit % · source "IMF / estimates".
- **Proposed**: −7.08% · 2024 · unit % · source World Bank (WDI
  `NY.GDP.MKTP.KD.ZG`), `obs_status` empty = **actual**, WDI base
  updated 2026-10-08, retrieved 2026-10-25.
- **Comparability**: same definition (real GDP growth, annual average),
  same unit and same period → comparable provided the discrepancy
  between sources is reconciled.
- **Unresolved gap between institutions**: WDI and the Lebanon Economic
  Monitor show **−7.1% for 2024** (LEM revision from −5.7% to −7.1% in
  spring 2025; MPO data sheet April 2026: −7.1% in 2024, consistent with
  the historical values of the same series: −6.9% in 2019, −21.4% in
  2020, −7.0% in 2021, −0.6% in 2022, −0.8% in 2023); the IMF (WEO,
  October 2026 vintage), however, shows **−5.2% for 2024**. The existing
  −6.5% (IMF) lies between the two.
- **Official source?** Yes (WDI, institution "Country official
  statistics… + Staff estimates, World Bank"); **actual** observation
  (not a forecast).
- **Effect of a substitution**: a gap of moderate narrative weight
  (−6.5 → −7.08) that could harden the analysis, but approving it today
  would mean settling an IMF/World Bank disagreement of 1.9 points
  without having reconciled it; production could later move to −7.1 or
  to a clearer IMF revision.
- **Decision: `seek_better_source`** — the World Bank provides three
  consistent publications at −7.1, while the IMF says −5.2; resolving
  the divergence (vintage, national accounts basis, conflict/damage
  estimate vs staff estimate) requires a targeted check (WEO Lebanon
  country page + Article IV if published). In the meantime, the
  existing value and order of magnitude remain valid.

### 2) Lebanon — `inflation` (annual CPI, %, 2025)

- **Existing**: 45.0% · 2024 · source "Central Administration of
  Statistics / IMF". **Cross-checked**: the IMF (WEO Oct. 2026) shows
  45.2% for 2024 → the existing value is validated to within 0.2 points.
- **Proposed**: 14.60% (14.5976) · **2025** · source World Bank (WDI
  `FP.CPI.TOTL.ZG`, series fed by IMF IFS), `obs_status` empty =
  **actual**; WDI updated 2026-10-08; retrieved 2026-10-25.
- **Comparability**: same concept (annual change in the consumer price
  index, yearly average), same unit (%), 2025 more recent than 2024.
  **Strong cross-check**: IMF WEO = **14.6%** for 2025, exactly the same
  value — consistent because both series derive from the same ecosystem
  (CAS via IFS).
- **Official source?** Yes (World Bank/IFS + CAS via IMF). **Actual**
  observation, estimated consistently by both institutions.
- **Effect of the substitution**: strong and **favorable** — moves the
  profile from a "very high inflation (45%)" regime to a
  **disinflation** regime with a stable exchange rate (converges with
  the LEM: "inflation projected to moderate to 15.2% in 2025"). The
  profile's `note` and `date` must be updated when applying; the
  current note mentions the collapse of the pound, and the text will
  become obsolete.
- **Decision: `approve_candidate`** — exact double corroboration
  (WDI = WEO = 14.6), current and comparable; the strongest candidate
  of the batch. Applying it remains a separate action signed off by the
  user (adopting `date` 2025, an updated `source` and a rewritten
  `note`).

### 3) Syria — `unemployment` (total unemployment, %, 2025)

- **Existing**: 50.0% · 2024 · source "ILO estimate" (detailed citation
  missing in production).
- **Proposed**: 13.57% (13.569) · 2025 · source World Bank (WDI
  `SL.UEM.TOTL.ZS`) = **ILO modeled estimate** (`ILOEST`), database
  consulted: January 2026, `obs_status` empty; WDI updated 2026-10-08;
  retrieved 2026-10-25.
- **Documented methodological context**: the ILO itself writes (Syria
  fact sheet, July 2025) that "there is a lack of recent labour market
  data for Syria, requiring the use of modelled estimates" — the 13%
  value (2024) is a **model output with high uncertainty** in a context
  of conflict and transitions. An independent report (EUAA COI Syria,
  July 2025) put it at **24% in 2024**. The existing 50% comes from
  crisis estimates that lack a precise citation in production and could
  not be traced. Finally, the IMF has systematically **excluded** Syria
  from the WEO since 2011 — no validation is possible on the IMF side.
- **Comparability**: identical concept (unemployment as % of the labor
  force, ILO) but bases diverge by a factor of ~2–4 — not reconcilable
  as things stand.
- **Official source?** Yes (WDI/ILO), but a **modeled estimate**, not a
  survey observation.
- **Effect of the substitution**: major and **potentially misleading** —
  50 → 13.6 would turn "half of the labor force without a job" into
  "moderate unemployment", which no recent Syrian survey supports; the
  ILO model has no visibility on the post-2024 transition.
- **Decision: `seek_better_source`** — neither the candidate nor the
  existing value rests on a solid survey. Forward-looking action: the
  next review should look for the Syria ILOEST series on ILOSTAT (13.6
  expected for 2025), the first surveys by the Syrian government after
  the transition and, where applicable, post-conflict World Bank
  publications; in the meantime, keep the production value with its
  "estimate" label.

### 4) Brazil — `gdp_growth` (real GDP, %, 2025) — expansion candidate

- **Existing**: — (no production file; Brazil is not covered; 10
  current countries).
- **Proposed**: 2.29% (2.2857) · 2025 · actual; source WDI
  `NY.GDP.MKTP.KD.ZG` ("Country official statistics…"), WDI 2026-10-08.
- **Comparability — triple agreement**: IBGE (release of 03/03/2026):
  **2.3% in 2025** (5th consecutive year of growth); IMF WEO: 2.3%;
  WDI: 2.29%. Identical definition (real GDP, year).
- **Decision: `approve_candidate`** — the strongest support for the
  future expansion workflow (WDI base, corroborated by national
  statistics and the IMF). When the profile is written, the primary
  source will still be cited: "IBGE / World Bank (WDI)".

### 5) Brazil — `inflation` (CPI, %, 2025) — expansion candidate

- **Existing**: — (expansion).
- **Proposed**: 5.02% (5.0168) · 2025 · actual; WDI `FP.CPI.TOTL.ZG`,
  institution "International Financial Statistics database, IMF".
- **Official cross-check**: the **official** reference inflation (IBGE,
  IPCA — broad national index) reached **4.26% in 2025** (within the
  4.5% target). The 0.76-point gap with WDI/IFS (5.02) cannot be
  explained at this stage: the exact CPI used by IFS for Brazil (IPCA,
  INPC, FGV general CPI, annual average vs December difference) could
  **not** be reconciled online — no assumption is made here.
- **Official source?** Yes, but divergent from the national source.
- **Effect of the substitution (future profile)**: presenting 5.02%
  would show inflation above target, while the official IBGE figure says
  the opposite (4.26 ≤ 4.5) — risk of signaling the "wrong" monetary
  policy regime.
- **Decision: `seek_better_source`** — prefer IBGE/IPCA (4.26%, year
  2025) and verify the exact label of the IFS series before any use. Do
  not present the World Bank value as is.

### 6) Brazil — `unemployment` (unemployment, %, 2025) — expansion candidate

- **Existing**: — (expansion).
- **Proposed**: 5.97% · 2025 · actual (on paper); WDI `SL.UEM.TOTL.ZS` =
  **ILO modeled estimate** (January 2026 base).
- **Official cross-check**: IBGE, PNAD Contínua (release of
  30/01/2026): annual rate ("desocupação") = **5.6% in 2025** (earlier
  years: 6.6% in 2024) — comparable definition (unemployment as % of
  the labor force). WB↔IBGE gap: 0.37 points (modeled vs survey).
- **Official source?** Yes; the WDI/ILO candidate is a modeled
  estimate, while IBGE is a genuine survey.
- **Effect**: low — both values establish the same story (labor market
  at the best level of the series).
- **Decision: `approve_candidate`** with a caveat: when the profile is
  created, the **primary source = IBGE PNAD Contínua (5.6%)**, the World
  Bank value serving only as a cross-check; the profile's `source` field
  must carry IBGE's name if that value is chosen.

### 7) Brazil — `debt_gdp` (debt/GDP, %, 2024) — expansion candidate

- **Existing**: — (expansion).
- **Proposed**: 81.86% · **2024** · WDI `GC.DOD.TOTL.GD.ZS` =
  **CENTRAL government** debt (source: Government Finance Statistics
  Yearbook, IMF).
- **Official cross-check (correct definition)**: the GeoCapp
  indicator corresponds to **general government** debt — in Brazil, the
  official measure is the **DBGG (dívida bruta do governo geral)**,
  published by the Banco Central (SGS 13762, 2008 methodology,
  IMF-aligned): **76.27% of GDP in Dec. 2024** and 78.64% in Dec. 2025.
  The World Bank proposal (central government) is **5.6 points higher**
  in 2024 — the gap cannot be reconciled simply by changing the year.
- **Official source?** Yes (both), but **incompatible definitions**
  (central ≠ general), giving a misleading sustainability signal if used
  as is.
- **Effect**: would overstate gross debt by ~5.6 p.p., feeding a "very
  high debt" narrative and overinterpretation of fiscal risk.
- **Decision: `seek_better_source`** — the future Brazil profile must
  carry the DBGG (76.3% in 2024, 78.6% in 2025, source Banco Central do
  Brasil, SGS series 13762); a connector is conditional on the next
  increment (free SGS API).
- (Methodological note: an attempt to reconcile via the DataMapper code
  `GGXWDG_NGDP` was unsuccessful — that code does not measure debt — and
  is **not** used as evidence here.)

### 8) Brazil — `reserves` (reserves, US$ bn, 2025) — expansion candidate

- **Existing**: — (expansion).
- **Proposed**: US$358.5 bn · 2025 · actual; WDI `FI.RES.TOTL.CD` (total
  reserves, **gold included**, US$) converted US$ → US$ bn (×10⁻⁹,
  defined conversion); source "IFS, IMF".
- **Official cross-check**: Banco Central do Brasil, *Relatório de
  Gestão das Reservas Internacionais* (March 2026): **US$358.23 bn at
  31/12/2025** ("conceito caixa"), versus US$329.73 bn at 31/12/2024.
  WB↔BCB gap: 0.08% — both figures describe the same quantity under the
  same concept (total incl. gold; fine difference: cash vs accrual).
- **Official source?** Yes; **actual** observation.
- **Effect**: none on interpretation (same order of magnitude).
- **Decision: `approve_candidate`** — with a unit caveat (US$ bn) and,
  when the profile is written, a deliberate choice of the concept to
  record (here **total, gold included** — which must be made explicit
  in `note`; the Lebanon profile, for its part, documents **net**
  reserves).

---

## Appendices — cases already rejected / deferred, noting the gaps to address

These candidates already have a documented `reject/gap` in the first
report; they are not among the 8 `manual`. The new facts gathered during
this review will serve as inputs for future increments:

- **Lebanon — unemployment (reject/2023 = 11.0%)**: the review
  established a triple divergence: ILO modeled 2023 = 11.0% (2024/2025
  **null**), MPO/Lebanon data sheet April 2026: 2023 = 23.3%, **2024 =
  22.8%, 2025e = 22.8%**, and the production profile = 30 (2024, "ILO /
  World Bank estimate", a citation close to the unemployment rates from
  recent Lebanese surveys, ~30%). No automatic decision: resolving it
  depends on work with ILOSTAT and national surveys (no usable WB
  candidate — the WDI series for LBN 2024/2025 are null).
- **Lebanon debt/reserves, SYR gdp/inflation/debt/reserves**: the
  rejection reasons from the first report remain valid (central vs
  general definition; gross vs net; earlier vintages and documented WDI
  gaps, e.g. SYR debt = 0 rows).

### Brazil — "expansion workflow" reading

Candidate by candidate, the future Brazil profile can rely on:

| Indicator | WB candidate | Review status | Best known source |
|---|---|---|---|
| GDP 2025 | 2.29% | `approve_candidate` | IBGE 2.3% (+ IMF 2.3%) — triple agreement |
| Unemployment 2025 | 5.97% | `approve_candidate` (cross-checked) | **IBGE PNADC 5.6%** (primary source desired when the profile is written) |
| Reserves 2025 | US$358.5 bn | `approve_candidate` | BCB US$358.23 bn (accrual) — 0.08% agreement |
| Inflation 2025 | 5.02% | `seek_better_source` | **IBGE IPCA 4.26%**; IFS series to be identified before use |
| Debt/GDP 2024 | 81.86% central | `seek_better_source` | **BCB DBGG 76.3% (2024)** — general definition to be preferred |

**Brazil expansion outcome: 3/5 candidates usable now, 2/5 need a
better source — and none authorizes writing
`data/countries/brazil.json` without a separate signal from the user.**

## Limits of the evidence

- No review can reasonably resolve the IMF/World Bank divergence on
  Lebanon's 2024 GDP within this framework: both institutions publish
  valid vintage estimates (−5.2 vs −7.1), with no public reconciliation
  basis known here.
- The unemployment values for Syria (modeled) and Lebanon (modeled vs
  MPO) are not direct surveys: this is a structural limit
  (conflict/transitions) documented by the ILO, not a retrieval defect.
- The identification of the exact CPI behind Brazil's IFS/WDI series
  (5.02 vs IPCA 4.26) remains to be clarified (untested hypothesis in
  this document: FGV CPI / shifted year) — no assumption is endorsed.
- There is no per-observation publication date on the WDI side: the
  date of the last update of the WDI database (2026-10-08) serves as a
  timestamped proxy, in addition to the retrieval dates (2026-10-25).
