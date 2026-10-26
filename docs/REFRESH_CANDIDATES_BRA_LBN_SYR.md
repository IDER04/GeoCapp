# Rapport candidats — rafraîchissement des données (Brésil, Liban, Syrie)

Date de récupération : **2026-10-25** · Source : Banque mondiale, Indicators API v2 (gratuite, sans clé).

> **Statut du rapport : revue avant application.** Aucune donnée de production
> (`data/countries/*.json`) n'a été modifiée. Chaque candidat porte une
> recommandation (`safe` / `manual` / `reject` / `gap`) à arbitrer manuellement.

Comptage global : **0 safe · 8 manual · 6 reject · 1 gap** (15 candidats).

## lebanon

### gdp_growth (lebanon)
- Série WB : `NY.GDP.MKTP.KD.ZG` (correspondance : exact)
- Existant : -6.5 % · 2024 · « FMI / estimations »
- Proposé : -7.0799 % · 2024 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série NY.GDP.MKTP.KD.ZG »
- Requête API : https://api.worldbank.org/v2/country/LBN/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- **Recommandation : `manual`** — même millésime (2024) : valeur WDI -7.0799 vs existant -6.5 — arbitrage de provenance (WB/FMI) à valider manuellement avant de toucher la fiche.

### inflation (lebanon)
- Série WB : `FP.CPI.TOTL.ZG` (correspondance : exact)
- Existant : 45.0 % · 2024 · « Administration centrale de la statistique / FMI »
- Proposé : 14.5976 % · 2025 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série FP.CPI.TOTL.ZG »
- Requête API : https://api.worldbank.org/v2/country/LBN/indicator/FP.CPI.TOTL.ZG?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- **Recommandation : `manual`** — observation WDI 2025 (14.5976 %) vs existant 2024 (45.0 %) : candidat sérieux — à valider manuellement (cohérence avec le 2e source avant application).

### unemployment (lebanon)
- Série WB : `SL.UEM.TOTL.ZS` (correspondance : partial)
- Existant : 30.0 % · 2024 · « Estimation OIT / Banque mondiale »
- Proposé : 10.985 % · 2023 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série SL.UEM.TOTL.ZS »
- Requête API : https://api.worldbank.org/v2/country/LBN/indicator/SL.UEM.TOTL.ZS?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : Série MODELLISÉE ILO (pas une enquête brute) : estimation tripartite OIT, potentiellement décalée en période de rupture (crise libano-syrienne).
- **Recommandation : `reject`** — observation 2023 plus ancienne que la valeur existante (2024) — valeur conservée, écart (stale) signalé côté freshness.

### debt_gdp (lebanon)
- Série WB : `GC.DOD.TOTL.GD.ZS` (correspondance : partial)
- Existant : 150 % · 2024 · « Estimation FMI »
- Proposé : 128.6413 % · 1999 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série GC.DOD.TOTL.GD.ZS »
- Requête API : https://api.worldbank.org/v2/country/LBN/indicator/GC.DOD.TOTL.GD.ZS?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : GeoCapital suit la dette OFFICIELLE (générale) du secteur public — la série WB « central government » sous-estime la dette générale (administration locale, entreprises publiques). Comparer avec précaution ; pour plusieurs pays la série s'arrête en années reculées.
- **Recommandation : `reject`** — série « dette du gouvernement central » obsolète (1999) et définition sous-couverte (gouvernement central ≠ dette générale) — conservé 2024: 150.

### reserves (lebanon)
- Série WB : `FI.RES.TOTL.CD` (correspondance : exact_for_total)
- Existant : 10 Mds $ · 2024 · « FMI / BDL »
- Proposé : 33.3 Mds $ · 2024 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série FI.RES.TOTL.CD · unité convertie US$ → Mds $ »
- Requête API : https://api.worldbank.org/v2/country/LBN/indicator/FI.RES.TOTL.CD?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : unité convertie (US$ → Mds $) : conversion définie, sans ambiguïté
- Écart de définition : Unité demandée GeoCapital : Mds $ (US$ / 1e9). Certaines fiches de production (ex. Liban) documentent les réserves NETTES — écart de définition, alors rejeté.
- **Recommandation : `reject`** — définitions incompatibles: la fiche documente des réserves NETTES (10 Mds $) alors que la série WB est TOTALE (brut, or inclus) (33.3 Mds $) — ne pas écraser.

## syria

### gdp_growth (syria)
- Série WB : `NY.GDP.MKTP.KD.ZG` (correspondance : exact)
- Existant : -1.2 % · 2024 · « Estimation Banque mondiale / FMI »
- Proposé : -0.2025 % · 2022 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série NY.GDP.MKTP.KD.ZG »
- Requête API : https://api.worldbank.org/v2/country/SYR/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- **Recommandation : `reject`** — observation 2022 plus ancienne que la valeur existante (2024) — valeur conservée, écart (stale) signalé côté freshness.

### inflation (syria)
- Série WB : `FP.CPI.TOTL.ZG` (correspondance : exact)
- Existant : 60.0 % · 2024 · « Estimation »
- Proposé : 13.4176 % · 2019 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série FP.CPI.TOTL.ZG »
- Requête API : https://api.worldbank.org/v2/country/SYR/indicator/FP.CPI.TOTL.ZG?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- **Recommandation : `reject`** — observation 2019 plus ancienne que la valeur existante (2024) — valeur conservée, écart (stale) signalé côté freshness.

### unemployment (syria)
- Série WB : `SL.UEM.TOTL.ZS` (correspondance : partial)
- Existant : 50.0 % · 2024 · « Estimation OIT »
- Proposé : 13.569 % · 2025 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série SL.UEM.TOTL.ZS »
- Requête API : https://api.worldbank.org/v2/country/SYR/indicator/SL.UEM.TOTL.ZS?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : Série MODELLISÉE ILO (pas une enquête brute) : estimation tripartite OIT, potentiellement décalée en période de rupture (crise libano-syrienne).
- **Recommandation : `manual`** — écart considérable avec la valeur existante (50.0 % vs 13.569 %) : série modélisée ILO pas encore ré-alignée sur la conjoncture de crise — croisement manuel OIT/FMI requis.

### debt_gdp (syria)
- Série WB : `GC.DOD.TOTL.GD.ZS` (correspondance : partial)
- Existant : 130 % · 2024 · « Estimation »
- Proposé : — (aucune observation exploitable)
- Requête API : https://api.worldbank.org/v2/country/SYR/indicator/GC.DOD.TOTL.GD.ZS?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : GeoCapital suit la dette OFFICIELLE (générale) du secteur public — la série WB « central government » sous-estime la dette générale (administration locale, entreprises publiques). Comparer avec précaution ; pour plusieurs pays la série s'arrête en années reculées.
- **Recommandation : `gap`** — aucune observation exploitable côté WDI — valeur existante conservée, écart signalé.

### reserves (syria)
- Série WB : `FI.RES.TOTL.CD` (correspondance : exact_for_total)
- Existant : 1 Mds $ · 2024 · « Estimation »
- Proposé : 20.6 Mds $ · 2010 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série FI.RES.TOTL.CD · unité convertie US$ → Mds $ »
- Requête API : https://api.worldbank.org/v2/country/SYR/indicator/FI.RES.TOTL.CD?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : unité convertie (US$ → Mds $) : conversion définie, sans ambiguïté
- **Recommandation : `reject`** — observation 2010 plus ancienne que la valeur existante (2024) — valeur conservée, écart (stale) signalé côté freshness.

## brazil (pays candidat à l'expansion — aucun fichier de production)

### gdp_growth (brazil)
- Série WB : `NY.GDP.MKTP.KD.ZG` (correspondance : exact)
- Existant : — (absent)
- Proposé : 2.2857 % · 2025 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série NY.GDP.MKTP.KD.ZG »
- Requête API : https://api.worldbank.org/v2/country/BRA/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- **Recommandation : `manual`** — nouveau pays (expansion, aucun fichier de production) : définition à confirmer contre la future fiche et données croisées avec une seconde source officielle.

### inflation (brazil)
- Série WB : `FP.CPI.TOTL.ZG` (correspondance : exact)
- Existant : — (absent)
- Proposé : 5.0168 % · 2025 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série FP.CPI.TOTL.ZG »
- Requête API : https://api.worldbank.org/v2/country/BRA/indicator/FP.CPI.TOTL.ZG?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- **Recommandation : `manual`** — nouveau pays (expansion, aucun fichier de production) : définition à confirmer contre la future fiche et données croisées avec une seconde source officielle.

### unemployment (brazil)
- Série WB : `SL.UEM.TOTL.ZS` (correspondance : partial)
- Existant : — (absent)
- Proposé : 5.97 % · 2025 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série SL.UEM.TOTL.ZS »
- Requête API : https://api.worldbank.org/v2/country/BRA/indicator/SL.UEM.TOTL.ZS?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : Série MODELLISÉE ILO (pas une enquête brute) : estimation tripartite OIT, potentiellement décalée en période de rupture (crise libano-syrienne).
- **Recommandation : `manual`** — nouveau pays (expansion, aucun fichier de production) : définition à confirmer contre la future fiche et données croisées avec une seconde source officielle.

### debt_gdp (brazil)
- Série WB : `GC.DOD.TOTL.GD.ZS` (correspondance : partial)
- Existant : — (absent)
- Proposé : 81.8554 % · 2024 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série GC.DOD.TOTL.GD.ZS »
- Requête API : https://api.worldbank.org/v2/country/BRA/indicator/GC.DOD.TOTL.GD.ZS?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : GeoCapital suit la dette OFFICIELLE (générale) du secteur public — la série WB « central government » sous-estime la dette générale (administration locale, entreprises publiques). Comparer avec précaution ; pour plusieurs pays la série s'arrête en années reculées.
- **Recommandation : `manual`** — nouveau pays (expansion, aucun fichier de production) : définition à confirmer contre la future fiche et données croisées avec une seconde source officielle.

### reserves (brazil)
- Série WB : `FI.RES.TOTL.CD` (correspondance : exact_for_total)
- Existant : — (absent)
- Proposé : 358.5 Mds $ · 2025 · obs_status=actual · publication (dataupdated) : 2026-10-08 · « Banque mondiale (WDI), série FI.RES.TOTL.CD · unité convertie US$ → Mds $ »
- Requête API : https://api.worldbank.org/v2/country/BRA/indicator/FI.RES.TOTL.CD?format=json&per_page=60&page=1
- Date de récupération : 2026-10-25
- Écart de définition : unité convertie (US$ → Mds $) : conversion définie, sans ambiguïté
- **Recommandation : `manual`** — nouveau pays (expansion, aucun fichier de production) : définition à confirmer contre la future fiche et données croisées avec une seconde source officielle.
