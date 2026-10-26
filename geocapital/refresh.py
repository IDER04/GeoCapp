"""Pipeline de rafraîchissement des données — World Bank Indicators API v2.

Priorité 6, premier incrément (Phase 1) : récupération **revue avant
application** (« review-first »). Ce module :

1. mappe chaque indicateur GeoCapital vers une série officielle
   (World Bank WDI v2 — gratuit, sans clé) **uniquement si la définition
   coïncide réellement** avec celle du fichier de production ;
2. interroge l'API (urllib stdlib, timeout, sans requérir de clé) ;
3. normalise et valide chaque observation (valeur numérique, millésime,
   statut d'observation : « A »=actuel, « E »=estimation, « F »=prévision,
   vide=actuel par convention WDI) ;
4. compare au payload **de production actuel** (jamais modifié ici) et
   produit une **recommandation** : « safe », « manual » ou « reject »,
   avec une explication brève et sourcée ;
5. écrit le rapport candidats sous `docs/` — **jamais** sous
   `data/countries/` (protection anti-écrasement : aucune fonction ne
   peut écrire dans les fichiers de production).

Politiques documentées (docs/DATA_REFRESH_PLAN.md) :
- millésime réel conservé (pas d'assimilation au « l'année courante ») ;
- une observation plus récente mais à définition nettement différente est
  rejetée ou mise en revue manuelle, jamais appliquée ;
- conversions d'unités uniquement quand elles sont définies et sans
  ambiguïté (US$ → Mds $), et signalées explicitement ;
- absence de donnée = « écart » documenté : la valeur existante est
  conservée, marquée à rafraîchir (couche freshness, Priorité 2).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "countries"
DOCS_DIR = ROOT / "docs"

WB_API_BASE = "https://api.worldbank.org/v2"
DEFAULT_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Cartographie des indicateurs (source de vérité de la correspondance)
# ---------------------------------------------------------------------------
# match : "exact" = même définition GeoCapital ; "partial" = chevauchement
# incomplet (problème de définition documenté) ; "none" = pas de série
# officielle adaptée (référence manuelle obligatoire).

RECEIVED_UNIT_USD = 1e-9  # conversion US$ -> Mds $ (définie, sans ambiguïté)

INDICATOR_MAP: dict[str, dict] = {
    "gdp_growth": {
        "wb_code": "NY.GDP.MKTP.KD.ZG",
        "definition": "Croissance du PIB réel, % annuel (moyenne annuelle)",
        "match": "exact",
        "conversion": None,
        "note": "PIB année de référence constante, moyenne annuelle — cohérent avec la définition GeoCapital.",
    },
    "inflation": {
        "wb_code": "FP.CPI.TOTL.ZG",
        "definition": "Inflation IPC moyenne annuelle, %",
        "match": "exact",
        "conversion": None,
        "note": "IPC générale, moyenne de l'année (pas un point fin d'année). Vérifier par pays que la source existante est aussi une moyenne annuelle.",
    },
    "unemployment": {
        "wb_code": "SL.UEM.TOTL.ZS",
        "definition": "Chômage total (OIT modélisé), %",
        "match": "partial",
        "conversion": None,
        "note": "Série MODELLISÉE ILO (pas une enquête brute) : estimation tripartite OIT, potentiellement décalée en période de rupture (crise libano-syrienne).",
    },
    "debt_gdp": {
        "wb_code": "GC.DOD.TOTL.GD.ZS",
        "definition": "Dette du gouvernement CENTRAL, % PIB",
        "match": "partial",
        "conversion": None,
        "note": "GeoCapital suit la dette OFFICIELLE (générale) du secteur public — la série WB « central government » sous-estime la dette générale (administration locale, entreprises publiques). Comparer avec précaution ; pour plusieurs pays la série s'arrête en années reculées.",
    },
    "reserves": {
        "wb_code": "FI.RES.TOTL.CD",
        "definition": "Réserves TOTALES (or inclus), US$ courants",
        "match": "exact_for_total",
        "conversion": RECEIVED_UNIT_USD,
        "note": "Unité demandée GeoCapital : Mds $ (US$ / 1e9). Certaines fiches de production (ex. Liban) documentent les réserves NETTES — écart de définition, alors rejeté.",
    },
}

# Indicateurs sans équivalent API World Bank (gouverneurs bancaires,
# notation, CDS, bourses, devise) — sources manuelles requises.
NO_WB_EQUIVALENT = ("policy_rate", "rating", "cds", "crp", "equity_index", "currency")

# Statuts d'observation WDI (page meta).
OBS_STATUS_LABELS = {
    "": "actual",
    "A": "actual",
    "E": "estimate",
    "F": "forecast",
    "NA": "not available",
}

# Date de récupération (trace « quand la donnée a été interrogée »),
# distincte du millésime d'observation et de la date de publication.


def retrieval_date() -> str:
    """Date ISO de l'interrogation (mockable dans les tests via RETRIEVAL_CLOCK)."""
    from datetime import date

    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Récupération API (stdlib, clé non requise)
# ---------------------------------------------------------------------------

def fetch_world_bank(
    country_iso3: str,
    series_code: str,
    per_page: int = 60,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Récupère la série WDI la plus récente pour un pays.

    Retourne un dict uniforme : success → {"success": True,
    "observations": [...]}; erreur → {"success": False, "error": ...}.
    Aucune valeur n'est inventée : tout vient de la réponse (ou de
    l'erreur, retranscrite).
    """
    params = {
        "format": "json",
        "per_page": str(per_page),
        "page": "1",
    }
    query = "&".join(f"{key}={value}" for key, value in params.items())
    url = f"{WB_API_BASE}/country/{country_iso3}/indicator/{series_code}?{query}"
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"success": False, "error": f"réseau/HTTP: {exc}", "url": url}
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"réponse JSON invalide: {exc}", "url": url}
    return _parse_world_bank_payload(payload, series_code, url)


def _parse_world_bank_payload(payload: Any, series_code: str, url: str) -> dict:
    """Valide la structure WB v2 [meta, rows] et normalise les observations.

    Cas rejetés explicitement : payload non liste, meta absente/erreur API
    (`{'message': ...}`), rows absentes, structure de ligne inattendue,
    valeurs None/non numériques (ignorées mais tracées), codes d'indicateur
    inattendus.
    """
    if not isinstance(payload, list) or len(payload) < 1:
        # webhook renvoie parfois 5xx JSON flat ; traité comme erreur
        return {"success": False, "error": "structure inattendue (liste [meta, rows] attendue)", "url": url}
    meta, rows = (payload + [None] * 2)[:2] if len(payload) == 1 else (payload[0], payload[1])
    if isinstance(meta, dict) and meta.get("message"):
        message = "; ".join(
            f"{m.get('id', 'code')}: {m.get('value', '')}" for m in meta["message"]
        )
        return {"success": False, "error": f"API World Bank: {message}", "url": url}
    if not isinstance(rows, list):
        return {"success": False, "error": "lignes absentes (page vide ou format inattendu)", "url": url}
    observations = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = (row.get("indicator") or {}).get("id") or row.get("indicatorid")
        if code and code != series_code:
            return {
                "success": False,
                "error": f"série inattendue dans la réponse: {code} ≠ {series_code}",
                "url": url,
            }
        value = row.get("value")
        if value is None:
            continue  # observation absente (null) : ignorée, pas inventée
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue  # valeur non numérique : ignorée
        obs_status = row.get("obs_status", "") or ""
        observations.append(
            {
                "year": int(row["date"]) if str(row.get("date", "")).isdigit() else str(row.get("date", "")),
                "value": value,
                "obs_status": obs_status,
                "obs_status_label": OBS_STATUS_LABELS.get(obs_status, f"unknown ({obs_status})"),
                "indicator_name": (row.get("indicator") or {}).get("value", ""),
                "country": (row.get("country") or {}).get("value", ""),
                "lastupdated": row.get("lastupdated") or (meta or {}).get("lastupdated"),
            }
        )
    return {
        "success": True,
        "url": url,
        "observations": observations,
        "lastupdated": (meta or {}).get("lastupdated"),
        "requested_series": series_code,
    }


def latest_actual(observations: list[dict]) -> dict | None:
    """L'observation la plus récente qui n'est PAS une prévision.

    Les estimations (« E ») sont acceptables (réelles estimations
    officielles, signalées) ; les prévisions (« F ») sont exclues, leur
    usage est celui du simulateur, pas des faits.
    """
    actual = [o for o in observations if o["obs_status"].upper() != "F"]
    if not actual:
        return None
    return max(actual, key=lambda o: _year_for_sort(o))


def _year_for_sort(observation: dict) -> int:
    year = observation["year"]
    try:
        return int(year)
    except (TypeError, ValueError):
        return -1


# ---------------------------------------------------------------------------
# Candidats : comparaison production (LISIBLE uniquement) vs API
# ---------------------------------------------------------------------------

def read_country(cid: str) -> dict:
    """Lit une fiche de production (lecture seule, pas d'écriture)."""
    path = DATA_DIR / f"{cid}.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _wb_country_code(country: dict) -> str:
    return (country.get("iso3") or country.get("id", "")).upper()


def _existing_for(country: dict, indicator: str) -> dict | None:
    meta = country.get("indicators", {}).get(indicator)
    return meta if isinstance(meta, dict) else None


def build_candidate(
    country: dict,
    indicator: str,
    observation: dict | None,
    fetch_error: str | None,
    is_new_country: bool,
) -> dict:
    """Compare l'existant (production) à la proposition API → recommandation.

    Retourne un candidat avec : valeurs existantes/proposées, unités,
    millésimes, dates de publication/retrieval, écart de définition,
    recommandation (« safe » / « manual » / « reject » / « gap ») et
    explication courte.
    """
    spec = INDICATOR_MAP[indicator]
    existing = _existing_for(country, indicator)
    country_id = country.get("id", "?")
    candidate = {
        "country": country_id,
        "indicator": indicator,
        "wb_series": spec["wb_code"],
        "wb_match": spec["match"],
        "existing": None,
        "proposed": None,
        "definition_notes": [],
        "recommendation": None,
        "explanation": "",
    }
    if existing is not None:
        candidate["existing"] = {
            "value": existing.get("value"),
            "unit": existing.get("unit", ""),
            "date": existing.get("date", ""),
            "source": existing.get("source", ""),
            "note": existing.get("note", ""),
        }
    if spec["match"] == "partial":
        candidate["definition_notes"].append(spec["note"])
    candidate["retrieved"] = retrieval_date()

    if fetch_error or observation is None:
        candidate["recommendation"] = "gap"
        if fetch_error:
            candidate["explanation"] = f"récupération indisponible — {fetch_error}. Valeur existante conservée, écart signalé."
        else:
            candidate["explanation"] = "aucune observation exploitable côté WDI — valeur existante conservée, écart signalé."
        return candidate

    raw_value = float(observation["value"])
    proposed = {
        # Présentation : 4 décimales pour %, 1 pour Mds $ (brut conservé dans les observations).
        "value": round(raw_value, 4),
        "unit": spec.get("received_unit") or ("Mds $" if spec["conversion"] else "%"),
        "date": str(observation["year"]),
        "source": f"Banque mondiale (WDI), série {spec['wb_code']}",
        "obs_status": observation.get("obs_status_label", "actual"),
        "published_lastupdated": observation.get("lastupdated"),
    }
    if spec["conversion"]:
        proposed["value"] = round(raw_value * spec["conversion"], 1)
        proposed["unit"] = "Mds $"
        proposed["source"] += " · unité convertie US$ → Mds $"
        candidate["definition_notes"].append("unité convertie (US$ → Mds $) : conversion définie, sans ambiguïté")
    candidate["proposed"] = proposed

    # ---- règles de recommandation -----------------------------------------
    existing_year = candidate["existing"]["date"] if candidate["existing"] else None
    existing_year_int = int(str(existing_year)[:4]) if existing_year and str(existing_year)[:4].isdigit() else None
    proposed_year_int = _year_for_sort(observation)

    if is_new_country:
        candidate["recommendation"] = "manual"
        candidate["explanation"] = (
            "nouveau pays (expansion, aucun fichier de production) : définition à confirmer "
            "contre la future fiche et données croisées avec une seconde source officielle."
        )
        if proposed["obs_status"] != "actual":
            candidate["explanation"] += f" Attention: obs_status = {proposed['obs_status']}."
        return candidate

    # Comparaison à l'existant de production
    if spec["match"] == "partial" and indicator == "debt_gdp" and existing_year_int and proposed_year_int < existing_year_int:
        candidate["recommendation"] = "reject"
        candidate["explanation"] = (
            f"série « dette du gouvernement central » obsolète ({proposed['date']}) et définition sous-couverte "
            f"(gouvernement central ≠ dette générale) — conservé {existing_year}: {candidate['existing']['value']}."
        )
        return candidate

    if proposed["obs_status"] == "forecast":
        candidate["recommendation"] = "reject"
        candidate["explanation"] = "observation = prévision (F) : ne remplace pas une observation réelle."
        return candidate

    if existing_year_int is not None and proposed_year_int < existing_year_int:
        candidate["recommendation"] = "reject"
        candidate["explanation"] = (
            f"observation {proposed['date']} plus ancienne que la valeur existante ({existing_year}) — "
            "valeur conservée, écart (stale) signalé côté freshness."
        )
        return candidate

    if existing is None:
        candidate["recommendation"] = "manual"
        candidate["explanation"] = "pas d'existant dans la fiche : à intégrer manuellement après vérification."
        return candidate

    if spec["match"] == "partial" and indicator == "unemployment" and abs(proposed["value"] - float(candidate["existing"]["value"])) > 10:
        candidate["recommendation"] = "manual"
        candidate["explanation"] = (
            f"écart considérable avec la valeur existante ({candidate['existing']['value']} % vs {proposed['value']} %) : "
            f"série modélisée ILO pas encore ré-alignée sur la conjoncture de crise — croisement manuel OIT/FMI requis."
        )
        return candidate

    # définition incompatible clairement identifiée (ex. réserves nettes vs totales)
    if indicator == "reserves" and "nettes" in (candidate["existing"].get("note", "") + candidate["existing"].get("source", "")).lower():
        candidate["recommendation"] = "reject"
        candidate["explanation"] = (
            f"définitions incompatibles: la fiche documente des réserves NETTES ({candidate['existing']['value']} Mds $) "
            f"alors que la série WB est TOTALE (brut, or inclus) ({proposed['value']} Mds $) — ne pas écraser."
        )
        candidate["definition_notes"].append(spec["note"])
        return candidate

    # vérifications standard restantes : millésime plus récent, définition exacte
    if existing_year_int is None or proposed_year_int > existing_year_int:
        candidate["recommendation"] = "manual"
        candidate["explanation"] = (
            f"observation WDI {proposed['date']} ({proposed['value']} {proposed['unit']}) vs existant {existing_year} "
            f"({candidate['existing']['value']} {candidate['existing']['unit']}) : candidat sérieux — à valider "
            "manuellement (cohérence avec le 2e source avant application)."
        )
        if proposed["obs_status"] != "actual":
            candidate["explanation"] += f" obs_status = {proposed['obs_status']}."
        return candidate

    # même millésime : la production reste la référence ; la valeur WDI éclaire la provenance
    candidate["recommendation"] = "manual"
    candidate["explanation"] = (
        f"même millésime ({existing_year}) : valeur WDI {proposed['value']} vs existant "
        f"{candidate['existing']['value']} — arbitrage de provenance (WB/FMI) à valider manuellement avant de toucher la fiche."
    )
    return candidate


def candidate_pack(
    country_id: str,
    indicators: tuple[str, ...] = ("gdp_growth", "inflation", "unemployment", "debt_gdp", "reserves"),
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Construit tous les candidats d'un pays (fetch API réel)."""
    country = read_country(country_id)
    iso3 = _wb_country_code(country)
    pack = {"country": country_id, "iso3": iso3, "new_country": False, "candidates": []}
    for indicator in indicators:
        spec = INDICATOR_MAP[indicator]
        fetched = fetch_world_bank(iso3, spec["wb_code"], timeout=timeout)
        if not fetched["success"]:
            candidate = build_candidate(country, indicator, None, fetched.get("error"), False)
        else:
            latest = latest_actual(fetched["observations"])
            obs = dict(latest) if latest else None
            if obs:
                obs["lastupdated"] = fetched.get("lastupdated")
            candidate = build_candidate(country, indicator, obs, None, False)
        candidate["api_url"] = fetched.get("url")  # traçabilité : URL réelle de la requête
        pack["candidates"].append(candidate)
    return pack


def expand_candidate(
    snapshot_country: dict,
    indicator: str,
    observation: dict | None,
    fetch_error: str | None,
) -> dict:
    """Candidat pour un pays en expansion (pas encore en production).

    `snapshot_country` est un prototype de fiche (ex. Brésil) passé par le
    générateur de rapport — l'API ne fait que fournir les observations.
    """
    return build_candidate(snapshot_country, indicator, observation, fetch_error, is_new_country=True)


def pack_for_new_country(
    snapshot_country: dict,
    indicators: tuple[str, ...] = ("gdp_growth", "inflation", "unemployment", "debt_gdp", "reserves"),
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Candidats complets pour un pays hors production (ex. Brésil).

    `snapshot_country` doit au minimum porter `id` et `iso3` ; il n'existe
    aucun fichier de production correspondant — les candidats sont tous
    classés « manual » par construction.
    """
    iso3 = (snapshot_country.get("iso3") or snapshot_country.get("id", "")).upper()
    pack = {"country": snapshot_country.get("id", "?"), "iso3": iso3, "new_country": True, "candidates": []}
    for indicator in indicators:
        spec = INDICATOR_MAP[indicator]
        fetched = fetch_world_bank(iso3, spec["wb_code"], timeout=timeout)
        if fetched["success"]:
            latest = latest_actual(fetched["observations"])
            obs = {**latest, "lastupdated": fetched.get("lastupdated")} if latest else None
            candidate = expand_candidate(snapshot_country, indicator, obs, None)
        else:
            candidate = expand_candidate(snapshot_country, indicator, None, fetched.get("error"))
        candidate["api_url"] = fetched.get("url")
        pack["candidates"].append(candidate)
    return pack


# ---------------------------------------------------------------------------
# Génération du rapport candidats (écriture limitée à docs/)
# ---------------------------------------------------------------------------

REPORT_COUNTRY_IDS = ("lebanon", "syria")
BRAZIL_SNAPSHOT = {"id": "brazil", "iso3": "BRA", "name": "Brésil", "indicators": {}}
REPORT_INDICATORS = ("gdp_growth", "inflation", "unemployment", "debt_gdp", "reserves")
REPORT_MD_NAME = "REFRESH_CANDIDATES_BRA_LBN_SYR.md"
REPORT_JSON_NAME = "REFRESH_CANDIDATES_BRA_LBN_SYR.json"


def _docs_path(name: str) -> Path:
    """Chemin d'écriture autorisé : uniquement sous docs/ (protection production)."""
    path = (DOCS_DIR / name).resolve()
    if path.parent != DOCS_DIR.resolve():
        raise ValueError(f"écriture non autorisée hors docs/ : {path}")
    return path


def count_recommendations(candidates: list[dict]) -> dict[str, int]:
    """Comptage des recommandations d'une liste de candidats."""
    counts: dict[str, int] = {"safe": 0, "manual": 0, "reject": 0, "gap": 0}
    for candidate in candidates:
        key = candidate.get("recommendation")
        if key in counts:
            counts[key] += 1
    return counts


def _fmt_existing(candidate: dict) -> str:
    existing = candidate.get("existing")
    if not existing:
        return "— (absent)"
    return f"{existing['value']} {existing['unit']} · {existing['date']} · « {existing['source']} »"


def _fmt_proposed(candidate: dict) -> str:
    proposed = candidate.get("proposed")
    if not proposed:
        return "— (aucune observation exploitable)"
    status = proposed.get("obs_status", "actual")
    published = proposed.get("published_lastupdated") or "n/d"
    return (
        f"{proposed['value']} {proposed['unit']} · {proposed['date']} · obs_status={status} · "
        f"publication (dataupdated) : {published} · « {proposed['source']} »"
    )


def generate_report(
    country_ids: tuple[str, ...] = REPORT_COUNTRY_IDS,
) -> dict:
    """Génère le rapport candidats complet (md + json) sous docs/.

    Lecture seule sur data/countries/ ; toutes les écritures se font
    sous `docs/`. Retourne le rapport formaté (dict) pour inspection.
    """
    packs = [candidate_pack(cid) for cid in country_ids]
    packs.append(pack_for_new_country(BRAZIL_SNAPSHOT))
    retrieved = retrieval_date()
    all_candidates = [c for pack in packs for c in pack["candidates"]]
    counts = count_recommendations(all_candidates)
    report = {
        "retrieved": retrieved,
        "api": "Banque mondiale — Indicators API v2 (gratuite, sans clé)",
        "production_modified": False,
        "countries": packs,
        "counts": counts,
    }
    report_path = _docs_path(REPORT_MD_NAME)
    json_path = _docs_path(REPORT_JSON_NAME)
    lines = [
        "# Rapport candidats — rafraîchissement des données (Brésil, Liban, Syrie)",
        "",
        f"Date de récupération : **{retrieved}** · Source : Banque mondiale, Indicators API v2 (gratuite, sans clé).",
        "",
        "> **Statut du rapport : revue avant application.** Aucune donnée de production",
        "> (`data/countries/*.json`) n'a été modifiée. Chaque candidat porte une",
        "> recommandation (`safe` / `manual` / `reject` / `gap`) à arbitrer manuellement.",
        "",
        f"Comptage global : **{counts['safe']} safe · {counts['manual']} manual · "
        f"{counts['reject']} reject · {counts['gap']} gap** ({len(all_candidates)} candidats).",
        "",
    ]
    for pack in packs:
        title = pack["country"] + (" (pays candidat à l'expansion — aucun fichier de production)" if pack.get("new_country") else "")
        lines += [f"## {title}", ""]
        for candidate in pack["candidates"]:
            lines += [
                f"### {candidate['indicator']} ({candidate['country']})",
                f"- Série WB : `{candidate['wb_series']}` (correspondance : {candidate['wb_match']})",
                f"- Existant : {_fmt_existing(candidate)}",
                f"- Proposé : {_fmt_proposed(candidate)}",
                f"- Requête API : {candidate.get('api_url') or 'n/d'}",
                f"- Date de récupération : {candidate['retrieved']}",
            ]
            for note in candidate["definition_notes"]:
                lines.append(f"- Écart de définition : {note}")
            lines += [
                f"- **Recommandation : `{candidate['recommendation']}`** — {candidate['explanation']}",
                "",
            ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["paths"] = {"markdown": str(report_path), "json": str(json_path)}
    return report
