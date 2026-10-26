# GeoCapital — Paramètres du modèle (source de vérité : `data/meta.json`)

> Priorité 3 Phase 1 — le modèle est désormais **piloté par la configuration**.
> Ce document définit la signification de chaque paramètre et liste ce qui
> reste volontairement dans le code. La docstring de `geocapital/scoring.py`
> et la clé `_doc` de `meta.json` renvoient ici.

## 1. principe général

| Sujet | Localisation |
|---|---|
| Valeurs numériques de calibration | `data/meta.json` → `financial_params` + `scoring_model` |
| Validation du schéma | `geocapital/scoring.py` → `validate_model_params()` |
| Lecture mémoisée | `geocapital/scoring.py` → `model()` (clé = signature de contenu ; `reset_model_cache()` pour forcer) |
| Formules (jamais de chiffres) | `geocapital/scoring.py` |
| Libellés FR des composantes, copies verdict, icônes | `geocapital/scoring.py` → `COMPONENT_LABELS`, `VERDICT_STYLES`, `_PROFILE_DESCRIPTIONS` (i18n EN via `data/i18n/en/*.json`) |
| Erreurs de configuration | `scoring.ConfigError("meta.<section>.<clé>: <problème>")` — **jamais avalée** : une config invalide arrête l'app avec un message précis, pas un repli silencieux |

Un paramètre n'existe **que dans meta.json** : les constantes historiques du
module scoring (`RISK_FREE_RATE`, `MATURE_ERP`, `BETA`,
`EQUITY_BOND_VOL_RATIO`, `PROFILES`, `RATING_SCORES`, `DEFAULT_SPREADS`)
sont des vues en lecture seule sur la configuration (PEP 562 `__getattr__`).

## 2. `financial_params` (rendement exigé, méthode Damodaran)

`Ke = taux_sans_risque + bêta × ERP_mature + prime_pays`,
avec `prime_pays = max(spread_notation, (cds − décalage)/100) × ratio_vol`.

| Paramètre | Valeur | Signification |
|---|---|---|
| `risk_free_rate` | 4.2 (%) | Taux du Trésor américain 10 ans, début 2025 |
| `mature_erp` | 4.5 (%) | Prime de risque actions d'un marché mature |
| `beta` | 1.0 | Bêta du marché large (sensible aux actions) |
| `equity_bond_vol_ratio` | 1.5 | Ratio volatilité actions / obligations : convertit un spread obligataire en prime actions |

## 3. `scoring_model.profiles` — poids des cinq composantes par profil

Les poids somment à 1 pour chaque profil (contrôle strict).

| Profil | dynamisme | stabilité | solvabilité | institutions | ouverture |
|---|---|---|---|---|---|
| `Prudent` | 0.15 | 0.30 | 0.30 | 0.15 | 0.10 |
| `Équilibré` | 0.25 | 0.20 | 0.25 | 0.15 | 0.15 |
| `Audacieux` | 0.35 | 0.10 | 0.20 | 0.10 | 0.25 |

Un profil inconnu retombe sur « Équilibré » (choix d'affichage, testé).

## 4. `scoring_model.components` — courbes internes de composantes

### 4.1 `dynamisme`
| Paramètre | Valeur | Signification |
|---|---|---|
| `weights.growth` | 0.55 | Poids de la croissance du PIB |
| `weights.unemployment` | 0.20 | Poids du chômage (inversé) |
| `weights.outlook` | 0.25 | Poids du qualitatif « outlook » (50 si manquant, cf. 4.6) |
| `growth_range` | [-2.0, 5.0] | Croissance : score linéaire 0-100 (−2 % → 0 ; 5 % → 100) |
| `unemployment_range` | [2.0, 20.0] | Chômage inversé (2 % → 100 ; 20 % → 0) |

### 4.2 `stabilite`
| Paramètre | Valeur | Signification |
|---|---|---|
| `weights.inflation` | 0.45 | Poids de l'écart d'inflation à la cible |
| `weights.policy_rate` | 0.15 | Poids du taux réel directeur (paliers) |
| `weights.currency` | 0.40 | Poids de la stabilité de devise (qualitatif) |
| `inflation_target` | 2.0 (%) | Cible : score = 100 − 4 × \|inflation − cible\| |
| `inflation_sensitivity` | 4.0 | Pentes de la pénalité inflation |
| `real_rate_bands` | [[−1, 2, 95], [−3, 4, 72], [−8, 6, 40]] | Taux réel directeur (nominal − inflation) inclusif-bas/exclusif-haut → score si en palier |
| `real_rate_outside_score` | 8.0 | Score par défaut quand hors de tout palier |

### 4.3 `solvabilite`
| Paramètre | Valeur | Signification |
|---|---|---|
| `weights.debt` | 0.30 | Poids dette/PIB (inversé sur `debt_range`) |
| `weights.rating` | 0.40 | Poids du score de notation (§ 3) |
| `weights.cds` | 0.30 | Poids du score CDS (§ 3) |
| `debt_range` | [20.0, 180.0] | Dette/PIB inversé (20 % → 100 ; 180 % → 0) |

### 4.4 `institutions`
`weights.governance` 0.60 (qualitatif), `weights.resilience` 0.40 (qualitatif).

### 4.5 `ouverture`
`weights.business` 0.60 (qualitatif), `weights.openness` 0.40 (qualitatif).

### 4.6 `missing_qualitative_score`
| Paramètre | Valeur | Signification |
|---|---|---|
| `missing_qualitative_score` | 50.0 | Score qualitatif par défaut (0-100) quand la donnée est absente ou null — pas un jugement, la valeur neutre du corpus |

## 5. `scoring_model.risk` — risque perçu et volatilité

`risque = 100 − (0.40 × stabilité + 0.35 × solvabilité + 0.25 × institutions)` ;
`volatilité = base + pente × risque`.

| Paramètre | Valeur | Signification |
|---|---|---|
| `weights.stabilite/solvabilite/institutions` | 0.40/0.35/0.25 | Seules les composantes « défensives » alimentent le risque (dynamisme/ouverture en sont exclues : un pays dynamique mais fragiles = risqué quand même) |
| `volatility_base` | 10.0 | Volatilité annuelle inférieure (risque 0) |
| `volatility_slope` | 0.48 | Volatilité ajoutée par point de risque (risque 90 → 53,2 %) |
| `bands` | [30, 50, 70] | Seuils de libellé de risque : < 30 « Faible », < 50 « Modéré », < 70 « Élevé », sinon « Très élevé » (`risk_label`) |

## 6. `scoring_model.cds_score` — courbe CDS (pb) → score

| Paramètre | Valeur | Signification |
|---|---|---|
| `none_score` | 5.0 | Score si CDS coté absent (signal de marché absent = mauvais signe) |
| `floor_pb` | 20.0 | À ≤ 20 pb, score = 100 |
| `log10_ceiling_ratio` | 50.0 | Trois décades de référence : score log dans [floor, floor×50] |
| `spread` | 95.0 | Score 100 − 95 × position logarithmique (plancher 5 à floor×ratio, puis clamp) |

## 7. `scoring_model.crp` — prime de risque pays (Damodaran)

| Paramètre | Valeur | Signification |
|---|---|---|
| `cds_offset_pb` | 25.0 | Pb avant de considérer que le CDS parle (bruit de marché) |
| `cds_divisor` | 100.0 | Pb → % : (cds − 25)/100 |

La source retenue est `max(crp_cds, crp_notation)` ; si CDS coté absent →
spread de notation (`Notation (CDS non coté)`), sinon `max(...)`.

## 8. `scoring_model.ratings` — tables de notation

| Paramètre | Signification |
|---|---|
| `scores` | Score 0-100 par note (AAA 100 … RD 1 ; **NR = 20**, un pays non noté est proche en bas) |
| `spreads` | Spread obligataire (%) par note, réf. Damodaran début 2025 ; sert à la prime pays |
| `default_score` | 20.0 — si la note du pays ne figure pas dans `scores` |
| `default_spread` | 15.5 — si la note du pays ne figure pas dans `spreads` |

Contrôle : `scores` et `spreads` doivent couvrir **exactement** les mêmes notes.

## 9. `scoring_model.verdicts` — seuils de décision

| Paramètre | Valeur | Signification |
|---|---|---|
| `invest_min` | 76.0 | ≥ 76 → « Investir » |
| `caution_min` | 62.0 | 62-75,9 → « Investir avec prudence » |
| `wait_min` | 45.0 | 45-61,9 → « Attendre » |
| `wait_rescue_score` | 38.0 | 38-44,9 peut être rattrapé si `wait_rescue_dynamisme` atteint |
| `wait_rescue_dynamisme` | 55.0 | Condition de rattrapage : dynamisme ≥ 55 → « Attendre » (sinon « Éviter ») |
| `blocking_ratings` | ["NR", "D", "RD"] | Un pays **non noté ou en défaut** **sans CDS coté** ne peut pas être au-dessus de « Attendre » (défaut de prix de marché : pas de signal, pas d'investir). Si CDS coté, le curseur du marché est utilisé. |

Contrôle : ordre strict `wait_rescue_score ≤ wait_min ≤ caution_min ≤ invest_min`.

## 10. Détails de la conversion

| Règle | Définition |
|---|---|
| `linear(value, low, high, reverse)` | (value − low)/(high − low) × 100, clampé 0-100, inversé si `reverse` |
| `clamp` | La moindre des deux bornes s'applique toujours |
| Arrondi de score | 1 décimale (`round(score, 1)`) ; sous-composantes arrondies à 0,1 |
| Arrondis Ke/CRP | 2 décimales (Ke), 2 décimales (CRP) |

## 11. Reste volontairement en dur (et pourquoi)

Ces éléments sont volontairement **hors calibration** :

1. **`indicator_status`** (feu vert/orange/rouge du tableau de bord) —
   ce sont des heuristiques d'affichage qualitatif, pas des paramètres
   utilisés dans les formules ; pas exemple:
   croissance ≥ 3 % / ≥ 1 % ; inflation 0,5-3,5 % ; dette ≤ 60/100 % ;
   chômage ≤ 6/10 % ; CDS ≤ 100/300 pb ; taux réel > 4 ou > 10-20 % nominal
   → vigilance/risque. Changer ces seuils ne touche donc **aucun** score,
   verdict ni Ke — leur migration vers la méta se justifiera dans un
   incrément dédié, avec les mêmes tests de régression.
2. **`correlation`** (matrice de corrélation du portefeuille) — les
   corrélations (0,80 intra-groupe, 0,55 développé/émergent, 0,30
   développé/frontalier, etc.) traduisent la structure des groupes
   (`developed`, `emerging`, `gulf`, `frontier`) référencés par le champ
   `group_key` des fiches pays. Leur migration gagnera à accompagner
   l'arrivée de nouveaux groupes (Priorité 6, pays supplémentaires).
3. **Affichage** : `COMPONENT_LABELS`, `VERDICT_STYLES` (ton, icône,
   phrase de verdict), `_PROFILE_DESCRIPTIONS` — ce sont des libellés
   FR ; le portage EN se fait via `data/i18n/en/*.json` (overlays),
   pas via la calibration numérique.
4. **Arrondis** des formules (1 décimale scores, 2 décimales Ke) :
   conventions d'affichage, pas des choix de calibration.

## 12. Historique

- 2026-10-25 : migration de tous les coefficients du code vers
  `data/meta.json` (`scoring_model`). **Aucun chiffre n'a changé** :
  régressions prouvées par `tests/test_scoring_config.py`
  (baseline figé pré-refactor, identité au 1/10 près).
- Définitions antérieures : cf. `docs/DATA_AUDIT.md` (fraîcheur des
  données) et la page Sources & méthode de l'app (pédagogie).
