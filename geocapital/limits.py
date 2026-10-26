"""Limite configurable de questions par session pour l'Analyste IA.

Priorité 5 de la Phase 1. Principe : chaque question soumise dans la
session Streamlit courante compte pour **une** unité, quel que soit le
résultat (réponse du fournisseur, échec réseau → repli éditorial, ou
mode éditorial sans clé). Une fois la limite atteinte, aucun appel
fournisseur ne part : l'interface désactive la saisie et affiche un
message expliqué (i18n FR/EN) :

- la limite est **par session Streamlit** (st.session_state côté
  serveur) : nouvelle session = compteur reparti à zéro ;
- ce n'est **ni un plafond de compte global, ni une garantie de dépense**
  (un utilisateur peut ouvrir plusieurs sessions ; se référer à
  docs/AI_LIMITS.md) ;
- ce ne sont **pas des questions factuelles hors IA** : les réponses
  éditoriales déterministes hors analyste restent illimitées.

Configuration : `data/meta.json` → `ai_limits.max_questions_per_session`
(entier >= 1, violation → `ConfigError` informative, aucun repli
silencieux). Le compteur lui-même vit dans `st.session_state` —
serveur, pas client.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from geocapital.scoring import ConfigError

# Clé du compteur serveur (une par session Streamlit).
USAGE_KEY = "ai_analyst_used"

_SECTION = "ai_limits"
_FIELD = "max_questions_per_session"


def session_limit(meta: dict[str, Any]) -> int:
    """Limite validée depuis un méta donné (pure — testable sans runtime)."""
    section = meta.get(_SECTION)
    if not isinstance(section, dict):
        raise ConfigError(f"meta.{_SECTION}: section absente (limite de questions par session attendue)")
    value = section.get(_FIELD)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError(
            f"meta.{_SECTION}.{_FIELD}: entier >= 1 attendu (reçu: {value!r})"
        )
    return value


def limit() -> int:
    """Limite courante lue depuis data/meta.json (chargé par data.load_data)."""
    import geocapital.data as _data

    return session_limit(_data.load_data())


def remaining(used: int, limit_value: int) -> int:
    """Questions encore soumises possibles (jamais négatif)."""
    return max(0, limit_value - used)


def can_ask(used: int, limit_value: int) -> bool:
    """True si une question de plus est possible pour cette session."""
    return remaining(used, limit_value) > 0


def used() -> int:
    """Compteur serveur de la session (0 avant la première question)."""
    value = st.session_state.get(USAGE_KEY, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def record() -> None:
    """Compte une question soumise (exactement une fois par soumission)."""
    st.session_state[USAGE_KEY] = used() + 1


def reset() -> None:
    """Réinitialise le compteur de la session (usage : tests, boutons internes)."""
    st.session_state[USAGE_KEY] = 0
