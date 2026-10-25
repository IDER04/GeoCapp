"""Sources, méthode et limites."""

from __future__ import annotations

import streamlit as st

from geocapital import i18n, ui
from geocapital.data import load_data
from geocapital.i18n import t
from geocapital.scoring import EQUITY_BOND_VOL_RATIO, MATURE_ERP, PROFILES, RISK_FREE_RATE


def _go_map() -> None:
    st.session_state["nav"] = "map"


def render() -> None:
    meta = load_data()
    ui.page_head(
        t("me.eyebrow"),
        t("me.title"),
        t("me.subtitle"),
    )

    cols = st.columns(3)
    steps = [
        (t("me.step1.eyebrow"), t("me.step1.title"), t("me.step1.text")),
        (t("me.step2.eyebrow"), t("me.step2.title"), t("me.step2.text")),
        (t("me.step3.eyebrow"), t("me.step3.title"), t("me.step3.text")),
    ]
    for col, (eyebrow, title, text) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
                <div class="gc-card" style="min-height:190px">
                  <div class="gc-eyebrow">{ui.esc(eyebrow)}</div>
                  <h4 style="font-family:'DM Serif Display',Georgia,serif;font-size:1.3rem;font-weight:400">{ui.esc(title)}</h4>
                  <p style="font-size:.82rem;line-height:1.65">{ui.esc(text)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    ui.section_title(t("me.score.title"), t("me.score.sub"))
    st.markdown(
        f"""
        <table class="gc-table">
          <thead><tr><th>{t("me.th.component")}</th><th>{t("me.th.measures")}</th><th>{t("me.th.inputs")}</th></tr></thead>
          <tbody>
            <tr><td class="gc-table-label">{t("me.component.dynamism")}</td><td>{t("me.component.dynamism.measures")}</td><td>{t("me.component.dynamism.inputs")}</td></tr>
            <tr><td class="gc-table-label">{t("me.component.stability")}</td><td>{t("me.component.stability.measures")}</td><td>{t("me.component.stability.inputs")}</td></tr>
            <tr><td class="gc-table-label">{t("me.component.solvency")}</td><td>{t("me.component.solvency.measures")}</td><td>{t("me.component.solvency.inputs")}</td></tr>
            <tr><td class="gc-table-label">{t("me.component.institutions")}</td><td>{t("me.component.institutions.measures")}</td><td>{t("me.component.institutions.inputs")}</td></tr>
            <tr><td class="gc-table-label">{t("me.component.openness")}</td><td>{t("me.component.openness.measures")}</td><td>{t("me.component.openness.inputs")}</td></tr>
          </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
    st.caption(t("me.score.caption"))

    ui.section_title(t("me.profiles.title"), t("me.profiles.sub"))
    header = "".join(f"<th>{ui.esc(i18n.profile_label(profile))}</th>" for profile in PROFILES)
    rows = []
    for key, label_key in [
        ("dynamisme", "me.row.dynamism"),
        ("stabilite", "me.row.stability"),
        ("solvabilite", "me.row.solvency"),
        ("institutions", "me.row.institutions"),
        ("ouverture", "me.row.openness"),
    ]:
        cells = "".join(f"<td>{PROFILES[profile]['weights'][key]*100:.0f} %</td>" for profile in PROFILES)
        rows.append(f"<tr><td class='gc-table-label'>{t(label_key)}</td>{cells}</tr>")
    st.markdown(
        f'<table class="gc-table"><thead><tr><th>{t("me.profiles.header")}</th>{header}</tr></thead><tbody>{"".join(rows)}</tbody></table>',
        unsafe_allow_html=True,
    )

    ui.section_title(t("me.ke.title"), t("me.ke.sub"))
    st.markdown(
        f"""
        <div class="gc-card gc-card-gold">
          <h4 style="font-family:'DM Serif Display',Georgia,serif;font-size:1.3rem;font-weight:400">{t("me.ke.formula")}</h4>
          <p style="margin-top:8px;font-size:.85rem;line-height:1.7">
            {t("me.ke.body", risk_free=RISK_FREE_RATE, mature_erp=MATURE_ERP, beta="1.0", ratio=EQUITY_BOND_VOL_RATIO)}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="gc-small" style="margin-top:8px">{t("me.ke.note")}</div>',
        unsafe_allow_html=True,
    )

    ui.section_title(t("me.missing.title"), t("me.missing.sub"))
    st.markdown(
        f'<div class="gc-callout red">{t("me.missing.body")}</div>',
        unsafe_allow_html=True,
    )

    ui.section_title(t("me.ai.title"), t("me.ai.sub"))
    ai_cols = st.columns(2)
    with ai_cols[0]:
        st.markdown(
            f"""
            <div class="gc-card">
              <div class="gc-eyebrow">{t("me.ai.does.eyebrow")}</div>
              <ul class="gc-list">
                <li>{t("me.ai.does.1")}</li>
                <li>{t("me.ai.does.2")}</li>
                <li>{t("me.ai.does.3")}</li>
                <li>{t("me.ai.does.4")}</li>
                <li>{t("me.ai.does.5")}</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with ai_cols[1]:
        st.markdown(
            f"""
            <div class="gc-card">
              <div class="gc-eyebrow">{t("me.ai.doesnt.eyebrow")}</div>
              <ul class="gc-list">
                <li>{t("me.ai.doesnt.1")}</li>
                <li>{t("me.ai.doesnt.2")}</li>
                <li>{t("me.ai.doesnt.3")}</li>
                <li>{t("me.ai.doesnt.4")}</li>
                <li>{t("me.ai.doesnt.5")}</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ui.section_title(t("me.sources.title"), t("me.sources.sub"))
    for source in meta.get("sources", []):
        st.markdown(
            f'<div style="padding:9px 0;border-bottom:1px solid rgba(148,163,184,.1)"><a href="{ui.esc(source.get("url"))}" target="_blank" style="font-size:.82rem;font-weight:650">{ui.esc(source.get("name"))}</a><div class="gc-small">{ui.esc(source.get("use"))}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption(t("me.sources.caption", last_update=meta.get("app", {}).get("last_update", "2024-2025")))

    ui.section_title(t("me.limits.title"), t("me.limits.sub"))
    st.markdown(
        f"""
        <div class="gc-card">
          <ul class="gc-list">
            <li>{t("me.limits.1")}</li>
            <li>{t("me.limits.2")}</li>
            <li>{t("me.limits.3")}</li>
            <li>{t("me.limits.4")}</li>
            <li>{t("me.limits.5")}</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.button(t("me.btn.back"), type="primary", on_click=_go_map)
    ui.footer()
