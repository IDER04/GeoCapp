"""Couche de récupération et de cadrage pour l'analyste IA GeoCapital.

Toutes les données proviennent de la base locale (data/countries, data/events,
data/meta) et des fonctions déterministes de geocapital.scoring, sans
modification des formules. Ce module construit les faits validés, identifie
explicitement les données manquantes et rédige les règles d'interprétation.
Les fonctions de base n'importent pas Streamlit, pour rester testables.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from geocapital import data, scoring

# Nombre maximal d'échanges (paire utilisateur + assistant) renvoyés à l'API.
# Les tours plus anciens restent visibles à l'écran mais ne partent plus.
MAX_EXCHANGES = 6

INTENTS = [
    ("country", "Analyse un pays"),
    ("compare", "Comparer des pays"),
    ("verdict", "Expliquer un verdict"),
    ("capital", "Expliquer le coût du capital"),
    ("event", "Comprendre un événement"),
    ("portfolio", "Analyser mon portefeuille"),
]

ANALYST_SYSTEM_RULES = """Tu es l'analyste IA de GeoCapital, application pédagogique.
Règles absolues :
- Utilise UNIQUEMENT les faits fournis dans la section « FAITS VALIDÉS » du message.
  N'invente aucun chiffre, aucune date, aucune source et aucune donnée absente.
- Les chiffres de la section FAITS VALIDÉS sont exacts et déjà calculés en
  Python : cite-les tels quels, avec leur source et leur date quand elles
  sont fournies.
- Distingue trois registres, explicitement :
  • Faits : données validées de la base, tu peux les rapporter directement.
  • Interprétation : quand tu relies deux faits fournis, commence la phrase
    par « Interprétation : ».
  • Hypothèse : quand l'utilisateur propose un scénario, commence par
    « Hypothèse : », traite-la comme une conjecture et ne la transforme
    jamais en fait établi.
- La liste « informations_manquantes » te dit ce qui n'existe pas dans la
  base : parle de « donnée non disponible » plutôt que de la deviner.
- Answer in the language of the user's question: a French question gets a
  French answer, an English question gets an English answer. In case of a
  genuine mix, use the dominant language of the question.
- Pas de conseil financier personnalisé (aucun « il faut acheter » ou
  « il faut vendre »). Si l'utilisateur demande un conseil, rappelle la
  limite pédagogique de l'outil.
- Réponse : 120 à 250 mots, paragraphes courts, ton précis et vivant.
"""

# Lumière rédactionnelle par langue de question (pas d'appel LLM de plus :
# la langue est déduite du texte de la question, cf. detect_question_language).
ANSWER_LANGUAGE_RULES = {
    "fr": "- Écris ta réponse en français clair, pour un étudiant ou un jeune investisseur.",
    "en": "- Write your answer in clear English, for a student or a young investor.",
}

# Détection de langue : indices lexicaux forts français / anglais.
# Pourquoi ces listes : fonction mots-outils quasi sans faux positifs croisés
# (jamais « the » dans une question française, jamais « quel » dans une
# question anglaise...) ; en cas de trop forte ambiguïté, la langue par
# défaut de l'application (français) l'emporte.
_QUESTION_FR_CUES = frozenset({
    "le", "la", "les", "des", "du", "un", "une", "de", "et", "est",
    "quel", "quelle", "quels", "quelles", "pourquoi", "explique",
    "expliquer", "montre", "donne", "d", "l", "qu", "ce",
})
_QUESTION_EN_CUES = frozenset({
    "what", "why", "how", "which", "when", "who", "the", "is", "are",
    "does", "would", "should", "explain", "show", "give", "compare", "my",
    "fed",
})
_ACCENT_RE = re.compile(r"[àâçéèêëîïôùûüœ«»]")
_TOKEN_RE = re.compile(r"[a-zà-ÿ']+")


def detect_question_language(question: str) -> str:
    """« fr » ou « en » selon la langue dominante de la question.

    Heuristique déterministe sans dépendance ni appel LLM : indices
    lexicaux les plus discriminants + présence d'accents français.
    Ambiguïté, mixture réelle ou question vide → « fr » (langue par
    défaut de l'application).
    """
    text = (question or "").replace("’", "'").strip().lower()
    if not text:
        return "fr"
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        tokens += [part for part in raw.split("'") if part]
    fr_hits = sum(1 for token in tokens if token in _QUESTION_FR_CUES)
    en_hits = sum(1 for token in tokens if token in _QUESTION_EN_CUES)
    if _ACCENT_RE.search(text):
        fr_hits += 2  # accent(s) français = indice fort
    if en_hits > fr_hits:
        return "en"
    return "fr"

ALIASES: dict[str, list[str]] = {
    "usa": ["etats-unis", "amerique", "eeuu", "united states", "fed"],
    "china": ["chine", "chinois", "pekin", "beijing"],
    "france": ["francais", "francaise"],
    "japan": ["japon", "tokyo", "nippone"],
    "lebanon": ["liban", "beyrouth", "beirut"],
    "morocco": ["maroc", "rabat", "bank al-maghrib"],
    "saudi": ["arabie", "riyad"],
    "south_africa": ["afrique du sud", "johannesburg", "rand"],
    "syria": ["syrie", "damas"],
    "uae": ["emirats", "dubai", "abu dhabi"],
}

EVENT_ALIASES: dict[str, list[str]] = {
    "usa-fed-cut-2024": ["baisse des taux", "abaisse ses taux"],
}

CAPITAL_LIMITATIONS = [
    "La formule Ke = taux sans risque + bêta × ERP mature + prime pays fige trois hypothèses : taux sans risque 4,20 %, ERP mature 4,50 %, bêta 1,00.",
    "Le bêta uniforme de 1,00 ignore la sensibilité sectorielle : une banque libanaise et une pétrolière saoudienne héritent du même bêta de marché.",
    "La prime de risque pays retient le maximum entre le spread de notation et le spread CDS ; quand le CDS n'est pas coté, la méthode revient à la notation seule, ce qui peut paraître plus prudent que le signal du marché.",
    "Le modèle n'intègre ni liquidité du marché, ni fiscalité de rapatriement, ni couverture de change : ce sont des limites explicites du prototype.",
]


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _match_entity(question: str, candidates: list[tuple[str, list[str]]]) -> str | None:
    normalized = _strip_accents(question)
    for entity, probes in candidates:
        for probe in probes:
            if probe in normalized:
                return entity
    return None


def detect_country(question: str) -> str | None:
    """Reconnaît un pays évoqué en français (nom ou alias usuel)."""
    candidates = []
    for country in data.countries():
        probes = [str(country["id"]).lower(), country["name"].lower()]
        probes += ALIASES.get(country["id"], [])
        candidates.append((str(country["id"]), probes))
    return _match_entity(question, candidates)


def detect_event(question: str) -> str | None:
    """Reconnaît un événement du décodeur par son titre ou un mot-clé."""
    candidates = []
    for event in data.load_events():
        probes = [str(event["id"]).lower(), str(event["title"]).lower()]
        probes += EVENT_ALIASES.get(event["id"], [])
        candidates.append((str(event["id"]), probes))
    return _match_entity(question, candidates)


def missing_indicators(country: dict[str, Any]) -> list[dict[str, str]]:
    """Liste explicite des indicateurs indisponibles pour un pays."""
    missing: list[dict[str, str]] = []
    for key in data.INDICATOR_ORDER:
        meta = data.indicator_meta(country, key)
        value = meta.get("value")
        label = data.INDICATOR_LABELS[key]
        if key == "rating":
            if value in (None, "", "NR"):
                missing.append({"label": label, "detail": "Aucune notation attribuée (NR)."})
            continue
        if key in ("equity_index", "currency"):
            continue
        if value is None or value == "":
            missing.append(
                {
                    "label": label,
                    "detail": "Non coté / non publié dans la base GeoCapital : à traiter comme « donnée non disponible ».",
                }
            )
    return missing


def _indicator_facts(country: dict[str, Any]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for key in data.INDICATOR_ORDER:
        meta = data.indicator_meta(country, key)
        kept = {k: v for k, v in meta.items() if k in ("value", "unit", "date", "agency")}
        if kept.get("value") not in (None, ""):
            facts[data.INDICATOR_LABELS[key]] = kept
    return facts


def payload_country(country: dict[str, Any], profile: str = "Équilibré") -> dict[str, Any]:
    result = scoring.overall_score(country, profile)
    return {
        "identite": {
            key: country[key]
            for key in ("name", "official_name", "region", "group", "group_key")
            if country.get(key)
        },
        "resume_editorial": country.get("summary"),
        "chiffres_clefs": _indicator_facts(country),
        "scores_qualitatifs_explicites": country.get("qualitative", {}),
        "forces": country.get("strengths", []),
        "risques": country.get("risks", []),
        "opportunites": country.get("opportunities", []),
        "relations": country.get("relations", {}),
        "score_geo_capital": {
            "profil": profile,
            "score": result["score"],
            "composantes": result["components"],
            "ponderations": result["weights"],
            "risque_estime": result["risk"],
            "volatilite_pedagogique": result["volatility"],
            "verdict": result["verdict"],
            "raison_verdict": result["verdict_reason"],
            "rendement_exige": result["ke"],
        },
        "informations_manquantes": missing_indicators(country),
    }


def payload_comparison(countries: list[dict[str, Any]], profile: str = "Équilibré") -> dict[str, Any]:
    rows = []
    for country in countries:
        result = scoring.overall_score(country, profile)
        rows.append(
            {
                "pays": country["name"],
                "groupe": country.get("group"),
                "score": result["score"],
                "composantes": result["components"],
                "verdict": result["verdict"],
                "rendement_exige": {
                    "ke": result["ke"]["ke"],
                    "crp": result["ke"]["crp"],
                    "source_crp": result["ke"]["crp_source"],
                },
                "risque_estime": result["risk"],
            }
        )
    table = data.comparison_frame(countries)
    comparable: dict[str, dict[str, str]] = {
        row["Indicateur"]: {
            name: row[name] for name in row.index if name != "Indicateur"
        }
        for _, row in table.iterrows()
    }
    return {
        "pays_selectionnes": [c["name"] for c in countries],
        "indicateurs_comparables": comparable,
        "scores_geo_capital": rows,
        "informations_manquantes": {
            c["name"]: missing_indicators(c) for c in countries if missing_indicators(c)
        },
    }


def payload_verdict(country: dict[str, Any], profile: str = "Équilibré") -> dict[str, Any]:
    result = scoring.overall_score(country, profile)
    breakdown = scoring.score_breakdown(country, profile)
    return {
        "pays": country["name"],
        "profil": profile,
        "verdict": result["verdict"],
        "raison_verdict": result["verdict_reason"],
        "score_global": result["score"],
        "composantes_detaillees": [
            {
                "composante": row["label"],
                "score": row["score"],
                "poids": row["weight"],
                "contribution": row["contribution"],
            }
            for row in breakdown
        ],
        "seuils_verdict": {
            "investir": "score >= 76 et un signal de marché disponible (notation ou CDS)",
            "investir_avec_prudence": "score >= 62 et un signal de marché disponible",
            "attendre": "score >= 45, ou >= 38 avec dynamisme >= 55",
            "eviter": "en deçà de ces seuils",
        },
        "raisons_implementation": {
            row["kind"]: row["text"] for row in scoring.top_reasons(country, profile)
        },
        "informations_manquantes": missing_indicators(country),
    }


def payload_capital(country: dict[str, Any]) -> dict[str, Any]:
    ke = scoring.required_return(country)
    data_root = data.load_data()
    params = data_root.get("financial_params", {})
    return {
        "pays": country["name"],
        "cout_du_capital": ke,
        "parametres_methode": {
            key: params[key]
            for key in (
                "risk_free_rate",
                "mature_erp",
                "beta",
                "equity_bond_vol_ratio",
                "risk_free_source",
                "erp_source",
            )
            if key in params
        },
        "methode_officielle": data_root.get("methodology", {}).get("ke"),
        "limites_explicites_du_modele": CAPITAL_LIMITATIONS,
        "informations_manquantes": missing_indicators(country),
    }


def payload_event(event: dict[str, Any], country: dict[str, Any] | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "faits_etablis": {
            "titre": event.get("title"),
            "date": event.get("date"),
            "categorie": event.get("category"),
            "source": event.get("source"),
            "resume": event.get("summary"),
            "chaine_causale": [
                {"etiquette": step.get("label"), "texte": step.get("text")}
                for step in event.get("chain", [])
            ],
        },
        "consequences_potentielles": {
            "gagnants": event.get("winners", []),
            "perdants": event.get("losers", []),
            "echo_historique": event.get("history"),
            "concepts": event.get("concepts", []),
        },
    }
    if country:
        payload["pays_concerne"] = {
            "name": country["name"],
            "verdict_actuel": scoring.overall_score(country, "Équilibré")["verdict"],
            "risques_associes": country.get("risks", [])[:3],
        }
    return payload


def build_holdings(
    amounts: dict[str, float | int],
) -> tuple[list[dict[str, Any]], float]:
    """Construit les positions à partir des montants saisis (logique identique au simulateur)."""
    holdings: list[dict[str, Any]] = []
    invested = 0.0
    for country in data.countries():
        amount = float(amounts.get(country["id"], 0) or 0)
        if amount > 0:
            invested += amount
            holdings.append({"country": country, "amount": amount})
    for holding in holdings:
        holding["weight"] = holding["amount"] / invested
    return holdings, invested


def payload_portfolio(amounts: dict[str, float | int]) -> dict[str, Any]:
    holdings, invested = build_holdings(amounts)
    metrics = scoring.portfolio_metrics(holdings)
    portfolio: dict[str, Any] = {
        "montant_investi_eur": round(invested, 0),
        "metriques": metrics,
        "positions": [],
    }
    for holding in holdings:
        req = scoring.required_return(holding["country"])
        risk = scoring.overall_score(holding["country"])
        portfolio["positions"].append(
            {
                "pays": holding["country"]["name"],
                "montant_eur": round(holding["amount"], 0),
                "poids_pct": round(holding["weight"] * 100, 1),
                "rendement_exige": req["ke"],
                "risque_estime": risk["risk"],
                "volatilite_pedagogique": risk["volatility"],
            }
        )
    if not portfolio["positions"]:
        portfolio["remarque"] = (
            "Aucune position active saisie : proposer à l'utilisateur de renseigner "
            "des montants dans l'onglet Portefeuille."
        )
    return portfolio


def payload_overview(profile: str = "Équilibré") -> dict[str, Any]:
    """Contexte global compact quand aucune intention précise n'est disponible."""
    rows = []
    for country in data.countries():
        result = scoring.overall_score(country, profile)
        rows.append(
            {
                "pays": country["name"],
                "groupe": country.get("group"),
                "score": result["score"],
                "verdict": result["verdict"],
                "rendement_exige": result["ke"]["ke"],
                "risques_declares": country.get("risks", [])[:2],
            }
        )
    return {"pays_disponibles": rows, "profil_utilisateur": profile}


def build_context(
    intent: str,
    question: str,
    profile: str = "Équilibré",
    country_id: str | None = None,
    compare_ids: list[str] | None = None,
    event_id: str | None = None,
    amounts: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    """Compose le contexte factuel pertinent pour l'intention choisie."""
    default_country = (
        data.country_by_id(country_id or "usa") or data.countries()[0]
    )
    if intent == "country":
        return payload_country(default_country, profile)
    if intent == "compare":
        selected = [data.country_by_id(cid) for cid in (compare_ids or ["usa", "china"])]
        selected = [c for c in selected if c]
        if len(selected) < 2:
            selected = data.countries()[:2]
        return payload_comparison(selected, profile)
    if intent == "verdict":
        return payload_verdict(default_country, profile)
    if intent == "capital":
        return payload_capital(default_country)
    if intent == "event":
        events = data.load_events()
        event = next((e for e in events if e["id"] == event_id), events[0])
        return payload_event(event, data.country_by_id(event.get("country", "")))
    if intent == "portfolio":
        return payload_portfolio(amounts or {})
    detected = detect_country(question or "") or detect_event(question or "")
    if detected:
        country = data.country_by_id(detected)
        if country:
            return payload_country(country, profile)
        events = data.load_events()
        event = next((e for e in events if e["id"] == detected), None)
        if event:
            return payload_event(event, data.country_by_id(event.get("country", "")))
    return payload_overview(profile)


def build_system_rules(question: str) -> str:
    """Règles système complétées de la consigne de langue de la question.

    La langue de réponse suit la question (détection sans appel LLM,
    cf. detect_question_language) ; l'interface ne joue aucun rôle.
    """
    lang = detect_question_language(question)
    return ANALYST_SYSTEM_RULES + "\n" + ANSWER_LANGUAGE_RULES[lang]


def build_messages(
    payload: dict[str, Any],
    question: str,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Assemble système + historique (6 derniers échanges au plus) + question."""
    recent = (history or [])[-MAX_EXCHANGES * 2 :]
    context_root = (
        "CONTEXTE : la base GeoCapital ne couvre que des données de référence "
        "2024-2025 ; les événements postérieurs sont hors du champ des faits.\n\n"
        "FAITS VALIDÉS :\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    return (
        [{"role": "system", "content": build_system_rules(question)}]
        + recent
        + [{"role": "user", "content": context_root + "\n\nQUESTION DE L'UTILISATEUR :\n" + question}]
    )


def editorial_answer(payload: dict[str, Any], question: str | None = None) -> str:
    """Réponse déterministe affichée quand l'IA est indisponible ou en échec.

    La langue rédactionnelle suit la question (question vide → français,
    langue par défaut) ; les faits, signatures de sources, dates, étiquettes
    de données et valeurs internes restent inchangés dans les deux langues.
    """
    lang = detect_question_language(question)
    lines = [
        "Mode éditorial : réponse construite sans IA, à partir des mêmes faits."
        if lang == "fr"
        else "Editorial mode: answer built without AI, from the same validated facts."
    ]

    score_block = payload.get("score_geo_capital")
    if score_block:
        ke = score_block.get("rendement_exige") or {}
        if lang == "fr":
            lines.append(
                f"Score GeoCapital : {score_block['score']}/100 ({score_block.get('profil')}) · "
                f"verdict : {score_block.get('verdict')}."
            )
            if ke:
                lines.append(
                    f"Rendement exigé calculé en Python : {ke.get('ke')} % "
                    f"(prime pays {ke.get('crp')} %, source : {ke.get('crp_source')})."
                )
        else:
            lines.append(
                f"GeoCapital score: {score_block['score']}/100 ({score_block.get('profil')}) · "
                f"verdict: {score_block.get('verdict')}."
            )
            if ke:
                lines.append(
                    f"Required return computed in Python: {ke.get('ke')} % "
                    f"(country risk premium {ke.get('crp')} %, source: {ke.get('crp_source')})."
                )

    verdict_reasons = payload.get("raisons_implementation")
    if verdict_reasons:
        for text in verdict_reasons.values():
            lines.append(text)

    breakdown = payload.get("composantes_detaillees")
    if breakdown:
        contributions = ", ".join(
            f"{row['composante']} {row['contribution']:.0f}/{row['max']:.0f}"
            for row in breakdown
        )
        lines.append(
            f"Contributions : {contributions}." if lang == "fr" else f"Contributions: {contributions}."
        )

    ke_payload = payload.get("cout_du_capital")
    if ke_payload and not score_block:
        if lang == "fr":
            lines.append(
                f"Rendement exigé : {ke_payload['ke']} % "
                f"(prime pays {ke_payload['crp']} %, source : {ke_payload['crp_source']})."
            )
        else:
            lines.append(
                f"Required return: {ke_payload['ke']} % "
                f"(country risk premium {ke_payload['crp']} %, source: {ke_payload['crp_source']})."
            )

    positions = payload.get("positions")
    metrics = payload.get("metriques") or {}
    if positions and metrics:
        top = positions[0]
        if lang == "fr":
            lines.append(
                f"Portefeuille : rendement exigé pondéré {metrics.get('expected_return')} %, "
                f"volatilité {metrics.get('volatility')} %, "
                f"{metrics.get('effective_countries')} pays effectifs, "
                f"premier poids : {top.get('pays')} à {top.get('poids_pct')} %."
            )
        else:
            lines.append(
                f"Portfolio: weighted required return {metrics.get('expected_return')} %, "
                f"volatility {metrics.get('volatility')} %, "
                f"{metrics.get('effective_countries')} effective countries, "
                f"largest position: {top.get('pays')} at {top.get('poids_pct')} %."
            )

    missing = payload.get("informations_manquantes")
    if missing:
        if isinstance(missing, dict):
            labels = []
            for value in missing.values():
                labels += [item["label"] for item in value]
        else:
            labels = [item["label"] for item in missing]
        if labels:
            if lang == "fr":
                lines.append(
                    "Données non disponibles : " + ", ".join(sorted(set(labels))) + "."
                )
            else:
                lines.append(
                    "Data not available: " + ", ".join(sorted(set(labels))) + "."
                )

    return "\n\n".join(lines)
