# GeoCapital — Plan de rafraîchissement des données (Phase 1, incrément 1)

> Priorité 6. Implémentation : `geocapital/refresh.py` · Première
> exécution : rapport candidats `docs/REFRESH_CANDIDATES_BRA_LBN_SYR.md`
> (+ `.json`) — Brésil, Liban, Syrie.
>
> **Statut : revue avant application.** Aucun fichier de production
> (`data/countries/*.json`) n'a été modifié par cet incrément.

## 1. Objectif et principes

Améliorer la **fraîcheur** et la **traçabilité** des données sans jouer
avec le modèle de scoring, sans écraser silencieusement une valeur et
sans invention de chiffres, dates ou URL. Trois principes :

1. **Review-first** : l'API fournit des *candidats* ; rien n'est
   appliqué automatiquement. Chaque candidat porte une recommandation
   (`safe` / `manual` / `reject` / `gap`), une explication et son URL de
   requête.
2. **Correspondance par définition, pas par nom** : une série WB n'est
   mappée que si sa définition couvre réellement celle de la fiche ; les
   chevauchements partiels sont documentés (`match: "partial"`) et
   orientés vers de la revue manuelle ou du rejet.
3. **Provenance** : chaque observation distingue
   - la **période d'observation** (ex. 2024 — jamais assimilée à
     l'année en cours),
   - la **date de publication/actualisation** de la source
     (`meta.lastupdated` de la réponse, quand disponible),
   - la **date de récupération** (horodatée à l'exécution du
     générateur),
   - le **statut d'observation** WDI (`obs_status`).

## 2. Sémantique des statuts d'observation (WDI)

| `obs_status` | Sens | Traitement |
|---|---|---|
| `` (vide) ou `A` | observation réelle | acceptée comme `actual` |
| `E` | estimation officielle | acceptée, signalée `estimate` (croisement conseillé) |
| `F` | prévision | **exclue** de `latest_actual()` — une prévision ne remplace pas une observation ; rejet explicite si proposée |
| `NA` | non disponible | ignorée |

## 3. Cartographie des indicateurs (WB WDI v2 uniquement)

Source : API Indicators de la Banque mondiale, v2
(`https://api.worldbank.org/v2/...`, gratuite, sans clé). Les
indicateurs de marché sans équivalent officiel gratuit unique
(`policy_rate`, `rating`, `cds`, `crp`, `equity_index`, `currency`) ne
sont **pas** mappés — sources manuelles obligatoires.

| Indicateur GeoCapital | Série WB | Correspondance | Note de définition |
|---|---|---|---|
| `gdp_growth` | `NY.GDP.MKTP.KD.ZG` | `exact` | PIB réel, croissance annuelle % |
| `inflation` | `FP.CPI.TOTL.ZG` | `exact` | IPC de consommation, moyenne annuelle % (pas un point fin d'année) |
| `unemployment` | `SL.UEM.TOTL.ZS` | `partial` | série **modélisée** OIT — peut diverger fortement des estimations de crise (Liban, Syrie) |
| `debt_gdp` | `GC.DOD.TOTL.GD.ZS` | `partial` | dette du **gouvernement central** ≠ dette du secteur public général (sous-estime) ; série souvent arrêtée dans les années reculées |
| `reserves` | `FI.RES.TOTL.CD` | `exact_for_total` | réserves **totales** (or inclus), US$ ; conversion définie US$ → Mds $ (×10⁻⁹). ⚠️ si la fiche documente des réserves **nettes** → définition incompatible, rejet |

## 4. Règles de recommandation (résumé)

- `gap` — récupération impossible ou aucune ligne exploitable : la
  valeur existante est conservée, l'écart est documenté (lui revenir
  côté freshness, Priorité 2).
- `reject` — observation *plus ancienne* que l'existant ; prévision ;
  série dette centrale dépassée ; réserves nettes ≠ totales.
- `manual` — millésime plus récent ; même millésime avec valeur
  divergente ; pays nouveau (expansion) ; divergence > 10 points sur le
  chômage modélisé. Aucune application sans arbitrage humain.
- `safe` — réservé à de futurs automatisements explicitement approuvés.
  **Aucun candidat « safe » n'a été produit dans cet incrément** : en
  revue-first, tout changement de valeur passe d'abord par une personne.

## 5. Premier tirage — Liban, Syrie, Brésil (2026-10-25)

Résultats : **15 candidats → 0 safe · 8 manual · 6 reject · 1 gap**.

Constats clés (détail dans le rapport) :

- **Liban** : PIB −7,08 % (2024, WB) vs −6,5 % (fiche, FMI) → revue de
  provenance ; inflation 2025 = 14,6 % (décrue) → revue ; chômage
  modélisé OIT 2023 = 11,0 % vs estimation de crise 30 % → série
  modélisée non alignée sur la rupture, rejetée au profit de l'existant
  ; réserves BRUTES 33,3 Mds $ vs réserves NETTES 10 Mds $ (BDL/FMI) →
  **définition incompatible, rejet** ; dette centrale arrêtée en 1999 →
  rejet.
- **Syrie** : couverture WDI gravement lacunaire (PIB fin 2022, IPC fin
  2019, échec de la dette, réserves fin 2010, une seule valeur de
  chômage modélisée 2025 = 13,6 %) → essentiellement des écarts, à
  combler ailleurs.
- **Brésil** : toutes les séries sont fraîches (2024–2025) et
  complètes ; candidats d'**expansion** (aucun fichier de production),
  donc tous « manual » par construction.

### Sources officielles à mobiliser pour les écarts (Liban / Syrie)

- **FMI — WEO et Article IV** : PIB, inflation, dette et réserves du
  Liban et de la Syrie (estimations staff, définition « secteur public
  général » pour la dette). `imf.org/weo`, notes-pays Article IV.
- **Banque du Liban (BDL)** : policy rate, réserves nettes et libres,
  base monétaire. `bdl.gov.lb` (séries « Bulletin BDL »).
- **Banque centrale de Syrie** : policy rate, réserves (informations
  éparses) ; *Central Bureau of Statistics* syrien pour l'IPC quand il
  publie.
- **Banque mondiale** : `SL.UEM.TOTL.ZS` (chômage modélisé OIT) — à
  croiser avec les estimations « crise » (OIT, études nationales) avant
  toute substitution.

Ces récupérations hors WB ne font pas partie de l'incrément 1 (pas de
connecteur) ; elles passent par une reprise manuelle documentée avec
URL + date, puis le même circuit de revue.

## 6. Workflow complet (cible)

1. `refresh.candidate_pack(cid)` / `pack_for_new_country(snapshot)` →
   candidats d'un pays (API WB, timeout, sans clé).
2. `build_candidate()` → recommandation + explication + métadonnées.
3. `generate_report()` → `docs/REFRESH_CANDIDATES_*.md` + `.json`
   (écriture **uniquement** sous `docs/`).
4. Revue humaine : arbitrer chaque `manual`, accepter/rejeter les
   `reject`, tracer les `gap` vers leur source officielle.
5. Incrément futur (non implémenté) : écriture contrôlée des candidats
   approuvés dans `data/countries/*.json` — avec conservation des
   champs `source`, `note`, millésime et `data_as_of` de `meta.json`,
   puis exécution de la suite de tests + vérification du scoring de
   référence figé.

## 7. Limites connues

- Ne couvre que WB WDI v2 ; pas de connecteur FMI/BDL/BCS (incrément
  suivant probable).
- Une « date de publication » fine n'est pas exposée par observation par
  l'API (seule la date de mise à jour de la base l'est) — d'où le champ
  `lastupdated` tracé, distinct de la période d'observation.
- `per_page=60` couvre largement les séries annuelles ; une série
  paginée au-delà nécessiterait une boucle (non nécessaire à ce stade).
- Les valeurs WDI sont parfois révisées à posteriori : un candidat
  `manual` doit toujours être recoupé avec une seconde source avant
  application.
- Le compteur `per_page`, les erreurs réseau et les JSON malformés sont
  convertis en `gap` traçable, jamais en valeur replacée par une
  estimation interne.

## 8. Suivi — évidence restante pour les trois cas non tranchés (2026-10-25)

Suite à la revue `docs/REFRESH_REVIEW.md`, aucun des trois cas ci-dessous
ne peut être arbitré par défaut : toute application reste bloquée tant
que cette évidence n'est pas rassemblée. **Aucune de ces trois valeurs
n'a été modifiée en production dans cet incrément.**

### 8.1 Liban — `gdp_growth` 2024 (écart FMI vs Banque mondiale)

Trois vintages officiels coexistent pour 2024 : la fiche (−6,5 %,
source « FMI / estimations »), la Banque mondiale (WDI et LEM :
−7,1 %), le FMI WEO d'octobre 2026 (−5,2 %). Évidence à réunir avant
tout choix :

- **Réconciliation interne au FMI** : identifier ce qui se cache derrière
  l'existant (« FMI / estimations ») et le confronter au WEO DataMapper
  (`NGDP_RPCH`) : vintages différents, révisions chronologiques, et
  éventuelle note de pays Article IV Liban expliquant l'écart ;
- **Base des comptes nationaux** : déterminer si −7,1 vs −5,2 provient
  d'une révision de base des comptes nationaux libanais ou d'hypothèses
  de staff différentes (séquelles du conflit de 2024, points d'entrée
  et de sortie du PIB) ;
- **Citation LEM précise** : édition LEM printemps 2025 (révision
  −5,7 → −7,1) — retrancher la page exacte et le millésime pour tracer
  la chronologie des révisions.

Sans cela, `seek_better_source` reste en vigueur (appliquer −7,1
reviendrait à arbitrer un désaccord inter-institutions de 1,9 point).

### 8.2 Liban — `unemployment` (divergence triple)

Trois valeurs coexistent dans les sources officielles consultées :
fiche 30 % (2024) · ILO modélisé 11,0 % (2023 ; 2024/25 **nuls** dans
WDI) · MPO avril 2026 ~22,8 % (2024). Évidence à réunir :

- **ILOSTAT ILOEST Liban** : télécharger la série Liban et vérifier
  l'année de référence exacte du 11,0 % ainsi que la note
  méthodologique (estimation modélisée, absence d'enquête récente) ;
- **Enquêtes nationales récentes** : rechercher auprès du CAS et de
  l'OLM (Observatoire libanais du marché du travail) toute publication
  post-2019 confirmant ou démentant le ~30 % de la fiche ;
- **LEM/MPO** : localiser la page exacte du 22,8 % (2024) dans la
  feuille MPO d'avril 2026, avec définition, période et statut
  (estimé vs observé).

Sans enquête sous-jacente, aucune des trois valeurs ne peut remplacer
l'autre de façon justifiable — d'où `seek_better_source` maintenu.

### 8.3 Syrie — `unemployment` 2025

Trois valeurs centrées sur la rupture de décembre 2024 : fiche 50 %
(2024, « Estimation OIT », citation jamais traçable) · ILO modélisé
13,6 % (2025) · EUAA COI 24 % (2024). Évidence à réunir :

- **ILOSTAT ILOEST Syrie** : série complète + note méthodologique ILO
  (« lack of recent labour market data ») — la valeur 13,6 % est une
  sortie de modèle, pas une observation;
- **Premières enquêtes du gouvernement syrien post-décembre 2024** :
  toute enquête post-transition exploitable (Echo, REACH, OCHA, ONS
  syrien si reprise) — une enquête directe, si elle est publiée, serait
  la première depuis des années ;
- **Publications post-conflit WB/FMI** : le FMI exclut la Syrie du WEO
  depuis 2011 ; toute réinclusion serait un signal de nouvelle donnée
  disponible à exploiter ;
- **Citation de l'existant 50 %** : retrouver la publication exacte
  derrière l'estimation de crise (fiches UNOCHA/EUAA/RNIS 2023-24)
  pour dater et qualifier ce niveau avant toute décision.

Les valeurs modélisées post-conflit (13,6 %) ne doivent **pas** être
appliquées sans enquête corroborante : elles reposent sur un modèle
sans visibilité sur la transition.
