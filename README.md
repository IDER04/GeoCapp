# GeoCapital — Connaître le passé pour anticiper le futur

Application Streamlit pédagogique qui relie **l'histoire d'un pays**, **ses indicateurs financiers** et **une décision d'investissement** lisible : score sur 100, rendement exigé (Ke, méthode Damodaran) et verdict en quatre niveaux.

> Prototype pédagogique. Les données sont préparées, datées et sourcées. L'application ne passe aucun ordre et ne constitue pas un conseil en investissement.

## Le parcours

1. **Carte vivante** — carte choroplèthe des 10 pays, filtres attractivité / risque / croissance / devise, trois profils investisseur.
2. **Fiche pays** — frise historique, institutions, relations (alliés, rivaux, dépendances), forces, risques, opportunités.
3. **Tableau de bord** — 11 indicateurs avec feu vert / orange / rouge, source, millésime et explication simple.
4. **Score & verdict** — décomposition transparente en 5 composantes, Ke, verdict et trois raisons.
5. **Décodeur d'actualité** — chaîne causale fait → économie → finance → gagnants/perdants, avec écho historique.
6. **Analyste IA** — posez vos questions en français ou en anglais ; la réponse suit la langue de votre question et s'appuie uniquement sur les faits validés de la base.
7. **Portefeuille mondial** — 100 000 € fictifs, rendement exigé pondéré, volatilité, diversification, diagnostic.
8. **Progression** — carte mentale, quiz éclair, badges.
9. **Sources & méthode** — formules, pondérations, limites et avertissements.

## Les 10 pays du MVP

États-Unis, France, Japon, Chine, Arabie saoudite, Émirats arabes unis, Maroc, Afrique du Sud, Liban, Syrie.

## Lancer en local

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

L'application s'ouvre sur <http://localhost:8501>.

## Données et méthode

- Un fichier JSON par pays dans `data/countries/`, complété par `data/meta.json` et `data/events.json`.
- **Score GeoCapital** : cinq composantes (dynamisme, stabilité macro, solvabilité, institutions, ouverture & affaires), notées de 0 à 100 et pondérées selon le profil Prudent / Équilibré / Audacieux.
- **Rendement exigé** : `Ke = 4,20 % + 1,0 × 4,50 % + prime de risque pays`.
- **Prime de risque pays** : maximum entre le spread de notation et le spread CDS, multiplié par 1,5 (ratio volatilité actions/obligations de Damodaran).
- **Données manquantes** : une notation absente ou un CDS non coté réduit la solvabilité et **bloque le verdict « Investir »**. Pour le Liban et la Syrie, le vide est traité comme un signal de risque.
- Les scores qualitatifs (gouvernance, résilience, climat des affaires, ouverture, stabilité devise) sont des évaluations GeoCapital explicites, pas des données brutes.

## Intelligence artificielle (optionnelle)

L'application fonctionne **entièrement sans IA** grâce aux contenus éditoriaux et aux calculs déterministes.

Pour activer l'IA (OpenRouter, modèle `openai/gpt-4o` par défaut) :

1. Créer un fichier `.env` à la racine du projet (jamais commité, exclus par `.gitignore`) :

```env
OPENROUTER_API_KEY = "votre_cle"
GEOCAPITAL_MODEL = "openai/gpt-4o"
```

2. ou, sur Streamlit Community Cloud, ajouter la clé dans les *secrets* :

```toml
OPENROUTER_API_KEY = "votre_cle"
GEOCAPITAL_MODEL = "openai/gpt-4o"
```

## Analyste IA (OpenRouter)

La page « Analyste » propose une interface conversationnelle bilingue : la réponse suit la langue de la question posée (français ou anglais), indépendamment de la langue d'affichage de l'interface. Elle combine :

1. **Récupération locale** : fiches pays, comparateur, verdicts, coût du capital (Damodaran), événements du décodeur et portefeuille. Les calculs restent déterministes (Python) ; le modèle ne calcule rien.
2. **Cadrage strict** : chaque question n'envoie qu'un ensemble de faits validés (avec sources et dates) pour l'intention choisie ; les données absentes sont listées comme « donnée non disponible ».
3. **Trois registres rendus visibles** : ● Faits validés, ◆ Interprétation IA, ○ Hypothèse. Le modèle doit qualifier ses phrases (« Interprétation : … », « Hypothèse : … »).
4. **Mémoire locale** : la conversation vit dans `session_state` Streamlit (aucune persistance, aucune fuite entre sessions) ; le bouton « Effacer la conversation » la réinitialise, et seuls les 6 derniers échanges sont renvoyés à l'API.
5. **Repli sans API** : sans clé ou en cas d'échec OpenRouter, la page affiche le même contexte factuel et l'analyse déterministe (dans la langue de la question) avec une notice explicite.

L'IA reçoit uniquement les faits déjà validés dans la base. Elle explique, reformule et relie ; elle ne crée aucun chiffre, aucune date et aucune notation.

## Structure

```
app.py                     # point d'entrée, navigation, session_state
geocapital/
  scoring.py               # score, Ke, verdicts, métriques de portefeuille
  data.py                  # chargement JSON, formats, comparaisons
  i18n.py                  # libellés FR/EN centralisés, t(), store de langue
  ai.py                    # couche IA optionnelle via OpenRouter
  analyst.py               # faits validés et cadrage de l'analyste IA
  ui.py                    # composants HTML/CSS
views/                     # 8 pages, dont l'Analyste
data/
  countries/*.json         # 10 fiches pays
  meta.json                # sources, paramètres, méthode
  events.json              # 10 événements du décodeur
assets/styles.css          # thème sombre et composants
.streamlit/config.toml     # thème Streamlit
```

## Déploiement

1. Pousser le dépôt sur GitHub.
2. Sur [Streamlit Community Cloud](https://share.streamlit.io), créer une app avec `app.py` comme fichier principal.
3. Ajouter éventuellement `OPENROUTER_API_KEY` dans les secrets.
4. Aucune base de données, aucun service payant, aucune connexion bancaire n'est nécessaire.

## Limites

- Données de référence 2024-2025, non actualisées en temps réel.
- Modèle de portefeuille simplifié : corrélations par groupe de pays, volatilité pédagogique, pas de couverture de change.
- Le score ne remplace ni une due diligence, ni une analyse de valorisation, ni un conseil personnalisé.
