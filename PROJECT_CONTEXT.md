# PROJECT_CONTEXT — GeoCapital (Handoff, Phase 3)

> Document de passation généré le 2026-10-24 (Phase 2), **mis à jour le 2026-10-25** après l'implémentation de la Phase 3. Il reflète l'état réel du dépôt à ces instants.
> Aucune clé d'API, aucun secret. Voir aussi `NEXT_SESSION.md`.

---

## A. Présentation du projet

**GeoCapital** est une application web pédagogique (prototype, interface **bilingue FR/EN**, défaut français) d'éducation financière : comprendre le passé d'un pays, son risque, et prendre une décision d'investissement fictive. Elle n'est **pas** un conseil en investissement.

**Architecture** — app Streamlit monopage à routes internes :

| Couche | Fichiers | Rôle |
|---|---|---|
| Entrée | `app.py` | `main()`, table `PAGES` (8 routes), icônes, navigation, chip moteur IA dans la sidebar, installation du normaliseur markdown |
| Métier déterministe | `geocapital/data.py` | Chargement des données (`data/countries/*.json`, `data/events.json`, `data/meta.json`, 10 pays), libellés d'indicateurs |
| Métier déterministe | `geocapital/scoring.py` | Scores, verdicts, Ke (rendement exigé), profils (Prudent/Équilibré/Audacieux) — **formules financières, à ne jamais modifier** |
| IA | `geocapital/ai.py` | Transport OpenRouter (`_post`, `_call`, `chat`), config clé/modèle, fallback `None` |
| Récupération | `geocapital/analyst.py` | Payloads de faits validés par intention, `build_messages`, `editorial_answer` |
| i18n | `geocapital/i18n.py` | 472 clés FR/EN (parité exacte), `t(key, **fmt)` avec repli FR, store `st.session_state["lang"]`, maps verdicts/profil/groupes/CRP → codes |
| UI partagée | `geocapital/ui.py` | Composants HTML/CSS (hero, ring, kpi, timeline…), `flatten_html`, `install_markdown_normalizer` |
| Vues | `views/*.py` (8) | Carte vivante, Fiche pays, Comparateur, Décodeur, **Analyste**, Portefeuille, Progression, Sources & méthode |
| Assets | `assets/styles.css` | Identité visuelle (thème sombre, chips, rose/or) |

**Pages (routes)** : Carte vivante · Fiche pays · Comparateur · Décodeur · Analyste · Portefeuille · Progression · Sources & méthode.

**Technologies** : Python 3.13 (python.org macOS), Streamlit **1.66.1**, Plotly **7.1.0**, pandas **3.0.3** (installés dans le Python système pour exécuter l'appli — aucun ajout aux dépendances du projet ; `requirements.txt` inchangé). Aucun framework de test externe : `unittest` + `unittest.mock`.

**Règles de sécurité du projet** :
- `.env`, `.env.*` (dont `.env.rtf`) sont ignorés par Git ; le pattern `!.env.example` existe dans `.gitignore` mais **aucun fichier `.env.example` n'existe ni n'est suivi** — la méthode documentée est `.env` en local, `secrets.toml` sur Cloud.
- `secrets.toml` absent (exemple seulement, placeholder) ; priorité clé : **variables d'env > `.env` > Streamlit secrets**.
- L'IA ne calcule jamais de nombres ; elle n'explique que des faits provenant des fonctions déterministes.

---

## B. État Git

- **Dépôt distante** : `https://github.com/IDER04/GeoCapp.git` — branche `main`.
- **Derniers commits** :
  - `4496c5e` — « feat: integrate OpenRouter AI provider » (Phase 1 complète, poussée).
  - `1f799e2` — « Initial commit: GeoCapital app ».
- **Changements NON commités** (Phases 2 et 3 + correctif de rendu, tous conservés, aucun push) — 12 fichiers modifiés + 10 non suivis :

| État | Fichier | Contenu |
|---|---|---|
| M | `README.md` | Doc Analyste + structure actualisée (i18n/analyst) |
| M | `app.py` | 8 routes à codes stables (`map`…`sources`), `_LEGACY_NAV`, sélecteur de langue, chip neutre, `ui.install_markdown_normalizer()` |
| M | `assets/styles.css` | Header transparent + contrôle natif d'agrandissement sidebar réparé ; highlight carte |
| M | `geocapital/ai.py` | `_post()` partagé + `ai.chat()` multi-tours |
| M | `geocapital/ui.py` | `flatten_html` + `install_markdown_normalizer` + libellés via `t()` |
| M | `views/*.py` (7) | i18n (t() partout, format_func), carte interactive, `_localized_reasons` |
| ?? (nouveau) | `geocapital/i18n.py` | 472 clés FR/EN, parité exacte, `t()`, `update_range()` |
| ?? (nouveau) | `geocapital/analyst.py` | Récupération, cadrage, multilingue, fallback |
| ?? (nouveau) | `views/analyst_page.py` | Page Analyste conversationnelle |
| ?? (nouveau) | `tests/test_i18n.py`, `tests/test_analyst.py`, `tests/test_ai_chat.py`, `tests/test_ui_flat.py` | +60 tests (81/81 au total, dont les 21 de la Phase 1) |
| ?? (nouveau) | `NEXT_SESSION.md`, `PROJECT_CONTEXT.md` | Passation (ce document + instructions) |

-_aucune suppression_ de fichier ; `geocapital/scoring.py` et `geocapital/data.py` **strictement inchangés** (vérifié via `git diff --name-only`, aucune sortie).
- Note : les compteurs de tests cités dans les sections D et E (22, 54) sont les instantanés historiques des phases concernées ; la couverture a évolué pendant la Phase 3 (multilingue, i18n) → état actuel : 21 (Phase 1) + 29 (`test_analyst`) + 14 (`test_i18n`) + 7 (`test_ai_chat`) + 10 (`test_ui_flat`) = **81/81 OK**.
- **Phase 3 : Étapes 1, 2 et 4 implémentées** (socle i18n, branding neutre + carte interactive, Analyste multilingue) ; **Étape 3 (overlays EN des données narratives) non écrite** — décision Option A vs B toujours en attente § F.
- `.env` existe sur disque (OpenRouter, fonctionnel) mais n'est jamais versionné. `.env.rtf` existe encore (à supprimer uniquement sur instruction explicite de l'utilisateur).

---

## C. Phase 1 — Intégration OpenRouter (TERMINÉE, committée, poussée)

- Transport HTTP : `POST https://openrouter.ai/api/v1/chat/completions` (client `urllib` standard, **aucune dépendance ajoutée**).
- Modèle par défaut : `openai/gpt-4o` ; surcharge via `GEOCAPITAL_MODEL`.
- Variables d'env : `OPENROUTER_API_KEY` (obligatoire), `GEOCAPITAL_MODEL` (optionnel). Chargement : variables d'env du processus > fichier `.env` (parseur maison, tolérant aux guillemets) > `streamlit.secrets`.
- **Gestion d'erreurs** : toute erreur (clé absente, HTTP non-2xx, timeout, JSON invalide, exception) renvoie `None` → l'UI bascule sur la rédaction éditoriale française (aucun crash, aucun message technique exposé).
- Incident SSL résolu : certificats Python 3.13 via `Install Certificates.command` (Python de python.org) ; test live OpenRouter réussi (HTTP 200).
- Tests : `tests/test_ai_config.py` — 21 tests, tout mocké (pas d'appel réseau).
- Commit + push sur `origin/main` (`4496c5e`).
- Secrets : scan regex `sk-(or|ant)-[A-Za-z0-9_-]{20,}` sur le diff — 0 occurrence ; jamais de valeur de `.env` dans le code ou les logs (vérification masquée uniquement).

---

## D. Phase 2 — Page « Analyste » chat IA fondée sur les données (TERMINÉE, NON committée)

**Architecture de grounding (Python, puis IA) :**
1. `geocapital/analyst.py` détecte l'entité (pays par nom FR + alias, insensible aux accents) et l'intention (`INTENTS` : country / compare / verdict / capital / event / portfolio) via widget + heuristiques de mots-clés.
2. Construction d'un **payload structuré** en Python : données du/des pays, score, verdict, Ke, risques, événements, portefeuille (poids normalisés). Champs manquants marqués explicitement `missing_indicators()` (jamais inventés).
3. `build_messages(payload, prompt, history)` : règles système (ne s'appuyer que sur les faits affichés, Sources & dates, distinguer « Faits validés / Interprétation IA / Hypothèse ») + **historique tronqué aux 6 derniers échanges** (`MAX_EXCHANGES = 6`) + payload JSON des faits.
4. `ai.chat(messages)` (nouveau, dans `geocapital/ai.py`) envoie le multi-turn via le transport `_post()` partagé. `_call()` (Phase 1) inchangé.

**Vue `views/analyst_page.py`** : page « ✎ Analyste » enregistrée comme 8<sup>e</sup> route dans `app.py` (après Décodeur).
- Barre d'outils : sélecteur « Sujet de question » (intent) → sélecteur d'entité contextuel (pays / comparaison 2-4 / verdict-coût / événement) ; bouton « Effacer la conversation ».
- Légende : `● Faits validés / ◆ Interprétation IA / ○ Hypothèse`.
- FALLBACK sans clé/API : encart orange neutral + `editorial_answer(payload)` (réponse déterministe côté Python, chip « ● Faits validés · Python »).
- Expander auditable « Faits validés envoyés au modèle » (payload JSON, `<pre>` préservé).

**Corrections appliquées pendant la Phase 2 (déjà dans les fichiers) :**
1. L'historique de session ne stocke plus que `{role, content}` « propres » ; le gros payload de contexte n'est plus réaffiché en bulle (reconstruit à chaque tour).
2. Le widget « Sujet de question » stocke désormais le **code** d'intention (`"country"`) au lieu du tuple `(code, label)` — les sélecteurs d'entité s'affichaient jamais avant ce fix.
3. Placeholders FR (« Choisir un pays… », etc.) sur les sélecteurs.

**Tests** : `tests/test_analyst.py` (14) + `tests/test_ai_chat.py` (8) = 22 nouveaux, tout mocké, réseau désactivé.
**Limites connues (acceptées)** : routage d'intention par widget + heuristique (aucun appel LLM de classification, voulu) ; payload ~1,5-2 k tokens envoyé par question ; pas d'optimisation du cache des faits.

---

## E. Correctif du bug de rendu HTML (TERMINÉ, NON committé)

**Symptôme** : plusieurs pages (dont Fiche pays, Comparateur) affichaient du HTML brut (`gc-kpi-label`, `gc-timeline-item`…) en texte.

**Cause racine** — Pas un problème d'échappement ni de `unsafe_allow_html` (tous les sites d'appel le passaient correctement) :
- Streamlit 1.66 transmet la chaîne markdown au **parseur CommonMark côté client**.
- Le HTML est construit par des f-strings Python indentés, avec parfois des **sous-snippets multi-lignes interpolés** (ex. `{ui.ring(...)}` dans `ui.country_hero` et les cartes du Comparateur).
- Après une ligne vide, toute ligne indentée de ≥ 4 espaces est analysée comme **bloc de code indenté** → le parseur transforme une partie du HTML en texte littéral et ne récupère jamais le bloc.

**Correctif centralisé (aucune vue modifiée, design/CSS/contenu inchangés)** :
- `geocapital/ui.py` : `flatten_html(markup)` — retire l'indentation et les lignes vides parasites des fragments HTML ; **le contenu des `<pre>` est préservé tel quel** (essentiel pour l'expander Analyste).
- `geocapital/ui.py` : `install_markdown_normalizer()` — wrapper transparent posé **une seule fois** sur `st.markdown` (idempotent, marqueur `_geocapital_normalized`) ; n'aplatit que les appels avec `unsafe_allow_html=True` (les booléens positionnels sont gérés) ; le markdown ordinaire (réponses IA) n'est pas altéré.
- `app.py` : appel `ui.install_markdown_normalizer()` en tête de `main()`.
- `tests/test_ui_flat.py` : 10 tests (aplatissement, `<pre>` préservé, contenu verbatim, HTML normalisé vs markdown ordinaire, double installation sans empilement).

**Vérification effectuée** : 54/54 tests OK ; parcours navigateur des 8 pages (port 8599) — **0 fuite de HTML brut sur chaque page** ; captures d'écran confirmées (Fiche pays avec anneau de score, Comparateur, Décodeur). Serveur lancé avec `python3 -m streamlit run app.py --server.port 8599`.

**Risques résiduels** : si Streamlit change de comportement CommonMark ou si une vue commence à passer du HTML par un autre chemin (`st.write`, composant custom), la parade ne s'applique pas — aucun cas aujourd'hui (aucun `st.code` / `st.write` HTML dans le code).

---

## F. Phase 3 — Exigences & décisions (PLAN APPROUVÉ ; ÉTAPES 1, 2 ET 4 IMPLÉMENTÉES)

### Objectifs approuvés
1. **Branding IA neutre** : la sidebar ne doit plus exposer ni le fournisseur ni le modèle. Cible : « Assistant IA disponible ». L'identification interne du modèle (debug, `ai.api_model()`) reste autorisée, jamais affichée. La config OpenRouter et la gestion d'erreurs restent inchangées.
2. **Carte vivante interactive (Plotly, aucune nouvelle dépendance)** : `st.plotly_chart(..., on_select="rerun", scrollZoom=True)` ; clic pays (ISO-3) → sélection ; zoom sur le pays via bbox par-pays (petit dict cartographique des 10 pays) + `fitbounds="locations"` en repli ; trace de surbrillance du pays choisi ; bouton « Réinitialiser la carte » (vue monde) ; pan/zoom activés (aujourd'hui `dragmode=False`) ; pays non pris en charge → notification + vue monde, sans crash ; **réutiliser** `data.py`/`scoring.py` — aucune donnée dupliquée, aucune formule reécrite.
3. **i18n FR/EN complète** : `geocapital/i18n.py` centralisé, `t(key, **fmt)` avec dictionnaire `STRINGS`, repli français sans KeyError ; sélecteur de langue **persistent** dans la sidebar via `st.session_state["lang"]` (défaut `fr`) ; toutes les pages respectent la langue ; traduire navigation, titres, labels, boutons, aide, infobulles, notifications, erreurs, fallback, profils pays, indicateurs, carte/légendes, décodeur d'événements, simulateur de portefeuille, quiz, analyste ; **IDs, valeurs numériques, formules et données sources inchangés** ; séparer libellés d'affichage des identifiants internes ; pas de conditionnels de langue dispersés ; ne pas traduire les entrées utilisateur, clés, IDs internes ni valeurs techniques.
4. **Contenu intégré aux données** : les textes FR nichés dans `data/countries/*.json` et `data/events.json` (~900 chaînes narratives) sont traduits via des **overlays EN** `data/i18n/en/*.json` (clé = `country_id`/`event_id`, champs `*_en`) appliqués par une fonction `data.localize()` ; repli français si l'overlay manque ; jamais toucher aux champs numériques/indicateurs/score.
5. **Analyste multilingue (sans appel LLM supplémentaire)** : directive bilingue dans le prompt système (« répondre dans la langue de la question de l'utilisateur ; respecter une demande explicite de langue ») ; aucune détection de langue par LLM ; le fallback déterministe `editorial_answer` doit respecter la langue ; grounding, sources, dates, données manquantes, troncature d'historique et hiérarchie faits/interprétation/hypothèse préservés ; aucun changement de transport API.
6. **Qualité** : pas de changement de formules/calculs ; pas de nouvelles dépendances ni de services externes ; ne pas toucher `.env`/secrets ; **aucun commit/push sans approbation explicite** ; identité visuelle et contenu FR préservés.

### Architecture approuvée
- `geocapital/i18n.py` (nouveau) — `LANGS`, store de langue, `t()`, dictionnaire central `STRINGS`.
- Overlays `data/i18n/en/*.json` + `data.localize()`.
- Carte : interaction Plotly native (`on_select`, `scrollZoom`, bbox), pas de nouvelle lib de carte.
- Tests : `tests/test_i18n.py` (parité fr/en des clés, repli fr, persistance session, intégrité `localize()` — un seul champ d'affichage traduit, jamais les `indicators`/scores), `tests/test_analyst_lang.py` (langue du prompt, `editorial_answer` localisé, zéro appel LLM en plus), mise à jour de `test_analyst.py` (les asserts accrochés à des chaînes FR deviennent langue-sensibles), vérification visuelle des deux langues.

### Séquence approuvée
Étape 1 socle i18n (i18n.py + sélecteur + intégration app.py/ui.py + libellés statiques) → Étape 2 branding neutre + carte interactive → Étape 3 overlays EN données → Étape 4 Analyste multilingue → Étape 5 passe de tests + vérification visuelle toutes pages ×2 langues.

### ⚠️ DÉCISION EN ATTENTE (bloquante pour l'Étape 3)
**Option A vs B pour le volume de traduction du contenu narratif :**
- **Option A** : traduire l'intégralité (~900 chaînes : pays + événements + notes d'indicateurs + quiz + chaînes). Gros fichier (~1 500 lignes), rien ne reste en français.
- **Option B** (recommandée) : traduire d'abord le contenu **visible statiquement** (noms pays/événements, titres, résumés, forces/risques/opportunités, quiz, verdicts, libellés d'indicateurs) ; les longues « notes » d'indicateurs retombent en français avec un badge transparent « Contenu source en français » quand l'overlay est incomplet ; traductions manquantes complétées ensuite par priorité.
→ **L'utilisateur n'a pas encore tranché.** Aucune Étape 3 ne doit démarrer sans décision.

Autres validations demandées au plan : ① maintien d'affiche FR pour le contenu non traduit (Option B) confirmé ; ② `ai.py` touché uniquement via le prompt système Analyste (pas de changement transport) — validé en principe.

---

## G. État d'implémentation (réel, vérifié sur disque)

| Élément | État |
|---|---|
| Phase 1 OpenRouter (`ai.py`, config, fallback, tests 21) | ✅ Implémenté et vérifié ; commit `4496c5e` poussé |
| Phase 2 Analyste (`analyst.py`, page, `ai.chat`) | ✅ Implémenté et vérifié ; **NON committé** |
| Correctif rendu (`flatten_html` + normalizer) | ✅ Implémenté et vérifié dans le navigateur ; **NON committé** |
| README (Analyste + structure) | ✅ Modifié ; **NON committé** |
| **Ph3-1 branding neutre** | ✅ **Implémenté** — chip « ● Assistant IA disponible / indisponible » via `t("side.ai_*")` piloté par `ai.is_available()` ; aucun nom de fournisseur/modèle affiché |
| **Ph3-2 carte interactive** | ✅ **Implémenté** — `on_select="rerun"` + parsing d'événement (chemin natif conservé, inopérant sur choropleth en 1.66), **chips pays** fiables (zoom via `COUNTRY_BOUNDS`, `st.session_state["map_zoom"]`), bouton reset vue monde, surlignage doré, carte du pays sélectionné |
| **Ph3-3 i18n** (`geocapital/i18n.py` + 8 pages + `t()`) | 🔶 **Partiellement implémenté** — socle fait : `i18n.py` 472 clés FR/EN (parité exacte), sélecteur de langue sidebar (défaut `fr`), tous libellés statiques traduits ; **restant (Étape 3)** : overlays `data/i18n/en/*.json` + `data.localize()` pour les contenus narratifs dans `data/` — bloqué par Option A vs B (§ F) |
| **Ph3-4 Analyste multilingue** (prompt bilingue, fallback langue) | ✅ **Implémenté** — `build_system_rules()` injecte la consigne FR/EN selon `detect_question_language()`, `editorial_answer(payload, question)` localisé, zéro appel LLM de détection |
| **Ph3-5 tests** | 🔶 **Implémenté pour ce qui est écrit** — `tests/test_i18n.py` (parité, repli, store), `tests/test_analyst.py` (recherche + `TestMultilingual` + fallback via vue), `tests/test_ai_chat.py`, `tests/test_ui_flat.py` : suite **81/81 OK** (pas de fichier `test_analyst_lang.py` séparé : le multilingue est couvert dans `test_analyst.py`) |
| Option A vs B de couverture de traduction | ⏳ Toujours en attente — décision utilisateur requise (seul travail restant : Étape 3) |

La Phase 3 est **terminée sauf l'Étape 3** (overlays EN des données narratives). Ne pas refaire les Étapes 1, 2, 4 ni les Phases 1-2 : tout est implémenté et testé.

---

## H. Prochaines étapes (dans l'ordre, à partir de l'état actuel)

1. Lire `PROJECT_CONTEXT.md` en entier ; lancer `git status --short` + `git diff --stat` et confirmer que l'état des fichiers correspond à la section B (Phases 2-3 + correctif non committés, 12 modifiés + 10 non suivis).
2. Poser à l'utilisateur la **question de l'Option A vs B** (couverture de traduction des données narratives) si elle n'a pas déjà été tranchée hors session.
3. **Étape 3 — overlays EN (seul travail restant)** : selon l'option — écrire `data/i18n/en/*.json` (pays + événements), introduire `data.localize()`, appliquer dans les vues/analyste, jamais toucher aux données chiffrées / IDs / formules.
4. **Étape 5 (fin)** — passe de tests : suite complète OK ; vérification visuelle des **8 pages × 2 langues**, 0 fuite FR côté EN sur le statique, libellés de données traduits selon l'option.
5. **Aucun commit ni push** tant que l'utilisateur n'a pas approuvé explicitement.

---

## I. Commandes

```bash
# Se placer dans le projet (chemin avec espace → guillemets obligatoires)
cd "/Users/ider/Downloads/GeoCapital app"

# Complet : exécuter les tests (81 attendus actuellement)
python3 -m unittest discover -s tests

# Lancer l'app en dev
python3 -m streamlit run app.py --server.headless true --server.port 8599
# (ou pour usage interactif) python3 -m streamlit run app.py

# Arrêter le serveur de dev
pkill -f "streamlit run app.py"

# Inspecter Git
git status --short
git diff --stat
git diff
git log --oneline -5

# Scan anti-fuite de secrets sur le diff working-tree + nouveaux fichiers
{ git diff; for f in geocapital/analyst.py geocapital/i18n.py views/analyst_page.py tests/test_analyst.py tests/test_ai_chat.py tests/test_i18n.py tests/test_ui_flat.py NEXT_SESSION.md PROJECT_CONTEXT.md; do git diff --no-index /dev/null "$f" 2>/dev/null; done; } | grep -cE 'sk-(or|ant)-[A-Za-z0-9_-]{20,}'
# (aucune valeur de .env ; uniquement un comptage, jamais l'affichage de la clé)
```

**Notions utiles** :
- Streamlit 1.66 rend les selectbox comme **react-aria ComboBox** — automatisation navigateur : cibler `.react-aria-ComboBox input`, `focus()` puis `keydown ArrowDown` (sur `KeyboardEvent` dispathé) pour ouvrir la liste, ensuite options `[role="option"]`.
- Le sélecteur de pages sidebar = radios dont les valeurs sont les **codes de route internes** (`map`, `country`, `compare`, `decoder`, `analyst`, `portfolio`, `progress`, `sources`) ; les libellés affichés via `format_func` → `t(f"nav.{code}")`. Migration des sessions anciennes : `_LEGACY_NAV` dans `app.py`.
- Port dev utilisé : **8599**.
- `scoring.py` & `data.py` : **ne jamais modifier** (toute la logique financière déterministe).

---

*Fin de PROJECT_CONTEXT.md — mis à jour le 2026-10-25 (documentation seule, aucun code modifié, sans commit, sans secret).*
