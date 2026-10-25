"""Module 2 à 4 — Fiche pays, tableau de bord, score et verdict."""

from __future__ import annotations

from typing import Any

import streamlit as st

from geocapital import ai, i18n, ui
from geocapital.i18n import t
from geocapital.data import (
    INDICATOR_LABELS,
    INDICATOR_ORDER,
    countries,
    country_by_id,
    indicator_display,
    indicator_meta,
    load_data,
)
from geocapital.scoring import (
    COMPONENT_LABELS,
    PROFILES,
    VERDICT_STYLES,
    component_scores,
    indicator_status,
    overall_score,
    required_return,
    risk_label,
    score_breakdown,
    top_reasons,
)


def _go_compare(country_id: str) -> None:
    current = st.session_state.get("compare_ids", [])
    others = [item for item in current if item != country_id]
    fallback = "china" if country_id != "china" else "usa"
    peers = ([others[0]] if others else [fallback])
    st.session_state["compare_ids"] = [country_id, peers[0]][:2]
    st.session_state["nav"] = "compare"


def _go_decoder(country_id: str) -> None:
    st.session_state["decoder_country"] = country_id
    st.session_state["nav"] = "decoder"


def _institution_card(institutions: dict[str, Any]) -> None:
    labels = {}
    for key in ("regime", "executive", "legislature", "central_bank", "currency", "law", "fact"):
        labels[key] = t(f"inst.{key}")
    blocks = []
    for key, label in labels.items():
        value = institutions.get(key)
        if not value:
            continue
        blocks.append(
            f"""
            <div style="padding:9px 0;border-top:1px solid rgba(148,163,184,.11)">
              <div style="color:#73849b;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;font-weight:800;margin-bottom:2px">{ui.esc(label)}</div>
              <div style="color:#c4d0df;font-size:.79rem;line-height:1.45">{ui.esc(value)}</div>
            </div>
            """
        )
    st.markdown(
        f'<div class="gc-card" style="padding:17px"><h4 style="margin-bottom:4px">{t("inst.card_title")}</h4>'
        + "".join(blocks)
        + "</div>",
        unsafe_allow_html=True,
    )


def _profile_scores(country: dict[str, Any]) -> dict[str, float]:
    return {profile: overall_score(country, profile)["score"] for profile in PROFILES}


def _localized_reasons(country: dict[str, Any], profile: str) -> list[dict[str, str]]:
    """Présentation traduite des raisons de scoring.top_reasons().

    Les calculs et la logique restent ceux de scoring.py (intouché) : on y
    reprend les libellés FR internes comme repères et on affiche les textes
    de la langue courante via i18n.
    """
    out = []
    for reason in top_reasons(country, profile):
        title, text = reason["title"], reason["text"]
        if title.startswith("Point de vigilance : "):
            comp_fr = title[len("Point de vigilance : ") :]
            key = next(k for k, v in COMPONENT_LABELS.items() if v == comp_fr)
            localized_title = t("reason.vigilance", component=t(f"component.{key}"))
            comment_code = "neg"
        else:
            key = next(k for k, v in COMPONENT_LABELS.items() if v == title)
            localized_title = t(f"component.{key}")
            comment_code = "pos"
        score_part, _, _ = text.partition(". ")
        value = score_part.rsplit(" ", 1)[-1].replace("/100", "")
        localized_text = f"{t('reason.score_line', value=value)} {t(f'comment.{key}.{comment_code}')}"
        out.append({"kind": reason["kind"], "title": localized_title, "text": localized_text})
    return out


def _render_reasons(country: dict[str, Any], profile: str) -> None:
    blocks = []
    for reason in _localized_reasons(country, profile):
        icon = "↗" if reason["kind"] == "positive" else "↘"
        color = "#4ade80" if reason["kind"] == "positive" else "#fb7185"
        blocks.append(
            f"""
            <div style="display:flex;gap:11px;padding:10px 0;border-top:1px solid rgba(148,163,184,.11)">
              <div style="color:{color};font-weight:800;font-size:1rem;margin-top:1px">{icon}</div>
              <div>
                <div style="color:#e4ecf6;font-size:.82rem;font-weight:750;margin-bottom:2px">{ui.esc(reason['title'])}</div>
                <div style="color:#98a8bd;font-size:.76rem;line-height:1.5">{ui.esc(reason['text'])}</div>
              </div>
            </div>
            """
        )
    st.markdown("".join(blocks), unsafe_allow_html=True)


def _ai_country_block(country: dict[str, Any], result: dict[str, Any], suffix: str = "story") -> None:
    with st.expander(t("ai.expander"), expanded=False):
        if not ai.is_available():
            st.caption(t("ai.editorial_caption"))
            return
        st.caption(t("ai.recaption"))
        if st.button(t("ai.button"), key=f"ai_brief_{country['id']}_{suffix}", type="primary"):
            with st.spinner(t("ai.spinner")):
                text = ai.country_brief(country, result)
            if text:
                st.markdown(text)
            else:
                st.warning(t("ai.unavailable"))


def _render_quiz(country: dict[str, Any]) -> None:
    question = country.get("quiz", {})
    if not question:
        return
    cid = country["id"]
    st.markdown(
        f"""
        <div class="gc-card gc-card-gold" style="margin-bottom:14px">
          <div class="gc-eyebrow">{t("quiz.eyebrow")}</div>
          <h4 style="font-size:1.14rem;line-height:1.4">{ui.esc(question.get('question'))}</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )
    choice = st.radio(
        t("quiz.radio"),
        question.get("options", []),
        index=None,
        key=f"quiz_choice_{cid}",
        label_visibility="collapsed",
    )
    validate = st.button(t("quiz.button"), key=f"quiz_btn_{cid}", type="primary")
    if validate:
        if choice is None:
            st.warning(t("quiz.warn_none"))
        else:
            correct = question["options"].index(choice) == question["answer"]
            st.session_state["quiz_correct"][cid] = correct
            st.session_state[f"quiz_result_{cid}"] = {"correct": correct, "choice": choice}

    saved = st.session_state.get(f"quiz_result_{cid}")
    if saved and saved.get("choice") == choice:
        correct = bool(saved["correct"])
        if correct:
            st.success(t("quiz.success"))
        else:
            st.error(t("quiz.error"))
        st.markdown(
            f'<div class="gc-callout {"green" if correct else "red"}"><strong>{t("quiz.why")}</strong> {ui.esc(question.get("explanation"))}</div>',
            unsafe_allow_html=True,
        )
        if ai.is_available():
            if st.button(t("quiz.ai_button"), key=f"ai_quiz_{cid}"):
                with st.spinner(t("quiz.ai_spinner")):
                    text = ai.explain_quiz(country, question, correct)
                if text:
                    st.markdown(text)
        else:
            st.caption(t("quiz.ai_hint"))

    if st.session_state["quiz_correct"].get(cid):
        st.markdown(f'<span class="gc-chip green">{t("quiz.chip_done")}</span>', unsafe_allow_html=True)


def render() -> None:
    all_countries = countries()
    ids = [c["id"] for c in all_countries]
    if st.session_state.get("country_id") not in ids:
        st.session_state["country_id"] = ids[0]

    select_col, profile_col = st.columns([1.5, 1.7])
    with select_col:
        selected_id = st.selectbox(
            t("country.select"),
            ids,
            format_func=lambda cid: f"{country_by_id(cid)['flag']} {country_by_id(cid)['name']}",
            key="country_id",
        )
    with profile_col:
        profile = st.radio(
            t("country.profile_radio"),
            list(PROFILES.keys()),
            horizontal=True,
            key="profile",
            format_func=i18n.profile_label,
        )

    country = country_by_id(selected_id)
    if country is None:
        st.error(t("country.error"))
        return

    if selected_id not in st.session_state["explored"]:
        st.session_state["explored"] = sorted([*st.session_state["explored"], selected_id])

    result = overall_score(country, profile)
    result["verdict_tone"] = VERDICT_STYLES[result["verdict"]]["tone"]
    ke = required_return(country)
    scores = _profile_scores(country)
    rank = sorted(
        [overall_score(c, profile)["score"] for c in all_countries],
        reverse=True,
    ).index(result["score"]) + 1

    ui.country_hero(country, result)
    action_a, action_b, action_c, action_d = st.columns([1, 1, 1, 2.2])
    profile_display = i18n.profile_label(profile)
    with action_a:
        st.button(t("country.action.compare"), key=f"country_compare_{selected_id}", width="stretch", on_click=_go_compare, args=(selected_id,))
    with action_b:
        st.button(t("nav.decoder"), key=f"country_decoder_{selected_id}", width="stretch", on_click=_go_decoder, args=(selected_id,))
    with action_c:
        st.markdown(
            f'<div class="gc-chip" style="margin-top:4px">{t("country.chip.rank", rank=rank, profile=ui.esc(profile_display))}</div>',
            unsafe_allow_html=True,
        )
    with action_d:
        st.markdown(
            f'<div style="text-align:right;color:#7f8fa5;font-size:.72rem;margin-top:8px">{t("country.updated")} {ui.esc(i18n.update_range())}</div>',
            unsafe_allow_html=True,
        )

    tab_story, tab_dashboard, tab_score, tab_quiz = st.tabs(
        [t("country.tab.story"), t("country.tab.dashboard"), t("country.tab.score"), t("country.tab.quiz")]
    )

    with tab_story:
        ui.callout(country.get("summary", ""), "gold")
        left, right = st.columns([1.65, 1], gap="large")
        with left:
            ui.section_title(t("country.section.timeline"), t("country.section.timeline_sub"))
            ui.timeline(country.get("history", []))
        with right:
            _institution_card(country.get("institutions", {}))
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            current = result["components"]
            st.markdown(
                f"""
                <div class="gc-card" style="padding:17px">
                  <div class="gc-eyebrow">{t("country.hero_to_risk")}</div>
                  <h4 style="font-size:.94rem">{t("country.story_in_numbers")}</h4>
                  <p style="font-size:.78rem;line-height:1.6">
                    {t("country.story_paragraph", solv=f"{current['solvabilite']:.0f}", stab=f"{current['stabilite']:.0f}", inst=f"{current['institutions']:.0f}")}
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        ui.section_title(t("country.section.relations"), t("country.section.relations_sub"))
        rel = country.get("relations", {})
        rel_cols = st.columns(3)
        with rel_cols[0]:
            ui.relation_column(t("country.rel.allies"), "🤝", rel.get("allies", []))
        with rel_cols[1]:
            ui.relation_column(t("country.rel.rivals"), "⚔️", rel.get("rivals", []))
        with rel_cols[2]:
            ui.relation_column(t("country.rel.dependencies"), "🔗", rel.get("dependencies", []))

        ui.section_title(t("country.section.decision"), t("country.section.decision_sub"))
        strength_col, risk_col, opp_col = st.columns(3)
        with strength_col:
            st.markdown(
                f'<div class="gc-card"><div class="gc-eyebrow">{t("country.eyebrow.strengths")}</div><ul class="gc-list">'
                + "".join(f"<li>{ui.esc(item)}</li>" for item in country.get("strengths", []))
                + "</ul></div>",
                unsafe_allow_html=True,
            )
        with risk_col:
            st.markdown(
                f'<div class="gc-card"><div class="gc-eyebrow">{t("country.eyebrow.risks")}</div><ul class="gc-list">'
                + "".join(f"<li>{ui.esc(item)}</li>" for item in country.get("risks", []))
                + "</ul></div>",
                unsafe_allow_html=True,
            )
        with opp_col:
            st.markdown(
                f'<div class="gc-card"><div class="gc-eyebrow">{t("country.eyebrow.opportunities")}</div><ul class="gc-list">'
                + "".join(f"<li>{ui.esc(item)}</li>" for item in country.get("opportunities", []))
                + "</ul></div>",
                unsafe_allow_html=True,
            )

        _ai_country_block(country, result)

    with tab_dashboard:
        ui.section_title(t("country.section.indicators"), t("country.section.indicators_sub"))
        st.markdown(
            f'<div class="gc-small" style="margin-bottom:12px">{t("country.dash.hint")}</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        for index, key in enumerate(INDICATOR_ORDER):
            meta = indicator_meta(country, key)
            value, unit, date = indicator_display(country, key)
            status = indicator_status(country, key)
            note = meta.get("note", "")
            source = meta.get("source", "Source non renseignée")
            if source == "Source non renseignée":
                source = t("dash.source_missing")
            with cols[index % 4]:
                ui.indicator_card(
                    INDICATOR_LABELS[key],
                    value,
                    unit,
                    status,
                    note,
                    source,
                    date,
                )
                st.markdown("<div style='height:9px'></div>", unsafe_allow_html=True)

        if country["id"] in {"lebanon", "syria"}:
            ui.callout(
                t("country.callout.missing"),
                "red",
            )

        ui.section_title(t("country.section.pricerisk"), t("country.section.pricerisk_sub"))
        ke_cols = st.columns(4)
        with ke_cols[0]:
            ui.kpi("4,20 %", t("country.kpi.risk_free"), t("country.kpi.risk_free_desc"))
        with ke_cols[1]:
            ui.kpi("4,50 %", t("country.kpi.erp"), t("country.kpi.erp_desc"))
        with ke_cols[2]:
            crp_source_label = t(f"crp_source.{i18n.crp_source_key(ke['crp_source'])}")
            ui.kpi(f"{ke['crp']:.1f} %", t("country.kpi.crp"), t("country.kpi.crp_desc", source=crp_source_label))
        with ke_cols[3]:
            ui.kpi(f"{ke['ke']:.1f} %", t("country.kpi.ke"), t("country.kpi.ke_desc"))
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="gc-card">
              <div class="gc-eyebrow">{t("country.howto.eyebrow")}</div>
              <h4 style="font-size:.98rem">{t("country.howto.title")}</h4>
              <p style="font-size:.82rem;line-height:1.65;margin-top:6px">
                {t("country.howto.text", name=ui.esc(country['name']), rf=f"{ke['risk_free']:.1f}", erp=f"{ke['erp']:.1f}", crp=f"{ke['crp']:.1f}", ke=f"{ke['ke']:.1f}")}
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(t("country.sources.caption"))

    with tab_score:
        score_left, score_right = st.columns([1, 1.15], gap="large")
        with score_left:
            st.markdown(
                f"""
                <div class="gc-card">
                  <div class="gc-score-row">
                    {ui.ring(result['score'], t('ring.scale'))}
                    <div>
                      {ui.verdict_badge(t(f'verdict.{i18n.verdict_key(result["verdict"])}'), result['verdict_tone'])}
                      <div class="gc-verdict-sub">{ui.esc(t(f"verdict.copy.{i18n.verdict_key(result['verdict'])}"))}</div>
                      <div class="gc-small" style="margin-top:10px">{t("country.risk_line", rank=rank, profile=ui.esc(profile_display), value=f"{result['risk']:.0f}", label=t(f"risk.{i18n.risk_key(risk_label(result['risk']))}").lower())}</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="gc-card">
                  <div class="gc-eyebrow">{t("country.reasons.eyebrow")}</div>
                  {''.join([f'<div style="padding:9px 0;border-top:1px solid rgba(148,163,184,.11)"><strong style="color:#e4ecf6;font-size:.82rem">{ui.esc(r["title"])}</strong><div style="color:#98a8bd;font-size:.76rem;line-height:1.5;margin-top:2px">{ui.esc(r["text"])}</div></div>' for r in _localized_reasons(country, profile)])}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="gc-card gc-card-gold">
                  <div class="gc-eyebrow">{t("country.ke.eyebrow")}</div>
                  <div class="gc-ke"><strong>{ke['ke']:.1f} %</strong><span>{t("country.ke.annual")}</span></div>
                  <div class="gc-small" style="margin-top:7px">{t("country.ke.line", rf=f"{ke['risk_free']:.1f}", erp=f"{ke['erp']:.1f}", crp=f"{ke['crp']:.1f}", source=ui.esc(t(f"crp_source.{i18n.crp_source_key(ke['crp_source'])}")))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with score_right:
            st.markdown(
                f"""
                <div class="gc-card">
                  <div class="gc-eyebrow">{t("country.breakdown.eyebrow")}</div>
                  <h4 style="margin-bottom:14px">{t("country.breakdown.title")}</h4>
                </div>
                """,
                unsafe_allow_html=True,
            )
            breakdown_rows = [dict(row, label=t(f"component.{row['key']}")) for row in score_breakdown(country, profile)]
            ui.component_bars(breakdown_rows)

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="gc-card">
                  <div class="gc-eyebrow">{t("country.by_profile.eyebrow")}</div>
                  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px">
                    {''.join([f'<div style="text-align:center;padding:11px 5px;border-radius:12px;background:{"rgba(230,184,107,.12)" if p == profile else "rgba(255,255,255,.035)"};border:1px solid {"rgba(230,184,107,.3)" if p == profile else "rgba(148,163,184,.14)"}"><div style="color:#e6b86b;font-weight:800;font-size:1.25rem">{scores[p]:.0f}</div><div style="color:#8fa0b6;font-size:.65rem;text-transform:uppercase;letter-spacing:.08em">{ui.esc(t(f"profile.{i18n.profile_key(p)}"))}</div></div>' for p in PROFILES])}
                  </div>
                  <p style="font-size:.76rem;margin-top:10px;color:#8292a8;line-height:1.5">{t("country.by_profile.text")}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            _ai_country_block(country, result, suffix="score")

            components = component_scores(country)
            weakest = min(components.items(), key=lambda item: item[1])
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            ui.callout(
                t("country.vigilance.callout", component=t(f"component.{weakest[0]}"), value=f"{weakest[1]:.0f}"),
                "orange",
            )

    with tab_quiz:
        _render_quiz(country)

    ui.footer()
