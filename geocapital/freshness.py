"""Couche d'affichage « fraîcheur des données » (Priorité 2 — lieux d'affichage).

Règle du projet : cette couche n'influence **ni** le score **ni** le verdict.
Elle se contente d'exposer, à côté de chaque indicateur, son millésime
d'observation, et marque comme « à rafraîchir » toute observation dont
l'année est antérieure au 1er janvier de l'année précédente.

Définitions (documentées sur la page Sources & méthode) :
- date d'OBSERVATION : la période couverte par la donnée (ex. « 2024 », « déc. 2024 ») ;
- date de CONSULTATION (retrieval) : la date à laquelle GeoCapital a vérifié
  la donnée auprès de la source (champ `app.data_as_of` de `data/meta.json`) ;
- observation « à rafraîchir » (stale) : année d'observation < année courante − 1.
  Exemple : en 2026, une observation 2024 est marquée ⚠ ; une observation
  2025 est encore considérée comme récente.
- une date non numérique (« calcul », vide) n'est pas une observation datée :
  elle n'est jamais marquée stale.

La langue des libellés suit `geocapital/i18n.t()` (FR par défaut).
"""

from __future__ import annotations

import datetime
import re
from typing import Any

_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _today_iso() -> str:
    """Date de consultation par défaut (aujourd'hui, au format ISO)."""
    return datetime.date.today().isoformat()


def as_of() -> str:
    """Date de consultation (retrieval) déclarée dans `data/meta.json`.

    Source de vérité : `app.data_as_of`. Repli transparent : la date du jour.
    Aucune donnée n'est modifiée ; c'est du metadata d'affichage.
    """
    from geocapital.data import load_data

    raw = load_data().get("app", {}).get("data_as_of", "")
    return str(raw) if raw else _today_iso()


def obs_year(date: Any) -> int | None:
    """Année d'observation extraite d'une chaîne de date d'indicateur.

    Retourne None si aucun millésime n'est identifiable (« calcul », vide…).
    """
    if date is None:
        return None
    match = _YEAR_RE.search(str(date))
    return int(match.group(0)) if match else None


def is_stale(date: Any, now_year: int | None = None) -> bool:
    """True si l'observation est antérieure au 1er janvier de l'an passé.

    Mathématiquement : obs_year(date) < now_year − 1.
    Une date sans millésime identifiable n'est jamais marquée stale.
    Le paramètre `now_year` permet des tests déterministes.
    """
    year = obs_year(date)
    if year is None:
        return False
    now = now_year if now_year is not None else datetime.date.today().year
    return year < now - 1


def stale_threshold(now_year: int | None = None) -> int:
    """Première année d'observation considérée récente (année courante − 1).

    Une observation dont le millésime est >= au seuil n'est pas marquée stale.
    Exposé pour les libellés i18n (« antérieure à {limit} »).
    """
    now = now_year if now_year is not None else datetime.date.today().year
    return now - 1


def any_stale(dates: list[Any], now_year: int | None = None) -> bool:
    """True si au moins une observation de la liste est à rafraîchir."""
    return any(is_stale(date, now_year) for date in dates)


def stale_badge(date: str) -> str:
    """Préfixe ⚠ pour une observation à rafraîchir, sinon la date inchangée."""
    if is_stale(date):
        return f"⚠ {date}"
    return str(date)


def oldest_obs_year(dates: list[Any], now_year: int | None = None) -> int | None:
    """Plus petite année d'observation d'une liste (None si aucune datée)."""
    years = [obs_year(item) for item in dates]
    dated = [year for year in years if year is not None]
    return min(dated) if dated else None
