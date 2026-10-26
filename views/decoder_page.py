"""Module 5 — Le décodeur d'actualité."""

from __future__ import annotations

import streamlit as st

from geocapital import ai, i18n, ui
from geocapital.i18n import t
from geocapital.data import countries, country_by_id, load_events
from geocapital.scoring import VERDICT_STYLES, overall_score, required_return


def _go_country(country_id: str) -> None:
    st.session_state["country_id"] = country_id
    st.session_state["nav"] = "country"


def render() -> None:
    ui.page_head(
        t("dec.eyebrow"),
        t("dec.title"),
        t("dec.subtitle"),
    )

    events = i18n.localize_events(load_events())
    valid_ids = [c["id"] for c in countries()]
    if st.session_state.get("decoder_country") not in valid_ids:
        st.session_state["decoder_country"] = valid_ids[0]

    control_a, control_b = st.columns([1, 2.2])
    with control_a:
        selected_country = st.selectbox(
            t("dec.country"),
            valid_ids,
            format_func=lambda cid: f"{country_by_id(cid)['flag']} {i18n.country_name(cid)}",
            key="decoder_country",
        )
    available = [event for event in events if event.get("country") == selected_country]
    with control_b:
        if not available:
            st.warning(t("dec.no_events"))
            return
        event_id = st.selectbox(
            t("dec.event_select"),
            [event["id"] for event in available],
            format_func=lambda eid: next(
                f"{event['date']} · {event['title']}" for event in available if event["id"] == eid
            ),
            key=f"decoder_event_{selected_country}",
        )
    event = next(event for event in available if event["id"] == event_id)
    country = country_by_id(selected_country)
    country_loc = i18n.localize_country(country)
    result = overall_score(country, st.session_state.get("profile", "Équilibré"))
    ke = required_return(country)

    st.markdown(
        f"""
        <div class="gc-card gc-card-gold" style="margin:10px 0 16px">
          <div style="display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;align-items:flex-start">
            <div>
              <div class="gc-eyebrow">{ui.esc(event.get('category'))} · {ui.esc(country['flag'])} {ui.esc(country_loc['name'])}</div>
              <h2 style="font-family:'DM Serif Display',Georgia,serif;font-weight:400;color:#f8f4e9;font-size:clamp(1.5rem,2.6vw,2.25rem);margin:.25rem 0 .55rem;line-height:1.1">{ui.esc(event.get('title'))}</h2>
              <p style="color:#aab7c9;font-size:.88rem;max-width:780px;margin:0">{ui.esc(event.get('summary'))}</p>
            </div>
            <div style="text-align:right">
              <span class="gc-chip gold">{ui.esc(event.get('date'))}</span>
              <div class="gc-small" style="margin-top:7px">{t("dec.source_prefix")} {ui.esc(event.get('source'))}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    main_col, side_col = st.columns([1.55, 1], gap="large")
    with main_col:
        ui.section_title(t("dec.section.chain"), t("dec.section.chain_sub"))
        ui.chain_steps(event.get("chain", []))
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        ui.callout(
            t("dec.callout.chain"),
            "blue",
        )

        with st.expander(t("dec.expander.concepts"), expanded=False):
            for concept in event.get("concepts", []):
                st.markdown(
                    f"**{ui.esc(concept['term'])}** — {ui.esc(concept['definition'])}"
                )

        with st.expander(t("dec.expander.ai"), expanded=False):
            if not ai.is_available():
                st.caption(t("dec.ai.editorial_caption"))
            else:
                st.caption(t("dec.ai.receive"))
                if st.button(t("dec.ai.button"), key=f"ai_event_{event['id']}", type="primary"):
                    with st.spinner(t("dec.ai.spinner")):
                        text = ai.decode_event(event, country)
                    if text:
                        st.markdown(text)
                    else:
                        st.warning(t("ai.unavailable"))

    with side_col:
        ui.section_title(t("dec.section.wl"), t("dec.section.wl_sub"))
        ui.winners_losers(event.get("winners", []), event.get("losers", []))

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        echo = event.get("history", {})
        st.markdown(
            f"""
            <div class="gc-card">
              <div class="gc-eyebrow">{t("dec.echo", year=ui.esc(echo.get('year')))}</div>
              <h4 style="font-size:1rem">{ui.esc(echo.get('title'))}</h4>
              <p style="font-size:.8rem;line-height:1.65">{ui.esc(echo.get('text'))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        tone = VERDICT_STYLES[result["verdict"]]["tone"]
        st.markdown(
            f"""
            <div class="gc-card">
              <div class="gc-eyebrow">{t("dec.link.eyebrow")}</div>
              <h4 style="font-size:1rem">{ui.esc(country_loc['name'])}</h4>
              <div style="display:flex;gap:8px;flex-wrap:wrap;margin:9px 0">
                {ui.verdict_badge(t(f"verdict.{i18n.verdict_key(result['verdict'])}"), tone)}
                <span class="gc-chip">{t("dec.link.chip_score", value=f"{result['score']:.0f}")}</span>
                <span class="gc-chip">Ke {ke['ke']:.1f} %</span>
              </div>
              <p style="font-size:.78rem">{t("dec.link.text")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            t("dec.open_full"),
            key=f"decoder_open_{country['id']}",
            width="stretch",
            on_click=_go_country,
            args=(country["id"],),
        )

    ui.callout(
        t("dec.callout.reliability"),
        "green",
    )
    ui.footer()
