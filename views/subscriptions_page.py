"""Subscriptions — prototype de la page des formules (frontend seul).

Aucun paiement, aucune facturation, aucune logique d'accès : la page présente
des formules BROUILLON (prix indicatifs, limites proposées) définies dans
geocapital/subscriptions.py. L'état de sélection vit dans st.session_state.
"""

from __future__ import annotations

import streamlit as st

from geocapital import i18n, subscriptions as subs, ui
from geocapital.data import countries
from geocapital.i18n import t

_SEL = "sub_selected"
_BILLING = "sub_billing"
_DIFF = "sub_diff_only"
_ANNUAL_PCT = round(subs.ANNUAL_DISCOUNT * 100)


def _amount(value: float) -> str:
    """Montant sans décimales s'il est entier, sinon 2 décimales (virgule en FR)."""
    text = f"{value:.0f}" if float(value).is_integer() else f"{value:.2f}"
    return text.replace(".", ",") if i18n.current_lang() == "fr" else text


def _money(value: float) -> str:
    return t("sub.price.fmt", amount=_amount(value))


def _value_text(value: subs.Value, core_n: int) -> str:
    if value is True:
        return t("sub.yes")
    if value is False:
        return t("sub.no")
    code, params = value
    return t(f"sub.v.{code}", n=core_n, **params)


def _select(plan: str) -> None:
    st.session_state[_SEL] = plan


def _clear() -> None:
    st.session_state[_SEL] = None


def _continue() -> None:
    st.toast(t("sub.sel.toast"), icon=":material/info:")


def _plan_card(plan: str, billing: str, selected: bool, core_n: int) -> str:
    price = subs.plan_price(plan, billing)
    recommended = plan == subs.RECOMMENDED_PLAN
    rows = {key: row for key, _group, row in subs.FEATURES}
    bullets = "".join(
        f'<li><span class="gc-plan-check">✓</span><span>{ui.esc(_value_text(rows[key][plan], core_n))}</span></li>'
        for key in subs.HIGHLIGHTS
        if rows[key][plan] is not False
    )
    if plan == "free":
        billed = t("sub.billed.free")
        placeholder = ""
    else:
        placeholder = f'<span class="gc-chip">{ui.esc(t("sub.placeholder"))}</span>'
        if billing == "annual":
            billed = t("sub.billed.annual", total=_money(price["total"]), saving=_money(price["saving"]))
        else:
            billed = t("sub.billed.monthly")
    classes = ["gc-plan"]
    if plan == "pro":
        classes.append("gc-dark")
    if recommended:
        classes.append("recommended")
    if selected:
        classes.append("selected")
    badge = f'<span class="gc-plan-badge">{ui.esc(t("sub.rec"))}</span>' if recommended else ""
    return f"""
    <div class="{' '.join(classes)}">
      <div class="gc-plan-top">
        <span class="gc-eyebrow">{ui.esc(t(f"sub.audience.{plan}"))}</span>{badge}
      </div>
      <h4>{ui.esc(t(f"sub.plan.{plan}"))}</h4>
      <p class="gc-plan-tag">{ui.esc(t(f"sub.tagline.{plan}"))}</p>
      <div class="gc-plan-price">
        <span class="gc-plan-amount">{ui.esc(_money(price["per_month"]))}</span>
        <span class="gc-plan-per">{ui.esc(t("sub.per_month"))}</span>
      </div>
      <div class="gc-plan-billed">{ui.esc(billed)} {placeholder}</div>
      <ul class="gc-plan-list">{bullets}</ul>
    </div>
    """


def _cell(value: subs.Value, core_n: int) -> str:
    if value is True:
        return f'<span class="gc-cmp-yes" aria-label="{ui.esc(t("sub.yes"))}">✓</span>'
    if value is False:
        return f'<span class="gc-cmp-no" aria-label="{ui.esc(t("sub.no"))}">—</span>'
    return ui.esc(_value_text(value, core_n))


def _comparison_table(core_n: int, diff_only: bool, selected: str | None) -> str:
    def col_class(plan: str) -> str:
        parts = []
        if plan == subs.RECOMMENDED_PLAN:
            parts.append("rec")
        if plan == selected:
            parts.append("sel")
        return " ".join(parts)

    head = "".join(
        f'<th class="{col_class(plan)}">{ui.esc(t(f"sub.plan.{plan}"))}</th>' for plan in subs.PLANS
    )
    body = []
    for group in subs.GROUPS:
        rows = [
            (key, row) for key, grp, row in subs.FEATURES
            if grp == group and (not diff_only or subs.is_differing(row))
        ]
        if not rows:
            continue
        body.append(f'<tr class="gc-cmp-group"><td colspan="{len(subs.PLANS) + 1}">{ui.esc(t(f"sub.group.{group}"))}</td></tr>')
        for key, row in rows:
            cells = "".join(
                f'<td class="{col_class(plan)}">{_cell(row[plan], core_n)}</td>' for plan in subs.PLANS
            )
            body.append(f'<tr><td class="gc-table-label">{ui.esc(t(f"sub.f.{key}"))}</td>{cells}</tr>')
    if not body:
        return f'<div class="gc-small">{ui.esc(t("sub.cmp.no_diff"))}</div>'
    return f"""
    <div class="gc-cmp-wrap">
      <table class="gc-table gc-cmp">
        <thead><tr><th>{ui.esc(t("sub.cmp.feature"))}</th>{head}</tr></thead>
        <tbody>{''.join(body)}</tbody>
      </table>
    </div>
    """


def _selection_panel(plan: str | None, billing: str, core_n: int) -> None:
    ui.section_title(t("sub.sel.title"))
    if plan is None:
        ui.callout(t("sub.sel.empty"), tone="gold")
        return
    price = subs.plan_price(plan, billing)
    rows = {key: row for key, _group, row in subs.FEATURES}
    included = "".join(
        f'<li><span class="gc-plan-check">✓</span><span><strong>{ui.esc(t(f"sub.f.{key}"))}</strong> · '
        f'{ui.esc(_value_text(rows[key][plan], core_n))}</span></li>'
        for key in subs.HIGHLIGHTS
        if rows[key][plan] is not False
    )
    cycle = t(f"sub.billing.{billing}").split(" · ")[0]
    note = t("sub.billed.free") if plan == "free" else (
        t("sub.billed.annual", total=_money(price["total"]), saving=_money(price["saving"]))
        if billing == "annual" else t("sub.billed.monthly")
    )
    st.markdown(
        f"""
        <div class="gc-card gc-sel">
          <div class="gc-sel-grid">
            <div>
              <div class="gc-kpi-label">{ui.esc(t("sub.sel.plan"))}</div>
              <div class="gc-sel-name">{ui.esc(t(f"sub.plan.{plan}"))}</div>
              <div class="gc-small">{ui.esc(cycle)}</div>
            </div>
            <div>
              <div class="gc-kpi-label">{ui.esc(t("sub.sel.price"))}</div>
              <div class="gc-sel-name">{ui.esc(_money(price["per_month"]))} <small>{ui.esc(t("sub.per_month"))}</small></div>
              <div class="gc-small">{ui.esc(note)}</div>
            </div>
            <div>
              <div class="gc-kpi-label">{ui.esc(t("sub.sel.includes"))}</div>
              <ul class="gc-plan-list compact">{included}</ul>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns([1, 1, 3])
    with cols[0]:
        st.button(t("sub.sel.continue"), key="sub_continue", type="primary", on_click=_continue, width="stretch")
    with cols[1]:
        st.button(t("sub.sel.clear"), key="sub_clear", on_click=_clear, width="stretch")


def render() -> None:
    core_n = len(countries())
    st.session_state.setdefault(_SEL, None)
    if st.session_state.get(_BILLING) not in subs.BILLING_CYCLES:
        st.session_state[_BILLING] = "monthly"
    st.session_state.setdefault(_DIFF, False)

    ui.page_head(t("sub.eyebrow"), t("sub.title"), t("sub.subtitle"))
    ui.callout(t("sub.draft"), tone="gold")

    st.radio(
        t("sub.billing.label"),
        subs.BILLING_CYCLES,
        format_func=lambda cycle: t(f"sub.billing.{cycle}", pct=_ANNUAL_PCT),
        key=_BILLING,
        horizontal=True,
    )
    billing = st.session_state[_BILLING]
    selected = st.session_state.get(_SEL)

    cols = st.columns(len(subs.PLANS))
    for col, plan in zip(cols, subs.PLANS):
        with col:
            st.markdown(_plan_card(plan, billing, plan == selected, core_n), unsafe_allow_html=True)
            is_selected = plan == selected
            st.button(
                t("sub.cta.selected") if is_selected else t(f"sub.cta.{plan}"),
                key=f"sub_pick_{plan}",
                type="primary" if (is_selected or plan == subs.RECOMMENDED_PLAN) else "secondary",
                on_click=_select,
                args=(plan,),
                width="stretch",
            )

    _selection_panel(selected, billing, core_n)

    ui.section_title(t("sub.cmp.title"), t("sub.cmp.sub"))
    st.toggle(t("sub.cmp.diff_only"), key=_DIFF)
    st.markdown(_comparison_table(core_n, bool(st.session_state[_DIFF]), selected), unsafe_allow_html=True)
    st.markdown(f'<div class="gc-small gc-cmp-note">{ui.esc(t("sub.cmp.draft"))}</div>', unsafe_allow_html=True)
