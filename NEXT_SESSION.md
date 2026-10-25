# NEXT_SESSION — Instructions pour une session fraîche (GeoCapital, Phase 3)

## Avant toute chose
1. **Lire `PROJECT_CONTEXT.md` en entier** — il décrit l'état réel du dépôt (mis à jour après l'implémentation de la Phase 3).
2. **Inspecter avant de modifier** : lancer `git status --short`, `git diff --stat` et comparer à la section B du contexte. Regarder les fichiers réels si un doute.
3. **Ne pas refaire le travail terminé** : Phases 1 & 2, le correctif de rendu HTML **et la Phase 3 (Étapes 1, 2 et 4)** sont implémentés et testés (81/81). **Seule l'Étape 3 reste ouverte** (overlays EN des données narratives) — repartir de la section « Checklist » ci-dessous.

## Règles impératives
- ❌ **Ne pas committer ni pousser** sans approbation explicite de l'utilisateur.
- ❌ Ne pas afficher, copier, logger ou modifier `.env`, `.env.rtf`, ni aucune clé (`OPENROUTER_API_KEY`). Scans de secrets en mode masqué uniquement (comptages, jamais de valeurs).
- ❌ Ne pas modifier `geocapital/scoring.py` ni `geocapital/data.py` (formules financières déterministes) — `data.localize()` doit se limiter aux **champs d'affichage** (`*_en`), sans toucher aux données chiffrées ni aux IDs.
- ❌ Ne pas supprimer/revertir des changements existants ; ne pas ajouter de dépendance ou service externe.
- ✅ Préserver l'identité visuelle et tout le travail Phases 1-2-3 déjà validé en navigateur.
- ✅ Interface bilingue FR/EN via `geocapital/i18n.py` (`t()`, défaut `fr`) ; l'Analyste répond dans la langue de la question (aucun appel LLM de détection).

## État implémenté (à ne PAS refaire)
- **Étape 1 — socle i18n** : `geocapital/i18n.py` (472 clés FR/EN, parité exacte), sélecteur de langue dans la sidebar, `t()` branché sur `app.py`, `ui.py` et les 8 pages.
- **Étape 2 — branding neutre + carte interactive** : chip « Assistant IA disponible » (aucun nom de fournisseur/modèle affiché), carte Plotly avec `on_select="rerun"`, chips pays 10 pays (zoom fiable + boutons), bouton reset vue monde, surbrillance du pays sélectionné.
- **Étape 4 — Analyste multilingue** : consigne de langue injectée via `analyst.build_system_rules()`, fallback `editorial_answer(payload, question)` bilingue, `ai.chat()` multi-tours (transport partagé `_post()`).
- **Étape 5 — tests** : `tests/test_i18n.py`, `tests/test_analyst.py` (multilingue inclus), `tests/test_ai_chat.py`, `tests/test_ui_flat.py` — suite complète **81/81 OK**.

## Checklist — tâches restantes
- [ ] 0. `git status --short` + diff → confirmer l'état = section B de `PROJECT_CONTEXT.md`.
- [ ] 1. Demander/confirmer la **décision Option A vs B** (volume de traduction des données narratives) — bloquant pour l'Étape 3.
- [ ] 2. Étape 3 : overlays `data/i18n/en/*.json` + `data.localize()` (selon l'option retenue). L'Étape 1 a déjà traduit tout le libellé statique ; l'Étape 3 ne concerne que les contenus narratifs dans `data/` (noms, résumés, forces/risques, quiz, événements, notes d'indicateurs, verdicts internes affichés).
- [ ] 3. Après Étape 3 : suite complète OK + vérification visuelle 8 pages × 2 langues (0 fuite FR en EN côté statique ; la langue des données suit alors l'option).
- [ ] 4. Rappeler que commit/push attend l'approbation.

## Commandes de référence
```bash
cd "/Users/ider/Downloads/GeoCapital app"
python3 -m unittest discover -s tests
python3 -m streamlit run app.py --server.headless true --server.port 8599
pkill -f "streamlit run app.py"
git status --short && git diff --stat
```
Quote le chemin (espace dans « GeoCapital app »). Port dev : 8599.

## Zone dangereuse à retenir
- Streamlit 1.66 : selectbox = react-aria ComboBox → automatisation via `.react-aria-ComboBox input` + `ArrowDown` `KeyboardEvent` (voir `PROJECT_CONTEXT.md` § I).
- Streamlit 1.66 : les clics natifs sur un choropleth ne remonteront pas comme sélection (le handler continu clic exige `id`+`parent`, hiérarchies uniquement). Le zoom fiable est assuré par les **chips pays** au-dessus de la carte (`st.session_state["map_zoom"]`) ; le chemin natif `on_select` reste branché en secours pour les versions futures.
- Radio/selectbox dans les tests AppTest : ne pas changer de langue ni de valeur en cours de run (ValueError « not in list ») ; scénarios en un seul run ou état pré-rempli (`st.session_state["map_zoom"] = "japan"`).
- Bug HTML corrigé par `ui.flatten_html()` + normalisateur installé dans `app.py` — ne pas réintroduire d'`st.markdown(..., unsafe_allow_html=True)` avec HTML indenté multi-lignes via un autre chemin (`st.write`, composant custom) : le wrapper couvre `st.markdown` seulement.
