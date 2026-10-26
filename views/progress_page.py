"""Module 6 — Progression et carte mentale."""

from __future__ import annotations

import streamlit as st

from geocapital import i18n, ui
from geocapital.i18n import t
from geocapital.data import countries
from geocapital.scoring import VERDICT_STYLES, overall_score


def _go_country(country_id: str) -> None:
    st.session_state["country_id"] = country_id
    st.session_state["nav"] = "country"


def _reset_progress() -> None:
    st.session_state["explored"] = []
    st.session_state["quiz_correct"] = {}
    for key in list(st.session_state.keys()):
        if key.startswith("quiz_choice_") or key.startswith("quiz_result_"):
            del st.session_state[key]


def render() -> None:
    all_countries = countries()
    explored = set(st.session_state.get("explored", []))
    quiz_correct = st.session_state.get("quiz_correct", {})
    correct_count = sum(1 for value in quiz_correct.values() if value)
    profile = st.session_state.get("profile", "Équilibré")

    ui.page_head(
        t("pr.eyebrow"),
        t("pr.title"),
        t("pr.subtitle"),
    )

    completion = len(explored) / len(all_countries) * 100 if all_countries else 0
    explored_scores = [
        overall_score(country, profile)["score"] for country in all_countries if country["id"] in explored
    ]
    average = sum(explored_scores) / len(explored_scores) if explored_scores else 0

    top_cols = st.columns([1.1, 1, 1, 1])
    with top_cols[0]:
        ui.kpi(f"{len(explored)}<small>/10</small>", t("pr.kpi.explored"), t("pr.kpi.explored_desc", pct=f"{completion:.0f}"))
    with top_cols[1]:
        ui.kpi(f"{correct_count}<small>/10</small>", t("pr.kpi.quiz"), t("pr.kpi.quiz_desc"))
    with top_cols[2]:
        ui.kpi(f"{average:.0f}<small>/100</small>", t("pr.kpi.average"), t("pr.kpi.average_desc", profile=i18n.profile_label(profile)))
    with top_cols[3]:
        ui.kpi(f"{len(all_countries) - len(explored)}", t("pr.kpi.remaining"), t("pr.kpi.remaining_desc"))

    st.markdown(
        f"""
        <div class="gc-card" style="margin-top:14px">
          <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">
            <div><div class="gc-eyebrow">{t("pr.card.eyebrow")}</div><h4 style="font-size:1rem">{t("pr.card.title")}</h4></div>
            <div style="color:#e6b86b;font-weight:800">{completion:.0f} %</div>
          </div>
          <div class="gc-progress"><div style="width:{completion:.1f}%"></div></div>
          <div class="gc-small">{t("pr.card.note")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ui.section_title(t("pr.section.badges"), t("pr.section.badges_sub"))
    badges = [
        (t("pr.badge.first"), len(explored) >= 1, t("pr.badge_note.first")),
        (t("pr.badge.curious"), len(explored) >= 3, t("pr.badge_note.curious")),
        (t("pr.badge.cartographer"), len(explored) >= 5, t("pr.badge_note.cartographer")),
        (t("pr.badge.world"), len(explored) >= 10, t("pr.badge_note.world")),
        (t("pr.badge.quiz"), correct_count >= 5, t("pr.badge_note.quiz")),
    ]
    badge_cols = st.columns(5)
    for col, (label, active, note) in zip(badge_cols, badges):
        with col:
            st.markdown(
                f'<div class="gc-badge {"on" if active else ""}" style="width:100%;justify-content:center;padding:12px 8px;text-align:center;display:flex;flex-direction:column;gap:3px"><span>{"★" if active else "☆"} {ui.esc(label)}</span><span style="font-weight:500;font-size:.62rem;opacity:.7">{ui.esc(note)}</span></div>',
                unsafe_allow_html=True,
            )

    ui.section_title(t("pr.section.countries"), t("pr.section.countries_sub"))
    groups = ["Développé", "Émergent", "Golfe", "Frontière"]
    group_cols = st.columns(4)
    for col, group in zip(group_cols, groups):
        with col:
            st.markdown(f'<div class="gc-eyebrow" style="margin-bottom:8px">{ui.esc(t(f"group.{i18n.group_key(group)}"))}</div>', unsafe_allow_html=True)
            for country in [i18n.localize_country(c) for c in all_countries if c["group"] == group]:
                done = country["id"] in explored
                quiz = quiz_correct.get(country["id"])
                result = overall_score(country, profile)
                status = t("pr.status.explored") if done else t("pr.status.to_discover")
                quiz_text = t("pr.quiz.done") if quiz else t("pr.quiz.todo") if done else t("pr.quiz.to_open")
                st.markdown(
                    f"""
                    <div class="gc-tile {'done' if done else ''}" style="min-height:132px;padding:13px">
                      <div class="gc-tile-top">
                        <span class="gc-tile-flag">{country['flag']}</span>
                        <span class="gc-chip {'green' if done else ''}" style="font-size:.6rem">{'✓' if done else '○'} {ui.esc(status)}</span>
                      </div>
                      <h4 style="font-size:.86rem">{ui.esc(country['name'])}</h4>
                      <p>{ui.esc(quiz_text)} · {t("pr.tile.score", value=f"{result['score']:.0f}")}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button(
                    t("pr.btn.revisit") if done else t("pr.btn.open"),
                    key=f"progress_open_{country['id']}",
                    width="stretch",
                    on_click=_go_country,
                    args=(country["id"],),
                )

    unvisited = [c for c in all_countries if c["id"] not in explored]
    ui.section_title(t("pr.section.next"), t("pr.section.next_sub"))
    if unvisited:
        ranked = sorted(unvisited, key=lambda c: overall_score(c, profile)["score"], reverse=True)
        next_country = i18n.localize_country(ranked[0])
        next_col, button_col = st.columns([3, 1])
        with next_col:
            st.markdown(
                f"""
                <div class="gc-card gc-card-gold">
                  <div class="gc-eyebrow">{t("pr.next.eyebrow")}</div>
                  <h4 style="font-size:1.05rem">{next_country['flag']} {ui.esc(next_country['name'])} · {overall_score(next_country, profile)['score']:.0f}/100</h4>
                  <p>{ui.esc(next_country.get('headline', ''))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with button_col:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            st.button(
                t("pr.btn.open_full"),
                key="progress_next",
                type="primary",
                width="stretch",
                on_click=_go_country,
                args=(next_country["id"],),
            )
    else:
        ui.callout(t("pr.done_callout"), "green")

    with st.expander(t("pr.reset.expander"), expanded=False):
        st.caption(t("pr.reset.caption"))
        confirm = st.checkbox(t("pr.reset.confirm"), key="confirm_reset_progress")
        st.button(
            t("pr.reset.button"),
            key="reset_progress",
            disabled=not confirm,
            on_click=_reset_progress,
        )

    ui.callout(
        t(
            "pr.callout.verdicts",
            invest=t("verdict.invest"),
            wait=t("verdict.wait"),
        ),
        "blue",
    )
    ui.footer()
