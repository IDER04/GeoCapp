# GeoCapital — Limite de questions de l'Analyste IA (par session)

> Priorité 5 Phase 1. Implémentation : `geocapital/limits.py`,
> câblée dans `views/analyst_page.py`. Config : `data/meta.json` →
> `ai_limits`.

## 1. Ce que fait la limite

L'Analyste IA accepte au maximum **`ai_limits.max_questions_per_session`
questions par session Streamlit** (valeur de départ : **8** ; modifiable
dans `data/meta.json`, validée comme entier ≥ 1 — violation →
`ConfigError`, aucun repli silencieux).

- Le compteur est **côté serveur** (`st.session_state`) : le navigateur
  ne porte aucun compteur falsifiable côté client.
- Une fois la limite atteinte : la saisie est désactivée
  (`st.chat_input(disabled=True)`), un encart explique la situation
  (FR/EN), et la barrière serveur `_handle_question` refuse toute
  soumission — **aucun appel au fournisseur IA ne part**.
- Sinon, un libellé discret affiche `remaining/total` en continu.

## 2. Politique de comptage (choisie et testée)

**Chaque question soumise compte exactement une unité, quel que soit le
résultat** :

| Cas | Compte ? |
|---|---|
| Réponse du fournisseur (OpenRouter) reçue | Oui |
| Fournisseur en échec (réseau, clé absente, HTTP) → réponse éditoriale du fait déterministe | Oui |
| Mode éditorial dès le départ (sans clé API) | Oui |
| Question bloquée par la limite (saisie désactivée) | Non — rien n'est soumis |

Raisonnement : la limite vise le rythme de sollicitation de l'utilisateur
dans une session, pas la facturation du fournisseur. Tout tour de
conversation produit une réponse (IA ou éditoriale) et consomme un tour ;
les compter tous garantit un comportement prévisible, évite qu'un service
indisponible « autorise » des soumissions illimitées, et reste simple à
expliquer in-app.

## 3. Anti-double-comptage (reruns Streamlit)

L'incrément vit dans `_handle_question(prompt)` — appelé uniquement quand
`st.chat_input` retourne une *nouvelle* valeur soumise. Sur un simple
re-run (changement de page, sélecteur, langue), `chat_input` retourne
`None` : rien ne s'incrémente. Testé : soumission → re-run sans
nouvelle valeur → compteur inchangé.

## 4. Périmètre : ce que la limite n'est PAS

- **Pas un plafond de compte global** : rien n'est partagé entre
  sessions, comptes ou navigateurs ; ouvrir une nouvelle session remet
  le compteur à zéro. Le message d'atteinte de limite l'explique
  explicitement in-app.
- **Pas une garantie de dépense** : le coût réel dépend du modèle
  OpenRouter choisi (`GEOCAPITAL_MODEL`, défaut `openai/gpt-4o`) et de
  la longueur des réponses (`MAX_TOKENS = 700` par réponse). La limite
  borne le *nombre de tours*, pas le facturage exact.
- Le *portée exacte* : par session de navigateur Streamlit (identité de
  session côté serveur). Les questions posées aux *autres* pages
  (fiches, quiz, décodeur : appels `ai.country_brief`, `explain_verdict`,
  etc.) ne passent pas par ce compteur — elles restent régies par leur
  usage interactif unitaire, hors périmètre de cet incrément.

## 5. Tests

`tests/test_limits.py` couvre : validation de configuration (section
absente, 0, négatif, non-entier, booléen), bornes exactes
(`can_ask`/`remaining` à `limit-1` et à `limit`), incrémentation
unitaire, comportement AppTest de bout en bout (soumission normale,
re-run sans double comptage, limite exacte atteinte puis blocage —
aucun appel `ai.chat` au-delà), politique de comptage des échecs
fournisseur (repli éditorial compte quand même), libellés FR et EN.
