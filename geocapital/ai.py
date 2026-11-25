"""Couche IA optionnelle via OpenRouter (API compatible OpenAI).

L'IA ne reçoit que des faits déjà validés dans la base GeoCapital.
Sans clé API, l'application reste entièrement fonctionnelle grâce aux
contenus éditoriaux et aux explications déterministes.

Configuration (variables d'environnement, fichier .env, puis secrets Streamlit) :
- OPENROUTER_API_KEY : clé OpenRouter.
- LLM_MODEL : identifiant du modèle, par exemple "openrouter/free" (modèle gratuit)
  ou "openai/gpt-4o". Prioritaire sur GEOCAPITAL_MODEL (conservé, compatibilité).
- LLM_BASE_URL : URL de base de l'API compatible OpenAI, par défaut
  "https://openrouter.ai/api/v1" (https obligatoire, sauf localhost).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
API_URL = DEFAULT_BASE_URL + "/chat/completions"  # endpoint par défaut (compat.)
DEFAULT_MODEL = "openai/gpt-4o"
MAX_TOKENS = 700

_ENV_LOADED = False

SYSTEM_RULES = """Tu es l'analyste pédagogique de GeoCapp.
Règles absolues :
- Explique uniquement à partir des faits fournis dans le message.
- N'invente aucun chiffre, aucune date, aucune notation et aucun événement.
- Si une donnée manque, dis-le et traite le vide comme un signal de prudence.
- Écris en français clair, pour un étudiant ou un jeune investisseur.
- Pas de conseil financier personnalisé. Termine par une nuance pédagogique si utile.
- Format : 120 à 180 mots, paragraphes courts, ton précis et vivant.
"""


def _parse_env(text: str) -> dict[str, str]:
    """Analyse un contenu type .env : lignes CLÉ=VALEUR, commentaires ignorés."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _load_dotenv(path: str | None = None) -> None:
    """Charge un fichier .env depuis la racine du projet.

    Les variables déjà présentes dans l'environnement ont la priorité
    (os.environ.setdefault ne les écrase pas).
    """
    global _ENV_LOADED
    if _ENV_LOADED and path is None:
        return
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [path, os.path.join(root, ".env")]
    for candidate in candidates:
        if not candidate or not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, encoding="utf-8") as handle:
                values = _parse_env(handle.read())
        except OSError:
            continue
        for key, value in values.items():
            os.environ.setdefault(key, value)
    _ENV_LOADED = True


def _from_secrets(name: str) -> str:
    try:
        import streamlit as st

        secret = st.secrets.get(name, "")
        return str(secret).strip()
    except Exception:
        return ""


def _setting(name: str) -> str:
    """Réglage texte : variable d'environnement (ou .env) puis secrets Streamlit ; "" sinon."""
    _load_dotenv()
    value = os.getenv(name, "").strip()
    return value or _from_secrets(name)


def api_model() -> str:
    """Identifiant du modèle : LLM_MODEL > GEOCAPITAL_MODEL > défaut (openai/gpt-4o).

    Pour chaque nom : environnement/.env d'abord, puis secrets Streamlit.
    """
    return _setting("LLM_MODEL") or _setting("GEOCAPITAL_MODEL") or DEFAULT_MODEL


def _is_safe_base_url(url: str) -> bool:
    """https obligatoire (la clé API part dans l'en-tête) ; http toléré en local seulement."""
    lowered = url.lower()
    if lowered.startswith("https://"):
        return len(lowered) > len("https://")
    return lowered.startswith(("http://localhost", "http://127.0.0.1"))


def api_base_url() -> str:
    """URL de base de l'API (LLM_BASE_URL), sans « / » final ; défaut OpenRouter.

    Une valeur non sûre (http distant, schéma inconnu) est ignorée au profit du défaut.
    """
    value = _setting("LLM_BASE_URL").rstrip("/")
    return value if value and _is_safe_base_url(value) else DEFAULT_BASE_URL


def api_url() -> str:
    return api_base_url() + "/chat/completions"


def api_key() -> str | None:
    """Clé OpenRouter : env (ou .env) > secrets Streamlit, sinon None."""
    _load_dotenv()
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    return _from_secrets("OPENROUTER_API_KEY") or None


def is_available() -> bool:
    return bool(api_key())


def _post(payload: dict[str, Any]) -> str | None:
    """Transport partagé : requête OpenRouter, parse compatible OpenAI, erreurs → None."""
    key = api_key()
    if not key:
        return None
    request = urllib.request.Request(
        api_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/IDER04/GeoCapp",
            "X-Title": "GeoCapital",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        choices = data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        return str(content).strip() or None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError, IndexError, TypeError):
        return None


def _call(prompt: str, max_tokens: int = MAX_TOKENS) -> str | None:
    payload = {
        "model": api_model(),
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_RULES},
            {"role": "user", "content": prompt},
        ],
    }
    return _post(payload)


def chat(messages: list[dict[str, str]], max_tokens: int = MAX_TOKENS) -> str | None:
    """Conversation multi-tours pour l'analyste (messages OpenAI-compatibles)."""
    if not messages:
        return None
    payload = {
        "model": api_model(),
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": messages,
    }
    return _post(payload)


def country_brief(country: dict[str, Any], score_payload: dict[str, Any]) -> str | None:
    facts = {
        "pays": country["name"],
        "résumé_éditorial": country.get("summary"),
        "profil": score_payload.get("profile"),
        "score": score_payload.get("score"),
        "verdict": score_payload.get("verdict"),
        "rendement_exigé": score_payload.get("ke"),
        "forces": country.get("strengths", []),
        "risques": country.get("risks", []),
        "indicateurs": {
            k: v.get("value") for k, v in country.get("indicators", {}).items()
        },
    }
    prompt = (
        "Rédige la synthèse GeoCapp de ce pays en 3 minutes de lecture. "
        "Relie une cause historique à un risque financier actuel, puis explique le verdict. "
        "N'ajoute aucun chiffre absent des faits.\n\nFAITS:\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )
    return _call(prompt)


def explain_verdict(country: dict[str, Any], score_payload: dict[str, Any]) -> str | None:
    facts = {
        "pays": country["name"],
        "score": score_payload.get("score"),
        "verdict": score_payload.get("verdict"),
        "composantes": score_payload.get("components"),
        "rendement_exigé": score_payload.get("ke"),
        "risque": score_payload.get("risk"),
    }
    prompt = (
        "Explique ce verdict d'investissement à un débutant. "
        "Décompose en : ce que le score mesure, pourquoi ce pays obtient ce résultat, "
        "et ce que le rendement exigé signifie concrètement. "
        "N'ajoute aucun chiffre absent des faits.\n\nFAITS:\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )
    return _call(prompt, max_tokens=500)


def decode_event(event: dict[str, Any], country: dict[str, Any]) -> str | None:
    facts = {
        "pays": country["name"],
        "événement": event.get("title"),
        "date": event.get("date"),
        "chaîne_causale": [step.get("text") for step in event.get("chain", [])],
        "gagnants": event.get("winners"),
        "perdants": event.get("losers"),
        "écho_historique": event.get("history"),
        "concepts": event.get("concepts"),
    }
    prompt = (
        "Explique cet événement en chaîne causale : fait → économie → finance → gagnants/perdants. "
        "Termine par l'écho historique fourni. N'invente aucun chiffre ni événement.\n\nFAITS:\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )
    return _call(prompt, max_tokens=550)


def portfolio_commentary(
    country_facts: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> str | None:
    facts = {
        "allocation": country_facts,
        "rendement_exigé_pondéré": metrics.get("expected_return"),
        "volatilité_estimée": metrics.get("volatility"),
        "diversification": metrics.get("diversification"),
        "concentration_hhi": metrics.get("hhi"),
        "pays_effectifs": metrics.get("effective_countries"),
    }
    prompt = (
        "Commente ce portefeuille pédagogique de 100 000 €. "
        "Explique le rendement exigé, le risque, la diversification et le principal point de concentration. "
        "Ne recommande pas un achat ou une vente et n'ajoute aucun chiffre absent des faits.\n\nFAITS:\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )
    return _call(prompt, max_tokens=500)


def explain_quiz(country: dict[str, Any], question: dict[str, Any], correct: bool) -> str | None:
    facts = {
        "pays": country["name"],
        "question": question.get("question"),
        "bonne_réponse": question.get("options", [None])[question.get("answer", 0)],
        "explication": question.get("explanation"),
        "réponse_de_l_utilisateur_correcte": correct,
    }
    prompt = (
        "Explique la réponse à ce quiz en une notion claire et une phrase de contexte. "
        "Ne donne pas de nouveaux faits.\n\nFAITS:\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )
    return _call(prompt, max_tokens=350)


_load_dotenv()
