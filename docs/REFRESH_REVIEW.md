# GeoCapital — Revue des 8 candidats « manual » (Priorité 6, incrément 1)

> Date de revue : 2026-10-25 · Portée : les **8 candidats classés
> `manual`** dans `docs/REFRESH_CANDIDATES_BRA_LBN_SYR.md`.
> **Statut : document de revue.** Aucune donnée de production
> (`data/countries/*.json`, `data/meta.json`) n'a été modifiée ;
> `data_as_of` reste `2026-10-25`.

## Méthode et preuves utilisées

Les candidats n'ont **pas** été validés sur la seule base du rapport ;
les sources officielles ont été consultées directement :

- **API Indicators Banque mondiale v2** (observations + métadonnées de
  série : définition, institution source) — y compris la vérification
  que LBN `SL.UEM` 2024/2025 sont **nulles** (gaps) ;
- **API officielle des statistiques du FMI (WEO DataMapper)** —
  `NGDP_RPCH` (croissance PIB réel) et `PCPIPCH` (inflation) pour LBN et
  BRA ; la Syrie y est **exclue** (« Data are excluded from 2011 onward
  because of the uncertain political situation », appendice
  statistique WEO) ;
- **API BCB (SGS)** série `13762` — « Dívida bruta do governo geral
  (% PIB) » méthodologie 2008 (dette brute du **Gouvernement général**) ;
- **Publications nationales** : IBGE (PIB 2025 = 2,3 %, IPCA 2025 =
  4,26 %, PNAD Contínua — desocupação 2025 = 5,6 % annuel) ;
  Banco Central (Relatório de Gestão das Reservas 2026 : US$ 358,23
  Md au 31/12/2025) ;
- **Banque mondiale, monitoring pays** : Lebanon Economic Monitor
  (communiqués 19/06/2025 et 22/01/2026), feuille de données MPO/Lebanon
  (avril 2026) ;
- **ILO/OIT** : ILOSTAT + fiche-emploi Syrie ILO
  (juillet 2025), rapport EUAA COI Syrie (juillet 2025).

Normes conservatrices appliquées : une valeur plus récente n'est
**pas** approuvée par défaut ; chaque proposition doit être recoupée
avec une seconde source officielle et comparable en définition, unité
et période. Si l'évidence se contredit ou reste insuffisante →
`seek_better_source`.

Codes de recommandation : `approve_candidate` (candidat validé en
l'état, application future après signal utilisateur),
`retain_existing` (garder la valeur de production),
`seek_better_source` (ni l'existant ni la proposition ne sont
évaluables — il faut une source meilleure).

---

## Table de décision (8 candidats `manual`)

| # | Pays | Indicateur | Recommandation |
|---|------|-----------|----------------|
| 1 | Liban | PIB réel 2024 | **`seek_better_source`** |
| 2 | Liban | Inflation | **`approve_candidate`** |
| 3 | Syrie | Chômage | **`seek_better_source`** |
| 4 | Brésil | PIB réel 2025 | **`approve_candidate`** |
| 5 | Brésil | Inflation 2025 | **`seek_better_source`** |
| 6 | Brésil | Chômage 2025 | **`approve_candidate`** |
| 7 | Brésil | Dette/PIB | **`seek_better_source`** |
| 8 | Brésil | Réserves 2025 | **`approve_candidate`** |

Comptage : **4 × `approve_candidate` · 0 × `retain_existing` ·
4 × `seek_better_source`.** Aucun de ces candidats ne doit être appliqué
sans signalement explicite de l'utilisateur ; les 4 approbations
concernent l'inflation du Liban et trois candidats Brésil (PIB, chômage,
réserves) — voir détail par entrée.

---

### 1) Liban — `gdp_growth` (PIB réel, %, 2024)

- **Existant** : −6,5 % · 2024 · unité % · source « FMI / estimations ».
- **Proposé** : −7,08 % · 2024 · unité % · source Banque mondiale
  (WDI `NY.GDP.MKTP.KD.ZG`), `obs_status` vide = **actuel**, base WDI
  mise à jour 2026-10-08, récupéré 2026-10-25.
- **Comparabilité** : même définition (croissance du PIB réel, moyenne
  annuelle), même unité et même période → comparables à condition de
  concilier l'écart des sources.
- **Écart non résolu entre institutions** : WDI et le Lebanon Economic
  Monitor affichent **−7,1 % pour 2024** (révision LEM de −5,7 % à
  −7,1 % au printemps 2025 ; feuille de données MPO avril 2026 :
  −7,1 % en 2024, en cohérence avec les valeurs historiques de la
  même série : −6,9 % en 2019, −21,4 % en 2020, −7,0 % en 2021, −0,6 %
  en 2022, −0,8 % en 2023) ; en revanche le FMI (WEO, vintage octobre
  2026), affiche **−5,2 % pour 2024**. L'existant −6,5 % (FMI) se
  situe entre les deux.
- **Source officielle ?** Oui (WDI, institution « Country official
  statistics… + Staff estimates, World Bank ») ; observation **actuelle**
  (pas une prévision).
- **Effet d'une substitution** : écart de portée narrative modérée
  (−6,5 → −7,08) qui pourrait durcir l'analyse, mais l'approuver
  aujourd'hui signifierait arbitrer un désaccord FMI/Banque mondiale de
  1,9 point sans l'avoir concilié ; la production pourrait migrer vers
  −7,1 plus tard ou vers une révision FMI plus claire.
- **Décision : `seek_better_source`** — la Banque mondiale fournit trois
  publications cohérentes sur −7,1, le FMI en dit −5,2 ; la levée de la
  divergence (vintage, base de comptabilité nationale, estimation
  conflit/dommage vs estimation staff) exige une vérification ciblée
  (WEO Lebanon country page + Article IV si publié). En attendant, la
  valeur existante et l'ordre de grandeur restent valides.

### 2) Liban — `inflation` (IPC annuel, %, 2025)

- **Existant** : 45,0 % · 2024 · source « Administration centrale de la
  statistique / FMI ». **Recoupé** : le FMI (WEO Oct. 2026) affiche
  45,2 % pour 2024 → l'existant est validé à 2 décimales près.
- **Proposé** : 14,60 % (14,5976) · **2025** · source Banque mondiale
  (WDI `FP.CPI.TOTL.ZG`, série alimentée par les IFS/FMI), `obs_status`
  vide = **actuel** ; WDI mis à jour 2026-10-08 ; récupéré 2026-10-25.
- **Comparabilité** : même concept (variation annuelle de l'IPC
  consommation, moyenne de l'année), même unité (%), 2025 plus récent
  que 2024. **Recoupement fort** : FMI WEO = **14,6 %** pour 2025, soit
  exactement la même valeur — cohérent car les deux séries dérivent du
  même écosystème (CAS via IFS).
- **Source officielle ?** Oui (Banque mondiale/IFS + CAS via FMI).
  Observation **actuelle**, estimée par les deux institutions de façon
  concordante.
- **Effet de la substitution** : fort et **favorable** — passe la fiche
  d'un régime « inflation très élevée (45 %) » à un régime de
  **désinflation** avec stabilité du taux de change (converge avec le LEM :
  « inflation projected to moderate to 15.2% in 2025 »). Il faut mettre
  à jour `note` et `date` de la fiche lors de l'application ; la note
  actuelle mentionne l'effondrement de la livre, le texte deviendra
  obsolète.
- **Décision : `approve_candidate`** — double-corroboration exacte
  (WDI = WEO = 14,6), actuelle et comparable ; candidat le plus solide
  du lot. L'application restera un geste séparé signé par l'utilisateur
  (avec adoption de `date` 2025, `source` mise à jour et `note`
  réécrite).

### 3) Syrie — `unemployment` (chômage total, %, 2025)

- **Existant** : 50,0 % · 2024 · source « Estimation OIT »
  (citation détaillée manquante en production).
- **Proposé** : 13,57 % (13,569) · 2025 · source Banque mondiale (WDI
  `SL.UEM.TOTL.ZS`) = **estimation modélisée ILO** (`ILOEST`), base
  consultée : janvier 2026, `obs_status` vide ; WDI mis à jour
  2026-10-08 ; récupéré 2026-10-25.
- **Contexte méthodologique documenté** : l'ILO lui-même écrit (fiche
  Syrie, juillet 2025) que « there is a lack of recent labour market
  data for Syria, requiring the use of modelled estimates » — la valeur
  13 % (2024) est une **sortie de modèle avec grande incertitude** dans
  un contexte de conflit/transitions. Un rapport indépendant (EUAA COI
  Syrie, juillet 2025) avançait **24 % en 2024**. L'existant 50 %
  provient d'estimations de crise dépourvues, en production, de
  citation précise et non retrouvée. Enfin, le FMI **exclut**
  systématiquement la Syrie du WEO depuis 2011 — aucune validation
  possible côté FMI.
- **Comparabilité** : concept identique (chômage % de la population
  active, OIT) mais bases divergentes d'un facteur ~2-4 — non
  conciliable en l'état.
- **Source officielle ?** Oui (WDI/ILO), mais **estimation modélisée**,
  pas une observation d'enquête.
- **Effet de la substitution** : majeur et **trompeur potentiellement** —
  50 → 13,6 transformerait « moitié de la population active sans
  emploi » en « chômage modéré », ce qui n'est soutenu par aucune
  enquête récente syrienne ; le modèle ILO n'a pas de visibilité sur la
  transition post-2024.
- **Décision : `seek_better_source`** — ni le candidat ni l'existant ne
  sont assis sur une enquête solide. Action prospective : la future
  revue doit chercher la série Syria ILOEST sur ILOSTAT (13,6 attendue
  pour 2025), les
  premières enquêtes du gouvernement syrien post-transition et, le cas
  échéant, les publications post-conflit de la Banque mondiale ; en
  attendant, conserver la valeur de
  production avec son label « estimation ».

### 4) Brésil — `gdp_growth` (PIB réel, %, 2025) — candidat d'expansion

- **Existant** : — (aucun fichier de production ; Brésil n'est pas
  couvert ; 10 pays actuels).
- **Proposé** : 2,29 % (2,2857) · 2025 · actuel ; source WDI
  `NY.GDP.MKTP.KD.ZG` (« Country official statistics… »), WDI 2026-10-08.
- **Comparabilité — triple accord** : IBGE (communiqué 03/03/2026) :
  **2,3 % en 2025** (5ᵉ année consécutive de croissance) ; FMI WEO :
  2,3 % ; WDI : 2,29 %. Définition identique (PIB réel, année).
- **Décision : `approve_candidate`** — soutien le plus solide pour le
  futur workflow d'expansion (base WDI, corroboré par la statistique
  nationale et le FMI). À l'écriture de la fiche, la source principale
  restera citée : « IBGE / Banque mondiale (WDI) ».

### 5) Brésil — `inflation` (IPC, %, 2025) — candidat d'expansion

- **Existant** : — (expansion).
- **Proposé** : 5,02 % (5,0168) · 2025 · actuel ; WDI `FP.CPI.TOTL.ZG`,
  institution « International Financial Statistics database, IMF ».
- **Confrontation officielle** : l'inflation **officielle** de référence
  (IBGE, IPCA — indice national large) a atteint **4,26 % en 2025**
  (cadré sous la cible de 4,5 %). L'écart de 0,76 point avec WDI/IFS
  (5,02) n'est pas explicable à ce stade : l'IPC exact utilisé par les
  IFS pour le Brésil (IPCA, INPC, IPC général FGV, différence
  année-moyenne vs déc.) n'a **pas** pu être réconcilié en ligne —
  aucune supposition n'est faite ici.
- **Source officielle ?** Oui, mais divergente de la source nationale.
- **Effet de la substitution (fiche future)** : présenter 5,02 %
  afficherait une inflation au-dessus de la cible
  alors que l'IBGE officiel dit l'inverse (4,26 ≤ 4,5) — risque de
  signaler le « mauvais » régime de politique monétaire.
- **Décision : `seek_better_source`** — préférer l'IBGE/IPCA (4,26 %,
  année 2025) et vérifier le libellé exact de la série IFS avant tout
  usage. Ne pas présenter la valeur WB en l'état.

### 6) Brésil — `unemployment` (chômage, %, 2025) — candidat d'expansion

- **Existant** : — (expansion).
- **Proposé** : 5,97 % · 2025 · actuel (sur le papier) ; WDI
  `SL.UEM.TOTL.ZS` = **estimation modélisée ILO** (base janvier 2026).
- **Confrontation officielle** : IBGE, PNAD Contínua (communiqué
  30/01/2026) : taux annuel (« desocupação ») = **5,6 % en 2025** (années
  antérieures : 6,6 % en 2024) — définition comparable (chômage % de
  la population active). Écart WB↔IBGE : 0,37 point (modélisé vs
  enquête).
- **Source officielle ?** Oui ; le candidat WDI/OIT est une estimation
  modélisée, l'IBGE est une véritable enquête.
- **Effet** : faible — les deux valeurs installent le même récit
  (marché du travail au meilleur niveau de la série).
- **Décision : `approve_candidate`** avec mention : à la création de la
  fiche, la **source primaire = IBGE PNAD Contínua (5,6 %)**, la
  valeur WB n'étant qu'un recoupement ; le champ `source` de la fiche
  doit porter le nom d'IBGE si cette valeur-là est choisie.

### 7) Brésil — `debt_gdp` (dette/PIB, %, 2024) — candidat d'expansion

- **Existant** : — (expansion).
- **Proposé** : 81,86 % · **2024** · WDI `GC.DOD.TOTL.GD.ZS` =
  dette du **gouvernement CENTRAL** (source : Government Finance
  Statistics Yearbook, FMI).
- **Confrontation officielle (définition correcte)** : l'indicateur
  GeoCapital correspond à la dette du **secteur public général** — au
  Brésil, la mesure officielle est la **DBGG (dívida bruta do governo
  geral)**, publiée par le Banco Central (SGS 13762, méthodologie 2008,
  alignée FMI) : **76,27 % du PIB en déc. 2024** et 78,64 % en déc.
  2025. La proposition WB (gouvernement central) est **5,6 points
  plus élevée** en 2024 — l'écart ne peut pas être concilié en
  changeant simplement d'année.
- **Source officielle ?** Oui (les deux), mais **définitions
  incompatibles** (central ≠ général), offrant un mauvais signal de
  soutenabilité si utilisée telle quelle.
- **Effet** : surestimerait la dette brute de ~5,6 p.p., poussant le
  récit « dette très élevée » et surinterprétation du risque fiscal.
- **Décision : `seek_better_source`** — la future fiche Brésil doit
  porter la DBGG (76,3 % en 2024, 78,6 % en 2025, source Banco Central
  do Brasil, série SGS 13762) ; un connecteur conditionné à
  l'incrément suivant (API SGS gratuite).
- (Note méthodologique : une tentative de rapprochement via le code
  DataMapper `GGXWDG_NGDP` n'a pas abouti — ce code ne mesure pas la
  dette — et n'est **pas** utilisée comme preuve ici.)

### 8) Brésil — `reserves` (réserves, Mds $, 2025) — candidat d'expansion

- **Existant** : — (expansion).
- **Proposé** : 358,5 Mds $ · 2025 · actuel ; WDI `FI.RES.TOTL.CD`
  (réserves totales, **or inclus**, US$) converti US$ → Mds $ (×10⁻⁹,
  conversion définie); source « IFS, FMI ».
- **Confrontation officielle** : Banco Central do Brasil,
  *Relatório de Gestão das Reservas Internacionais* (mars 2026) :
  **US$ 358,23 Md au 31/12/2025** (« conceito caixa »), contre
  US$ 329,73 Md au 31/12/2024. Écart WB↔BCB : 0,08 % — les deux
  figures décrivent la même quantité au même concept (total incl. or ;
  différence fine : caixa vs accrual).
- **Source officielle ?** Oui ; observation **actuelle**.
- **Effet** : nul sur l'interprétation (même ordre de grandeur).
- **Décision : `approve_candidate`** — avec mention d'unité (Mds $)
  et, au moment d'écrire la fiche, délibération sur le concept à
  inscrire (ici **total, or inclus** — ce qui doit être explicité dans
  `note`, la fiche Liban documente pour sa part des réserves **nettes**).

---

## Annexes — cas déjà rejetés / reportés, indiquant les écarts à traiter

Ces candidats ont déjà un `reject/gap` documenté dans le premier rapport
; ils n'appartiennent pas aux 8 `manual`. Les faits nouveaux relevés
lors de cette revue serviront d'inputs aux futurs incréments :

- **Liban — chômage (reject/2023 = 11,0 %)** : la revue a établi une
  triple divergence : ILO modélisé 2023 = 11,0 % (2024/2025 **nuls**),
  feuille de données MPO/Lebanon avril 2026 : 2023 = 23,3 %, **2024 =
  22,8 %, 2025e = 22,8 %**, et la fiche de production = 30 (2024,
  « Estimation OIT / Banque mondiale », citation proche des taux de
  chômage issus des enquêtes libanaises récentes ~30 %). Aucun arbitrage
  automatique : trouver dépend d'un travail sur ILOSTAT et les enquêtes
  nationales (Pas de candidature WB exploitable — les séries WDI
  LBN 2024/2025 sont nulles).
- **Liban dette/reserves, SYR gdp/inflation/debt/reserves** : les motifs
  de rejet du premier rapport restent valables (définition centrale vs
  générale ; brut vs net ; millésimes antérieurs et lacunes WDI
  documentées, p. ex. SYR dette = 0 ligne).

### Brésil — lecture « workflow d'expansion »

Candidats par candidat, la future fiche Brésil peut s'appuyer sur :

| Indicateur | Candidat WB | Statut de revue | Meilleure source connue |
|---|---|---|---|
| PIB 2025 | 2,29 % | `approve_candidate` | IBGE 2,3 % (+ FMI 2,3 %) — accord triple |
| Chômage 2025 | 5,97 % | `approve_candidate` (recoupé) | **IBGE PNADC 5,6 %** (source primaire souhaitée à l'écriture de la fiche) |
| Réserves 2025 | 358,5 Mds $ | `approve_candidate` | BCB 358,23 Md$ (accr.) — accord 0,08 % |
| Inflation 2025 | 5,02 % | `seek_better_source` | **IBGE IPCA 4,26 %** ; série IFS à identifier avant usage |
| Dette/PIB 2024 | 81,86 % central | `seek_better_source` | **BCB DBGG 76,3 % (2024)** — définition générale à privilégier |

**Bilan expansion Brésil : 3/5 candidats utilisables dès maintenant,
2/5 nécessitent une source meilleure — et aucun n'autorise l'écriture
de `data/countries/brazil.json` sans le signalement séparé de
l'utilisateur.**

## Limites de l'évidence

- Aucune revue ne peut raisonnablement résoudre la divergence FMI/Banque
  mondiale sur le PIB libanais 2024 dans ce cadre : les deux
  institutions publient des vintages-estimations valides (−5,2 vs
  −7,1), sans base de conciliation publique connue ici.
- Les valeurs de chômage Syrie (modélisé) et Liban (modélisé vs MPO)
  ne sont pas des enquêtes directes : c'est une limite structurelle
  (conflit/transitions) documentée par l'ILO, non un défaut de
  récupération.
- L'identification de l'IPC exact derrière la série IFS/WDI du Brésil
  (5,02 vs IPCA 4,26) reste à clarifier (hypothèse non testée dans ce
  document : IPC FGV/année décalée) — aucune supposition n'entérinée.
- Pas de date de publication par-observation côté WDI : on a la date
  de dernière mise à jour de la base WDI (2026-10-08) comme proxy
  horodaté, en plus des dates de récupération (2026-10-25).
