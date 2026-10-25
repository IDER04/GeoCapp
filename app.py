"""GeoCapital — application Streamlit.

Lancement local :
    py -m streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from geocapital import i18n, ui
from geocapital.i18n import t

# Codes de route internes (stables, jamais traduits) — libellés via i18n.t().
PAGES = ["map", "country", "compare", "decoder", "analyst", "portfolio", "progress", "sources"]

ICONS = {
    "map": "◉",
    "country": "▤",
    "compare": "⇄",
    "decoder": "⌁",
    "analyst": "✎",
    "portfolio": "◫",
    "progress": "✦",
    "sources": "◎",
}

# Migration des sessions existantes créées avant i18n (nav stockée en libellé FR).
_LEGACY_NAV = {
    "Carte vivante": "map",
    "Fiche pays": "country",
    "Comparateur": "compare",
    "Décodeur": "decoder",
    "Analyste": "analyst",
    "Portefeuille": "portfolio",
    "Progression": "progress",
    "Sources & méthode": "sources",
}


def _init_state() -> None:
    from geocapital.data import countries

    st.session_state.setdefault("lang", i18n.DEFAULT_LANG)
    st.session_state.setdefault("nav", "map")
    st.session_state.setdefault("country_id", "usa")
    st.session_state.setdefault("profile", "Équilibré")
    st.session_state.setdefault("map_metric", "Attractivité")
    st.session_state.setdefault("compare_ids", ["usa", "china"])
    st.session_state.setdefault("decoder_country", "usa")
    st.session_state.setdefault("explored", [])
    st.session_state.setdefault("quiz_correct", {})
    for country in countries():
        st.session_state.setdefault(f"amount_{country['id']}", 10000)
    nav = st.session_state.get("nav")
    if nav not in PAGES:
        # Conversion des anciens libellés FR en code de route ; sinon défaut.
        st.session_state["nav"] = _LEGACY_NAV.get(nav, "map")
    if st.session_state.get("lang") not in i18n.LANGS:
        st.session_state["lang"] = i18n.DEFAULT_LANG


def _sidebar() -> None:
    from geocapital import ai
    from geocapital.data import country_by_id, load_data

    explored = st.session_state.get("explored", [])
    profile = st.session_state.get("profile", "Équilibré")
    profile_display = t(f"profile.{i18n.profile_key(profile)}")
    completion = len(explored) / 10 * 100
    quiz_passed = sum(1 for value in st.session_state.get("quiz_correct", {}).values() if value)
    current = country_by_id(st.session_state.get("country_id", "usa"))

    with st.sidebar:
        st.markdown(
            f"""
            <div class="gc-brand">
              <div class="gc-brand-row">
                <div class="gc-brand-mark">◍</div>
                <div>
                  <div class="gc-brand-title">GeoCapital</div>
                  <div class="gc-brand-sub">{t("side.brand_sub")}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.selectbox(
            t("side.language"),
            options=list(i18n.LANGS),
            format_func=lambda code: i18n.LANGS[code],
            key="lang",
        )
        st.markdown(f'<div class="gc-side-label">{t("side.navigation")}</div>', unsafe_allow_html=True)
        st.radio(
            t("side.navigation"),
            PAGES,
            format_func=lambda page: f"{ICONS.get(page, '·')}  {t(f'nav.{page}')}",
            key="nav",
            label_visibility="collapsed",
        )

        st.markdown(f'<div class="gc-side-label">{t("side.journey")}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="gc-side-progress">
              <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">
                <span class="gc-side-muted">{t("side.mental_map")}</span>
                <strong>{len(explored)}/10</strong>
              </div>
              <div class="gc-progress"><div style="width:{completion:.1f}%"></div></div>
              <div class="gc-side-muted">{t("side.profile_line", profile=profile_display, quiz_passed=quiz_passed)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if current:
            st.markdown(
                f'<div style="margin-top:10px;color:#7f8ea4;font-size:.72rem;line-height:1.5">{t("side.last_sheet")} {current["flag"]} <strong style="color:#c8d4e3">{current["name"]}</strong></div>',
                unsafe_allow_html=True,
            )

        st.markdown(f'<div class="gc-side-label">{t("side.engine")}</div>', unsafe_allow_html=True)
        if ai.is_available():
            st.markdown(f'<span class="gc-chip green">{t("side.ai_available")}</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="gc-chip">{t("side.ai_unavailable")}</span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="gc-side-muted" style="margin-top:10px">{t("side.last_update", range=i18n.update_range())}<br>{t("side.prototype_line")}</div>',
            unsafe_allow_html=True,
        )


def main() -> None:
    ui.install_markdown_normalizer()
    st.set_page_config(
        page_title=t("app.page_title"),
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ui.inject_css()
    _init_state()
    _sidebar()

    # Imports après set_page_config : les modules de vues utilisent Streamlit.
    from views import (
        analyst_page,
        comparator_page,
        country_page,
        decoder_page,
        map_page,
        methodology_page,
        portfolio_page,
        progress_page,
    )

    page = st.session_state.get("nav", "map")
    routes = {
        "map": map_page.render,
        "country": country_page.render,
        "compare": comparator_page.render,
        "decoder": decoder_page.render,
        "analyst": analyst_page.render,
        "portfolio": portfolio_page.render,
        "progress": progress_page.render,
        "sources": methodology_page.render,
    }
    routes.get(page, map_page.render)()


if __name__ == "__main__":
    main()
