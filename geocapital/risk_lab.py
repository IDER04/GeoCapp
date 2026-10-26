"""Sovereign Risk Lab — analyse de risque souverain approfondie (Priorité 8).

Couche de calcul déterministe derrière la vue ``views/risk_lab_page.py``.
Conventions du projet :

- **Lecture seule** sur ``data/`` : aucune donnée de production n'est
  modifiée, aucune formule ni paramètre de scoring n'est changé ;
- **aucune valeur inventée** : un indicateur absent du schéma est
  déclaré indisponible (``available=False``), jamais remplacé par zéro
  ni par une estimation ;
- les statuts de qualité (stale / estimé / conflit / vérifié) sont
  **réutilisés** du module d'audit (``data_quality_audit.status_for``),
  qui s'appuie sur la liste documentée des conflits — pas de registre
  dupliqué ici ;
- les paliers (taux réel, dette) viennent de ``scoring.model()`` — la
  même source de vérité que le moteur, non re-définie ;
- le taux réel est un **calcul dérivé** (policy_rate − inflation),
  identique à scoring.component_scores ; le mélange de millésimes est
  signalé explicitement (warning d'alignement), pas corrigé ;
- une analyse complète de durabilité de la dette (DSA) n'est **pas**
  présentée tant que les entrées requises (solde budgétaire, intérêts /
  recettes) manquent : la limite est expliquée à la place.

Ce module n'importe pas Streamlit : il est testable hors application.
"""

from __future__ import annotations

from typing import Any

from geocapital import data, freshness, scoring
from geocapital.data_quality_audit import status_for as audit_status_for

# Indicateurs OBSERVÉS du schéma actuel utilisés par le lab (clés exactes
# de data/countries/*.json). Les autres demandés (solde budgétaire,
# balance courante, dette externe…) n'existent pas dans le schéma v1 :
# voir ABSENT_METRICS.
SECTION_METRICS: dict[str, list[str]] = {
    "fiscal": ["debt_gdp"],
    "external": ["reserves"],
    "macro": ["gdp_growth", "inflation", "policy_rate"],
}

# Métrique DÉRIVÉE du lab (policy_rate − inflation, paliers du modèle).
DERIVED_METRICS: dict[str, dict[str, Any]] = {
    "real_rate": {"section": "macro", "unit": "%"},
}

# Indicateurs demandés mais ABSENTS du schéma de production. Chaque entrée
# porte l'unité attendue. Si un jour la donnée apparaît dans une fiche
# (clé éponyme ou alias), build_metrics la lira automatiquement.
ABSENT_METRICS: dict[str, dict[str, Any]] = {
    "fiscal_balance": {
        "section": "fiscal",
        "unit": "% du PIB",
        "aliases": ("fiscal_balance", "primary_balance"),
    },
    "interest_revenue": {
        "section": "fiscal",
        "unit": "% des recettes",
        "aliases": ("interest_payments", "interest_revenue"),
    },
    "current_account": {
        "section": "external",
        "unit": "% du PIB",
        "aliases": ("current_account", "current_account_balance"),
    },
    "external_debt_total": {
        "section": "external",
        "unit": "% du PIB",
        "aliases": ("external_debt", "external_debt_total"),
    },
    "external_debt_short": {
        "section": "external",
        "unit": "% du PIB",
        "aliases": ("external_debt_short", "short_term_external_debt"),
    },
    # Mois d'importations : nécessite une donnée d'importations compatible
    # (même devise, même période que les réserves). Une donnée « imports »
    # seule ne suffit pas : elle ne devient pas une couverture inventée.
    "reserves_import_months": {
        "section": "external",
        "unit": "mois d'importations",
        "aliases": ("reserves_import_months",),
    },
}

SECTION_ORDER = ("fiscal", "external", "macro")


def _block(country: dict[str, Any], key: str) -> dict[str, Any]:
    return country.get("indicators", {}).get(key, {}) or {}


def _observed_metric(country: dict[str, Any], key: str, display_key: str | None = None) -> dict[str, Any]:
    """Carte indicateur du schéma → entrée du lab (statuts d'audit réutilisés)."""
    block = _block(country, key)
    audit_status, _flags, _confidence, basis = audit_status_for(country, key, block)
    warnings: list[str] = []
    if audit_status == "stale":
        warnings.append("stale")
    if audit_status == "estimated":
        warnings.append("estimated")
    if audit_status == "conflicting":
        warnings.append("conflicting")
    if audit_status == "unverified":
        warnings.append("unverified")

    # feux tricolores : conflit = rouge ; stale/estimé = orange ; sinon vert
    if audit_status == "conflicting":
        display = "red"
    elif audit_status in {"stale", "estimated"}:
        display = "orange"
    else:
        display = "green"

    value = block.get("value")
    return {
        "key": display_key or key,
        "kind": "observed",
        "available": value is not None,
        "value": value,
        "unit": block.get("unit", data.INDICATOR_UNITS.get(key, "")),
        "obs_period": None if block.get("date") is None else str(block.get("date")),
        "source": block.get("source"),
        "audit_status": audit_status,
        "warnings": warnings if value is not None else [],
        "warning_detail": basis if warnings and audit_status in {"conflicting", "estimated"} else None,
        "note": block.get("note"),
    }


def _absent_metric(country: dict[str, Any], key: str) -> dict[str, Any]:
    """Indicateur demandé mais absent du schéma : indisponible, jamais zéro.

    La donnée peut exister dans une fiche future (alias du schéma) : on la
    cherche d'abord, sinon on déclare l'indisponibilité avec explication.
    """
    spec = ABSENT_METRICS[key]
    for alias in spec["aliases"]:
        if _block(country, alias).get("value") is not None:
            return _observed_metric(country, alias, display_key=key)
    return {
        "key": key,
        "kind": "unavailable",
        "available": False,
        "value": None,
        "unit": spec["unit"],
        "obs_period": None,
        "source": None,
        "audit_status": "missing",
        "warnings": [],
        "warning_detail": None,
        "note": None,
    }


def _derived_metric(country: dict[str, Any], key: str) -> dict[str, Any]:
    if key == "real_rate":
        detail = real_rate_detail(country)
        if not detail["available"]:
            return {
                "key": key,
                "kind": "derived",
                "available": False,
                "value": None,
                "unit": DERIVED_METRICS[key]["unit"],
                "obs_period": None,
                "source": None,
                "audit_status": "missing",
                "warnings": [],
                "warning_detail": None,
                "note": None,
            }
        warnings: list[str] = []
        if detail["vintage_mismatch"]:
            warnings.append("vintage_mismatch")
        if detail["stale_inputs"]:
            warnings.append("stale")
        return {
            "key": key,
            "kind": "derived",
            "available": True,
            "value": detail["real_rate"],
            "unit": DERIVED_METRICS[key]["unit"],
            "obs_period": f"{detail['policy_period']} / {detail['inflation_period']}",
            "source": f"policy_rate − inflation (paliers scoring.model) — {detail['policy_period']} × {detail['inflation_period']}",
            "audit_status": "verified",
            "warnings": warnings,
            "warning_detail": None,
            "note": None,
        }
    raise KeyError(key)


def build_metrics(country: dict[str, Any]) -> list[dict[str, Any]]:
    """Toutes les métriques du lab pour un pays, ordonnées par section.

    Sections : fiscal (dette + soldes), external (réserves, balance
    courante, dette externe), macro (croissance, inflation, taux, réel).
    """
    metrics: list[dict[str, Any]] = []
    for section in SECTION_ORDER:
        for key in SECTION_METRICS.get(section, []):
            metric = _observed_metric(country, key)
            metric["section"] = section
            metrics.append(metric)
        for key, spec in ABSENT_METRICS.items():
            if spec["section"] != section:
                continue
            metric = _absent_metric(country, key)
            metric["section"] = section
            metrics.append(metric)
        for key, spec in DERIVED_METRICS.items():
            if spec["section"] != section:
                continue
            metric = _derived_metric(country, key)
            metric["section"] = section
            metrics.append(metric)
    return metrics


def real_rate_detail(country: dict[str, Any]) -> dict[str, Any]:
    """Taux réel policy_rate − inflation, paliers du modèle (lecture seule).

    ``aligned`` est faux quand les deux observations n'ont pas le même
    millésime (ex. Liban : taux 2024 × inflation 2025) — le mélange est
    signalé, jamais corrigé (known issue K1 de l'audit qualité).
    """
    policy = data.indicator_value(country, "policy_rate")
    inflation = data.indicator_value(country, "inflation")
    policy_block = _block(country, "policy_rate")
    inflation_block = _block(country, "inflation")

    if policy is None or inflation is None:
        return {
            "available": False,
            "real_rate": None,
            "policy_rate": policy,
            "inflation": inflation,
            "policy_period": policy_block.get("date"),
            "inflation_period": inflation_block.get("date"),
            "band": None,
            "band_score": None,
            "aligned": None,
            "vintage_mismatch": False,
        }

    real = float(policy) - float(inflation)
    cfg = scoring.model()["components"]["stabilite"]
    bands = [tuple(band) for band in cfg["real_rate_bands"]]
    band = next((b for b in bands if b[0] <= real <= b[1]), None)  # même
    # convention que scoring.component_scores (inclusif bas ET haut)
    policy_year = freshness.obs_year(policy_block.get("date"))
    inflation_year = freshness.obs_year(inflation_block.get("date"))
    aligned = policy_year is not None and policy_year == inflation_year
    return {
        "available": True,
        "real_rate": real,
        "policy_rate": float(policy),
        "inflation": float(inflation),
        "policy_period": policy_block.get("date"),
        "inflation_period": inflation_block.get("date"),
        "policy_year": policy_year,
        "inflation_year": inflation_year,
        "band": list(band) if band else None,
        "band_score": float(band[2]) if band else float(cfg["real_rate_outside_score"]),
        "bands": [list(band_) for band_ in bands],
        "aligned": aligned,
        "vintage_mismatch": not aligned,
        "stale_inputs": freshness.any_stale(
            [policy_block.get("date"), inflation_block.get("date")]
        ),
    }


def debt_sustainability(country: dict[str, Any]) -> dict[str, Any]:
    """Lecture de durabilité fiscale, bornée aux entrées disponibles.

    Le palier de dette vient de ``scoring.model()`` (config existante,
    non re-définie). Une DSA complète exige solde budgétaire et charge
    d'intérêts : absents du schéma v1 → ``dsa_complete=False`` et liste
    des entrées manquantes (jamais de valeur de substitution).
    """
    debt = data.indicator_value(country, "debt_gdp")
    debt_block = _block(country, "debt_gdp")
    low, high = scoring.model()["components"]["solvabilite"]["ranges"]["debt_range"]

    position: str | None = None
    if debt is not None:
        if debt < low:
            position = "below_low"
        elif debt > high:
            position = "above_high"
        else:
            position = "within"

    missing_inputs = [
        key for key in ("fiscal_balance", "interest_revenue") if not _absent_metric(country, key)["available"]
    ]
    growth = data.indicator_value(country, "gdp_growth")
    return {
        "debt_gdp": None if debt is None else float(debt),
        "obs_period": debt_block.get("date"),
        "source": debt_block.get("source"),
        "note": debt_block.get("note"),
        "stale": freshness.is_stale(debt_block.get("date")),
        "band": [float(low), float(high)],
        "position": position,
        "growth": None if growth is None else float(growth),
        "missing_inputs": missing_inputs,
        "dsa_complete": not missing_inputs and debt is not None,
    }


def summary_lines(country: dict[str, Any]) -> list[str]:
    """Synthèse analytique déterministe, fondée UNIQUEMENT sur les données
    disponibles (libellés i18n ; aucun chiffre inventé)."""
    from geocapital.i18n import t

    lines: list[str] = []
    metrics = build_metrics(country)
    by_key = {m["key"]: m for m in metrics}

    debt = debt_sustainability(country)
    if debt["debt_gdp"] is not None:
        lines.append(
            t(
                "rl.summary.debt",
                value=data.format_number(debt["debt_gdp"], 0),
                period=str(debt["obs_period"] or "—"),
                position=t(
                    f"rl.dsa.position.{debt['position']}",
                    low=data.format_number(debt["band"][0], 0),
                    high=data.format_number(debt["band"][1], 0),
                ),
                low=data.format_number(debt["band"][0], 0),
                high=data.format_number(debt["band"][1], 0),
            )
        )
    reserves = by_key["reserves"]
    if reserves["available"]:
        lines.append(
            t(
                "rl.summary.reserves",
                value=data.format_number(reserves["value"], 0),
                period=str(reserves["obs_period"] or "—"),
            )
        )
    growth, inflation = by_key["gdp_growth"], by_key["inflation"]
    if growth["available"] and inflation["available"]:
        lines.append(
            t(
                "rl.summary.macro",
                growth=data.format_number(growth["value"], 1),
                inflation=data.format_number(inflation["value"], 1),
                period=str(growth["obs_period"] or "—"),
            )
        )
    real = by_key["real_rate"]
    if real["available"]:
        detail = real_rate_detail(country)
        if detail["band"]:
            band_note = t(
                "rl.summary.real_band",
                low=data.format_number(detail["band"][0], 1),
                high=data.format_number(detail["band"][1], 1),
                score=data.format_number(detail["band_score"], 0),
            )
        else:
            band_note = t("rl.summary.real_outside")
        lines.append(t("rl.summary.real", value=data.format_number(detail["real_rate"], 1), band_note=band_note))
    return lines


def comparison_matrix(selected: list[dict[str, Any]]) -> dict[str, Any]:
    """Matrice comparée des métriques du lab pour 2 à 4 pays.

    Une cellule indisponible reste explicite (``available=False``),
    jamais zéro ; les warnings (stale / estimé / conflit / millésimes
    mélangés) suivent la cellule.
    """
    columns = [
        {"id": country["id"], "name": country["name"], "flag": country["flag"]}
        for country in selected
    ]
    rows: list[dict[str, Any]] = []
    for section in SECTION_ORDER:
        keys = [
            *(("observed", key) for key in SECTION_METRICS.get(section, [])),
            *(("absent", key) for key, spec in ABSENT_METRICS.items() if spec["section"] == section),
            *(("derived", key) for key, spec in DERIVED_METRICS.items() if spec["section"] == section),
        ]
        for kind, key in keys:
            cells: dict[str, dict[str, Any]] = {}
            for country in selected:
                if kind == "derived":
                    metric = _derived_metric(country, key)
                elif kind == "absent":
                    metric = _absent_metric(country, key)
                else:
                    metric = _observed_metric(country, key)
                cells[country["id"]] = {
                    "value": metric["value"],
                    "unit": metric["unit"],
                    "obs_period": metric["obs_period"],
                    "warnings": metric["warnings"],
                    "available": metric["available"],
                }
            rows.append({"key": key, "section": section, "cells": cells})
    return {"columns": columns, "rows": rows}
