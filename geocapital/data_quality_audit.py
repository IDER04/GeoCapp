"""Data-quality audit (review-first) — Priority 7, increment 7.1.

Generates:
- ``data/audit/data_quality_audit.json`` — machine-readable matrix;
- ``docs/DATA_QUALITY_AUDIT.md`` — human-readable report derived from it.

Increment guarantees:
- **writes nothing** outside ``docs/`` and ``data/audit/``; production
  (``data/countries/*.json``, ``data/meta.json``) is not modified, and
  neither are scoring formulas/parameters or app behavior — this module
  only READS;
- statuses are derived deterministically from the real metadata; a
  missing ``source_url``/``retrieved`` field is distinguished from a
  genuinely missing value;
- conflicts come only from existing documentation
  (``docs/REFRESH_REVIEW.md``, ``docs/DATA_REFRESH_PLAN.md`` §8) —
  no conflict is invented here;
- scoring influence reflects ``geocapital/scoring.py`` and
  ``data/meta.json::scoring_model`` — never an assumed weight;
- a sixth status ``unverified`` (beyond the five requested) is reserved
  for the case "recent observation but no per-observation provenance";
  it is explicitly documented as an extension in this docstring, in the
  JSON, and in the report.

Run: ``python3 -m geocapital.data_quality_audit``
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
from typing import Any

from geocapital import data, freshness, scoring

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
AUDIT_DIR = ROOT / "data" / "audit"
AUDIT_JSON = AUDIT_DIR / "data_quality_audit.json"
AUDIT_MD = DOCS_DIR / "DATA_QUALITY_AUDIT.md"

MONTH_PREFIX_RE = re.compile(r"^(déc|oct|nov|janv|févr|mars|avr|mai|juin|juil|août|sept)", re.IGNORECASE)

# ------------------------------------------------------------------ statuses

STATUS_VERIFIED = "verified"
STATUS_STALE = "stale"
STATUS_ESTIMATED = "estimated"
STATUS_CONFLICTING = "conflicting"
STATUS_MISSING = "missing"
STATUS_UNVERIFIED = "unverified"  # documented extension (see docstring)

ALL_STATUSES = frozenset(
    {STATUS_VERIFIED, STATUS_STALE, STATUS_ESTIMATED, STATUS_CONFLICTING, STATUS_MISSING, STATUS_UNVERIFIED}
)

# Keywords marking an explicitly estimated/modelled source (checked in the
# `source` field text only — never inferred from narrative `note` text).
ESTIMATE_KEYWORDS = ("estimat", "OIT", "ILO", "modélis")

# Documented conflicts — exhaustive list from docs/REFRESH_REVIEW.md
# (entries 1-3 + annex) and docs/DATA_REFRESH_PLAN.md §8. Nothing else.
DOCUMENTED_CONFLICTS: dict[tuple[str, str], str] = {
    ("lebanon", "gdp_growth"): (
        "IMF WEO −5.2 (2024) vs World Bank WDI+LEM −7.1 vs production −6.5 (IMF) — "
        "docs/REFRESH_REVIEW.md entry 1 (seek_better_source)."
    ),
    ("lebanon", "unemployment"): (
        "Production 30 (2024) vs ILO modelled 11.0 (2023; WDI 2024/25 null) vs MPO April 2026 ≈22.8 — "
        "docs/REFRESH_REVIEW.md annex + docs/DATA_REFRESH_PLAN.md §8.2."
    ),
    ("syria", "unemployment"): (
        "Production 50 (« Estimation OIT », citation never traceable) vs ILO modelled 13.6 (2025) vs "
        "EUAA COI ≈24 (2024) — docs/REFRESH_REVIEW.md entry 3 + docs/DATA_REFRESH_PLAN.md §8.3."
    ),
}


def source_text_is_estimate(source_text: Any) -> bool:
    text = str(source_text or "").lower()
    return any(keyword.lower() in text for keyword in ESTIMATE_KEYWORDS)


QUALITATIVE_KEYS = ("outlook", "currency_stability", "governance", "resilience", "business", "openness")

# ------------------------------------------ PROPOSED freshness thresholds
# (separate review: `geocapital/freshness.py` and displayed labels are NOT
# modified in this increment.)
PROPOSED_FRESHNESS_THRESHOLDS: dict[str, Any] = {
    "annual_macro": {
        "keys": ["gdp_growth", "inflation", "unemployment", "debt_gdp"],
        "current_rule_is_adequate": True,
        "proposed": "keep the uniform rule: ⚠ if observation year < current year − 1",
        "rationale": "national accounts, CPI, unemployment and debt are published as annual vintages; the current uniform threshold matches that granularity.",
    },
    "policy_rate": {
        "keys": ["policy_rate"],
        "current_rule_is_adequate": False,
        "proposed": "⚠ if the decision is older than ~3 months; require the exact decision date (not « 2024 »).",
        "rationale": "the policy rate is the most volatile datum in the corpus; an annual vintage hides dated revisions.",
    },
    "rating": {
        "keys": ["rating"],
        "current_rule_is_adequate": False,
        "proposed": "re-verify agency matrices every ~6 months (actions/outlooks); deliberate NR (LBN/SYR) preserved unless contradicted by evidence.",
        "rationale": "interim agency actions (outlooks) are more frequent than the annual cycle.",
    },
    "cds": {
        "keys": ["cds"],
        "current_rule_is_adequate": False,
        "proposed": "if quoted: keep a quote date; if unquoted: documented absence treated as a deliberate signal (never « stale »).",
        "rationale": "near-daily series; the absence of a market remains the model's chosen signal.",
    },
    "market_levels": {
        "keys": ["reserves", "equity_index", "currency"],
        "current_rule_is_adequate": False,
        "proposed": "monthly reserves (⚠ once the published quarter has passed); 1-year performance recomputed at least quarterly.",
        "rationale": "reserves are published monthly; rolling performances have no meaningful annual vintage.",
    },
    "qualitative": {
        "keys": ["qualitative:*"],
        "current_rule_is_adequate": False,
        "proposed": "dated annual review (a `reviewed` field to introduce), never automatically « stale ».",
        "rationale": "editorial assessments are not observations; their age is not a market vintage.",
    },
}

# ------------------------------------------------------------ influence map

def scoring_influence(indicator_key: str, meta: dict[str, Any]) -> dict[str, Any]:
    """Real scoring influence (code + meta.json), per indicator key.

    Returns ``role: display_only`` when the indicator enters no formula —
    never an invented weight.
    """
    sm = meta["scoring_model"]
    profiles = sm["profiles"]
    comps = sm["components"]
    stab_w = comps["stabilite"]["weights"]
    dyn_w = comps["dynamisme"]["weights"]
    sol_w = comps["solvabilite"]["weights"]
    inst_w = comps["institutions"]["weights"]
    ouv_w = comps["ouverture"]["weights"]
    risk_w = sm["risk"]["weights"]
    verdicts = sm["verdicts"]

    def base(component: str, sub_weight: float) -> dict[str, Any]:
        return {
            "role": "component_input",
            "component": component,
            "sub_weight": sub_weight,
            "profile_component_weights": {p: profiles[p]["weights"][component] for p in ("Prudent", "Équilibré", "Audacieux")},
            "risk_component_weight": risk_w.get(component),
            "risk": component in risk_w,
            "verdict_paths": ["verdict thresholds via the score"],
        }

    if indicator_key == "gdp_growth":
        entry = base("dynamisme", dyn_w["growth"])
        entry["subscale"] = {"name": "growth_s", "range": comps["dynamisme"]["growth_range"], "curve": "linear"}
        entry["verdict_paths"].append("« Attendre » rescue path if dynamisme ≥ %s" % verdicts["wait_rescue_dynamisme"])
        return entry
    if indicator_key == "unemployment":
        entry = base("dynamisme", dyn_w["unemployment"])
        entry["subscale"] = {"name": "unemployment_s", "range": comps["dynamisme"]["unemployment_range"], "curve": "linear_reversed"}
        entry["verdict_paths"].append("« Attendre » rescue path if dynamisme ≥ %s" % verdicts["wait_rescue_dynamisme"])
        return entry
    if indicator_key == "inflation":
        entry = base("stabilite", stab_w["inflation"])
        entry["subscale"] = {
            "name": "inflation_s",
            "formula": "clamp(100 − |inflation − %s| × %s)" % (comps["stabilite"]["inflation_target"], comps["stabilite"]["inflation_sensitivity"]),
        }
        return entry
    if indicator_key == "policy_rate":
        entry = base("stabilite", stab_w["policy_rate"])
        entry["subscale"] = {
            "name": "rate_s",
            "formula": "real = policy_rate − inflation → bands, else real_rate_outside_score",
            "temporal_caveat": "combines the policy_rate vintage with the inflation vintage (known issue K1)",
        }
        return entry
    if indicator_key == "debt_gdp":
        entry = base("solvabilite", sol_w["debt"])
        entry["subscale"] = {"name": "debt_s", "range": comps["solvabilite"]["debt_range"], "curve": "linear_reversed"}
        return entry
    if indicator_key == "rating":
        entry = base("solvabilite", sol_w["rating"])
        entry["subscale"] = {"name": "rating_score", "table": "scoring_model.ratings.scores (NR = %s)" % sm["ratings"]["scores"].get("NR")}
        entry["verdict_paths"].append("verdict capped at « Attendre »: rating %s without quoted CDS" % verdicts["blocking_ratings"])
        entry["ke"] = "rating spread → CRP/Ke (fallback path)"
        return entry
    if indicator_key == "cds":
        entry = base("solvabilite", sol_w["cds"])
        entry["subscale"] = {"name": "cds_score", "curve": "scoring_model.cds_score (none_score=%s when unquoted)" % sm["cds_score"]["none_score"]}
        entry["verdict_paths"].append("no CDS + rating %s → verdict capped at « Attendre »" % verdicts["blocking_ratings"])
        entry["ke"] = "CDS → CRP (max spread) → Ke"
        return entry
    if indicator_key == "qualitative:currency_stability":
        entry = base("stabilite", stab_w["currency"])
        entry["subscale"] = {"name": "currency_s", "default_if_missing": comps["missing_qualitative_score"]}
        return entry
    if indicator_key == "qualitative:outlook":
        entry = base("dynamisme", dyn_w["outlook"])
        entry["subscale"] = {"name": "outlook_s", "default_if_missing": comps["missing_qualitative_score"]}
        entry["verdict_paths"].append("« Attendre » rescue path if dynamisme ≥ %s" % verdicts["wait_rescue_dynamisme"])
        return entry
    if indicator_key == "qualitative:governance":
        entry = base("institutions", inst_w["governance"])
        entry["subscale"] = {"name": "governance_s", "default_if_missing": comps["missing_qualitative_score"]}
        return entry
    if indicator_key == "qualitative:resilience":
        entry = base("institutions", inst_w["resilience"])
        entry["subscale"] = {"name": "resilience_s", "default_if_missing": comps["missing_qualitative_score"]}
        return entry
    if indicator_key == "qualitative:business":
        entry = base("ouverture", ouv_w["business"])
        entry["subscale"] = {"name": "business_s", "default_if_missing": comps["missing_qualitative_score"]}
        return entry
    if indicator_key == "qualitative:openness":
        entry = base("ouverture", ouv_w["openness"])
        entry["subscale"] = {"name": "openness_s", "default_if_missing": comps["missing_qualitative_score"]}
        return entry
    if indicator_key in ("reserves", "equity_index", "currency"):
        return {
            "role": "display_only",
            "component": None,
            "note": "no component, risk or Ke uses this indicator (scoring.py: indicator_status/display only).",
        }
    if indicator_key == "crp":
        return {
            "role": "ke_driver",
            "component": None,
            "ke": "CRP = max(rating spread, (cds − %s) / %s) × %s, then Ke = rf + β×ERP + CRP" % (
                sm["crp"]["cds_offset_pb"], sm["crp"]["cds_divisor"], meta["financial_params"]["equity_bond_vol_ratio"],
            ),
            "note": "derived — not an observation; inherits the rating/cds vintages.",
        }
    return {"role": "none"}


DEFINITION_NOTES = {
    "gdp_growth": "annual real GDP growth; WDI mapping NY.GDP.MKTP.KD.ZG is « exact » (docs/DATA_REFRESH_PLAN §3).",
    "inflation": "annual consumer-price change; WDI FP.CPI.TOTL.ZG is an annual average — a Dec→Dec index (Brazilian IPCA) is not the same definition.",
    "policy_rate": "central-bank policy rate (%); cross-country modalities (level vs corridor) are not documented in the country files.",
    "unemployment": "unemployment % of labour force; WDI SL.UEM.TOTL.ZS = ILO modelled estimate — a « partial » match in the refresh mapping.",
    "debt_gdp": "public debt / GDP; the central vs GENERAL government distinction is not documented in production files (known from review 6.2: WDI = central government).",
    "reserves": "foreign-exchange reserves (Bn $); gross vs NET nuance — Lebanon's reserves are NET and documented as such; WDI FI.RES.TOTL.CD is total (incl. gold).",
    "rating": "sovereign rating; NR = 20 in the scoring table (an unrated country sits near the bottom).",
    "cds": "5-year sovereign CDS (bp); unquoted for 2 countries — absence treated as a maximal-risk signal.",
    "equity_index": "local equity index + 1-year performance; display only.",
    "currency": "currency code + 1-year performance; display only — the scoring input is the qualitative currency_stability.",
}

NEXT_ACTION = {
    "policy_rate": "batch B2",
    "rating": "batch B4",
    "cds": "batch B4",
    "debt_gdp": "batch B3 (re-check central vs general before any substitution)",
    "reserves": "batch B3/B4",
    "unemployment": "batch B5",
    "gdp_growth": "batch B3 (others) / batch B5 (Lebanon)",
    "inflation": "batch B3",
    "equity_index": "batch B4 (display)",
    "currency": "batch B4 (display)",
}

EVIDENCE_REQUIRED = {
    "policy_rate": "central-bank site/bulletin: exact decision date + level.",
    "rating": "dated agency matrices (S&P / Moody's / Fitch).",
    "cds": "dated market quotes, or a sourced confirmation that no liquid market exists.",
    "debt_gdp": "citable source with an explicit definition (central OR general) + vintage.",
    "reserves": "CB/IMF publication with the concept (gross/NET, incl. gold) and period end-date.",
    "unemployment": "citable national survey OR an ILOSTAT note acknowledging the modelled nature (vintage).",
    "gdp_growth": "reconciled institutional source (WB/IMF) + vintage.",
    "inflation": "institutional source + methodological precision (annual average vs Dec→Dec).",
    "equity_index": "exchange: exact index + performance date.",
    "currency": "citable FX source (code, performance, date).",
}

# ---------------------------------------------------------------- findings

KNOWN_ISSUES = [
    {
        "id": "K1",
        "title": "Real-rate temporal mixing (Lebanon) — known, not corrected",
        "finding": (
            "policy_rate 20.0 % (vintage 2024, source « Banque du Liban ») is combined with "
            "inflation 14.6 % (2025, WDI, applied in 6.1) → real_rate = 5.4, inside the [−8, 6] "
            "band → rate_s = 40. This vintage mixing is a property of the data, not a model rule; "
            "it is recorded here as a known issue without changing the calculation."
        ),
        "countries": ["lebanon"],
        "impact": "stabilite (inflation w 0.45, policy w 0.15, currency w 0.40) → risk (w 0.40) → verdicts.",
        "evidence_required": "current BDL policy rate (BDL site/bulletin) with the exact decision date.",
        "action": "batch B2 (policy-rate refresh) — not a formula change.",
        "tier": 1,
    },
    {
        "id": "K2",
        "title": "NR rating and unquoted CDS (Lebanon, Syria)",
        "finding": (
            "rating = NR and cds = None for both countries → rating_score = 20, cds_score = "
            "none_score = 5, CRP falls back to the rating spread (15.5 × 1.5), and the verdict is "
            "capped at « Attendre » regardless of the score (blocking_ratings). This is a deliberate "
            "model signal, but it rests on 2024 vintages."
        ),
        "countries": ["lebanon", "syria"],
        "impact": "solvabilite (w 0.40/0.30) → risk; Ke/CRP; verdict capping.",
        "evidence_required": "dated agency matrices; sourced confirmation that no quoted CDS market exists.",
        "action": "batch B4.",
        "tier": 1,
    },
    {
        "id": "K3",
        "title": "Unemployment values in conflict (Lebanon 30, Syria 50)",
        "finding": (
            "No citable national survey; diverging ILO modelled series (LBN 11.0 in 2023, WDI 2024/25 "
            "null; SYR 13.6 in 2025); crisis levels (30/50) without a traceable citation. Documented "
            "conflicts — no default arbitration."
        ),
        "countries": ["lebanon", "syria"],
        "impact": "dynamisme (w 0.20) + the « Attendre » rescue path (dynamisme ≥ 55 threshold).",
        "evidence_required": "docs/DATA_REFRESH_PLAN.md §8.2 / §8.3 (ILOSTAT + national surveys + post-transition).",
        "action": "batch B5 — evidence first.",
        "tier": 1,
    },
    {
        "id": "K4",
        "title": "Lebanon GDP 2024: three institutional vintages",
        "finding": "Production −6.5 (IMF) vs WDI+LEM −7.1 vs WEO Oct 2026 −5.2. The file stays at −6.5; conflict documented.",
        "countries": ["lebanon"],
        "impact": "dynamisme (w 0.55) — the largest dynamisme influence in the corpus.",
        "evidence_required": "docs/DATA_REFRESH_PLAN.md §8.1 (IMF internal reconciliation + national-accounts base).",
        "action": "batch B5.",
        "tier": 1,
    },
    {
        "id": "K5",
        "title": "Per-observation provenance nearly absent",
        "finding": (
            "Out of 100 data pairs, ONLY lebanon-inflation carries source_url/obs_status/retrieved "
            "(the pattern set in 6.1). meta.sources is a dataset-level registry, not per observation. "
            "Absent fields (verification impossible) are distinguished from missing values."
        ),
        "countries": ["*"],
        "impact": "capacity to re-verify and refresh repeatedly; the displayed freshness flag is currently the only signal.",
        "evidence_required": "backfill URL + obs_status + retrieved at each future application batch (the 6.1 pattern).",
        "action": "batch B1 (metadata), transversal.",
        "tier": 2,
    },
    {
        "id": "K6",
        "title": "Real-rate band specification vs code mismatch (documentation only)",
        "finding": (
            "docs/MODEL_PARAMS.md §4.2 describes the bands as « inclusive-low / exclusive-high » while "
            "the code compares low ≤ real ≤ high (inclusive on both ends). The difference only appears "
            "at exact band edges (e.g. real = 4.0 → code 72, strict doc reading 40). No country sits on "
            "an edge today; this is a documentation/test alignment finding, with no formula change in "
            "this increment."
        ),
        "countries": ["*"],
        "impact": "no current score effect; a future vintage could land on an edge.",
        "evidence_required": "decide the documentary convention (align the doc to the code, or the reverse via a dedicated increment).",
        "action": "keep on the documentation watch-list.",
        "tier": 4,
    },
]

REMEDIATION_BATCHES = [
    {"id": "B1", "name": "provenance backfill (metadata)", "keys": "transversal", "risk": "low", "note": "URL + obs_status + retrieved per value, alongside future application batches; no value changes."},
    {"id": "B2", "name": "policy rates (10 countries)", "keys": ["policy_rate"], "risk": "medium — also mitigates K1", "note": "exact decision date required; refreshes rate_s (band)."},
    {"id": "B3", "name": "annual macro (documented batch)", "keys": ["gdp_growth", "inflation", "unemployment", "debt_gdp"], "risk": "medium", "note": "definition-first; central vs general explicit; Lebanon-GDP and LBN/SYR-unemployment excluded → B5."},
    {"id": "B4", "name": "market signals", "keys": ["rating", "cds", "equity_index", "currency", "reserves"], "risk": "medium", "note": "display + Ke; deliberate NR preserved; net vs gross made explicit."},
    {"id": "B5", "name": "documented conflicts", "keys": ["lebanon:gdp_growth", "lebanon:unemployment", "syria:unemployment"], "risk": "high — human review required", "note": "only after the §8 DATA_REFRESH_PLAN evidence; no automatic arbitration (no « newest wins »)."},
    {"id": "B6", "name": "qualitative: grid and dating", "keys": "qualitative:*", "risk": "medium", "note": "publish the qualitative scoring grid + a review date per assessment."},
]

# --------------------------------------------------------------- audit rows

def provenance_of(block: dict[str, Any]) -> dict[str, Any]:
    """Provenance exactly as it exists — absent field ≠ None value."""
    return {
        "source": block.get("source"),
        "source_url": block.get("source_url"),
        "obs_status": block.get("obs_status"),
        "retrieved": block.get("retrieved"),
        "agency": block.get("agency"),
        "published_lastupdated": None,  # never exposed by the current data (docs/DATA_REFRESH_PLAN §7)
    }


def status_for(country: dict[str, Any], key: str, block: dict[str, Any]) -> tuple[str, list[str], str, str]:
    """Primary status + flags + confidence + justification.

    The status qualifies the STATE OF OUR KNOWLEDGE (not a property of
    the source): verified, stale, estimated, conflicting, missing, or
    ``unverified`` (recent but with no per-observation provenance).
    """
    cid = country["id"]
    date_raw = block.get("date")
    year = freshness.obs_year(date_raw)

    # 1) value absent
    if key not in country.get("indicators", {}) or block.get("value") is None:
        if key == "cds":
            return (
                STATUS_MISSING,
                ["documented_absence", "deliberate signal: none_score + verdict cap without quoted CDS (scoring.py::decide_verdict)"],
                "high",
                "value=None with a documented « non coté » block — the absence is a signal handled by the model, not a data-entry gap.",
            )
        if key in ("equity_index", "currency") and block and (block.get("perf_1y") is not None or block.get("level") is not None or block.get("code")):
            # structured block without a scalar `value` (index level / currency code + perf):
            # not a missing value — falls through to date-based classification below.
            pass
        else:
            return STATUS_MISSING, [], "high", "block absent or value=None with no alternative documentation."

    # 2) fully proven row (increment 6.1: Lebanon inflation 2025)
    if block.get("obs_status") == "actual" and block.get("retrieved") and block.get("source_url"):
        return (
            STATUS_VERIFIED,
            ["IMF WEO cross-check == 14.6 (docs/REFRESH_REVIEW.md entry 2)"],
            "high",
            "complete provenance (source + URL + obs_status + retrieved) and a documented WEO cross-check.",
        )

    # 3) documented conflict
    if (cid, key) in DOCUMENTED_CONFLICTS:
        return STATUS_CONFLICTING, ["conflict_documented"], "high", DOCUMENTED_CONFLICTS[(cid, key)]

    # 4) source explicitly estimated / modelled
    if source_text_is_estimate(block.get("source")):
        return (
            STATUS_ESTIMATED,
            ["source_labelled_estimate"],
            "medium",
            "the `source` field carries an explicit estimate/modelling mention (real text).",
        )
    # ILO-modelled series known from the refresh mapping although the file does not say so
    source_text = str(block.get("source", ""))
    if key == "unemployment" and "OIT" not in source_text and ("Banque mondiale" in source_text or "World" in source_text):
        return (
            STATUS_ESTIMATED,
            ["ilo_modelled_series_implied"],
            "medium",
            "WDI SL.UEM.TOTL.ZS = ILO modelled estimate (refresh mapping); the file does not state it explicitly.",
        )

    # 5) stale: current uniform rule (year < current − 1)
    if year is not None and freshness.is_stale(date_raw):
        flags = []
        if block.get("value") is None:
            flags.append("scalar_value_absent_by_design")
        if MONTH_PREFIX_RE.search(str(date_raw)):
            flags.append("precise_month")
        flags.append("no per-observation provenance")
        return (
            STATUS_STALE,
            flags,
            "high",
            "vintage %s < current−1 threshold (freshness.is_stale); no per-source verification in this audit." % year,
        )

    # 6) recent but with no per-observation provenance (documented extension)
    if year is not None:
        extra = ["scalar_value_absent_by_design"] if block.get("value") is None else []
        return (
            STATUS_UNVERIFIED,
            extra + ["provenance_absent"],
            "medium",
            "observation (vintage %s) neither verified in this audit nor accompanied by source_url/obs_status/retrieved." % year,
        )

    return STATUS_UNVERIFIED, ["date_absent"], "low", "no identifiable vintage (date field absent/non-numeric)."


# ------------------------------------------------------------------ matrix

def build_matrix(meta: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    matrix: dict[str, list[dict[str, Any]]] = {"data": [], "computed": [], "qualitative": []}

    for country in data.countries():
        cid = country["id"]
        for key in data.INDICATOR_ORDER:
            if key == "crp":
                crp_value, crp_source = scoring.country_risk_premium(country)
                matrix["computed"].append(
                    {
                        "country_id": cid,
                        "country_name": country["name"],
                        "indicator_key": key,
                        "display_label": data.INDICATOR_LABELS[key],
                        "value_present": True,
                        "value": crp_value,
                        "unit": "%",
                        "obs_period": "calcul",
                        "data_status": STATUS_VERIFIED,
                        "status_flags": ["computed", "inherits rating/cds vintages"],
                        "confidence": "high",
                        "confidence_basis": (
                            "deterministic recomputation vs scoring.country_risk_premium "
                            "(basis: %s); freshness remains that of the rating/cds inputs."
                            % str(crp_source).lower()
                        ),
                        "scoring_influence": scoring_influence(key, meta),
                        "freshness": {
                            "obs_period": "calcul",
                            "obs_year": None,
                            "current_rule_stale": False,
                            "proposed_per_type": "n/a (derived) — freshness is handled on rating/cds",
                        },
                        "definition_notes": "Damodaran: max(rating spread, (cds − offset)/divisor) × volatility ratio.",
                        "gov_coverage": None,
                        "provenance": {"source": "computed (scoring.crp)", "source_url": None, "obs_status": None, "retrieved": None, "agency": None, "published_lastupdated": None},
                        "next_action": "via the rating/cds actions (no action of its own).",
                        "evidence_required": "—",
                    }
                )
                continue

            block = country.get("indicators", {}).get(key, {})
            has_block = bool(block)
            value_present = has_block and block.get("value") is not None
            status, flags, confidence, basis = status_for(country, key, block)

            gov_coverage, gov_basis = None, "n/a"
            if key == "debt_gdp" and has_block:
                text = str(block.get("note", "")).lower()
                if "général" in text or "general" in text or "secteur public" in text:
                    gov_coverage, gov_basis = "general_government", "documented in the file note"
                elif "central" in text:
                    gov_coverage, gov_basis = "central_government", "documented in the file note"
                else:
                    gov_coverage, gov_basis = None, "not_documented"

            matrix["data"].append(
                {
                    "country_id": cid,
                    "country_name": country["name"],
                    "indicator_key": key,
                    "display_label": data.INDICATOR_LABELS[key],
                    "value_present": value_present,
                    "value": block.get("value"),
                    "unit": block.get("unit", data.INDICATOR_UNITS.get(key, "")),
                    "obs_period": None if block.get("date") is None else str(block.get("date")),
                    "provenance": provenance_of(block),
                    "data_status": status,
                    "status_flags": flags,
                    "confidence": confidence,
                    "confidence_basis": basis,
                    "scoring_influence": scoring_influence(key, meta),
                    "freshness": {
                        "obs_period": None if block.get("date") is None else str(block.get("date")),
                        "obs_year": freshness.obs_year(block.get("date")),
                        "current_rule_stale": freshness.is_stale(block.get("date")),
                        "proposed_per_type": "see current_freshness_rule.proposed_per_type (separate review; nothing changed)",
                    },
                    "definition_notes": DEFINITION_NOTES.get(key),
                    "gov_coverage": gov_coverage,
                    "gov_coverage_basis": gov_basis,
                    "note": block.get("note"),
                    "next_action": NEXT_ACTION.get(key, "manual review: identify the official source (URL + period)."),
                    "evidence_required": EVIDENCE_REQUIRED.get(key, "citable official source (URL), period, actual/estimated status."),
                }
            )

        qualitative = country.get("qualitative", {})
        for key in QUALITATIVE_KEYS:
            matrix["qualitative"].append(
                {
                    "country_id": cid,
                    "country_name": country["name"],
                    "indicator_key": "qualitative:" + key,
                    "display_label": "Qualitative assessment — " + key,
                    "value_present": qualitative.get(key) is not None,
                    "value": qualitative.get(key),
                    "unit": "score 0–100",
                    "obs_period": None,
                    "data_status": STATUS_UNVERIFIED,
                    "status_flags": ["editorial_assessment", "no review date in the file"],
                    "confidence": "low",
                    "confidence_basis": (
                        "GeoCapital editorial score with no published grid and no traceable review date; "
                        "never marked stale by freshness (non-numeric text), which also limits the display layer."
                    ),
                    "scoring_influence": scoring_influence("qualitative:" + key, meta),
                    "freshness": {
                        "obs_period": None,
                        "obs_year": None,
                        "current_rule_stale": False,
                        "proposed_per_type": "proposal: dated annual review (see proposed_per_type.qualitative) — never automatically stale",
                    },
                    "definition_notes": "editorial 0-100 score (meta.methodology.score) — not an external observation.",
                    "gov_coverage": None,
                    "provenance": {"source": "GeoCapital (editorial)", "source_url": None, "obs_status": None, "retrieved": None, "agency": None, "published_lastupdated": None},
                    "next_action": "review dating + publishing the grid (batch B6).",
                    "evidence_required": "qualitative scoring grid (criteria + sources) and the date of the last review.",
                }
            )
    return matrix


def build_audit() -> dict[str, Any]:
    meta = json.load(open(data.META_FILE, encoding="utf-8"))
    matrix = build_matrix(meta)
    counts: dict[str, int] = {}
    for section in ("data", "computed", "qualitative"):
        for row in matrix[section]:
            counts[row["data_status"]] = counts.get(row["data_status"], 0) + 1
    return {
        "generated": datetime.date.today().isoformat(),
        "data_as_of": meta["app"]["data_as_of"],
        "data_as_of_caveat": "data_as_of = the app-level declared verification date; it does NOT prove every underlying observation is current.",
        "scope": {
            "countries": len(data.countries()),
            "country_ids": [c["id"] for c in data.countries()],
            "indicator_keys": list(data.INDICATOR_ORDER),
            "qualitative_keys": list(QUALITATIVE_KEYS),
            "pairs": {
                "data": len(matrix["data"]),
                "computed": len(matrix["computed"]),
                "qualitative": len(matrix["qualitative"]),
                "total": sum(len(matrix[s]) for s in ("data", "computed", "qualitative")),
            },
        },
        "status_vocabulary": {
            "verified": "complete per-observation provenance + documented cross-check (Lebanon-inflation only).",
            "stale": "dated observation beyond the current uniform threshold (year < current − 1) — a display signal, not a judgment.",
            "estimated": "source explicitly estimated/modelled (real `source` text, or the ILO-modelled series known from the refresh mapping).",
            "conflicting": "at least two official sources in disagreement — manual arbitration required (exhaustive list in DOCUMENTED_CONFLICTS).",
            "missing": "block or value absent; documented absences (unquoted CDS) are distinguished via flags.",
            "unverified": "documented extension: recent or undated observation with no per-observation provenance (no URL, obs_status or retrieved).",
        },
        "current_freshness_rule": {
            "definition": "stale ⇔ obs_year < current year − 1 (freshness.py, display only — score and verdict unchanged)",
            "per_indicator_uniformity": "a single rule for everything: annual macro, rates, ratings, CDS, market levels, qualitative",
            "proposed_per_type": PROPOSED_FRESHNESS_THRESHOLDS,
            "note": "this section PROPOSES; freshness.py and displayed labels are not modified in this increment.",
        },
        "scoring_model_reference": {
            "source_of_truth": "data/meta.json::scoring_model — read via scoring.model()",
            "components": {
                "dynamisme": ["gdp_growth", "unemployment", "qualitative:outlook"],
                "stabilite": ["inflation", "policy_rate", "qualitative:currency_stability"],
                "solvabilite": ["debt_gdp", "rating", "cds"],
                "institutions": ["qualitative:governance", "qualitative:resilience"],
                "ouverture": ["qualitative:business", "qualitative:openness"],
            },
            "risk_weights": meta["scoring_model"]["risk"]["weights"],
            "ke_inputs": ["risk_free_rate", "mature_erp", "beta", "crp ← rating/cds"],
            "ke_not_driven_by": ["gdp/inflation/unemployment/debt/reserves/equity/currency (no direct Ke effect)"],
            "verdict_gates": [
                "blocking_ratings %s without quoted CDS" % meta["scoring_model"]["verdicts"]["blocking_ratings"],
                "invest/caution/wait/wait_rescue(dynamisme) thresholds",
            ],
        },
        "known_issues": KNOWN_ISSUES,
        "matrix": matrix,
        "status_counts": counts,
        "remediation_batches": REMEDIATION_BATCHES,
    }


def fmt_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return "%g" % value
    return str(value)


def status_cell(row: dict[str, Any]) -> str:
    flag = ""
    if row["status_flags"]:
        flag = " ({})".format(row["status_flags"][0])
    return "`{}`{}".format(row["data_status"], flag)


def generate_markdown(audit: dict[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append

    add("# GeoCapital — Data Quality Audit (Priority 7, increment 7.1)")
    add("")
    add("> **Review-first matrix** generated on %s from production data, with no changes to data, formulas, parameters, or app behavior." % audit["generated"])
    add("> Machine-readable companion: `data/audit/data_quality_audit.json`.")
    add("> `app.data_as_of` = **%s** — ⚠ %s" % (audit["data_as_of"], audit["data_as_of_caveat"]))
    add("")
    add("## 1. Method")
    add("")
    add("- **Read-only** inspection of: `data/countries/*.json`, `data/meta.json`, `geocapital/data.py`, `geocapital/scoring.py`, `geocapital/freshness.py`, plus the traceable documents (`docs/DATA_AUDIT.md`, `docs/DATA_REFRESH_PLAN.md`, `docs/REFRESH_REVIEW.md`, `docs/MODEL_PARAMS.md`).")
    add("- **Statuses**: " + " ; ".join("`%s` — %s" % (k, v) for k, v in audit["status_vocabulary"].items()))
    add("- The sixth status `unverified` is a **transparent extension**, motivated by the metadata reality (no per-observation provenance outside Lebanon-inflation). It is documented here and in the JSON.")
    add("- **Conflicts**: only those already documented (REFRESH_REVIEW entries 1–3 + annex, DATA_REFRESH_PLAN §8).")
    add("- **Provenance**: absent field ≠ missing value; the absence of `source_url`/`obs_status`/`retrieved` is recorded as a metadata gap (K5).")
    add("- **Scoring influence**: read from the code and `scoring_model` (exact sub-weights); no assumed weights; « display only » is stated explicitly when a key enters no formula (reserves, equity index, currency).")
    add("")
    add("## 2. Coverage")
    add("")
    scope = audit["scope"]
    add("- Production countries: **%s** (%s)." % (scope["countries"], ", ".join("`%s`" % cid for cid in scope["country_ids"])))
    add("- Keys: %s data indicators + `crp` (computed) + %s qualitative keys → **%s country-indicator pairs** (%s data + %s computed + %s qualitative)." % (
        len(scope["indicator_keys"]) - 1, len(scope["qualitative_keys"]), scope["pairs"]["total"], scope["pairs"]["data"], scope["pairs"]["computed"], scope["pairs"]["qualitative"]))
    add("- Status counts: " + ", ".join("`%s` **%s**" % (k, v) for k, v in sorted(audit["status_counts"].items())) + ".")
    add("")
    add("## 3. Freshness: one uniform rule today, per-type thresholds PROPOSED (separate review)")
    add("")
    add("Current rule: `%s`." % audit["current_freshness_rule"]["definition"])
    add("")
    add("| Type | Keys | Current rule adequate? | Proposal (not applied) | Rationale |")
    add("|---|---|---|---|---|")
    for name, threshold in audit["current_freshness_rule"]["proposed_per_type"].items():
        add("| `%s` | %s | %s | %s | %s |" % (
            name,
            ", ".join("`%s`" % key for key in threshold["keys"]),
            "✓ adequate" if threshold["current_rule_is_adequate"] else "✗ to differentiate",
            threshold["proposed"],
            threshold["rationale"],
        ))
    add("")
    add("> No change to `geocapital/freshness.py` or displayed labels: this section is a proposal for review, aligned with data natures (annual macro ≈ OK; rates/ratings/CDS/levels/qualitative → differentiation needed).")
    add("")
    add("## 4. Prioritized findings (methodology)")
    add("")
    add("Findings are ordered **lexicographically**: (tier 1) potential impact on the final score/verdict → (tier 2) staleness + provenance → (tier 3) cross-country definition incompatibility → (tier 4) confidence that a defensible correction is possible. **No numeric sensitivity is simulated**: the model exposes no elasticities (counterfactuals would require changing data, forbidden here). Findings K1–K4 (tier 1) concern the model's heaviest paths (currency_stability ×0.40 of stabilite; rating/CDS → solvabilite + Ke + verdict capping; unemployment/GDP → dynamisme).")
    add("")
    for finding in audit["known_issues"]:
        add("### %s — %s (tier %s; countries: %s)" % (finding["id"], finding["title"], finding["tier"], ", ".join("`%s`" % c for c in finding["countries"])))
        add("")
        add("- **Finding**: %s" % finding["finding"])
        add("- **Impact**: %s" % finding["impact"])
        add("- **Evidence required**: %s" % finding["evidence_required"])
        add("- **Recommended path**: %s" % finding["action"])
        add("")
    add("## 5. Matrix — data by country (10 × 10)")
    add("")
    add("Columns: key | value | period (observation ≠ retrieved — rarely distinct today) | status | confidence | scoring influence | source | URL | recommended batch.")
    add("")
    for cid in scope["country_ids"]:
        add("### `%s`" % cid)
        add("")
        add("| Key | Value (unit) | Period | Status | Conf. | Scoring influence | Source | URL | Batch |")
        add("|---|---|---|---|---|---|---|---|---|")
        for row in audit["matrix"]["data"]:
            if row["country_id"] != cid:
                continue
            influence = row["scoring_influence"]
            if influence.get("component"):
                influence_cell = "%s (sub-weight %s%s)" % (
                    influence["component"],
                    influence["sub_weight"],
                    "; risk w %s" % influence["risk_component_weight"] if influence.get("risk") else "",
                )
            elif influence.get("role") == "ke_driver":
                influence_cell = "Ke via CRP (%)"
            else:
                influence_cell = "display only"
            provenance = row["provenance"]
            add("| `%s` | %s (%s) | %s | %s | %s | %s | %s | %s | %s |" % (
                row["indicator_key"],
                fmt_value(row["value"]),
                row["unit"],
                row["obs_period"] or "—",
                status_cell(row),
                row["confidence"],
                influence_cell,
                provenance["source"] or "—",
                "yes" if provenance["source_url"] else "—",
                row["next_action"],
            ))
        add("")
        extra_rows = [row for row in audit["matrix"]["data"] if row["country_id"] == cid and (row["data_status"] in (STATUS_CONFLICTING, STATUS_MISSING) or row["gov_coverage"] or row["confidence"] != "high")]
        if extra_rows:
            for row in extra_rows:
                provenance = row["provenance"]
                add("- ⚠ `%s.%s` — %s" % (cid, row["indicator_key"], row["confidence_basis"]))
                if row["gov_coverage"]:
                    add("  - Government coverage: `%s` (%s)" % (row["gov_coverage"], row["gov_coverage_basis"]))
                if provenance["source_url"]:
                    add("  - URL: %s" % provenance["source_url"])
            add("")
    add("## 6. Matrix — qualitative keys (6 per country)")
    add("")
    add("Each assessment is an editorial score with no review date — status `unverified`, low confidence (a structural limit, not a data-entry error).")
    add("")
    add("| Country | outlook | currency_stability | governance | resilience | business | openness |")
    add("|---|---|---|---|---|---|---|")
    for cid in scope["country_ids"]:
        values = {row["indicator_key"]: row["value"] for row in audit["matrix"]["qualitative"] if row["country_id"] == cid}
        add("| `%s` | %s | %s | %s | %s | %s | %s |" % (
            cid,
            fmt_value(values["qualitative:outlook"]),
            fmt_value(values["qualitative:currency_stability"]),
            fmt_value(values["qualitative:governance"]),
            fmt_value(values["qualitative:resilience"]),
            fmt_value(values["qualitative:business"]),
            fmt_value(values["qualitative:openness"]),
        ))
    add("")
    add("Sub-weights: outlook 0.25 (dynamisme); **currency_stability 0.40 (stabilite — tied with inflation for the heaviest weight)**; governance 0.60 + resilience 0.40 (institutions — the third component entering risk, w 0.25); business 0.60 + openness 0.40 (ouverture, excluded from risk).")
    add("")
    add("## 7. Derived — country risk premium")
    add("")
    add("| Country | CRP | Basis | Usage note |")
    add("|---|---|---|---|")
    for row in audit["matrix"]["computed"]:
        add("| `%s` | %s %% | Damodaran (max rating-spread/CDS spread) × 1.5 | %s |" % (row["country_id"], fmt_value(row["value"]), row["confidence_basis"]))
    add("")
    add("## 8. Proposed action batches (none applied)")
    add("")
    add("| Batch | Name | Keys | Risk | Note |")
    add("|---|---|---|---|---|")
    for batch in audit["remediation_batches"]:
        keys = ", ".join("`%s`" % key for key in batch["keys"]) if isinstance(batch["keys"], list) else batch["keys"]
        add("| %s | %s | %s | %s | %s |" % (batch["id"], batch["name"], keys, batch["risk"], batch["note"]))
    add("")
    add("## 9. Limitations")
    add("")
    add("- Without per-observation URLs or publication dates, per-source verification is not reproducible at scale in this audit (finding K5).")
    add("- No numeric sensitivity simulated — the model exposes no derivable elasticities without a counterfactual (forbidden here).")
    add("- Qualitative keys are never « stale » under the current code; the « not an observation » distinction is assumed here, reported without correction.")
    add("- Currency and equity-index data (2024 performance) sit outside the model; whether to bring them into scoring is a separate architecture decision.")
    add("- Brazil (candidate 6.3) is excluded from the matrix: no production coverage.")
    add("")
    return "\n".join(lines) + "\n"


def generate() -> dict[str, Any]:
    audit = build_audit()
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    AUDIT_MD.write_text(generate_markdown(audit), encoding="utf-8")
    return {"json": str(AUDIT_JSON), "md": str(AUDIT_MD), "audit": audit}


if __name__ == "__main__":
    paths = generate()
    print("JSON:", paths["json"])
    print("MD  :", paths["md"])
