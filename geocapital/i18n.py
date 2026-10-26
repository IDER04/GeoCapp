"""GeoCapital — module i18n centralisé (FR/EN).

Fournit :
- ``LANGS`` : langues disponibles (codes → libellés d'affichage).
- ``STRINGS`` : dictionnaire central des libellés, par langue.
- ``t(key, **fmt)`` : traduction avec repli français (jamais de ``KeyError``).
- ``current_lang()`` / ``set_lang()`` : store de langue persistant
  (``st.session_state["lang"]``, défaut ``fr``).

Règles du projet :
- Les IDs internes (codes de route, clés de scoring, IDs de pays, valeurs
  numériques) ne sont JAMAIS traduits : on ne traduit que l'affichage.
- Le dictionnaire français est la source de repli si une clé manque en EN.
"""

from __future__ import annotations

import json  # noqa: E402  (chargement des overlays)

import re

import streamlit as st

LANGS: dict[str, str] = {"fr": "Français", "en": "English"}
DEFAULT_LANG = "fr"

# Libellés d'affichage des profils (les clés de scoring restent les noms FR
# internes tels que "Équilibré" — vues passerelles vers i18n via profile_key()).
PROFILE_KEYS: dict[str, str] = {
    "Prudent": "prudent",
    "Équilibré": "balanced",
    "Audacieux": "bold",
}

# Verdicts produits par scoring.py (valeurs FR internes → codes i18n).
VERDICT_KEYS: dict[str, str] = {
    "Investir": "invest",
    "Investir avec prudence": "invest_careful",
    "Attendre": "wait",
    "Éviter": "avoid",
}

# Étiquettes de risque de scoring.risk_label() (valeurs FR internes → codes).
RISK_KEYS: dict[str, str] = {
    "Faible": "faible",
    "Modéré": "modere",
    "Élevé": "eleve",
    "Très élevé": "tres_eleve",
}

# Sources de prime pays de scoring.country_risk_premium().
CRP_SOURCE_KEYS: dict[str, str] = {
    "CDS": "cds",
    "Notation": "rating",
    "Notation (CDS non coté)": "rating_no_cds",
}

# Groupes de pays (valeurs FR internes des données → codes).
GROUP_KEYS: dict[str, str] = {
    "Développé": "developed",
    "Émergent": "emerging",
    "Golfe": "gulf",
    "Frontière": "frontier",
}


def verdict_key(verdict_label: str) -> str:
    """Code i18n d'un verdict à partir de sa valeur interne FR (scoring)."""
    return VERDICT_KEYS.get(verdict_label, verdict_label)


def risk_key(risk_label_value: str) -> str:
    """Code i18n d'une étiquette de risque à partir de sa valeur FR (scoring)."""
    return RISK_KEYS.get(risk_label_value, risk_label_value)


def crp_source_key(source: str) -> str:
    """Code i18n d'une source de prime pays à partir de sa valeur FR (scoring)."""
    return CRP_SOURCE_KEYS.get(source, source)


GROUP_KEYS_EN: dict[str, str] = {
    "Developed": "developed",
    "Emerging": "emerging",
    "Gulf": "gulf",
    "Frontier": "frontier",
}


def group_key(group: str) -> str:
    """Code i18n d'un groupe de pays, depuis sa valeur FR ou EN (données)."""
    return GROUP_KEYS.get(group) or GROUP_KEYS_EN.get(group) or group


def profile_label(profile: str) -> str:
    """Libellé affiché d'un profil à partir de sa clé interne FR de scoring."""
    return t(f"profile.{profile_key(profile)}")


def update_range(default: str = "2024-2025") -> str:
    """Intervalle de millésimes extrait de data->app->last_update (valeur
    interne FR du fichier de données) : on n'affiche que la partie
    neutre (« 2024-2025 »), le libellé reste traduit côté appelant."""
    from geocapital.data import load_data

    raw = str(load_data().get("app", {}).get("last_update", "") or "")
    match = re.search(r"\d{4}(?:\s*[-–]\s*\d{4})?", raw)
    return match.group(0).replace(" ", "") if match else default


INTENT_KEYS: dict[str, str] = {
    "country": "country",
    "compare": "compare",
    "verdict": "verdict",
    "capital": "capital",
    "event": "event",
    "portfolio": "portfolio",
}


def intent_label(intent_code: str) -> str:
    """Libellé affiché d'une intention d'analyste à partir de son code interne."""
    return t(f"an.intent.{INTENT_KEYS.get(intent_code, intent_code)}")

STRINGS: dict[str, dict[str, str]] = {
    "fr": {
        # Navigation (codes de route internes → libellés d'affichage)
        "nav.map": "Carte vivante",
        "nav.country": "Fiche pays",
        "nav.compare": "Comparateur",
        "nav.decoder": "Décodeur",
        "nav.analyst": "Analyste",
        "nav.portfolio": "Portefeuille",
        "nav.progress": "Progression",
        "nav.sources": "Sources & méthode",
        # App
        "app.page_title": "GeoCapital — Passé, risque, décision",
        # Sidebar
        "side.language": "Langue",
        "side.brand_sub": "Passé · Risque · Décision",
        "side.navigation": "Navigation",
        "side.journey": "Votre parcours",
        "side.mental_map": "Carte mentale",
        "side.profile_line": "Profil {profile} · {quiz_passed} quiz réussis",
        "side.last_sheet": "Dernière fiche :",
        "me.limits.5": "<strong>Qualitatif assumé :</strong> les scores de gouvernance et de résilience sont des jugements explicites, pas des mesures objectives.",
        "me.btn.back": "Retour à la carte vivante",
        "side.engine": "Moteur",
        "side.last_update": "Données de référence {range}",
        "side.ai_available": "● Assistant IA disponible",
        "side.ai_unavailable": "○ Assistant IA indisponible · mode éditorial",
        "side.prototype_line": "Prototype pédagogique · v1.0",
        # Sources & méthode (views/methodology_page.py)
        "me.eyebrow": "Sources & méthode",
        "me.title": "Un score n'a de valeur que si l'on peut l'expliquer.",
        "me.subtitle": "GeoCapital relie trois couches : l'histoire, les indicateurs et la décision financière. Cette page rend les règles visibles, y compris les limites.",
        "me.step1.eyebrow": "01 · Passé",
        "me.step1.title": "Le récit",
        "me.step1.text": "5 à 7 dates fondatrices, les institutions, les relations et les dépendances. Le passé n'explique pas tout, mais il éclaire les rigidités.",
        "me.step2.eyebrow": "02 · Présent",
        "me.step2.title": "Les chiffres",
        "me.step2.text": "11 indicateurs datés et sourcés, traduits en feux vert/orange/rouge. Aucun chiffre n'est généré par l'IA.",
        "me.step3.eyebrow": "03 · Décision",
        "me.step3.title": "Le prix du risque",
        "me.step3.text": "Score pondéré selon votre profil, rendement exigé Ke, verdict et trois raisons. La décision reste la vôtre.",
        "me.score.title": "Le score GeoCapital",
        "me.score.sub": "5 composantes, 100 points",
        "me.th.component": "Composante",
        "me.th.measures": "Ce qu'elle mesure",
        "me.th.inputs": "Entrées principales",
        "me.component.dynamism": "Dynamisme économique",
        "me.component.dynamism.measures": "Capacité à créer de la valeur et de l'emploi",
        "me.component.dynamism.inputs": "Croissance du PIB, chômage, potentiel de croissance",
        "me.component.stability": "Stabilité macro",
        "me.component.stability.measures": "Prévisibilité des prix et de la monnaie",
        "me.component.stability.inputs": "Inflation, taux réel, stabilité de la devise",
        "me.component.solvency": "Solvabilité",
        "me.component.solvency.measures": "Capacité à honorer la dette",
        "me.component.solvency.inputs": "Dette/PIB, notation, CDS",
        "me.component.institutions": "Institutions",
        "me.component.institutions.measures": "Qualité de l'État et capacité de rebond",
        "me.component.institutions.inputs": "Gouvernance, résilience historique",
        "me.component.openness": "Ouverture & affaires",
        "me.component.openness.measures": "Facilité à investir, exporter, s'implanter",
        "me.component.openness.inputs": "Climat des affaires, ouverture commerciale",
        "me.score.caption": "Les scores qualitatifs (gouvernance, résilience, climat des affaires, ouverture, stabilité devise) sont des évaluations GeoCapital explicites, calibrées à partir de sources publiques. Ils ne sont pas des données brutes.",
        "me.profiles.title": "Les trois profils",
        "me.profiles.sub": "le même pays, trois lectures",
        "me.profiles.header": "Pondération",
        "me.row.dynamism": "Dynamisme",
        "me.row.stability": "Stabilité",
        "me.row.solvency": "Solvabilité",
        "me.row.institutions": "Institutions",
        "me.row.openness": "Ouverture",
        "me.ke.title": "Le rendement exigé",
        "me.ke.sub": "Ke, méthode Damodaran",
        "me.ke.formula": "Ke = taux sans risque + bêta × prime de marché + prime de risque pays",
        "me.ke.body": "Taux sans risque retenu : <strong>{risk_free:.2f} %</strong>. Prime de marché mature : <strong>{mature_erp:.2f} %</strong>. Bêta de marché : <strong>{beta}</strong>. La prime pays est le maximum entre le spread de notation et le spread CDS, multiplié par <strong>{ratio:.1f}</strong> (ratio volatilité actions/obligations).",
        "me.ke.note": "Le Ke est un seuil de rendement exigé, pas une performance attendue. Il sert à comparer le prix du risque entre pays et à éviter de payer trop cher un actif risqué.",
        "me.missing.title": "Données manquantes",
        "me.missing.sub": "le vide est une information",
        "me.missing.body": "<strong>Liban et Syrie.</strong> Une notation absente, un CDS non coté ou des comptes publics non certifiés ne sont pas traités comme des cases neutres. Le score de solvabilité est pénalisé, la prime de risque est portée à un niveau élevé et le verdict « Investir » est bloqué. C'est une règle de prudence : quand le marché ne peut pas prix le risque, l'investisseur doit exiger une marge d'incertitude supplémentaire.",
        "me.ai.title": "Le rôle de l'IA",
        "me.ai.sub": "expliquer, jamais inventer",
        "me.ai.does.eyebrow": "Ce que fait l'IA",
        "me.ai.does.1": "Reformuler la synthèse d'un pays.",
        "me.ai.does.2": "Décrypter un événement en chaîne causale.",
        "me.ai.does.3": "Expliquer le verdict à un débutant.",
        "me.ai.does.4": "Commenter une allocation fictive.",
        "me.ai.does.5": "Expliquer une réponse de quiz.",
        "me.ai.doesnt.eyebrow": "Ce qu'elle ne fait pas",
        "me.ai.doesnt.1": "Elle ne crée aucun chiffre, aucune date, aucune notation.",
        "me.ai.doesnt.2": "Elle ne remplace pas les sources de la base.",
        "me.ai.doesnt.3": "Elle ne donne pas de conseil personnalisé.",
        "me.ai.doesnt.4": "Elle ne prédit pas les marchés.",
        "me.ai.doesnt.5": "Elle ne comble pas une donnée manquante.",
        "me.sources.title": "Sources",
        "me.sources.sub": "la base GeoCapital",
        "me.sources.caption": "Mise à jour : {last_update}. Les valeurs sont arrondies, les millésimes peuvent différer d'un indicateur à l'autre, et les CDS sont des ordres de grandeur.",
        "me.limits.title": "Limites et avertissement",
        "me.limits.sub": "à lire avant de décider",
        "me.limits.1": "<strong>Pas de temps réel :</strong> les données sont préparées pour le MVP, pas actualisées automatiquement.",
        "me.limits.2": "<strong>Pas de conseil en investissement :</strong> le score et le verdict sont pédagogiques et ne tiennent pas compte de votre situation personnelle.",
        "me.limits.3": "<strong>Modèle simplifié :</strong> les corrélations et volatilités du portefeuille sont des estimations, pas un modèle de risque professionnel.",
        "me.limits.4": "<strong>Risque politique :</strong> un score peut être démenti par un choc brutal, une sanction ou une guerre.",
        # Profils (affichage uniquement — clés de scoring inchangées)
        "profile.prudent": "Prudent",
        "profile.balanced": "Équilibré",
        "profile.bold": "Audacieux",
        "profile_desc.prudent": "Priorité à la stabilité et à la capacité de rembourser.",
        "profile_desc.balanced": "Le bon compromis entre croissance, risque et gouvernance.",
        "profile_desc.bold": "Recherche de croissance, tolérance au risque plus élevée.",
        # Composants du score (labels de scoring.COMPONENT_LABELS — affichage)
        "component.dynamisme": "Dynamisme économique",
        "component.stabilite": "Stabilité macro",
        "component.solvabilite": "Solvabilité",
        "component.institutions": "Institutions",
        "component.ouverture": "Ouverture & affaires",
        # Verdicts (valeurs internes FR de scoring.VERDICT_STYLES — affichage)
        "verdict.invest": "Investir",
        "verdict.invest_careful": "Investir avec prudence",
        "verdict.wait": "Attendre",
        "verdict.avoid": "Éviter",
        "verdict.copy.invest": "Les fondamentaux compensent le risque.",
        "verdict.copy.invest_careful": "Le potentiel existe, mais la taille de position compte.",
        "verdict.copy.wait": "Le couple risque/rendement reste insuffisant.",
        "verdict.copy.avoid": "Le risque n'est pas correctement rémunéré.",
        # Risque / statut / prime pays (valeurs internes FR de scoring — affichage)
        "risk.faible": "Faible",
        "risk.modere": "Modéré",
        "risk.eleve": "Élevé",
        "risk.tres_eleve": "Très élevé",
        "status.green": "Solide",
        "status.orange": "Vigilance",
        "status.red": "Risque",
        "crp_source.cds": "CDS",
        "crp_source.rating": "Notation",
        "crp_source.rating_no_cds": "Notation (CDS non coté)",
        "group.developed": "Développé",
        "group.emerging": "Émergent",
        "group.gulf": "Golfe",
        "group.frontier": "Frontière",
        "reason.score_line": "Score de {value}/100.",
        "reason.vigilance": "Point de vigilance : {component}",
        "comment.dynamisme.pos": "La croissance, l'emploi et l'élan économique soutiennent la demande.",
        "comment.dynamisme.neg": "Le moteur de croissance est fragile, ce qui réduit la visibilité.",
        "comment.stabilite.pos": "L'inflation, le taux directeur et la devise forment un cadre prévisible.",
        "comment.stabilite.neg": "L'inflation ou la devise rendent le cadre macroéconomique moins lisible.",
        "comment.solvabilite.pos": "La dette, la notation et les CDS signalent une capacité de remboursement crédible.",
        "comment.solvabilite.neg": "La dette ou l'absence de prix de marché pèsent sur la signature souveraine.",
        "comment.institutions.pos": "La gouvernance et la capacité de rebond historique rassurent l'investisseur.",
        "comment.institutions.neg": "La gouvernance et la continuité institutionnelle restent des angles morts.",
        "comment.ouverture.pos": "L'ouverture et le climat des affaires facilitent l'implantation.",
        "comment.ouverture.neg": "Les frictions administratives ou commerciales renchérissent l'entrée.",
        # Échelle de l'anneau de score
        "ring.scale": "score / 100",
        # Composants UI partagés (ui.py) — tout ce qui apparaît sur les pages 1-2
        "ui.hero.ke_label": "Rendement exigé",
        "ui.hero.ke_annual": "Ke annuel",
        "ui.hero.risk_prefix": "Risque :",
        "ui.footer.tagline": "Connaître le passé pour anticiper le futur.",
        "ui.footer.disclaimer": "Prototype pédagogique. Données indicatives, non actualisées en temps réel.",
        "ui.footer.not_advice": "Pas un conseil en investissement · Les chiffres sont sourcés dans la base GeoCapital.",
        "ui.footer.ai_line": "L'IA explique les données, elle ne les invente pas.",
        "ui.bars.head": "{score}/100 · poids {pct}%",
        "ui.bars.contribution": "Contribution au score : {points} pts sur {max}",
        # Carte vivante (views/map_page.py)
        "map.hero.title": "Carte vivante · 10 pays · 3 profils",
        "map.hero.subtitle": "Comprendre le passé. Mesurer le risque. Décider.",
        "map.hero.text": "Cliquez sur un pays, lisez son histoire en trois minutes, puis regardez ses indicateurs devenir une décision financière. Le score change avec votre tolérance au risque.",
        "map.hero.chip1": "Passé → présent → décision",
        "map.hero.chip2": "Données sourcées",
        "map.hero.chip3": "IA explicative",
        "map.kpi.countries": "pays couverts",
        "map.kpi.countries_desc": "Du plus sûr au plus fragile",
        "map.kpi.best": "meilleur score",
        "map.kpi.median": "rendement médian exigé",
        "map.kpi.median_desc": "Prime de risque pays incluse",
        "map.kpi.positive": "verdicts positifs",
        "map.kpi.positive_desc": "Investir ou investir avec prudence",
        "map.profile.radio": "Votre profil d'investisseur",
        "map.profile.help": "Le score n'est pas absolu : il dépend de ce que vous cherchez.",
        "map.metric.radio_label": "Indicateur affiché",
        "map.metric.attractivite": "Attractivité",
        "map.metric.risque": "Risque maîtrisé",
        "map.metric.croissance": "Croissance",
        "map.metric.devise": "Stabilité devise",
        "map.metric_desc.attractivite": "Score GeoCapital",
        "map.metric_desc.risque": "Plus haut = risque plus faible",
        "map.metric_desc.croissance": "Dynamisme économique",
        "map.metric_desc.devise": "Score de stabilité de la devise",
        "map.chip_profile": "Profil {profile} · {pct}% croissance",
        "map.section.world": "Le monde vu par le risque",
        "map.caption.mvp": "Seuls les 10 pays du MVP sont colorés. Les pays gris ne sont pas notés dans cette version.",
        "map.zoom.hint": "Sélectionnez un pays pour zoomer sur la carte et afficher son résumé.",
        "map.selected.eyebrow": "Pays sélectionné",
        "map.card.score": "Score {value}/100",
        "map.card.ke": "Ke {value}%",
        "map.card.risk": "Risque {value}/100",
        "map.btn.reset": "Revenir à la vue monde",
        "map.card.eyebrow": "Grille de lecture",
        "map.chip.growth": "Croissance {pct}%",
        "map.chip.stability": "Stabilité {pct}%",
        "map.chip.solvency": "Solvabilité {pct}%",
        "map.section.top": "Les mieux notés",
        "map.section.top_sub": "pour ce profil",
        "map.note.score": "Le score mesure l'attractivité relative. Il ne remplace ni une due diligence, ni un conseil personnalisé.",
        "map.section.explore": "Zoomer sur un pays",
        "map.section.explore_sub": "cliquez pour zoomer et afficher le résumé",
        "map.expander.risk_return": "Voir la carte risque / rendement",
        "map.riskret.hint": "Plus un pays est à droite, plus son risque est élevé. Plus il est haut, plus l'investisseur exige de rendement. La taille de la bulle représente le score GeoCapital.",
        "map.riskret.xaxis": "Risque pays (0 = faible, 100 = très élevé)",
        "map.riskret.yaxis": "Rendement exigé Ke (%)",
        "map.hover.risk": "Risque :",
        "map.hover.ke": "Rendement exigé :",
        "map.hover.score": "Score GeoCapital :",
        "map.hover.score_short": "Score :",
        "map.hover.verdict": "Verdict :",
        "map.ai.caption": "Mode IA activé : les analyses optionnelles utilisent uniquement les données de la base GeoCapital.",
        "map.callout.ke": "Le rendement exigé n'est pas une prédiction de performance. C'est le rendement minimum qu'un investisseur rationnel devrait demander pour accepter ce niveau de risque. Un pays peut offrir un fort potentiel et rester risqué : c'est tout l'intérêt de lire le score et le verdict ensemble.",
        # Fiche pays (views/country_page.py)
        "country.select": "Choisir un pays",
        "country.profile_radio": "Profil d'investisseur",
        "country.error": "Pays introuvable.",
        "country.action.compare": "Comparer",
        "country.chip.rank": "Rang {rank}/10 · profil {profile}",
        "country.risk_line": "Rang {rank}/10 · profil {profile} · risque {value}/100 ({label})",
        "country.updated": "Dernière mise à jour des données :",
        "country.tab.story": "Récit & institutions",
        "country.tab.dashboard": "Tableau de bord",
        "country.tab.score": "Score & verdict",
        "country.tab.quiz": "Quiz",
        "country.section.timeline": "Frise historique",
        "country.section.timeline_sub": "les dates qui expliquent le risque actuel",
        "country.hero_to_risk": "Du passé au risque",
        "country.story_in_numbers": "Ce récit se lit dans les chiffres",
        "country.story_paragraph": "Le passé pèse sur la solvabilité ({solv}/100), la stabilité ({stab}/100) et la qualité des institutions ({inst}/100). C'est cette chaîne que le score transforme en décision.",
        "country.section.relations": "Relations & dépendances",
        "country.section.relations_sub": "alliés, rivaux, points de fragilité",
        "country.rel.allies": "Alliés",
        "country.rel.rivals": "Rivaux",
        "country.rel.dependencies": "Dépendances",
        "country.section.decision": "Ce qui pèse sur la décision",
        "country.section.decision_sub": "forces, risques et portes d'entrée",
        "country.eyebrow.strengths": "Forces",
        "country.eyebrow.risks": "Risques",
        "country.eyebrow.opportunities": "Opportunités",
        "country.section.indicators": "Les 11 indicateurs",
        "country.section.indicators_sub": "feu vert, orange ou rouge",
        "country.dash.hint": "Chaque indicateur est daté et sourcé. La couleur est une grille de lecture GeoCapital, pas une opinion de marché en temps réel.",
        "dash.source_missing": "Source non renseignée",
        "fresh.as_of": "Données au {as_of}",
        "fresh.stale_note": "⚠ = observation antérieure à {limit} : la valeur retenue reste la plus récente confirmée, à rafraîchir dès qu'une source fiable le permet.",
        "fresh.verdict_dates": "Le verdict composite repose sur les observations ci-dessus ; plus ancienne retenue : millésime {oldest}.",
        "country.callout.missing": "Ici, une donnée manquante n'est pas une case vide : c'est un signal de risque. Sans notation active ni CDS coté, le marché ne peut pas donner de prix fiable à la dette. GeoCapital bloque donc le verdict « Investir ».",
        "country.section.pricerisk": "Le prix du risque",
        "country.section.pricerisk_sub": "formule de Damodaran",
        "country.kpi.risk_free": "Taux sans risque",
        "country.kpi.risk_free_desc": "Référence : Trésor américain 10 ans",
        "country.kpi.erp": "Prime de marché mature",
        "country.kpi.erp_desc": "Actions vs obligations, Damodaran",
        "country.kpi.crp": "Prime de risque pays",
        "country.kpi.crp_desc": "Calculée via {source}",
        "country.kpi.ke": "Rendement exigé Ke",
        "country.kpi.ke_desc": "Taux minimal pour accepter ce risque",
        "country.howto.eyebrow": "Comment lire",
        "country.howto.title": "Ke = taux sans risque + bêta × prime de marché + prime pays",
        "country.howto.text": "Pour {name}, le calcul donne {rf} % + 1,0 × {erp} % + {crp} % = <strong style='color:#e6b86b'>{ke} %</strong>. Plus le risque perçu est élevé, plus l'investisseur doit exiger de rendement. Ce n'est pas un rendement promis : c'est un seuil de rentabilité exigé.",
        "country.sources.caption": "Sources : FMI, banques centrales, agences de notation, marché CDS, Damodaran. Données arrondies et indicatives.",
        "country.reasons.eyebrow": "Les 3 raisons du verdict",
        "country.ke.eyebrow": "Rendement exigé",
        "country.ke.annual": "Ke annuel",
        "country.ke.line": "Taux sans risque {rf} % + prime mature {erp} % + prime pays {crp} % ({source}).",
        "country.breakdown.eyebrow": "Décomposition transparente",
        "country.breakdown.title": "Cinq briques, une décision",
        "country.by_profile.eyebrow": "Selon votre profil",
        "country.by_profile.text": "Le même pays ne convient pas à tout le monde. Le profil pondère différemment la croissance, la stabilité et la solvabilité.",
        "country.vigilance.callout": "Point de vigilance principal : {component} ({value}/100). Le score est un outil de comparaison, pas une prévision. Une note élevée peut cacher un risque politique brutal.",
        "inst.card_title": "Institutions & pouvoir",
        "inst.regime": "Régime",
        "inst.executive": "Exécutif",
        "inst.legislature": "Législatif",
        "inst.central_bank": "Banque centrale",
        "inst.currency": "Devise",
        "inst.law": "Cadre juridique",
        "inst.fact": "À retenir",
        "ai.expander": "Approfondir avec l'IA",
        "ai.editorial_caption": "Mode éditorial : la synthèse GeoCapital ci-dessus fonctionne sans IA. Pour activer l'analyse générative, ajoutez `OPENROUTER_API_KEY` dans le fichier .env ou les secrets Streamlit. L'IA ne reçoit que les données validées de cette fiche.",
        "ai.recaption": "L'IA reformule les faits de la fiche. Elle ne crée aucun chiffre et ne remplace pas les sources.",
        "ai.button": "Générer la synthèse",
        "ai.spinner": "Lecture de la fiche et rédaction...",
        "ai.unavailable": "L'appel IA n'a pas abouti. Le contenu éditorial reste disponible.",
        "country.select": "Choisir un pays",
        "quiz.eyebrow": "Quiz éclair · 1 question",
        "quiz.radio": "Votre réponse",
        "quiz.button": "Valider ma réponse",
        "quiz.warn_none": "Choisissez une réponse avant de valider.",
        "quiz.success": "Bonne réponse. Vous pouvez cocher ce pays comme compris.",
        "quiz.error": "Pas tout à fait. Lisez l'explication, puis réessayez.",
        "quiz.why": "Pourquoi ?",
        "quiz.ai_button": "Expliquer avec l'IA",
        "quiz.ai_spinner": "Explication...",
        "quiz.ai_hint": "Astuce : l'explication ci-dessus est éditoriale et vérifiée. L'IA peut la reformuler si une clé API est configurée.",
        "quiz.chip_done": "Quiz réussi",
        # Comparateur (views/comparator_page.py)
        "comp.eyebrow": "Comparateur · 2 à 3 pays",
        "comp.title": "Deux histoires, deux risques, deux prix.",
        "comp.subtitle": "Comparez la trajectoire, les institutions et le rendement exigé. Un score plus élevé ne signifie pas automatiquement un meilleur investissement : regardez aussi ce que le marché vous fait payer.",
        "comp.preset.usa_china": "USA vs Chine",
        "comp.preset.saudi_uae": "Arabie vs Émirats",
        "comp.preset.lebanon_syria": "Liban vs Syrie",
        "comp.preset.france_japan": "France vs Japon",
        "comp.preset.morocco_sa": "Maroc vs Afrique du Sud",
        "comp.select": "Pays à comparer",
        "comp.select_help": "Sélectionnez 2 ou 3 pays.",
        "comp.profile_radio": "Profil",
        "comp.min_two": "Sélectionnez au moins deux pays pour lancer la comparaison.",
        "comp.ring_label": "score",
        "comp.card_ke_risk": "Ke · risque {value}/100",
        "comp.section.radar": "Profil de risque",
        "comp.section.radar_sub": "les cinq briques du score",
        "comp.section.ke": "Rendement exigé",
        "comp.section.ke_sub": "plus le risque est perçu, plus Ke monte",
        "comp.ke_note": "Le rendement exigé intègre le risque de crédit, pas seulement la croissance. Un pays peut croître vite et rester cher à financer.",
        "comp.section.table": "Tableau de bord comparé",
        "comp.section.table_sub": "vert / orange / rouge",
        "comp.table.indicator": "Indicateur",
        "comp.section.reading": "Lecture GeoCapital",
        "comp.section.reading_sub": "ce que le comparatif raconte",
        "comp.reading": "Avec le profil <strong>{profile}</strong>, <strong>{best}</strong> obtient le meilleur score ({best_score}/100). Le pays au risque le plus faible est <strong>{safest}</strong> (risque {safest_risk}/100). Le rendement exigé va de <strong>{ke_min}</strong> pour {cheapest} à <strong>{ke_max}</strong> pour {most_expensive}. L'écart mesure le prix que le marché demande pour accepter l'incertitude.",
        "comp.export_csv": "Exporter en CSV",
        "comp.open_sheet": "Fiche {flag}",
        "comp.callout.ke": "Un rendement exigé élevé n'est pas une promesse de gain. Il signifie que l'investisseur doit être compensé pour un risque plus grand. Si le rendement attendu d'un actif est inférieur à Ke, la décision rationnelle est de ne pas l'acheter.",
        # Décodeur (views/decoder_page.py)
        "dec.eyebrow": "Décodeur d'actualité",
        "dec.title": "Un fait divers n'est pas une causalité.",
        "dec.subtitle": "Choisissez un événement. GeoCapital déroule la chaîne : fait → économie → finance → gagnants et perdants. Chaque étape renvoie à une notion et à un précédent historique du pays.",
        "dec.country": "Pays",
        "dec.no_events": "Aucun événement préparé pour ce pays.",
        "dec.event_select": "Événement récent",
        "dec.source_prefix": "Source :",
        "dec.section.chain": "La chaîne causale",
        "dec.section.chain_sub": "4 étapes, aucune saute",
        "dec.callout.chain": "La finance ne réagit pas à l'événement lui-même, mais à ce qu'il change dans les flux, les taux, les profits et le risque perçu. C'est pour cela qu'un même fait peut faire monter un actif et en faire baisser un autre.",
        "dec.expander.concepts": "Les concepts nécessaires",
        "dec.expander.ai": "Décoder avec l'IA",
        "dec.ai.editorial_caption": "Le décodage éditorial ci-dessus est complet et ne dépend pas d'une API. Ajoutez `OPENROUTER_API_KEY` pour faire reformuler la chaîne causale par l'IA, à partir des mêmes faits.",
        "dec.ai.receive": "L'IA reçoit uniquement l'événement, la chaîne et l'écho historique préparés.",
        "dec.ai.button": "Générer une explication",
        "dec.ai.spinner": "Relecture de la chaîne causale...",
        "dec.section.wl": "Qui gagne, qui perd",
        "dec.section.wl_sub": "entreprises, actifs, pays exposés",
        "dec.echo": "Écho historique · {year}",
        "dec.link.eyebrow": "Lien avec la fiche pays",
        "dec.link.chip_score": "Score {value}/100",
        "dec.link.text": "Le même choc n'a pas le même effet selon la dette, les réserves et la crédibilité de la banque centrale.",
        "dec.open_full": "Ouvrir la fiche complète",
        "dec.callout.reliability": "Règle de fiabilité : chaque chiffre affiché vient de la base GeoCapital. L'IA peut expliquer, reformuler ou relier, mais elle n'a pas le droit d'inventer une donnée. Quand une donnée manque, le décodeur le signale et le traite comme un risque.",
        # Portefeuille (views/portfolio_page.py)
        "pf.eyebrow": "Portefeuille mondial",
        "pf.title": "100 000 €, dix pays, une leçon de risque.",
        "pf.subtitle": "Répartissez un capital fictif entre les pays. Le simulateur calcule le rendement exigé pondéré, la volatilité et l'effet réel de la diversification. Aucun ordre n'est passé, aucun rendement n'est garanti.",
        "pf.preset.defensive": "Défensif",
        "pf.preset.balanced": "Équilibré",
        "pf.preset.offensive": "Offensif",
        "pf.presets_hint": "Les presets sont pédagogiques. Modifiez ensuite librement chaque poche.",
        "pf.section.allocation": "Votre allocation",
        "pf.section.allocation_sub": "montants en euros",
        "pf.amount_of": "Montant {name}",
        "pf.total_exact": "Total saisi : 100 000 € · allocation exacte",
        "pf.total_normalized": "Total saisi : {amount} · normalisé à 100 000 € pour la simulation",
        "pf.total_zero": "Total saisi : 0 €",
        "pf.reset_all": "Tout réinitialiser",
        "pf.need_amount": "Ajoutez au moins un montant pour lancer la simulation.",
        "pf.kpi.return": "Rendement espéré",
        "pf.kpi.return_desc": "Proxy : Ke moyen pondéré",
        "pf.kpi.volatility": "Volatilité estimée",
        "pf.kpi.volatility_desc": "Risque annualisé du portefeuille",
        "pf.kpi.diversification": "Gain de diversification",
        "pf.kpi.diversification_desc": "Moins de volatilité grâce aux corrélations",
        "pf.kpi.effective": "Pays effectifs",
        "pf.kpi.effective_desc": "Concentration HHI {hhi}",
        "pf.section.chart": "Répartition normalisée",
        "pf.section.chart_sub": "100 000 €",
        "pf.donut.ke_mean": "Ke moyen",
        "pf.section.diagnosis": "Diagnostic",
        "pf.section.diagnosis_sub": "ce que votre allocation raconte",
        "pf.commentary.empty": "Aucune allocation : le portefeuille ne peut pas être analysé.",
        "pf.concentration.high": "très concentré",
        "pf.concentration.medium": "modérément concentré",
        "pf.concentration.low": "relativement diversifié",
        "pf.diversification.good": "La diversification réduit la volatilité estimée par rapport à la moyenne pondérée des pays.",
        "pf.diversification.poor": "La diversification apporte peu : les pays choisis évoluent de façon trop proche.",
        "pf.commentary": "Votre allocation est {concentration} : {top} pèse {top_weight} % du portefeuille. Le rendement exigé pondéré s'élève à {ke} % par an, pour une volatilité estimée de {vol} %. {diversification} Le pays qui contribue le plus au risque est {riskiest}. Le portefeuille n'est pas une recommandation : c'est une manière de voir que le rendement et le risque se paient ensemble.",
        "pf.section.risk": "Contribution au risque",
        "pf.section.risk_sub": "poids × volatilité",
        "pf.hover.contrib": "Contribution approx. :",
        "pf.chart.weight_vol": "Poids × volatilité",
        "pf.section.detail": "Détail du portefeuille",
        "pf.section.detail_sub": "montants normalisés à 100 000 €",
        "pf.th.country": "Pays",
        "pf.th.weight": "Poids normalisé",
        "pf.th.amount": "Montant",
        "pf.th.ke": "Ke",
        "pf.th.vol": "Volatilité",
        "pf.th.contrib": "Contribution risque",
        "pf.expander.ai": "Commenter avec l'IA",
        "pf.ai.editorial_caption": "Le diagnostic ci-dessus est déterministe et fonctionne sans API. Ajoutez `OPENROUTER_API_KEY` pour obtenir une reformulation pédagogique de cette même allocation.",
        "pf.ai.receive": "L'IA reçoit uniquement l'allocation et les métriques calculées.",
        "pf.ai.button": "Générer le commentaire",
        "pf.ai.spinner": "Analyse de l'allocation...",
        "pf.ai.unavailable": "L'appel IA n'a pas abouti. Le diagnostic déterministe reste disponible.",
        "pf.download": "Télécharger l'allocation",
        "pf.csv.country": "Pays",
        "pf.csv.weight": "Poids (%)",
        "pf.csv.amount": "Montant (€)",
        "pf.csv.ke": "Ke (%)",
        "pf.csv.vol": "Volatilité (%)",
        "pf.callout.limits": "Limites du modèle : la volatilité est une estimation pédagogique, les corrélations sont simplifiées par groupe de pays, et le portefeuille est investi en actions pays sans couverture de change. Une vraie allocation doit tenir compte de votre horizon, de votre situation fiscale et de votre capacité à supporter une perte.",
        # Progression (views/progress_page.py)
        "pr.eyebrow": "Ma progression",
        "pr.title": "Une carte mentale se remplit pays après pays.",
        "pr.subtitle": "GeoCapital ne récompense pas le temps passé : il récompense la compréhension. Chaque fiche lue et chaque quiz réussi ajoute un pays à votre carte mentale.",
        "pr.kpi.explored": "pays explorés",
        "pr.kpi.explored_desc": "{pct} % de la carte",
        "pr.kpi.quiz": "quiz réussis",
        "pr.kpi.quiz_desc": "Une notion par pays",
        "pr.kpi.average": "score moyen exploré",
        "pr.kpi.average_desc": "Profil {profile}",
        "pr.kpi.remaining": "pays restants",
        "pr.kpi.remaining_desc": "À vous de choisir le prochain",
        "pr.card.eyebrow": "Votre carte mentale",
        "pr.card.title": "Progression globale",
        "pr.card.note": "Comprendre un pays ne veut pas dire l'aimer. L'objectif est de savoir pourquoi vous l'incluez ou l'excluez.",
        "pr.section.badges": "Badges",
        "pr.section.badges_sub": "la progression, pas la performance",
        "pr.badge.first": "Premier pas",
        "pr.badge.curious": "Curieux",
        "pr.badge.cartographer": "Cartographe",
        "pr.badge.world": "Tour du monde",
        "pr.badge.quiz": "Quiz solide",
        "pr.badge_note.first": "1 pays exploré",
        "pr.badge_note.curious": "3 pays explorés",
        "pr.badge_note.cartographer": "5 pays explorés",
        "pr.badge_note.world": "10 pays explorés",
        "pr.badge_note.quiz": "5 quiz réussis",
        "pr.section.countries": "Les 10 pays",
        "pr.section.countries_sub": "votre état d'avancement",
        "pr.status.explored": "Exploré",
        "pr.status.to_discover": "À découvrir",
        "pr.quiz.done": "Quiz réussi",
        "pr.quiz.todo": "Quiz à faire",
        "pr.quiz.to_open": "Fiche à ouvrir",
        "pr.tile.score": "score {value}/100",
        "pr.btn.revisit": "Revoir",
        "pr.btn.open": "Ouvrir",
        "pr.section.next": "Prochaine étape",
        "pr.section.next_sub": "une suggestion, pas une obligation",
        "pr.next.eyebrow": "À explorer ensuite",
        "pr.btn.open_full": "Ouvrir la fiche",
        "pr.done_callout": "Vous avez parcouru les dix pays. Revenez sur les fiches pour comparer les trajectoires et tester les trois profils.",
        "pr.reset.expander": "Réinitialiser ma progression",
        "pr.reset.caption": "Cette action efface uniquement les pays explorés et les quiz de cette session. Le portefeuille n'est pas modifié.",
        "pr.reset.confirm": "Je confirme la réinitialisation.",
        "pr.reset.button": "Réinitialiser",
        "pr.callout.verdicts": "La note d'un pays dépend de votre profil. Un pays peut être « {invest} » pour un profil audacieux et « {wait} » pour un profil prudent. La progression ne mesure donc pas une vérité absolue, mais votre capacité à lire le compromis risque/rendement.",
        # Analyste (views/analyst_page.py)
        "an.eyebrow": "Analyste",
        "an.title": "Discutez avec la base GeoCapital.",
        "an.subtitle": "Posez vos questions sur un pays, un verdict, le coût du capital, un événement ou votre portefeuille. Les réponses s'appuient uniquement sur les faits validés de la base et les calculs déterministes de l'application.",
        "an.select.topic": "Sujet de question",
        "an.intent.country": "Analyse un pays",
        "an.intent.compare": "Comparer des pays",
        "an.intent.verdict": "Expliquer un verdict",
        "an.intent.capital": "Expliquer le coût du capital",
        "an.intent.event": "Comprendre un événement",
        "an.intent.portfolio": "Analyser mon portefeuille",
        "an.select.country": "Pays à analyser",
        "an.select.compare": "Pays à comparer (2 à 4)",
        "an.select.verdict": "Verdict / coût du capital de quel pays ?",
        "an.select.event": "Événement du décodeur",
        "an.ph.country": "Choisir un pays…",
        "an.ph.compare": "Choisir au moins deux pays…",
        "an.ph.event": "Choisir un événement…",
        "an.allocation.current": "Votre allocation actuelle : {amount} sur 100 000 € fictifs (réglée dans l'onglet Portefeuille).",
        "an.btn.clear": "Effacer la conversation",
        "an.chip.facts": "● Faits validés",
        "an.chip.interpretation": "◆ Interprétation IA",
        "an.chip.hypothesis": "○ Hypothèse",
        "an.chip.facts_python": "● Faits validés · Python",
        "an.facts.expander": "Faits validés envoyés au modèle",
        "an.facts.caption": "Ces données proviennent de la base GeoCapital et des calculs déterministes (score, Ke, portefeuille). Le modèle ne peut s'appuyer que sur elles.",
        "an.portfolio.empty": "Votre portefeuille est vide : renseignez des montants dans l'onglet Portefeuille pour que l'analyse s'appuie sur vos positions.",
        "an.editorial_mode": "Mode éditorial : l'IA générative est désactivée. Les questions restent utiles — vous obtiendrez les faits validés et l'analyse déterministe de la base.",
        "an.spinner.model": "Interrogation du modèle…",
        "an.spinner.editorial": "Analyse éditoriale…",
        "an.unavailable": "IA indisponible (clé absente ou service injoignable). Réponse fondée uniquement sur les données validées et les calculs déterministes.",
        "an.prototype_caption": "Prototype pédagogique : aucune recommandation personnalisée ; l'IA ne reçoit que les faits validés affichés ci-dessus.",
        "an.input.placeholder": "Ex : « Explique le verdict de la France » ou « Que change une baisse de la Fed ? »",
        "an.limit.remaining": "Questions restantes : {remaining}/{total} · limite par session",
        "an.limit.reached": "Vous avez utilisé les {total} questions d'analyste de cette session. Pour rester raisonnable, l'assistant fonctionne par session de navigateur : ce n'est ni un plafond global ni une garantie de dépense, et une nouvelle session remet le compteur à zéro. Toutes les autres pages restent accessibles.",
    },
    "en": {
        "nav.map": "Living map",
        "nav.country": "Country profile",
        "nav.compare": "Comparator",
        "nav.decoder": "Decoder",
        "nav.analyst": "Analyst",
        "nav.portfolio": "Portfolio",
        "nav.progress": "Progress",
        "nav.sources": "Sources & method",
        "app.page_title": "GeoCapital — Past, risk, decision",
        "side.language": "Language",
        "side.brand_sub": "Past · Risk · Decision",
        "side.navigation": "Navigation",
        "side.journey": "Your journey",
        "side.mental_map": "Mental map",
        "side.profile_line": "{profile} profile · {quiz_passed} quizzes passed",
        "side.last_sheet": "Last profile viewed:",
        "side.engine": "Engine",
        "side.last_update": "Reference data {range}",
        "side.ai_available": "● AI assistant available",
        "side.ai_unavailable": "○ AI assistant unavailable · editorial mode",
        "side.prototype_line": "Educational prototype · v1.0",
        # Sources & method (views/methodology_page.py)
        "me.eyebrow": "Sources & method",
        "me.title": "A score is only worth what can be explained.",
        "me.subtitle": "GeoCapital connects three layers: history, indicators and the financial decision. This page makes the rules visible, including the limits.",
        "me.step1.eyebrow": "01 · Past",
        "me.step1.title": "The narrative",
        "me.step1.text": "5 to 7 founding dates, the institutions, the relations and the dependencies. The past doesn't explain everything, but it sheds light on rigidities.",
        "me.step2.eyebrow": "02 · Present",
        "me.step2.title": "The figures",
        "me.step2.text": "11 dated and sourced indicators, translated into green/orange/red lights. No figure is generated by the AI.",
        "me.step3.eyebrow": "03 · Decision",
        "me.step3.title": "The price of risk",
        "me.step3.text": "Weighted score based on your profile, required return Ke, verdict and three reasons. The decision remains yours.",
        "me.score.title": "The GeoCapital score",
        "me.score.sub": "5 components, 100 points",
        "me.th.component": "Component",
        "me.th.measures": "What it measures",
        "me.th.inputs": "Main inputs",
        "me.component.dynamism": "Economic dynamism",
        "me.component.dynamism.measures": "Capacity to create value and jobs",
        "me.component.dynamism.inputs": "GDP growth, unemployment, growth potential",
        "me.component.stability": "Macro stability",
        "me.component.stability.measures": "Price and currency predictability",
        "me.component.stability.inputs": "Inflation, real rate, currency stability",
        "me.component.solvency": "Solvency",
        "me.component.solvency.measures": "Capacity to honor debt",
        "me.component.solvency.inputs": "Debt/GDP, rating, CDS",
        "me.component.institutions": "Institutions",
        "me.component.institutions.measures": "State quality and resilience",
        "me.component.institutions.inputs": "Governance, historical resilience",
        "me.component.openness": "Openness & business",
        "me.component.openness.measures": "Ease of investing, exporting, setting up",
        "me.component.openness.inputs": "Business climate, trade openness",
        "me.score.caption": "The qualitative scores (governance, resilience, business climate, openness, currency stability) are explicit GeoCapital assessments, calibrated from public sources. They are not raw data.",
        "me.profiles.title": "The three profiles",
        "me.profiles.sub": "the same country, three readings",
        "me.profiles.header": "Weighting",
        "me.row.dynamism": "Dynamism",
        "me.row.stability": "Stability",
        "me.row.solvency": "Solvency",
        "me.row.institutions": "Institutions",
        "me.row.openness": "Openness",
        "me.ke.title": "The required return",
        "me.ke.sub": "Ke, the Damodaran method",
        "me.ke.formula": "Ke = risk-free rate + beta × market risk premium + country risk premium",
        "me.ke.body": "Selected risk-free rate: <strong>{risk_free:.2f} %</strong>. Mature market risk premium: <strong>{mature_erp:.2f} %</strong>. Market beta: <strong>{beta}</strong>. The country risk premium is the maximum between the rating spread and the CDS spread, multiplied by <strong>{ratio:.1f}</strong> (equity/bond volatility ratio).",
        "me.ke.note": "Ke is a required-return threshold, not an expected performance. It is used to compare the price of risk across countries and to avoid overpaying for a risky asset.",
        "me.missing.title": "Missing data",
        "me.missing.sub": "emptiness is information",
        "me.missing.body": "<strong>Lebanon and Syria.</strong> A missing rating, a non-traded CDS or uncertified public accounts are not treated as neutral boxes. The solvency score is penalized, the country risk premium is raised to a high level and the “Invest” verdict is blocked. It is a prudence rule: when the market cannot price the risk, the investor must require an additional margin of uncertainty.",
        "me.ai.title": "The role of the AI",
        "me.ai.sub": "explain, never invent",
        "me.ai.does.eyebrow": "What the AI does",
        "me.ai.does.1": "Rephrase a country's synthesis.",
        "me.ai.does.2": "Decipher an event in a causal chain.",
        "me.ai.does.3": "Explain the verdict to a beginner.",
        "me.ai.does.4": "Comment on a fictional allocation.",
        "me.ai.does.5": "Explain a quiz answer.",
        "me.ai.doesnt.eyebrow": "What it does not do",
        "me.ai.doesnt.1": "It creates no figure, no date, no rating.",
        "me.ai.doesnt.2": "It does not replace the database sources.",
        "me.ai.doesnt.3": "It gives no personalized advice.",
        "me.ai.doesnt.4": "It does not predict the markets.",
        "me.ai.doesnt.5": "It does not fill in missing data.",
        "me.sources.title": "Sources",
        "me.sources.sub": "the GeoCapital database",
        "me.sources.caption": "Updated: {last_update}. Values are rounded, vintages may differ from one indicator to another, and CDS are orders of magnitude.",
        "me.limits.title": "Limits and warning",
        "me.limits.sub": "to read before deciding",
        "me.limits.1": "<strong>No real time:</strong> data is prepared for the MVP, not automatically refreshed.",
        "me.limits.2": "<strong>No investment advice:</strong> the score and verdict are educational and do not account for your personal situation.",
        "me.limits.3": "<strong>Simplified model:</strong> portfolio correlations and volatilities are estimates, not a professional risk model.",
        "me.limits.4": "<strong>Political risk:</strong> a score can be disproved by a sudden shock, a sanction or a war.",
        "me.limits.5": "<strong>Acknowledged qualitative:</strong> governance and resilience scores are explicit judgments, not objective measurements.",
        "me.btn.back": "Back to the living map",
        "profile.prudent": "Cautious",
        "profile.balanced": "Balanced",
        "profile.bold": "Bold",
        "profile_desc.prudent": "Priority on stability and repayment capacity.",
        "profile_desc.balanced": "The right balance between growth, risk and governance.",
        "profile_desc.bold": "Seeking growth, with higher risk tolerance.",
        # Score components (scoring.COMPONENT_LABELS display labels)
        "component.dynamisme": "Economic momentum",
        "component.stabilite": "Macro stability",
        "component.solvabilite": "Solvency",
        "component.institutions": "Institutions",
        "component.ouverture": "Openness & business",
        # Verdicts (scoring.VERDICT_STYLES internal FR values — display only)
        "verdict.invest": "Invest",
        "verdict.invest_careful": "Invest with caution",
        "verdict.wait": "Wait",
        "verdict.avoid": "Avoid",
        "verdict.copy.invest": "The fundamentals offset the risk.",
        "verdict.copy.invest_careful": "The potential exists, but position sizing matters.",
        "verdict.copy.wait": "The risk/return pairing is still not enough.",
        "verdict.copy.avoid": "The risk is not properly rewarded.",
        # Risk / status / country premium (scoring internal FR values — display)
        "risk.faible": "Low",
        "risk.modere": "Moderate",
        "risk.eleve": "High",
        "risk.tres_eleve": "Very high",
        "status.green": "Solid",
        "status.orange": "Watch",
        "status.red": "Risk",
        "crp_source.cds": "CDS",
        "crp_source.rating": "Credit rating",
        "crp_source.rating_no_cds": "Rating (no quoted CDS)",
        "group.developed": "Developed",
        "group.emerging": "Emerging",
        "group.gulf": "Gulf",
        "group.frontier": "Frontier",
        "reason.score_line": "Score of {value}/100.",
        "reason.vigilance": "Watch point: {component}",
        "comment.dynamisme.pos": "Growth, employment and economic momentum support demand.",
        "comment.dynamisme.neg": "The growth engine is fragile, which reduces visibility.",
        "comment.stabilite.pos": "Inflation, the policy rate and the currency form a predictable framework.",
        "comment.stabilite.neg": "Inflation or the currency makes the macro framework less readable.",
        "comment.solvabilite.pos": "Debt, the rating and CDS point to a credible repayment capacity.",
        "comment.solvabilite.neg": "Debt or the absence of a market price weighs on the sovereign signature.",
        "comment.institutions.pos": "Governance and historical resilience reassure the investor.",
        "comment.institutions.neg": "Governance and institutional continuity remain blind spots.",
        "comment.ouverture.pos": "Openness and the business climate make market entry easier.",
        "comment.ouverture.neg": "Administrative or trade frictions make entry more costly.",
        # Score ring scale
        "ring.scale": "score / 100",
        # Shared UI components (ui.py) — everything visible on pages 1-2
        "ui.hero.ke_label": "Required return",
        "ui.hero.ke_annual": "Ke per year",
        "ui.hero.risk_prefix": "Risk:",
        "ui.footer.tagline": "Know the past to anticipate the future.",
        "ui.footer.disclaimer": "Educational prototype. Indicative data, not updated in real time.",
        "ui.footer.not_advice": "Not investment advice · Figures are sourced from the GeoCapital database.",
        "ui.footer.ai_line": "The AI explains the data, it does not invent it.",
        "ui.bars.head": "{score}/100 · weight {pct}%",
        "ui.bars.contribution": "Contribution to score: {points} pts out of {max}",
        # Living map (views/map_page.py)
        "map.hero.title": "Living map · 10 countries · 3 profiles",
        "map.hero.subtitle": "Understand the past. Measure risk. Decide.",
        "map.hero.text": "Click a country, read its history in three minutes, then watch its indicators become a financial decision. The score changes with your risk tolerance.",
        "map.hero.chip1": "Past → present → decision",
        "map.hero.chip2": "Sourced data",
        "map.hero.chip3": "Explanatory AI",
        "map.kpi.countries": "countries covered",
        "map.kpi.countries_desc": "From the safest to the most fragile",
        "map.kpi.best": "best score",
        "map.kpi.median": "median required return",
        "map.kpi.median_desc": "Country risk premium included",
        "map.kpi.positive": "positive verdicts",
        "map.kpi.positive_desc": "Invest or invest with caution",
        "map.profile.radio": "Your investor profile",
        "map.profile.help": "The score is not absolute: it depends on what you are looking for.",
        "map.metric.radio_label": "Displayed indicator",
        "map.metric.attractivite": "Attractiveness",
        "map.metric.risque": "Controlled risk",
        "map.metric.croissance": "Growth",
        "map.metric.devise": "Currency stability",
        "map.metric_desc.attractivite": "GeoCapital score",
        "map.metric_desc.risque": "Higher = lower risk",
        "map.metric_desc.croissance": "Economic momentum",
        "map.metric_desc.devise": "Currency stability score",
        "map.chip_profile": "{profile} profile · {pct}% growth",
        "map.section.world": "The world seen through risk",
        "map.caption.mvp": "Only the 10 MVP countries are colored. Grey countries are not rated in this version.",
        "map.zoom.hint": "Select a country to zoom the map in and display its summary.",
        "map.selected.eyebrow": "Selected country",
        "map.card.score": "Score {value}/100",
        "map.card.ke": "Ke {value}%",
        "map.card.risk": "Risk {value}/100",
        "map.btn.reset": "Back to the world view",
        "map.card.eyebrow": "Reading grid",
        "map.chip.growth": "Growth {pct}%",
        "map.chip.stability": "Stability {pct}%",
        "map.chip.solvency": "Solvency {pct}%",
        "map.section.top": "Top rated",
        "map.section.top_sub": "for this profile",
        "map.note.score": "The score measures relative attractiveness. It is no substitute for due diligence or personalised advice.",
        "map.section.explore": "Zoom in on a country",
        "map.section.explore_sub": "click to zoom in and display the summary",
        "map.expander.risk_return": "View the risk / return map",
        "map.riskret.hint": "The further right a country is, the higher its risk. The higher it is, the more return the investor demands. The bubble size represents the GeoCapital score.",
        "map.riskret.xaxis": "Country risk (0 = low, 100 = very high)",
        "map.riskret.yaxis": "Required return Ke (%)",
        "map.hover.risk": "Risk:",
        "map.hover.ke": "Required return:",
        "map.hover.score": "GeoCapital score:",
        "map.hover.score_short": "Score:",
        "map.hover.verdict": "Verdict:",
        "map.ai.caption": "AI mode enabled: optional analyses use only the data from the GeoCapital database.",
        "map.callout.ke": "The required return is not a performance forecast. It is the minimum return a rational investor should demand to accept this level of risk. A country can offer strong potential and remain risky: that is exactly why the score and the verdict should be read together.",
        # Country profile (views/country_page.py)
        "country.select": "Choose a country",
        "country.profile_radio": "Investor profile",
        "country.error": "Country not found.",
        "country.action.compare": "Compare",
        "country.chip.rank": "Rank {rank}/10 · profile {profile}",
        "country.risk_line": "Rank {rank}/10 · profile {profile} · risk {value}/100 ({label})",
        "country.updated": "Last data update:",
        "country.tab.story": "Story & institutions",
        "country.tab.dashboard": "Dashboard",
        "country.tab.score": "Score & verdict",
        "country.tab.quiz": "Quiz",
        "country.section.timeline": "Historical timeline",
        "country.section.timeline_sub": "the dates that explain today's risk",
        "country.hero_to_risk": "From past to risk",
        "country.story_in_numbers": "This story can be read in the numbers",
        "country.story_paragraph": "The past weighs on solvency ({solv}/100), stability ({stab}/100) and institutional quality ({inst}/100). This is the chain the score turns into a decision.",
        "country.section.relations": "Relations & dependencies",
        "country.section.relations_sub": "allies, rivals, points of fragility",
        "country.rel.allies": "Allies",
        "country.rel.rivals": "Rivals",
        "country.rel.dependencies": "Dependencies",
        "country.section.decision": "What weighs on the decision",
        "country.section.decision_sub": "strengths, risks and entry points",
        "country.eyebrow.strengths": "Strengths",
        "country.eyebrow.risks": "Risks",
        "country.eyebrow.opportunities": "Opportunities",
        "country.section.indicators": "The 11 indicators",
        "country.section.indicators_sub": "green, amber or red",
        "country.dash.hint": "Every indicator is dated and sourced. The color is a GeoCapital reading grid, not a real-time market opinion.",
        "dash.source_missing": "Source not provided",
        "fresh.as_of": "Data as of {as_of}",
        "fresh.stale_note": "⚠ = observation predating {limit}: the retained value remains the most recent confirmed one, to be refreshed as soon as a reliable source allows it.",
        "fresh.verdict_dates": "The composite verdict rests on the observations above; oldest retained: {oldest} vintage.",
        "country.callout.missing": "Here, a missing data point is not an empty cell: it is a risk signal. With no active rating and no quoted CDS, the market cannot price the debt reliably. GeoCapital therefore blocks the “Invest” verdict.",
        "country.section.pricerisk": "The price of risk",
        "country.section.pricerisk_sub": "Damodaran formula",
        "country.kpi.risk_free": "Risk-free rate",
        "country.kpi.risk_free_desc": "Reference: 10-year US Treasury",
        "country.kpi.erp": "Mature market premium",
        "country.kpi.erp_desc": "Equities vs bonds, Damodaran",
        "country.kpi.crp": "Country risk premium",
        "country.kpi.crp_desc": "Computed from {source}",
        "country.kpi.ke": "Required return Ke",
        "country.kpi.ke_desc": "Minimum rate to accept this risk",
        "country.howto.eyebrow": "How to read",
        "country.howto.title": "Ke = risk-free rate + beta × market premium + country premium",
        "country.howto.text": "For {name}, the computation gives {rf} % + 1.0 × {erp} % + {crp} % = <strong style='color:#e6b86b'>{ke} %</strong>. The higher the perceived risk, the more return the investor must demand. This is not a promised return: it is a required break-even threshold.",
        "country.sources.caption": "Sources: IMF, central banks, rating agencies, CDS market, Damodaran. Rounded and indicative data.",
        "country.reasons.eyebrow": "The 3 reasons behind the verdict",
        "country.ke.eyebrow": "Required return",
        "country.ke.annual": "Ke per year",
        "country.ke.line": "Risk-free rate {rf} % + mature premium {erp} % + country premium {crp} % ({source}).",
        "country.breakdown.eyebrow": "Transparent breakdown",
        "country.breakdown.title": "Five building blocks, one decision",
        "country.by_profile.eyebrow": "By profile",
        "country.by_profile.text": "The same country does not suit everyone. The profile weights growth, stability and solvency differently.",
        "country.vigilance.callout": "Main watch point: {component} ({value}/100). The score is a comparison tool, not a forecast. A high grade can hide a brutal political risk.",
        "inst.card_title": "Institutions & power",
        "inst.regime": "Regime",
        "inst.executive": "Executive",
        "inst.legislature": "Legislature",
        "inst.central_bank": "Central bank",
        "inst.currency": "Currency",
        "inst.law": "Legal framework",
        "inst.fact": "Key takeaway",
        "ai.expander": "Go deeper with AI",
        "ai.editorial_caption": "Editorial mode: the GeoCapital synthesis above works without AI. To enable generative analysis, add `OPENROUTER_API_KEY` to the .env file or Streamlit secrets. The AI only receives the validated data of this profile.",
        "ai.recaption": "The AI rephrases the facts of the profile. It creates no numbers and does not replace the sources.",
        "ai.button": "Generate the synthesis",
        "ai.spinner": "Reading the profile and writing...",
        "ai.unavailable": "The AI call did not go through. The editorial content remains available.",
        "quiz.eyebrow": "Quick quiz · 1 question",
        "quiz.radio": "Your answer",
        "quiz.button": "Validate my answer",
        "quiz.warn_none": "Choose an answer before validating.",
        "quiz.success": "Correct answer. You can mark this country as understood.",
        "quiz.error": "Not quite. Read the explanation, then try again.",
        "quiz.why": "Why?",
        "quiz.ai_button": "Explain with AI",
        "quiz.ai_spinner": "Explanation...",
        "quiz.ai_hint": "Tip: the explanation above is editorial and verified. The AI can rephrase it if an API key is configured.",
        "quiz.chip_done": "Quiz passed",
        # Comparator (views/comparator_page.py)
        "comp.eyebrow": "Comparator · 2 to 3 countries",
        "comp.title": "Two histories, two risks, two prices.",
        "comp.subtitle": "Compare the trajectory, the institutions and the required return. A higher score does not automatically mean a better investment: look at what the market makes you pay too.",
        "comp.preset.usa_china": "USA vs China",
        "comp.preset.saudi_uae": "Saudi vs Emirates",
        "comp.preset.lebanon_syria": "Lebanon vs Syria",
        "comp.preset.france_japan": "France vs Japan",
        "comp.preset.morocco_sa": "Morocco vs South Africa",
        "comp.select": "Countries to compare",
        "comp.select_help": "Select 2 or 3 countries.",
        "comp.profile_radio": "Profile",
        "comp.min_two": "Select at least two countries to start the comparison.",
        "comp.ring_label": "score",
        "comp.card_ke_risk": "Ke · risk {value}/100",
        "comp.section.radar": "Risk profile",
        "comp.section.radar_sub": "the five building blocks of the score",
        "comp.section.ke": "Required return",
        "comp.section.ke_sub": "the more risk is perceived, the higher Ke goes",
        "comp.ke_note": "The required return includes credit risk, not only growth. A country can grow fast and remain expensive to finance.",
        "comp.section.table": "Compared dashboard",
        "comp.section.table_sub": "green / amber / red",
        "comp.table.indicator": "Indicator",
        "comp.section.reading": "GeoCapital reading",
        "comp.section.reading_sub": "what the comparison tells",
        "comp.reading": "With the <strong>{profile}</strong> profile, <strong>{best}</strong> gets the best score ({best_score}/100). The lowest-risk country is <strong>{safest}</strong> (risk {safest_risk}/100). The required return ranges from <strong>{ke_min}</strong> for {cheapest} to <strong>{ke_max}</strong> for {most_expensive}. The gap measures the price the market demands to accept the uncertainty.",
        "comp.export_csv": "Export to CSV",
        "comp.open_sheet": "Profile {flag}",
        "comp.callout.ke": "A high required return is not a promise of gain. It means the investor must be compensated for greater risk. If the expected return of an asset is below Ke, the rational decision is not to buy it.",
        # Decoder (views/decoder_page.py)
        "dec.eyebrow": "News decoder",
        "dec.title": "A news event is not a causality.",
        "dec.subtitle": "Choose an event. GeoCapital unfolds the chain: fact → economy → finance → winners and losers. Each step points to a concept and a historical precedent of the country.",
        "dec.country": "Country",
        "dec.no_events": "No event prepared for this country.",
        "dec.event_select": "Recent event",
        "dec.source_prefix": "Source:",
        "dec.section.chain": "The causal chain",
        "dec.section.chain_sub": "4 steps, no shortcuts",
        "dec.callout.chain": "Finance does not react to the event itself, but to what it changes in flows, rates, profits and perceived risk. That is why the same news can lift one asset and depress another.",
        "dec.expander.concepts": "The necessary concepts",
        "dec.expander.ai": "Decode with AI",
        "dec.ai.editorial_caption": "The editorial decoding above is complete and does not depend on an API. Add `OPENROUTER_API_KEY` to have the causal chain rephrased by the AI, from the same facts.",
        "dec.ai.receive": "The AI only receives the prepared event, chain and historical echo.",
        "dec.ai.button": "Generate an explanation",
        "dec.ai.spinner": "Re-reading the causal chain...",
        "dec.section.wl": "Who wins, who loses",
        "dec.section.wl_sub": "companies, assets, exposed countries",
        "dec.echo": "Historical echo · {year}",
        "dec.link.eyebrow": "Link with the country profile",
        "dec.link.chip_score": "Score {value}/100",
        "dec.link.text": "The same shock does not have the same effect depending on debt, reserves and the credibility of the central bank.",
        "dec.open_full": "Open the full profile",
        "dec.callout.reliability": "Reliability rule: every displayed figure comes from the GeoCapital database. The AI may explain, rephrase or connect, but it is not allowed to invent a data point. When a data point is missing, the decoder flags it and treats it as a risk.",
        # Portfolio (views/portfolio_page.py)
        "pf.eyebrow": "World portfolio",
        "pf.title": "€100,000, ten countries, one lesson in risk.",
        "pf.subtitle": "Allocate fictional capital across the countries. The simulator computes the weighted required return, volatility and the real effect of diversification. No order is placed, no return is guaranteed.",
        "pf.preset.defensive": "Defensive",
        "pf.preset.balanced": "Balanced",
        "pf.preset.offensive": "Offensive",
        "pf.presets_hint": "Presets are educational. Feel free to adjust each pocket afterwards.",
        "pf.section.allocation": "Your allocation",
        "pf.section.allocation_sub": "amounts in euros",
        "pf.amount_of": "Amount {name}",
        "pf.total_exact": "Entered total: €100,000 · exact allocation",
        "pf.total_normalized": "Entered total: {amount} · normalized to €100,000 for the simulation",
        "pf.total_zero": "Entered total: €0",
        "pf.reset_all": "Reset everything",
        "pf.need_amount": "Add at least one amount to start the simulation.",
        "pf.kpi.return": "Expected return",
        "pf.kpi.return_desc": "Proxy: weighted average Ke",
        "pf.kpi.volatility": "Estimated volatility",
        "pf.kpi.volatility_desc": "Annualized portfolio risk",
        "pf.kpi.diversification": "Diversification gain",
        "pf.kpi.diversification_desc": "Less volatility thanks to correlations",
        "pf.kpi.effective": "Effective countries",
        "pf.kpi.effective_desc": "HHI concentration {hhi}",
        "pf.section.chart": "Normalized allocation",
        "pf.section.chart_sub": "€100,000",
        "pf.donut.ke_mean": "Average Ke",
        "pf.section.diagnosis": "Diagnosis",
        "pf.section.diagnosis_sub": "what your allocation tells",
        "pf.commentary.empty": "No allocation: the portfolio cannot be analyzed.",
        "pf.concentration.high": "very concentrated",
        "pf.concentration.medium": "moderately concentrated",
        "pf.concentration.low": "relatively diversified",
        "pf.diversification.good": "Diversification reduces the estimated volatility versus the weighted average of the countries.",
        "pf.diversification.poor": "Diversification brings little: the chosen countries move too closely together.",
        "pf.commentary": "Your allocation is {concentration}: {top} weighs {top_weight}% of the portfolio. The weighted required return is {ke}% per year, for an estimated volatility of {vol}%. {diversification} The country contributing most to risk is {riskiest}. The portfolio is not a recommendation: it shows that return and risk are paid for together.",
        "pf.section.risk": "Contribution to risk",
        "pf.section.risk_sub": "weight × volatility",
        "pf.hover.contrib": "Approx. contribution:",
        "pf.chart.weight_vol": "Weight × volatility",
        "pf.section.detail": "Portfolio detail",
        "pf.section.detail_sub": "amounts normalized to €100,000",
        "pf.th.country": "Country",
        "pf.th.weight": "Normalized weight",
        "pf.th.amount": "Amount",
        "pf.th.ke": "Ke",
        "pf.th.vol": "Volatility",
        "pf.th.contrib": "Risk contribution",
        "pf.expander.ai": "Comment with AI",
        "pf.ai.editorial_caption": "The diagnosis above is deterministic and works without an API. Add `OPENROUTER_API_KEY` to get an educational rephrasing of this same allocation.",
        "pf.ai.receive": "The AI only receives the allocation and the computed metrics.",
        "pf.ai.button": "Generate the commentary",
        "pf.ai.spinner": "Analyzing the allocation...",
        "pf.ai.unavailable": "The AI call did not go through. The deterministic diagnosis remains available.",
        "pf.download": "Download the allocation",
        "pf.csv.country": "Country",
        "pf.csv.weight": "Weight (%)",
        "pf.csv.amount": "Amount (€)",
        "pf.csv.ke": "Ke (%)",
        "pf.csv.vol": "Volatility (%)",
        "pf.callout.limits": "Model limits: volatility is an educational estimate, correlations are simplified by country group, and the portfolio is invested in country equities without currency hedging. A real allocation must account for your horizon, your tax situation and your ability to bear a loss.",
        # Progress (views/progress_page.py)
        "pr.eyebrow": "My progress",
        "pr.title": "A mental map fills up country by country.",
        "pr.subtitle": "GeoCapital does not reward time spent: it rewards understanding. Each profile read and each quiz passed adds a country to your mental map.",
        "pr.kpi.explored": "countries explored",
        "pr.kpi.explored_desc": "{pct}% of the map",
        "pr.kpi.quiz": "quizzes passed",
        "pr.kpi.quiz_desc": "One concept per country",
        "pr.kpi.average": "average explored score",
        "pr.kpi.average_desc": "{profile} profile",
        "pr.kpi.remaining": "countries remaining",
        "pr.kpi.remaining_desc": "The next one is your choice",
        "pr.card.eyebrow": "Your mental map",
        "pr.card.title": "Overall progress",
        "pr.card.note": "Understanding a country does not mean liking it. The goal is to know why you include or exclude it.",
        "pr.section.badges": "Badges",
        "pr.section.badges_sub": "progress, not performance",
        "pr.badge.first": "First step",
        "pr.badge.curious": "Curious",
        "pr.badge.cartographer": "Cartographer",
        "pr.badge.world": "Around the world",
        "pr.badge.quiz": "Solid quizzes",
        "pr.badge_note.first": "1 country explored",
        "pr.badge_note.curious": "3 countries explored",
        "pr.badge_note.cartographer": "5 countries explored",
        "pr.badge_note.world": "10 countries explored",
        "pr.badge_note.quiz": "5 quizzes passed",
        "pr.section.countries": "The 10 countries",
        "pr.section.countries_sub": "your progress state",
        "pr.status.explored": "Explored",
        "pr.status.to_discover": "To discover",
        "pr.quiz.done": "Quiz passed",
        "pr.quiz.todo": "Quiz to take",
        "pr.quiz.to_open": "Profile to open",
        "pr.tile.score": "score {value}/100",
        "pr.btn.revisit": "Revisit",
        "pr.btn.open": "Open",
        "pr.section.next": "Next step",
        "pr.section.next_sub": "a suggestion, not an obligation",
        "pr.next.eyebrow": "To explore next",
        "pr.btn.open_full": "Open the profile",
        "pr.done_callout": "You have gone through the ten countries. Return to the profiles to compare trajectories and test the three profiles.",
        "pr.reset.expander": "Reset my progress",
        "pr.reset.caption": "This action clears only the explored countries and the quizzes of this session. The portfolio is not modified.",
        "pr.reset.confirm": "I confirm the reset.",
        "pr.reset.button": "Reset",
        "pr.callout.verdicts": "A country's grade depends on your profile. A country can be “{invest}” for a bold profile and “{wait}” for a cautious profile. Progress therefore does not measure an absolute truth, but your ability to read the risk/return trade-off.",
        # Analyst (views/analyst_page.py)
        "an.eyebrow": "Analyst",
        "an.title": "Talk to the GeoCapital database.",
        "an.subtitle": "Ask questions about a country, a verdict, the cost of capital, an event or your portfolio. Answers rely solely on the validated facts of the database and the application's deterministic calculations.",
        "an.select.topic": "Question topic",
        "an.intent.country": "Analyze a country",
        "an.intent.compare": "Compare countries",
        "an.intent.verdict": "Explain a verdict",
        "an.intent.capital": "Explain the cost of capital",
        "an.intent.event": "Understand an event",
        "an.intent.portfolio": "Analyze my portfolio",
        "an.select.country": "Country to analyze",
        "an.select.compare": "Countries to compare (2 to 4)",
        "an.select.verdict": "Verdict / cost of capital of which country?",
        "an.select.event": "Event from the decoder",
        "an.ph.country": "Choose a country…",
        "an.ph.compare": "Choose at least two countries…",
        "an.ph.event": "Choose an event…",
        "an.allocation.current": "Your current allocation: {amount} of a fictional €100,000 (set in the Portfolio tab).",
        "an.btn.clear": "Clear the conversation",
        "an.chip.facts": "● Validated facts",
        "an.chip.interpretation": "◆ AI interpretation",
        "an.chip.hypothesis": "○ Hypothesis",
        "an.chip.facts_python": "● Validated facts · Python",
        "an.facts.expander": "Validated facts sent to the model",
        "an.facts.caption": "This data comes from the GeoCapital database and the deterministic calculations (score, Ke, portfolio). The model can rely only on these.",
        "an.portfolio.empty": "Your portfolio is empty: enter amounts in the Portfolio tab so the analysis builds on your positions.",
        "an.editorial_mode": "Editorial mode: generative AI is disabled. Questions remain useful — you will get the validated facts and the database's deterministic analysis.",
        "an.spinner.model": "Querying the model...",
        "an.spinner.editorial": "Editorial analysis...",
        "an.unavailable": "AI unavailable (missing key or unreachable service). Response based only on validated data and deterministic calculations.",
        "an.prototype_caption": "Educational prototype: no personalized advice; the AI receives only the validated facts displayed above.",
        "an.input.placeholder": "E.g. “Explain France's verdict” or “What does a Fed rate cut change?”",
        "an.limit.remaining": "Questions remaining: {remaining}/{total} · per-session limit",
        "an.limit.reached": "You have used this session's {total} analyst questions. To stay restrained, the assistant works per browser session: this is neither a global account limit nor a guaranteed spending cap, and a new session resets the counter. Every other page remains accessible.",
    },
}


def current_lang() -> str:
    """Code de langue courant (store de session, défaut ``fr``)."""
    lang = st.session_state.get("lang", DEFAULT_LANG)
    return lang if lang in LANGS else DEFAULT_LANG


def set_lang(lang: str) -> None:
    """Définit la langue persistante (fallback vers ``fr`` si inconnue)."""
    st.session_state["lang"] = lang if lang in LANGS else DEFAULT_LANG


def t(key: str, **fmt: object) -> str:
    """Traduit ``key`` dans la langue courante.

    Repli : français si la clé manque dans la langue courante, à défaut la clé
    elle-même (jamais de ``KeyError``). Les ``**fmt`` utilisent ``str.format``.
    """
    lang = current_lang()
    value = STRINGS.get(lang, {}).get(key)
    if value is None:
        value = STRINGS[DEFAULT_LANG].get(key, key)
    if fmt:
        try:
            return value.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return value
    return value


def profile_key(profile_label: str) -> str:
    """Clé i18n d'un profil à partir de sa clé interne FR de scoring."""
    return PROFILE_KEYS.get(profile_label, profile_label)


# --- Localisation des données narratives (Étape 3 — Phase 3) ---
#
# Les textes FR de data/countries/*.json, data/events.json et data/meta.json
# sont traduits via des overlays EN dans data/i18n/en/ (les valeurs
# numériques, les IDs, les clés et les formules ne sont JAMAIS modifiés).
# Le repli entre overlay incomplet et valeur source reste le français :
# aucune donnée ne peut disparaître par une traduction partielle.

from pathlib import Path  # noqa: E402

_DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
_EN_DIR = _DATA_ROOT / "i18n" / "en"

_OVERLAYS: dict[str, dict[str, Any]] = {}


def _overlay(name: str) -> dict[str, Any]:
    """Charge (une seule fois) l'overlay EN ``data/i18n/en/<name>.json``."""
    if name not in _OVERLAYS:
        path = _EN_DIR / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        _OVERLAYS[name] = data
    return _OVERLAYS[name]


def _is_en() -> bool:
    return current_lang() == "en"


def _apply_overlay(source: Any, overlay: Any) -> Any:
    """Fusionne récursivement overlay et source ; l'overlay gagne.

    - dict: clés de l'overlay appliquées, les autres conservées.
    - list: remplacée en bloc uniquement si l'overlay fournit la même
      longueur (traduction complète ou rien — jamais une liste à moitié).
    - scalaires : une chaîne de l'overlay remplace une chaîne de la source ;
      les valeurs numériques et les clés ne passent jamais par l'overlay
      (traduction interdite), la source est conservée.
    """
    if isinstance(source, dict):
        overlay = overlay if isinstance(overlay, dict) else {}
        out = {}
        for key, value in source.items():
            out[key] = _apply_overlay(value, overlay.get(key))
        return out
    if isinstance(source, list):
        if isinstance(overlay, list) and len(overlay) == len(source):
            return [_apply_overlay(item, trans) for item, trans in zip(source, overlay)]
        return [_apply_overlay(item, None) for item in source]
    # Scalars : seule une chaîne de l'overlay peut remplacer une chaîne de la source.
    if isinstance(source, str) and isinstance(overlay, str) and overlay.strip():
        return overlay
    return source


def localize_country(country: dict[str, Any]) -> dict[str, Any]:
    """Copie traduite d'une fiche pays (aucune donnée numérique modifiée).

    En français : renvoie la fiche source sans copie (chemin zéro coût)."""
    if not _is_en():
        return country
    translated = _apply_overlay(country, _overlay(f"{country.get('id')}.json"))
    return translated if isinstance(translated, dict) else country


def localize_countries(countries_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Liste de fiches pays localisées (identiques en FR)."""
    return [localize_country(c) for c in countries_list]


def localize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Copie traduite d'un événement du décodeur (champs éditoriaux)."""
    if not _is_en():
        return event
    translated = _apply_overlay(event, _overlay("events.json").get(event.get("id", "")))
    return translated if isinstance(translated, dict) else event


def localize_events(events_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Liste d'événements localisés (identiques en FR)."""
    return [localize_event(e) for e in events_list]


def localize_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """Copie traduite de meta.json (libellés de sources et de méthode)."""
    if not _is_en():
        return meta
    return _apply_overlay(meta, _overlay("meta.json"))


def indicator_label(key: str) -> str:
    """Libellé affiché d'un indicateur (clé interne de data.INDICATOR_ORDER)."""
    return t(f"ind.{key}")


def display_label(fr_label: str) -> str:
    """Traduit un libellé FR issu des données (INDICATOR_LABELS, verdicts…) ; repli FR."""
    return t(f"lbl.{fr_label}")


def country_name(country_id: str) -> str:
    """Nom affiché d'un pays par ID (traduit en EN, sans charger plus de données)."""
    from geocapital.data import country_by_id

    local = country_by_id(country_id)
    if not local:
        return country_id
    return str(localize_country(local).get("name", country_id))


def event_name(event_id: str) -> str:
    """Libellé affiché d'un événement du décodeur par ID."""
    from geocapital.data import load_events

    local = next((e for e in load_events() if e.get("id") == event_id), None)
    if not local:
        return event_id
    local = localize_event(local)
    return f"{local.get('date', '')} · {local.get('title', '')}".strip(" ·")


# Libellés des étiquettes FR affichées, traduits via des clés lbl.* (les
# deux langues contiennent les mêmes clés, garantie par les tests de parité).
STRINGS["fr"].update({
    "ind.gdp_growth": "Croissance du PIB",
    "ind.inflation": "Inflation",
    "ind.debt_gdp": "Dette publique / PIB",
    "ind.policy_rate": "Taux directeur",
    "ind.unemployment": "Chômage",
    "ind.reserves": "Réserves de change",
    "ind.rating": "Notation souveraine",
    "ind.cds": "CDS 5 ans",
    "ind.crp": "Prime de risque pays",
    "ind.equity_index": "Indice boursier",
    "ind.currency": "Devise",
})
STRINGS["en"].update({
    "ind.gdp_growth": "GDP growth",
    "ind.inflation": "Inflation",
    "ind.debt_gdp": "Public debt / GDP",
    "ind.policy_rate": "Policy rate",
    "ind.unemployment": "Unemployment",
    "ind.reserves": "FX reserves",
    "ind.rating": "Sovereign rating",
    "ind.cds": "5y CDS",
    "ind.crp": "Country risk premium",
    "ind.equity_index": "Equity index",
    "ind.currency": "Currency",
})
# Libellés FR issus des données (data.INDICATOR_LABELS) traduits via lbl.*.
STRINGS["fr"].update({
    "lbl.Croissance du PIB": "Croissance du PIB",
    "lbl.Inflation": "Inflation",
    "lbl.Dette publique / PIB": "Dette publique / PIB",
    "lbl.Taux directeur": "Taux directeur",
    "lbl.Chômage": "Chômage",
    "lbl.Réserves de change": "Réserves de change",
    "lbl.Notation souveraine": "Notation souveraine",
    "lbl.CDS 5 ans": "CDS 5 ans",
    "lbl.Prime de risque pays": "Prime de risque pays",
    "lbl.Indice boursier": "Indice boursier",
    "lbl.Devise": "Devise",
    "lbl.Non coté": "Non coté",
    # Valeurs FR de data.INDICATOR_LABELS affichées (tableaux, CSV) : clés
    # identiques dans les deux langues, garantie par les tests de parité.
    "comp.csv.indicator": "Indicateur",
    "ind.crp.note": "Prime exigée pour détenir le risque souverain, au-delà du risque de marché mature.",
})
STRINGS["en"].update({
    "lbl.Croissance du PIB": "GDP growth",
    "lbl.Inflation": "Inflation",
    "lbl.Dette publique / PIB": "Public debt / GDP",
    "lbl.Taux directeur": "Policy rate",
    "lbl.Chômage": "Unemployment",
    "lbl.Réserves de change": "FX reserves",
    "lbl.Notation souveraine": "Sovereign rating",
    "lbl.CDS 5 ans": "5y CDS",
    "lbl.Prime de risque pays": "Country risk premium",
    "lbl.Indice boursier": "Equity index",
    "lbl.Devise": "Currency",
    "lbl.Non coté": "Not quoted",
    # Valeurs FR de data.INDICATOR_LABELS affichées (tableaux, CSV) : clés
    # identiques dans les deux langues, garantie par les tests de parité.
    "comp.csv.indicator": "Indicator",
    "ind.crp.note": "Premium required to hold sovereign risk, on top of mature market risk.",
})

# ---------------------------------------------------------------------------
# Sovereign Risk Lab (Priorité 8 — phase 2) : libellés du lab de risque
# souverain. Le dictionnaire français est la source de repli.
# ---------------------------------------------------------------------------
STRINGS["fr"].update({
    "nav.risk_lab": "Lab risque souverain",
    "rl.eyebrow": "Lab risque souverain",
    "rl.title": "La dette se lit avec ses angles morts.",
    "rl.subtitle": "Analyse souveraine approfondie : durabilité fiscale, vulnérabilité externe, conditions macro-financières. Chaque indicateur est daté, sourcé et honnête sur ses limites — une donnée indisponible est dite indisponible, jamais remplacée par zéro.",
    "rl.select": "Pays analysé",
    "rl.section.fiscal": "Durabilité fiscale",
    "rl.section.fiscal_sub": "dette publique, solde budgétaire, charge des intérêts",
    "rl.section.external": "Vulnérabilité externe",
    "rl.section.external_sub": "balance courante, dette externe, réserves de change",
    "rl.section.macro": "Conditions macro-financières",
    "rl.section.macro_sub": "croissance, inflation, taux directeur et taux réel",
    "rl.metric.fiscal_balance": "Solde budgétaire (ou primaire)",
    "rl.metric.interest_revenue": "Paiements d'intérêts / recettes",
    "rl.metric.current_account": "Balance courante",
    "rl.metric.external_debt_total": "Dette externe (totale)",
    "rl.metric.external_debt_short": "Dette externe court terme",
    "rl.metric.reserves_import_months": "Réserves en mois d'importations",
    "rl.metric.real_rate": "Taux réel (directeur − inflation)",
    "rl.why.fiscal_balance": "Le solde budgétaire (ou primaire) mesure l'effort fiscal annuel : sans lui, impossible de dire si la dette se stabilise ou dérive.",
    "rl.why.interest_revenue": "Le ratio intérêts/recettes mesure le poids du service de la dette sur le budget : au-delà d'un seuil critique, la soutenabilité devient fragile.",
    "rl.why.current_account": "La balance courante indique si le pays vit au-dessus ou en dessous de ses moyens : un déficit durable financé par la dette externe fragilise la devise.",
    "rl.why.external_debt_total": "La dette vis-à-vis du reste du monde expose au risque de change et aux arrêts de financement ; la dette publique seule ne la capture pas.",
    "rl.why.external_debt_short": "La part court terme de la dette externe mesure la vulnérabilité aux arrêts soudains de financement.",
    "rl.why.reserves_import_months": "Réserves ÷ importations mensuelles : le coussin classique de résilience externe. Les réserves en Mds $ seules ne permettent pas de le calculer.",
    "rl.need.fiscal_balance": "Source requise : FMI WEO (solde recettes-dépenses, % du PIB) ou trésorerie nationale, avec millésime explicite.",
    "rl.need.interest_revenue": "Source requise : statistiques de finances publiques (FMI GFS) ou budget voté — intérêts payés et recettes totales, même millésime.",
    "rl.need.current_account": "Source requise : balance des paiements (FMI BOP), balance courante en % du PIB, avec millésime.",
    "rl.need.external_debt_total": "Source requise : base de la dette externe de la Banque mondiale (IDS), encours total en % du PIB.",
    "rl.need.external_debt_short": "Source requise : Banque mondiale IDS, dette externe à moins d'un an, avec millésime.",
    "rl.need.reserves_import_months": "Source requise : importations de biens et services (Mds $, même période et devise que les réserves) — ex. WDI TM.VAL.MRCH.CD.",
    "rl.badge.derived": "Calculé (dérivé)",
    "rl.badge.observed": "Observation sourcée",
    "rl.chip.estimated": "Estimation",
    "rl.chip.conflicting": "Sources divergentes",
    "rl.q.observed": "observation sourcée",
    "rl.q.estimated": "estimation de la source — valeur à manier comme un ordre de grandeur",
    "rl.q.conflicting": "sources institutionnelles divergentes",
    "rl.q.stale": "millésime antérieur au seuil de fraîcheur ({limit})",
    "rl.q.unverified": "provenance non documentée observation par observation",
    "rl.warn.vintage_mismatch": "Taux réel calculé à partir d'observations d'années différentes (taux {policy_period}, inflation {inflation_period}) : à lire comme un ordre de grandeur, non comme une mesure alignée.",
    "rl.real.title": "Taux réel et paliers du modèle",
    "rl.real.sub": "taux réel = taux directeur − inflation ; lecture dans les paliers existants du moteur (aucun re-paramétrage)",
    "rl.real.aligned": "Millésimes alignés ({year}) : les deux observations portent sur la même période.",
    "rl.real.band_label": "Palier",
    "rl.real.outside_label": "Hors paliers",
    "rl.real.xaxis": "Taux réel (%)",
    "rl.real.kpi.policy": "Taux directeur",
    "rl.real.kpi.inflation": "Inflation",
    "rl.real.kpi.real": "Taux réel",
    "rl.real.kpi.bandscore": "Score du palier",
    "rl.dsa.title": "Lecture de durabilité de la dette",
    "rl.dsa.sub": "ce que les données disponibles permettent — et ne permettent pas — de conclure",
    "rl.dsa.position.below_low": "sous la borne basse du palier de scoring ({low}–{high} % du PIB)",
    "rl.dsa.position.within": "dans le palier de scoring ({low}–{high} % du PIB)",
    "rl.dsa.position.above_high": "au-dessus de la borne haute du palier de scoring ({low}–{high} % du PIB)",
    "rl.dsa.band_note": "Palier existant du scoring (solvabilité) : {low}–{high} % du PIB. Lecture indicative uniquement : le score reste calculé par le moteur, inchangé.",
    "rl.dsa.limitation": "Analyse complète de durabilité non présentée : il manque {count} entrée(s) requise(s). Une DSA exige au minimum le solde budgétaire (ou primaire), la charge d'intérêts rapportée aux recettes et la trajectoire de croissance — voir la section « Indicateurs non disponibles » ci-dessus.",
    "rl.dsa.growth_line": "Croissance disponible pour la trajectoire : {growth} % ({period}) — insuffisante à elle seule pour une DSA.",
    "rl.summary.title": "Synthèse analytique",
    "rl.summary.sub": "fondée uniquement sur les données disponibles ci-dessus",
    "rl.summary.debt": "Dette publique : {value} % du PIB ({period}) — {position}.",
    "rl.summary.reserves": "Réserves de change : {value} Mds $ ({period}).",
    "rl.summary.macro": "Croissance {growth} % · inflation {inflation} % (millésime {period}).",
    "rl.summary.real": "Taux réel : {value} % — {band_note}",
    "rl.summary.real_band": "dans le palier [{low} ; {high}] (score {score}/100).",
    "rl.summary.real_outside": "hors des paliers documentés du modèle.",
    "rl.comp.section": "Comparaison entre pays",
    "rl.comp.section_sub": "métriques disponibles côte à côte ; les indisponibilités restent visibles",
    "rl.comp.select": "Pays à comparer",
    "rl.comp.select_help": "Sélectionnez 2 à 4 pays.",
    "rl.comp.min_two": "Sélectionnez au moins deux pays pour lancer la comparaison.",
    "rl.comp.chart_metric": "Métrique affichée",
    "rl.comp.no_data": "Aucun pays sélectionné ne dispose de cette métrique.",
    "rl.comp.legend": "e = estimation de la source · d = sources divergentes · m = millésimes mélangés",
    "rl.real.unavailable": "Taux directeur ou inflation indisponible : le taux réel ne peut pas être calculé pour ce pays.",
    "rl.details.title": "Détails des données",
    "rl.details.sub": "provenance, millésimes et statuts de validation, indicateur par indicateur",
    "rl.details.period": "Période",
    "rl.details.source": "Source",
    "rl.details.status": "Statut",
    "rl.details.as_of": "data_as_of = {as_of} : date de consultation de la base, qui ne garantit pas l'actualité de chaque observation sous-jacente.",
    "rl.method.title": "Formules, hypothèses et limites",
    "rl.method.real_rate": "Taux réel = taux directeur − inflation. C'est la même convention que le moteur de scoring (scoring.component_scores). Le calcul combine les millésimes des deux indicateurs : quand ils diffèrent (ex. Liban 2024 × 2025), un avertissement explicite est affiché et le résultat doit se lire comme un ordre de grandeur.",
    "rl.method.bands": "Paliers du taux réel : {bands} (score {outside} si hors paliers). Ces paliers viennent de la configuration existante du scoring — ils ne sont ni re-définis ni re-calibrés ici.",
    "rl.method.debt": "Dette : position par rapport au palier de solvabilité existant ({low}–{high} % du PIB). Aucune projection de dette, aucun différentiel croissance-taux : ces calculs exigent le solde budgétaire et la charge d'intérêts, indisponibles dans la base v1.",
    "rl.method.reserves": "Réserves : valeur sourcée de la fiche (Mds $). Attention brut vs net : les réserves libanaises sont nettes et documentées comme telles. La couverture en mois d'importations n'est calculée que si des importations compatibles (période/devise) existent — pas le cas aujourd'hui.",
    "rl.method.caveat": "Fraîcheur : les observations dont le millésime est antérieur à {limit} sont signalées dans les « Détails des données ». Les statuts d'estimation et de conflit proviennent de l'audit qualité (docs/DATA_QUALITY_AUDIT.md). data_as_of = {as_of} : date de consultation, qui ne garantit pas l'actualité de chaque observation sous-jacente.",
    "rl.method.assumption": "Hypothèses explicites : aucune valeur manquante n'est traitée comme zéro ; aucune donnée n'est inventée ; les calculs du lab n'influencent ni le score ni le verdict de la fiche pays.",
    "rl.missing.title": "Indicateurs non disponibles dans la base actuelle",
    "rl.missing.sub": "l'analyse s'appuie sur les indicateurs disponibles ; chaque absence est explicite, jamais remplacée par zéro ni estimée",
    "rl.missing.count": "{count} indicateur(s) requis pour une analyse complète ne sont pas couverts par la base : pour chacun, son importance analytique et la source qui le documenterait.",
    "rl.missing.section_empty": "Aucun indicateur disponible dans cette section pour l'instant — voir la section « Indicateurs non disponibles ».",
    "rl.missing.th.why": "Pourquoi c'est important",
    "rl.missing.th.source": "Source requise",
    "me.risklab.title": "Lab risque souverain",
    "me.risklab.sub": "l'analyse approfondie et ses règles",
    "me.risklab.body": "Le lab approfondit la lecture du risque souverain sur trois blocs : durabilité fiscale (dette publique, solde budgétaire, charge d'intérêts), vulnérabilité externe (balance courante, dette externe, réserves) et conditions macro-financières (croissance, inflation, taux directeur et taux réel). Le taux réel est le seul calcul dérivé : taux directeur − inflation, dans les paliers existants du scoring — quand les deux millésimes diffèrent (ex. Liban 2024 × 2025), un avertissement est affiché. Les indicateurs absents de la base (solde budgétaire, intérêts/recettes, balance courante, dette externe, mois d'importations) sont affichés comme indisponibles avec leur source requise : ils ne sont jamais remplacés par zéro ni par une estimation. Tant que ces entrées manquent, aucune analyse complète de durabilité de la dette n'est présentée — la limite est expliquée à la place. Les statuts de fraîcheur, d'estimation et de conflit proviennent de l'audit qualité ; les calculs du lab n'influencent ni le score ni le verdict.",
    "me.risklab.caption": "Détail des formules et hypothèses : onglet « Lab risque souverain », section Formules, hypothèses et limites.",
})
STRINGS["en"].update({
    "nav.risk_lab": "Sovereign Risk Lab",
    "rl.eyebrow": "Sovereign Risk Lab",
    "rl.title": "Debt is read through its blind spots.",
    "rl.subtitle": "Deeper sovereign analysis: fiscal sustainability, external vulnerability, macro-financial conditions. Every indicator is dated, sourced, and honest about its limits — an unavailable datum is stated as unavailable, never replaced by zero.",
    "rl.select": "Country analysed",
    "rl.section.fiscal": "Fiscal sustainability",
    "rl.section.fiscal_sub": "public debt, fiscal balance, interest burden",
    "rl.section.external": "External vulnerability",
    "rl.section.external_sub": "current account, external debt, FX reserves",
    "rl.section.macro": "Macro-financial conditions",
    "rl.section.macro_sub": "growth, inflation, policy rate and real rate",
    "rl.metric.fiscal_balance": "Fiscal (or primary) balance",
    "rl.metric.interest_revenue": "Interest payments / revenue",
    "rl.metric.current_account": "Current-account balance",
    "rl.metric.external_debt_total": "External debt (total)",
    "rl.metric.external_debt_short": "Short-term external debt",
    "rl.metric.reserves_import_months": "Reserves in months of imports",
    "rl.metric.real_rate": "Real rate (policy − inflation)",
    "rl.why.fiscal_balance": "The fiscal (or primary) balance measures the annual fiscal effort: without it, there is no way to tell whether debt is stabilising or drifting.",
    "rl.why.interest_revenue": "The interest-to-revenue ratio measures the weight of debt service on the budget: beyond a critical threshold, sustainability becomes fragile.",
    "rl.why.current_account": "The current account shows whether a country lives within its means: a lasting deficit financed by external debt weakens the currency.",
    "rl.why.external_debt_total": "Debt owed to the rest of the world exposes the country to FX risk and funding stops; public debt alone does not capture it.",
    "rl.why.external_debt_short": "The short-term share of external debt measures vulnerability to sudden stops in funding.",
    "rl.why.reserves_import_months": "Reserves ÷ monthly imports: the classic external-resilience cushion. Reserves in $bn alone are not enough to compute it.",
    "rl.need.fiscal_balance": "Source required: IMF WEO (revenue-expenditure balance, % of GDP) or national treasury, with an explicit vintage.",
    "rl.need.interest_revenue": "Source required: public-finance statistics (IMF GFS) or the voted budget — interest paid and total revenue, same vintage.",
    "rl.need.current_account": "Source required: balance of payments (IMF BOP), current account in % of GDP, with a vintage.",
    "rl.need.external_debt_total": "Source required: World Bank International Debt Statistics, total stock in % of GDP.",
    "rl.need.external_debt_short": "Source required: World Bank IDS, external debt under one year, with a vintage.",
    "rl.need.reserves_import_months": "Source required: imports of goods and services ($bn, same period and currency as reserves) — e.g. WDI TM.VAL.MRCH.CD.",
    "rl.badge.derived": "Derived calculation",
    "rl.badge.observed": "Sourced observation",
    "rl.chip.estimated": "Estimated",
    "rl.chip.conflicting": "Diverging sources",
    "rl.q.observed": "sourced observation",
    "rl.q.estimated": "source-declared estimate — value to read as an order of magnitude",
    "rl.q.conflicting": "institutional sources diverge",
    "rl.q.stale": "vintage older than the freshness threshold ({limit})",
    "rl.q.unverified": "no per-observation provenance documented",
    "rl.warn.vintage_mismatch": "Real rate computed from observations of different years (rate {policy_period}, inflation {inflation_period}): read it as an order of magnitude, not an aligned measure.",
    "rl.real.title": "Real rate and model bands",
    "rl.real.sub": "real rate = policy rate − inflation; read against the engine's existing bands (no re-parametrisation)",
    "rl.real.aligned": "Aligned vintages ({year}): both observations cover the same period.",
    "rl.real.band_label": "Band",
    "rl.real.outside_label": "Outside bands",
    "rl.real.xaxis": "Real rate (%)",
    "rl.real.kpi.policy": "Policy rate",
    "rl.real.kpi.inflation": "Inflation",
    "rl.real.kpi.real": "Real rate",
    "rl.real.kpi.bandscore": "Band score",
    "rl.dsa.title": "Debt-sustainability reading",
    "rl.dsa.sub": "what the available data allows — and does not allow — to conclude",
    "rl.dsa.position.below_low": "below the low end of the scoring band ({low}–{high} % of GDP)",
    "rl.dsa.position.within": "within the scoring band ({low}–{high} % of GDP)",
    "rl.dsa.position.above_high": "above the high end of the scoring band ({low}–{high} % of GDP)",
    "rl.dsa.band_note": "Existing scoring band (solvency): {low}–{high} % of GDP. Indicative reading only: the score remains computed by the engine, unchanged.",
    "rl.dsa.limitation": "No complete debt-sustainability analysis is presented: {count} required input(s) are missing. A DSA needs at least the fiscal (or primary) balance, interest payments relative to revenue, and a growth trajectory — see the « Indicators not covered » section above.",
    "rl.dsa.growth_line": "Growth available for the trajectory: {growth} % ({period}) — not sufficient on its own for a DSA.",
    "rl.summary.title": "Analytical summary",
    "rl.summary.sub": "grounded only in the available data above",
    "rl.summary.debt": "Public debt: {value} % of GDP ({period}) — {position}.",
    "rl.summary.reserves": "FX reserves: {value} $bn ({period}).",
    "rl.summary.macro": "Growth {growth} % · inflation {inflation} % (vintage {period}).",
    "rl.summary.real": "Real rate: {value} % — {band_note}",
    "rl.summary.real_band": "inside the [{low} ; {high}] band (score {score}/100).",
    "rl.summary.real_outside": "outside the model's documented bands.",
    "rl.comp.section": "Cross-country comparison",
    "rl.comp.section_sub": "available metrics side by side; unavailability stays visible",
    "rl.comp.select": "Countries to compare",
    "rl.comp.select_help": "Select 2 to 4 countries.",
    "rl.comp.min_two": "Select at least two countries to start the comparison.",
    "rl.comp.chart_metric": "Displayed metric",
    "rl.comp.no_data": "No selected country has this metric.",
    "rl.comp.legend": "e = source-declared estimate · d = diverging sources · m = mixed vintages",
    "rl.real.unavailable": "Policy rate or inflation unavailable: the real rate cannot be computed for this country.",
    "rl.details.title": "Data details",
    "rl.details.sub": "provenance, vintages and validation status, indicator by indicator",
    "rl.details.period": "Period",
    "rl.details.source": "Source",
    "rl.details.status": "Status",
    "rl.details.as_of": "data_as_of = {as_of}: the database retrieval date, which does not guarantee every underlying observation is current.",
    "rl.method.title": "Formulas, assumptions and limitations",
    "rl.method.real_rate": "Real rate = policy rate − inflation. This is the same convention as the scoring engine (scoring.component_scores). The calculation combines the vintages of the two indicators: when they differ (e.g. Lebanon 2024 × 2025), an explicit warning is displayed and the result should be read as an order of magnitude.",
    "rl.method.bands": "Real-rate bands: {bands} (score {outside} when outside all bands). These bands come from the existing scoring configuration — they are neither redefined nor recalibrated here.",
    "rl.method.debt": "Debt: position relative to the existing solvency band ({low}–{high} % of GDP). No debt projections, no growth-rate differential: those calculations require the fiscal balance and the interest burden, both unavailable in the v1 database.",
    "rl.method.reserves": "Reserves: sourced value from the country file ($bn). Mind gross vs net: Lebanon's reserves are net and documented as such. The months-of-imports coverage is computed only if compatible imports (period/currency) exist — not the case today.",
    "rl.method.caveat": "Freshness: observations with a vintage earlier than {limit} are flagged in « Data details ». Estimated/conflict statuses come from the data-quality audit (docs/DATA_QUALITY_AUDIT.md). data_as_of = {as_of}: a retrieval date, which does not guarantee every underlying observation is current.",
    "rl.method.assumption": "Explicit assumptions: no missing value is treated as zero; no data is invented; the lab's calculations influence neither the score nor the verdict of the country page.",
    "rl.missing.title": "Indicators not covered by the current database",
    "rl.missing.sub": "the analysis relies on the indicators available; every gap is explicit, never replaced by zero or estimated",
    "rl.missing.count": "{count} indicator(s) required for a full analysis are not covered by the database: for each, its analytical importance and the source that would document it.",
    "rl.missing.section_empty": "No indicator is available in this section yet — see the « Indicators not covered » section.",
    "rl.missing.th.why": "Why it matters",
    "rl.missing.th.source": "Required source",
    "me.risklab.title": "Sovereign Risk Lab",
    "me.risklab.sub": "the deeper analysis and its rules",
    "me.risklab.body": "The lab deepens the sovereign-risk reading across three blocks: fiscal sustainability (public debt, fiscal balance, interest burden), external vulnerability (current account, external debt, reserves) and macro-financial conditions (growth, inflation, policy rate and real rate). The real rate is the only derived calculation: policy rate − inflation, read against the engine's existing bands — when the two vintages differ (e.g. Lebanon 2024 × 2025), a warning is displayed. Indicators absent from the database (fiscal balance, interest/revenue, current account, external debt, months of imports) are shown as unavailable with the source required: they are never replaced by zero or an estimate. As long as those inputs are missing, no complete debt-sustainability analysis is presented — the limitation is explained instead. Freshness, estimated and conflict statuses come from the data-quality audit; the lab's calculations influence neither the score nor the verdict.",
    "me.risklab.caption": "Full formulas and assumptions: the « Sovereign Risk Lab » tab, section Formulas, assumptions and limitations.",
})
