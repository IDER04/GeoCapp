"""Subscription plans — editable DRAFT definitions (frontend prototype only).

Nothing here is enforced anywhere in the application: no plan gates any data,
no billing exists and no price is final. Every number below is a placeholder
meant to be edited while the offer is being designed.

To change the offer, edit the constants in this file:
- ``PLAN_PRICES``: placeholder monthly prices (``ANNUAL_DISCOUNT`` applies to annual billing);
- ``FEATURES``: the per-plan allowances of each comparison row;
- ``RECOMMENDED_PLAN``: the plan highlighted on the page.
Display labels live in ``geocapital/i18n.py`` under the ``sub.*`` keys.
"""

from __future__ import annotations

from typing import Any

PLANS: tuple[str, ...] = ("free", "student", "pro")
RECOMMENDED_PLAN = "student"
BILLING_CYCLES: tuple[str, ...] = ("monthly", "annual")

# PLACEHOLDER pricing (EUR per month, billed monthly). Not final.
PLAN_PRICES: dict[str, float] = {"free": 0.0, "student": 9.0, "pro": 29.0}
# PLACEHOLDER share saved when billing annually (0.20 = 20 %). Not final.
ANNUAL_DISCOUNT = 0.20

# Comparison rows: (key, group, {plan: (value code, params)}).
# A value is True / False (included / not included) or a ``(code, params)``
# pair rendered through the ``sub.v.<code>`` label with ``params``.
# All allowances are a DRAFT proposal, not existing restrictions.
Value = bool | tuple[str, dict[str, Any]]
FEATURES: tuple[tuple[str, str, dict[str, Value]], ...] = (
    ("coverage", "data", {
        "free": ("coverage_core", {}),
        "student": ("coverage_plus", {}),
        "pro": ("coverage_full", {}),
    }),
    ("history", "data", {
        "free": ("history_recent", {}),
        "student": ("history_extended", {}),
        "pro": ("history_full", {}),
    }),
    ("risk_analysis", "risk", {
        "free": ("risk_basic", {}),
        "student": ("risk_detailed", {}),
        "pro": ("risk_full", {}),
    }),
    ("crp", "risk", {
        "free": ("crp_value", {}),
        "student": ("crp_method", {}),
        "pro": ("crp_full", {}),
    }),
    ("coe", "risk", {
        "free": ("coe_standard", {}),
        "student": ("coe_profiles", {}),
        "pro": ("coe_custom", {}),
    }),
    ("portfolio", "tools", {
        "free": ("portfolio_n", {"lim": 1}),
        "student": ("portfolio_n", {"lim": 3}),
        "pro": ("portfolio_unlimited", {}),
    }),
    ("advanced", "tools", {
        "free": ("tools_core", {}),
        "student": ("tools_plus", {}),
        "pro": ("tools_all", {}),
    }),
    ("export", "tools", {
        "free": False,
        "student": ("export_csv", {}),
        "pro": ("export_extended", {}),
    }),
    ("ai", "ai", {
        "free": ("ai_n", {"lim": 5}),
        "student": ("ai_n", {"lim": 25}),
        "pro": ("ai_n", {"lim": 100}),
    }),
    ("access", "ai", {
        "free": ("access_standard", {}),
        "student": ("access_higher", {}),
        "pro": ("access_highest", {}),
    }),
)

# Rows summarised as bullet points on each plan card.
HIGHLIGHTS: tuple[str, ...] = ("coverage", "risk_analysis", "ai", "export")
GROUPS: tuple[str, ...] = ("data", "risk", "tools", "ai")


def plan_price(plan: str, billing: str) -> dict[str, float]:
    """Placeholder price breakdown for ``plan`` under ``billing``.

    ``per_month``: effective monthly amount; ``total``: amount billed per
    period (a month, or a year for annual billing); ``saving``: yearly saving
    versus paying monthly. All values derive from the placeholder constants.
    """
    if plan not in PLAN_PRICES:
        raise ValueError(f"unknown plan: {plan!r}")
    if billing not in BILLING_CYCLES:
        raise ValueError(f"unknown billing cycle: {billing!r}")
    monthly = PLAN_PRICES[plan]
    yearly_full = monthly * 12
    if billing == "annual":
        total = round(yearly_full * (1 - ANNUAL_DISCOUNT), 2)
        return {"per_month": round(total / 12, 2), "total": total, "saving": round(yearly_full - total, 2)}
    return {"per_month": monthly, "total": monthly, "saving": 0.0}


def feature_values(row: dict[str, Value]) -> list[Value]:
    return [row[plan] for plan in PLANS]


def is_differing(row: dict[str, Value]) -> bool:
    """True when the plans do not all share the same value for this row."""
    values = feature_values(row)
    return any(value != values[0] for value in values[1:])
