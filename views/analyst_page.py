"""Page Analyste — interface conversationnelle ancrée aux données."""

from __future__ import annotations

import json

import streamlit as st

from geocapital import ai, analyst, data, i18n, limits, scoring, ui
from geocapital.i18n import t

PAGE_KEY = "analyst_messages"

INTENT_ICONS = {
    "country": "▤",
    "compare": "⇄",
    "verdict": "✓",
    "capital": "⌁",
    "event": "⌦",
    "portfolio": "◫",
}

FALLBACK_QUESTION = "Donne-moi une vue d'ensemble des pays couverts par GeoCapital."


def _init_state() -> None:
    st.session_state.setdefault(PAGE_KEY, [])
    st.session_state.setdefault("analyst_intent", "country")
    st.session_state.setdefault("analyst_country", st.session_state.get("country_id", "usa"))
    st.session_state.setdefault("analyst_compare", ["usa", "china"])
    st.session_state.setdefault("analyst_event", None)


def _clear_conversation() -> None:
    st.session_state[PAGE_KEY] = []


def _entity_selector(intent: str) -> None:
    countries = data.countries()
    # Noms affichés dans la langue courante ; les payloads (analyst.py)
    # restent construits sur la donnée FR, langue des faits déterministe.
    names = {c["id"]: f"{c['flag']} {i18n.country_name(c['id'])}" for c in countries}
    if intent == "country":
        st.selectbox(
            t("an.select.country"),
            list(names.keys()),
            format_func=lambda cid: names.get(cid, cid),
            key="analyst_country",
            placeholder=t("an.ph.country"),
        )
    elif intent == "compare":
        st.multiselect(
            t("an.select.compare"),
            list(names.keys()),
            default=["usa", "china"],
            format_func=lambda cid: names.get(cid, cid),
            key="analyst_compare",
            placeholder=t("an.ph.compare"),
        )
    elif intent in ("verdict", "capital"):
        st.selectbox(
            t("an.select.verdict"),
            list(names.keys()),
            format_func=lambda cid: names.get(cid, cid),
            key="analyst_country",
            placeholder=t("an.ph.country"),
        )
    elif intent == "event":
        events = data.load_events()
        event_names = {e["id"]: i18n.event_name(e["id"]) for e in events}
        st.selectbox(
            t("an.select.event"),
            list(event_names.keys()),
            format_func=lambda eid: event_names.get(eid, eid),
            key="analyst_event",
            placeholder=t("an.ph.event"),
        )
    elif intent == "portfolio":
        total = sum(int(st.session_state.get(f"amount_{c['id']}", 0) or 0) for c in countries)
        st.caption(t("an.allocation.current", amount=ui.eur(total)))


def _payload_for(question: str) -> dict:
    intent = st.session_state.get("analyst_intent", "country")
    profile = st.session_state.get("profile", "Équilibré")
    return analyst.build_context(
        intent,
        question,
        profile=profile,
        country_id=st.session_state.get("analyst_country"),
        compare_ids=st.session_state.get("analyst_compare"),
        event_id=st.session_state.get("analyst_event"),
        amounts={
            c["id"]: st.session_state.get(f"amount_{c['id']}", 0) for c in data.countries()
        },
    )


def _facts_expander(payload: dict, expanded: bool = False) -> None:
    with st.expander(t("an.facts.expander"), expanded=expanded):
        st.caption(t("an.facts.caption"))
        st.markdown(
            "<pre style='font-size:.72rem;line-height:1.5;color:#a9b7cc;"
            "white-space:pre-wrap'>"
            + ui.esc(json.dumps(payload, ensure_ascii=False, indent=2))
            + "</pre>",
            unsafe_allow_html=True,
        )


def _render_history() -> None:
    for message in st.session_state[PAGE_KEY]:
        role = "user" if message["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(message["content"])


def _handle_question(prompt: str) -> None:
    # Garde-fou serveur : au-delà de la limite, aucun appel fournisseur n'est
    # émis (le garde-fou d'affichage désactive déjà la saisie — double barrière).
    if not limits.can_ask(limits.used(), limits.limit()):
        return
    # Une question soumise = une unité, quel que soit le résultat (réponse
    # fournisseur, échec → repli éditorial, mode éditorial sans clé).
    # cf. docs/AI_LIMITS.md
    limits.record()
    payload = _payload_for(prompt)
    history = st.session_state[PAGE_KEY][-analyst.MAX_EXCHANGES * 2 :]
    messages = analyst.build_messages(payload, prompt, history=history)

    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner(t("an.spinner.model") if ai.is_available() else t("an.spinner.editorial")):
            response = ai.chat(messages) if ai.is_available() else None
        if response:
            st.markdown(f'<span class="gc-chip gold">{ui.esc(t("an.chip.interpretation"))}</span>', unsafe_allow_html=True)
        else:
            ui.callout(t("an.unavailable"), "orange")
            response = analyst.editorial_answer(payload, prompt)
            st.markdown(f'<span class="gc-chip orange">{ui.esc(t("an.chip.facts_python"))}</span>', unsafe_allow_html=True)
        st.markdown(response)
        _facts_expander(payload)
        st.caption(t("an.prototype_caption"))

    # L'historique persisté ne contient que l'échange net ; le riche contexte
    # factuel est reconstruit à chaque tour et n'encombre pas l'écran.
    st.session_state[PAGE_KEY].append({"role": "user", "content": prompt})
    st.session_state[PAGE_KEY].append({"role": "assistant", "content": response})


def render() -> None:
    _init_state()
    ui.page_head(
        t("an.eyebrow"),
        t("an.title"),
        t("an.subtitle"),
    )

    toolbar_cols = st.columns([2.2, 1.4, 1.2])
    with toolbar_cols[0]:
        intent_codes = [code for code, _ in analyst.INTENTS]
        st.selectbox(
            t("an.select.topic"),
            intent_codes,
            format_func=lambda code: f"{INTENT_ICONS.get(code, '·')}  {i18n.intent_label(code)}",
            key="analyst_intent",
        )
    with toolbar_cols[1]:
        _entity_selector(st.session_state.get("analyst_intent", "country"))
    with toolbar_cols[2]:
        st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
        if st.button(t("an.btn.clear"), width="stretch"):
            _clear_conversation()

    st.markdown(
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 10px'>"
        f'<span class="gc-chip green">{ui.esc(t("an.chip.facts"))}</span>'
        f'<span class="gc-chip lime">{ui.esc(t("an.chip.interpretation"))}</span>'
        f'<span class="gc-chip">{ui.esc(t("an.chip.hypothesis"))}</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("analyst_intent") == "portfolio" and not any(
        int(st.session_state.get(f"amount_{c['id']}", 0) or 0) > 0 for c in data.countries()
    ):
        ui.callout(t("an.portfolio.empty"), "orange")

    _render_history()

    if not ai.is_available():
        ui.callout(t("an.editorial_mode"), "orange")

    # Limite de questions par session (serveur) : affichage + blocage doux.
    limit_value = limits.limit()
    used_value = limits.used()
    remaining_value = limits.remaining(used_value, limit_value)
    if remaining_value > 0:
        st.caption(t("an.limit.remaining", remaining=remaining_value, total=limit_value))
        prompt = st.chat_input(t("an.input.placeholder"))
    else:
        ui.callout(t("an.limit.reached", total=limit_value), "orange")
        st.chat_input(t("an.input.placeholder"), disabled=True)
        prompt = None
    if prompt and prompt.strip():
        _handle_question(prompt.strip())

    ui.footer()
