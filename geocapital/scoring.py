"""Moteur de score, de risque et de rendement exigé de GeoCapital.

Toutes les données chiffrées proviennent du fichier data/countries.json.
Les formules sont volontairement explicites et reproductibles.

Paramètres du modèle (Priorité 3 de la Phase 1 — refactorisation sans
calibration) : depuis ce commit, la source de vérité unique est
`data/meta.json` —
- `financial_params` : taux sans risque, ERP mature, bêta, ratio de
  volatilité actions/obligations (déjà présent, éventuellement sourcé) ;
- `scoring_model` : poids par profil, courbes de composantes, formule de
  risque, courbe CDS, paramètres CRP, tables rating/spread et seuils de
  verdict (signification de chaque clé : `docs/MODEL_PARAMS.md`).

Le chargement est strict : une section absente, incomplète ou incohérente
lève `ConfigError` (message pointant la clé fautive) au lieu de retomber
silencieusement sur des valeurs par défaut arbitraires. Les identifiants
affichables (libellés FR des composantes et des verdicts, icônes, copies
verdict/profil) restent dans le code : ce sont des libellés d'affichage,
pas des paramètres de calibration, et ils sont traduits côté i18n.
"""

from __future__ import annotations

import json
import math
from typing import Any

# Tolérance de cohérence pour les poids (somme = 1 ± ε).
_WEIGHT_EPS = 1e-9


class ConfigError(ValueError):
    """Configuration du modèle invalide ou incomplète dans data/meta.json."""


# Valeurs par défaut utilisées UNIQUEMENT pour l'échec explicite
# (aucun aval silencieux) : si `scoring_model` manque dans meta.json,
# ces vides restent vides et l'utilisateur voit une erreur explicite.
_ALLOWED_PROFILES = ("Prudent", "Équilibré", "Audacieux")
_COMPONENT_KEYS = ("dynamisme", "stabilite", "solvabilite", "institutions", "ouverture")

_PROFILE_DESCRIPTIONS = {
    "Prudent": "Priorité à la stabilité et à la capacité de rembourser.",
    "Équilibré": "Le bon compromis entre croissance, risque et gouvernance.",
    "Audacieux": "Recherche de croissance, tolérance au risque plus élevée.",
}

COMPONENT_LABELS = {
    "dynamisme": "Dynamisme économique",
    "stabilite": "Stabilité macro",
    "solvabilite": "Solvabilité",
    "institutions": "Institutions",
    "ouverture": "Ouverture & affaires",
}

VERDICT_STYLES = {
    "Investir": {"tone": "green", "icon": "↗", "copy": "Les fondamentaux compensent le risque."},
    "Investir avec prudence": {"tone": "lime", "icon": "→", "copy": "Le potentiel existe, mais la taille de position compte."},
    "Attendre": {"tone": "orange", "icon": "Ⅱ", "copy": "Le couple risque/rendement reste insuffisant."},
    "Éviter": {"tone": "red", "icon": "↘", "copy": "Le risque n'est pas correctement rémunéré."},
}


# ---------------------------------------------------------------------------
# Chargement / validation de la configuration (source de vérité = meta.json)
# ---------------------------------------------------------------------------

_config_cache: dict[str, dict[str, Any]] = {}
_config_signature: str = ""


def _fail(path: str, problem: str) -> None:
    raise ConfigError(f"meta.scoring_model.{path}: {problem}")


def _section(raw: dict[str, Any], path: str, kind: str = "dictionnaire", label: str | None = None) -> dict[str, Any]:
    value = raw.get(path)
    if not isinstance(value, dict):
        raise ConfigError(f"meta.{label or f'scoring_model.{path}'}: section absente (attendue : {kind})")
    return value


def _number(raw: dict[str, Any], path: str, low: float, high: float, prefix: str = "scoring_model") -> float:
    value = raw.get(path)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"meta.{prefix}.{path}: nombre attendu entre {low} et {high}, reçu: {value!r}")
    value = float(value)
    if not (low <= value <= high):
        raise ConfigError(f"meta.{prefix}.{path}: valeur {value} hors bornes [{low}, {high}]")
    return value


def _weights(raw: dict[str, Any], path: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        _fail(path, "table de poids (dictionnaire) attendue")
    checked: dict[str, float] = {}
    total = 0.0
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, (int, float)) or isinstance(value, bool):
            _fail(f"{path}.{key}", f"poids numérique attendu, reçu: {value!r}")
        if value < 0 or value > 1:
            _fail(f"{path}.{key}", f"poids {value} hors [0, 1]")
        checked[key] = float(value)
        total += float(value)
    if abs(total - 1.0) > _WEIGHT_EPS:
        detail = ", ".join(f"{k}={v}" for k, v in checked.items())
        _fail(path, f"la somme des poids vaut {total} au lieu de 1 ({detail})")
    return checked


def _range_pair(raw: list[Any], path: str, low: float, high: float) -> tuple[float, float]:
    if not isinstance(raw, list) or len(raw) != 2:
        _fail(path, "liste de 2 bornes [basse, haute] attendue")
    lo, hi = raw
    for bound in (lo, hi):
        if not isinstance(bound, (int, float)) or isinstance(bound, bool):
            _fail(path, f"bornes numériques attendues, reçu: {raw!r}")
    lo, hi = float(lo), float(hi)
    if not (low <= lo < hi <= high):
        _fail(path, f"bornes {lo} ; {hi} invalides (attendu {low} <= basse < haute <= {high})")
    return lo, hi


def _validate_financial_params(meta: dict[str, Any]) -> dict[str, float]:
    """`financial_params` (existant) devient paramètres du modèle : strict."""
    params = meta.get("financial_params")
    if not isinstance(params, dict):
        raise ConfigError("meta.financial_params: section absente (taux sans risque, ERP, bêta, ratio)")
    spec = (
        ("risk_free_rate", 0.0, 20.0),
        ("mature_erp", 0.0, 20.0),
        ("beta", 0.0, 5.0),
        ("equity_bond_vol_ratio", 1.0, 5.0),
    )
    out: dict[str, float] = {}
    for key, low, high in spec:
        out[key] = _number(params, key, low, high, prefix="financial_params")
    return out


def validate_model_params(meta: dict[str, Any]) -> dict[str, Any]:
    """Charge et valide `scoring_model` (+ financial_params) depuis meta.

    Lève ConfigError avec le chemin exact de la clé fautive. Retourne un
    dictionnaire figé de sous-sections validées utilisé par tout le moteur.
    """
    model = _section(meta, "scoring_model", label="scoring_model")
    financial = _validate_financial_params(meta)

    profiles_raw = _section(model, "profiles")
    profiles: dict[str, dict[str, Any]] = {}
    for name in _ALLOWED_PROFILES:
        node = profiles_raw.get(name)
        if not isinstance(node, dict):
            _fail(f"profiles.{name}", "profil attendu (dictionnaire de poids)")
        weights = _weights(node.get("weights"), f"profiles.{name}.weights")
        missing = [key for key in _COMPONENT_KEYS if key not in weights]
        if missing:
            _fail(f"profiles.{name}.weights", f"composantes manquantes: {', '.join(missing)}")
        unexpected = [key for key in weights if key not in _COMPONENT_KEYS]
        if unexpected:
            _fail(f"profiles.{name}.weights", f"composantes inconnues: {', '.join(unexpected)}")
        profiles[name] = {"label": name, "description": _PROFILE_DESCRIPTIONS[name], "weights": weights}

    components_raw = _section(model, "components")
    missing_qualitative = _number(
        model["components"], "missing_qualitative_score", 0.0, 100.0, prefix="scoring_model.components"
    )

    components: dict[str, Any] = {"missing_qualitative_score": missing_qualitative}
    # Sous-poids attendus par composante (validés : présence + somme = 1).
    _SUB_WEIGHTS: dict[str, tuple[str, ...]] = {
        "dynamisme": ("growth", "unemployment", "outlook"),
        "stabilite": ("inflation", "policy_rate", "currency"),
        "solvabilite": ("debt", "rating", "cds"),
        "institutions": ("governance", "resilience"),
        "ouverture": ("business", "openness"),
    }
    # Sous-clés numériques attendues par composante. Les paliers « other »
    # (stabilite : real_rate_*) sont validés dans le cas dédié ci-dessous.
    _RANGE_FIELDS: dict[str, tuple[str, ...]] = {
        "dynamisme": ("growth_range", "unemployment_range"),
        "solvabilite": ("debt_range",),
    }
    for key in _COMPONENT_KEYS:
        node = components_raw.get(key)
        if not isinstance(node, dict):
            _fail(f"components.{key}", "section de composante attendue")
        required = _SUB_WEIGHTS[key]
        checked_weights = _weights(node.get("weights"), f"components.{key}.weights")
        missing = [k for k in required if k not in checked_weights]
        if missing:
            _fail(f"components.{key}.weights", f"sous-poids manquants: {', '.join(missing)}")
        stored: dict[str, Any] = {"weights": checked_weights}
        # sous-poids optionnels (mélange dynamisme : stabilite.<…>)
        if key == "stabilite":
            stored["inflation_target"] = _number(node, "inflation_target", 0.0, 15.0, prefix=f"scoring_model.components.{key}")
            stored["inflation_sensitivity"] = _number(node, "inflation_sensitivity", 0.1, 50.0, prefix=f"scoring_model.components.{key}")
            bands_raw = node.get("real_rate_bands")
            if not isinstance(bands_raw, list) or not bands_raw:
                _fail("components.stabilite.real_rate_bands", "liste de paliers [bas, haut, score] attendue")
            bands = []
            for index, band in enumerate(bands_raw):
                if not isinstance(band, list) or len(band) != 3:
                    _fail(f"components.stabilite.real_rate_bands[{index}]", "palier [bas, haut, score] attendu")
                low, high, score = band
                if not isinstance(low, (int, float)) or isinstance(low, bool) or not isinstance(high, (int, float)) or isinstance(high, bool):
                    _fail(f"components.stabilite.real_rate_bands[{index}]", "bornes numériques attendues")
                if not isinstance(score, (int, float)) or isinstance(score, bool) or not (0 <= score <= 100):
                    _fail(f"components.stabilite.real_rate_bands[{index}].score", f"score 0-100 attendu, reçu: {score!r}")
                if low >= high:
                    _fail(f"components.stabilite.real_rate_bands[{index}]", "borne haute doit dépasser la borne basse")
                bands.append([float(low), float(high), float(score)])
            stored["real_rate_bands"] = bands
            stored["real_rate_outside_score"] = _number(node, "real_rate_outside_score", 0.0, 100.0, prefix=f"scoring_model.components.{key}")
        if key in {"dynamisme", "solvabilite"}:
            ranges = {}
            for field in _RANGE_FIELDS[key]:
                low, high = _range_pair(node.get(field), f"components.{key}.{field}", -100.0, 1000.0)
                ranges[field] = (low, high)
            stored["ranges"] = ranges
        components[key] = stored

    risk_raw = _section(model, "risk")
    bands_size = 3
    bands = risk_raw.get("bands")
    if not isinstance(bands, list) or len(bands) != bands_size or not all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in bands
    ):
        _fail("risk.bands", f"3 seuils numériques croissants attendus (reçu: {bands!r})")
    band_values = [float(item) for item in bands]
    if not all(band_values[i] < band_values[i + 1] for i in range(len(band_values) - 1)):
        _fail("risk.bands", f"seuils non croissants: {band_values}")
    risk = {
        "weights": _weights(risk_raw.get("weights"), "risk.weights"),
        "volatility_base": _number(risk_raw, "volatility_base", 0.0, 100.0, prefix="scoring_model.risk"),
        "volatility_slope": _number(risk_raw, "volatility_slope", 0.0, 10.0, prefix="scoring_model.risk"),
        "bands": band_values,
    }

    cds_raw = model.get("cds_score")
    if not isinstance(cds_raw, dict):
        _fail("cds_score", "section attendue (courbe de score CDS)")
    cds_curve = {
        "none_score": _number(cds_raw, "none_score", 0.0, 100.0, prefix="scoring_model.cds_score"),
        "floor_pb": _number(cds_raw, "floor_pb", 0.1, 1000.0, prefix="scoring_model.cds_score"),
        "log10_ceiling_ratio": _number(cds_raw, "log10_ceiling_ratio", 1.0, 1000.0, prefix="scoring_model.cds_score"),
        "spread": _number(cds_raw, "spread", 0.0, 100.0, prefix="scoring_model.cds_score"),
    }

    crp_raw = model.get("crp")
    if not isinstance(crp_raw, dict):
        _fail("crp", "section attendue (paramètres de la prime de risque pays)")
    crp = {
        "cds_offset_pb": _number(crp_raw, "cds_offset_pb", 0.0, 500.0, prefix="scoring_model.crp"),
        "cds_divisor": _number(crp_raw, "cds_divisor", 0.1, 1000.0, prefix="scoring_model.crp"),
    }

    ratings_raw = model.get("ratings")
    if not isinstance(ratings_raw, dict):
        _fail("ratings", "section attendue (tables scores/spreads de notation)")
    ratings_scores = ratings_raw.get("scores")
    ratings_spreads = ratings_raw.get("spreads")
    if not isinstance(ratings_scores, dict) or not isinstance(ratings_spreads, dict):
        _fail("ratings", "tables `scores` et `spreads` (dictionnaires) attendues")
    if set(ratings_scores) != set(ratings_spreads):
        _fail("ratings", "les tables scores et spreads doivent couvrir les mêmes notations")
    rating_scores_f: dict[str, float] = {}
    for grade, value in ratings_scores.items():
        if not isinstance(grade, str) or not isinstance(value, (int, float)) or isinstance(value, bool):
            _fail(f"ratings.scores.{grade}", "score numérique attendu par note")
        if not (0 <= value <= 100):
            _fail(f"ratings.scores.{grade}", f"score {value} hors [0, 100]")
        rating_scores_f[grade] = float(value)
    rating_spreads_f: dict[str, float] = {}
    for grade, value in ratings_spreads.items():
        if not isinstance(grade, str) or not isinstance(value, (int, float)) or isinstance(value, bool):
            _fail(f"ratings.spreads.{grade}", "spread numérique attendu par note")
        if not (0 <= value <= 100):
            _fail(f"ratings.spreads.{grade}", f"spread {value} hors [0, 100]")
        rating_spreads_f[grade] = float(value)
    ratings = {
        "scores": rating_scores_f,
        "spreads": rating_spreads_f,
        "default_score": _number(ratings_raw, "default_score", 0.0, 100.0, prefix="scoring_model.ratings"),
        "default_spread": _number(ratings_raw, "default_spread", 0.0, 100.0, prefix="scoring_model.ratings"),
    }

    verdicts_raw = model.get("verdicts")
    if not isinstance(verdicts_raw, dict):
        _fail("verdicts", "section attendue (seuils de verdict)")
    invest_min = _number(verdicts_raw, "invest_min", 0.0, 100.0, prefix="scoring_model.verdicts")
    caution_min = _number(verdicts_raw, "caution_min", 0.0, 100.0, prefix="scoring_model.verdicts")
    wait_min = _number(verdicts_raw, "wait_min", 0.0, 100.0, prefix="scoring_model.verdicts")
    rescue_score = _number(verdicts_raw, "wait_rescue_score", 0.0, 100.0, prefix="scoring_model.verdicts")
    rescue_gate = _number(verdicts_raw, "wait_rescue_dynamisme", 0.0, 100.0, prefix="scoring_model.verdicts")
    if not (rescue_score <= wait_min <= caution_min <= invest_min):
        _fail("verdicts", f"seuils non ordonnés: {rescue_score} <= {wait_min} <= {caution_min} <= {invest_min} attendus")
    blocked = verdicts_raw.get("blocking_ratings")
    if not isinstance(blocked, list) or not all(isinstance(rate, str) for rate in blocked):
        _fail("verdicts.blocking_ratings", "liste de codes de notation attendue (ex. NR, D, RD)")
    verdicts = {
        "invest_min": invest_min,
        "caution_min": caution_min,
        "wait_min": wait_min,
        "wait_rescue_score": rescue_score,
        "wait_rescue_dynamisme": rescue_gate,
        "blocking_ratings": frozenset(blocked),
    }

    return {
        "financial": financial,
        "profiles": profiles,
        "components": components,
        "risk": risk,
        "cds_score": cds_curve,
        "crp": crp,
        "ratings": ratings,
        "verdicts": verdicts,
    }


def model() -> dict[str, Any]:
    """Configuration validée du modèle (mémoisée par signature de contenu).

    Lit `data.load_data()` à chaque appel (module attribute, jamais lié à
    l'import : cf. tests mockant `load_data`), ne revalide que si le
    contenu brut a changé.
    """
    global _config_signature

    import geocapital.data as _data

    meta = _data.load_data()
    signature = json.dumps(
        {"scoring_model": meta.get("scoring_model"), "financial_params": meta.get("financial_params")},
        sort_keys=True,
        default=str,
    )
    if signature != _config_signature:
        _config_cache.clear()
        _config_cache["valid"] = validate_model_params(meta)
        _config_signature = signature
    return _config_cache["valid"]


def reset_model_cache() -> None:
    """Force une relecture de meta.json (usage : réinitialisation en test)."""
    global _config_signature
    _config_cache.clear()
    _config_signature = ""


# Constantes historiques résolues à la volée depuis la configuration
# (compatibilité : méthodology_page, tests, analyst payloads) — il n'y a
# désormais qu'une définition numérique, dans data/meta.json.
def __getattr__(name: str) -> Any:
    if name in {"RISK_FREE_RATE", "MATURE_ERP", "BETA", "EQUITY_BOND_VOL_RATIO"}:
        mapping = {
            "RISK_FREE_RATE": "risk_free_rate",
            "MATURE_ERP": "mature_erp",
            "BETA": "beta",
            "EQUITY_BOND_VOL_RATIO": "equity_bond_vol_ratio",
        }
        return model()["financial"][mapping[name]]
    if name == "PROFILES":
        return model()["profiles"]
    if name == "RATING_SCORES":
        return model()["ratings"]["scores"]
    if name == "DEFAULT_SPREADS":
        return model()["ratings"]["spreads"]
    raise AttributeError(f"module 'geocapital.scoring' has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Formules (inchangées — seules les valeurs viennent de la configuration)
# ---------------------------------------------------------------------------

def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def linear(value: float, low: float, high: float, reverse: bool = False) -> float:
    """Transforme une valeur en score 0-100 sur un intervalle."""
    if high == low:
        return 50.0
    score = (value - low) / (high - low) * 100
    score = clamp(score)
    return 100 - score if reverse else score


def _get_indicator(country: dict[str, Any], key: str) -> dict[str, Any]:
    return country.get("indicators", {}).get(key, {}) or {}


def _numeric(country: dict[str, Any], key: str, default: float | None = None) -> float | None:
    raw = _get_indicator(country, key).get("value")
    if raw is None or isinstance(raw, str):
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def rating_of(country: dict[str, Any]) -> str:
    return str(_get_indicator(country, "rating").get("value") or "NR")


def rating_score(country: dict[str, Any]) -> float:
    cfg = model()["ratings"]
    return float(cfg["scores"].get(rating_of(country), cfg["default_score"]))


def cds_score(cds: float | None) -> float:
    """Score CDS : plafond à floor_pb (proche), quasi nul au-delà plafond×ratio."""
    curve = model()["cds_score"]
    if cds is None:
        return float(curve["none_score"])
    floor = float(curve["floor_pb"])
    if cds <= floor:
        return 100.0
    log_position = math.log10(max(cds, floor) / floor) / math.log10(float(curve["log10_ceiling_ratio"]))
    return clamp(100 - log_position * float(curve["spread"]))


def default_spread(country: dict[str, Any]) -> float:
    cfg = model()["ratings"]
    return float(cfg["spreads"].get(rating_of(country), cfg["default_spread"]))


def country_risk_premium(country: dict[str, Any]) -> tuple[float, str]:
    """Prime de risque pays en %, méthode Damodaran.

    On retient le maximum entre le spread de notation et le spread CDS,
    puis on applique le ratio de volatilité actions/obligations.
    """
    cfg = model()
    ratio = float(cfg["financial"]["equity_bond_vol_ratio"])
    cds_offset = float(cfg["crp"]["cds_offset_pb"])
    cds_divisor = float(cfg["crp"]["cds_divisor"])
    cds = _numeric(country, "cds")
    cds_crp = max(0.0, ((cds or 0.0) - cds_offset) / cds_divisor) * ratio
    rating_crp = default_spread(country) * ratio
    if cds is None:
        return round(rating_crp, 2), "Notation (CDS non coté)"
    if cds_crp >= rating_crp:
        return round(cds_crp, 2), "CDS"
    return round(rating_crp, 2), "Notation"


def required_return(country: dict[str, Any]) -> dict[str, float | str]:
    financial = model()["financial"]
    risk_free = float(financial["risk_free_rate"])
    mature_erp = float(financial["mature_erp"])
    beta = float(financial["beta"])
    crp, source = country_risk_premium(country)
    ke = risk_free + beta * mature_erp + crp
    return {
        "risk_free": risk_free,
        "erp": mature_erp,
        "beta": beta,
        "crp": crp,
        "crp_source": source,
        "ke": round(ke, 2),
    }


def indicator_status(country: dict[str, Any], key: str) -> str:
    """Retourne green / orange / red pour le tableau de bord."""
    c = country
    if key == "gdp_growth":
        value = _numeric(c, key, 0) or 0
        return "green" if value >= 3 else "orange" if value >= 1 else "red"
    if key == "inflation":
        value = _numeric(c, key, 0) or 0
        return "green" if 0.5 <= value <= 3.5 else "orange" if 0 <= value <= 7 else "red"
    if key == "debt_gdp":
        value = _numeric(c, key, 0) or 0
        return "green" if value <= 60 else "orange" if value <= 100 else "red"
    if key == "policy_rate":
        nominal = _numeric(c, key, 0) or 0
        inflation = _numeric(c, "inflation", 0) or 0
        real = nominal - inflation
        if nominal > 20 or real < -8:
            return "red"
        if nominal > 10 or real < -3 or real > 4:
            return "orange"
        return "green"
    if key == "unemployment":
        value = _numeric(c, key, 0) or 0
        return "green" if value <= 6 else "orange" if value <= 10 else "red"
    if key == "reserves":
        value = _numeric(c, key, 0) or 0
        stability = c.get("qualitative", {}).get("currency_stability", 50)
        if value >= 100 or stability >= 80:
            return "green"
        if value >= 20:
            return "orange"
        return "red"
    if key == "rating":
        score = rating_score(c)
        return "green" if score >= 80 else "orange" if score >= 50 else "red"
    if key == "cds":
        value = _numeric(c, key)
        if value is None:
            return "red"
        return "green" if value <= 100 else "orange" if value <= 300 else "red"
    if key == "crp":
        value = country_risk_premium(c)[0]
        return "green" if value <= 2 else "orange" if value <= 6 else "red"
    if key == "equity_index":
        value = _get_indicator(c, key).get("perf_1y", 0) or 0
        return "green" if value >= 0 else "orange" if value >= -10 else "red"
    if key == "currency":
        stability = c.get("qualitative", {}).get("currency_stability", 50)
        return "green" if stability >= 70 else "orange" if stability >= 45 else "red"
    return "orange"


def component_scores(country: dict[str, Any]) -> dict[str, float]:
    cfg = model()["components"]
    qualitative_default = float(cfg["missing_qualitative_score"])
    growth = _numeric(country, "gdp_growth", 0) or 0
    unemployment = _numeric(country, "unemployment", 0) or 0
    inflation = _numeric(country, "inflation", 0) or 0
    policy = _numeric(country, "policy_rate", 0) or 0
    debt = _numeric(country, "debt_gdp", 0) or 0
    cds = _numeric(country, "cds")
    q = country.get("qualitative", {})

    def q_value(key: str) -> float:
        value = q.get(key, qualitative_default)
        return qualitative_default if value is None else float(value)

    growth_low, growth_high = cfg["dynamisme"]["ranges"]["growth_range"]
    unemployment_low, unemployment_high = cfg["dynamisme"]["ranges"]["unemployment_range"]
    growth_weights = cfg["dynamisme"]["weights"]
    growth_s = linear(growth, growth_low, growth_high)
    unemployment_s = linear(unemployment, unemployment_low, unemployment_high, reverse=True)
    outlook_s = q_value("outlook")
    inflation_values = cfg["stabilite"]
    inflation_s = clamp(
        100 - abs(inflation - float(inflation_values["inflation_target"])) * float(inflation_values["inflation_sensitivity"])
    )
    real_rate = policy - inflation
    rate_s: float = float(inflation_values["real_rate_outside_score"])
    for low, high, score in inflation_values["real_rate_bands"]:
        if low <= real_rate <= high:
            rate_s = score
            break
    currency_s = q_value("currency_stability")
    debt_low, debt_high = cfg["solvabilite"]["ranges"]["debt_range"]
    debt_s = linear(debt, debt_low, debt_high, reverse=True)
    rating_s = rating_score(country)
    cds_s = cds_score(cds)
    governance_s = q_value("governance")
    resilience_s = q_value("resilience")
    business_s = q_value("business")
    openness_s = q_value("openness")

    dw = cfg["dynamisme"]["weights"]
    sw = cfg["stabilite"]["weights"]
    solw = cfg["solvabilite"]["weights"]
    iw = cfg["institutions"]["weights"]
    ow = cfg["ouverture"]["weights"]

    return {
        "dynamisme": round(dw["growth"] * growth_s + dw["unemployment"] * unemployment_s + dw["outlook"] * outlook_s, 1),
        "stabilite": round(sw["inflation"] * inflation_s + sw["policy_rate"] * rate_s + sw["currency"] * currency_s, 1),
        "solvabilite": round(solw["debt"] * debt_s + solw["rating"] * rating_s + solw["cds"] * cds_s, 1),
        "institutions": round(iw["governance"] * governance_s + iw["resilience"] * resilience_s, 1),
        "ouverture": round(ow["business"] * business_s + ow["openness"] * openness_s, 1),
    }


def overall_score(country: dict[str, Any], profile: str = "Équilibré") -> dict[str, Any]:
    cfg = model()
    valid_profiles = cfg["profiles"]
    profile = profile if profile in valid_profiles else "Équilibré"
    weights = valid_profiles[profile]["weights"]
    components = component_scores(country)
    score = sum(components[key] * weights[key] for key in weights)
    risk_weights = cfg["risk"]["weights"]
    risk = clamp(
        100
        - (risk_weights["stabilite"] * components["stabilite"]
           + risk_weights["solvabilite"] * components["solvabilite"]
           + risk_weights["institutions"] * components["institutions"])
    )
    volatility_base = float(cfg["risk"]["volatility_base"])
    volatility_slope = float(cfg["risk"]["volatility_slope"])
    volatility = round(volatility_base + risk * volatility_slope, 1)
    ke = required_return(country)
    verdict, verdict_reason = decide_verdict(score, components, country)
    return {
        "score": round(score, 1),
        "profile": profile,
        "weights": weights,
        "components": components,
        "risk": round(risk, 1),
        "volatility": volatility,
        "ke": ke,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }


def decide_verdict(score: float, components: dict[str, float], country: dict[str, Any]) -> tuple[str, str]:
    verdicts = model()["verdicts"]
    # Un pays sans notation active ni CDS ne peut pas être "Investir".
    missing_market_signal = rating_of(country) in verdicts["blocking_ratings"] and _numeric(country, "cds") is None
    if score >= verdicts["invest_min"] and not missing_market_signal:
        return "Investir", VERDICT_STYLES["Investir"]["copy"]
    if score >= verdicts["caution_min"] and not missing_market_signal:
        return "Investir avec prudence", VERDICT_STYLES["Investir avec prudence"]["copy"]
    if score >= verdicts["wait_min"] or (
        score >= verdicts["wait_rescue_score"] and components["dynamisme"] >= verdicts["wait_rescue_dynamisme"]
    ):
        return "Attendre", VERDICT_STYLES["Attendre"]["copy"]
    return "Éviter", VERDICT_STYLES["Éviter"]["copy"]


def score_breakdown(country: dict[str, Any], profile: str = "Équilibré") -> list[dict[str, Any]]:
    result = overall_score(country, profile)
    rows = []
    for key, label in COMPONENT_LABELS.items():
        weight = result["weights"][key]
        raw = result["components"][key]
        rows.append(
            {
                "key": key,
                "label": label,
                "score": raw,
                "weight": weight,
                "contribution": round(raw * weight, 1),
                "max": round(weight * 100, 1),
            }
        )
    return rows


def top_reasons(country: dict[str, Any], profile: str = "Équilibré", limit: int = 3) -> list[dict[str, str]]:
    """Deux forces structurantes + le principal point de vigilance."""
    result = overall_score(country, profile)
    components = result["components"]
    strengths = sorted(
        ((key, value) for key, value in components.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    weakness = min(components.items(), key=lambda item: item[1])
    reasons: list[dict[str, str]] = []
    for key, value in strengths[:2]:
        reasons.append(
            {
                "kind": "positive",
                "title": COMPONENT_LABELS[key],
                "text": f"Score de {value:.0f}/100. {_component_comment(key, value, positive=True)}",
            }
        )
    reasons.append(
        {
            "kind": "negative",
            "title": f"Point de vigilance : {COMPONENT_LABELS[weakness[0]]}",
            "text": f"Score de {weakness[1]:.0f}/100. {_component_comment(weakness[0], weakness[1], positive=False)}",
        }
    )
    return reasons[:limit]


def _component_comment(key: str, value: float, positive: bool) -> str:
    if key == "dynamisme":
        return "La croissance, l'emploi et l'élan économique soutiennent la demande." if positive else "Le moteur de croissance est fragile, ce qui réduit la visibilité."
    if key == "stabilite":
        return "L'inflation, le taux directeur et la devise forment un cadre prévisible." if positive else "L'inflation ou la devise rendent le cadre macroéconomique moins lisible."
    if key == "solvabilite":
        return "La dette, la notation et les CDS signalent une capacité de remboursement crédible." if positive else "La dette ou l'absence de prix de marché pèsent sur la signature souveraine."
    if key == "institutions":
        return "La gouvernance et la capacité de rebond historique rassurent l'investisseur." if positive else "La gouvernance et la continuité institutionnelle restent des angles morts."
    return "L'ouverture et le climat des affaires facilitent l'implantation." if positive else "Les frictions administratives ou commerciales renchérissent l'entrée."


def status_label(status: str) -> str:
    return {"green": "Solide", "orange": "Vigilance", "red": "Risque"}.get(status, "Vigilance")


def risk_label(risk: float) -> str:
    bands = model()["risk"]["bands"]
    low, medium, high = bands
    if risk < low:
        return "Faible"
    if risk < medium:
        return "Modéré"
    if risk < high:
        return "Élevé"
    return "Très élevé"


def correlation(group_a: str, group_b: str) -> float:
    if group_a == group_b:
        return 0.80 if group_a != "frontier" else 0.60
    pair = {group_a, group_b}
    if pair == {"developed", "emerging"}:
        return 0.55
    if pair == {"developed", "gulf"}:
        return 0.50
    if pair == {"developed", "frontier"}:
        return 0.30
    if pair == {"emerging", "gulf"}:
        return 0.60
    if pair == {"emerging", "frontier"}:
        return 0.40
    if pair == {"gulf", "frontier"}:
        return 0.35
    return 0.45


def portfolio_metrics(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcule rendement exigé, volatilité et diversification d'un portefeuille.

    holdings: [{"country": country_dict, "weight": 0.25, "amount": 25000}, ...]
    """
    active = [h for h in holdings if h.get("weight", 0) > 0]
    total_weight = sum(h["weight"] for h in active)
    if total_weight <= 0:
        return {
            "expected_return": 0,
            "volatility": 0,
            "diversification": 0,
            "hhi": 0,
            "effective_countries": 0,
            "top_weight": 0,
            "top_country": "—",
            "weighted_vol": 0,
        }
    normalized = [{**h, "weight": h["weight"] / total_weight} for h in active]
    expected = sum(h["weight"] * required_return(h["country"])["ke"] for h in normalized)
    weighted_vol = sum(h["weight"] * overall_score(h["country"])["volatility"] for h in normalized)
    variance = 0.0
    for i, hi in enumerate(normalized):
        for j, hj in enumerate(normalized):
            sigma_i = overall_score(hi["country"])["volatility"]
            sigma_j = overall_score(hj["country"])["volatility"]
            rho = 1.0 if i == j else correlation(hi["country"]["group_key"], hj["country"]["group_key"])
            variance += hi["weight"] * hj["weight"] * sigma_i * sigma_j * rho
    volatility = math.sqrt(max(variance, 0))
    hhi = sum(h["weight"] ** 2 for h in normalized)
    top = max(normalized, key=lambda h: h["weight"])
    return {
        "expected_return": round(expected, 2),
        "volatility": round(volatility, 1),
        "diversification": round(weighted_vol - volatility, 1),
        "hhi": round(hhi, 3),
        "effective_countries": round(1 / hhi, 1) if hhi else 0,
        "top_weight": round(top["weight"] * 100, 1),
        "top_country": top["country"]["name"],
        "weighted_vol": round(weighted_vol, 1),
    }
