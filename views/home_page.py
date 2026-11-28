"""Accueil — page d'entrée de GeoCapp.

Composition : un hero central (titre, texte, deux notes adhésives), un bouton
d'appel à l'action réel (st.button) puis trois dossiers flottants présentant des
fonctionnalités qui existent dans l'application.

Éléments interactifs : le bouton « Explorer GeoCapp » (ouvre la Carte vivante).
Tout le reste est décoratif ou informatif (aucun comportement caché).
"""

from __future__ import annotations

import streamlit as st

from geocapital import ui
from geocapital.i18n import t

# Illustrations de dossier : SVG au trait, couleur héritée (currentColor).
_SVG_ATTRS = 'viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'
_ICONS = {
    # Conversation / assistance analytique
    "ai": (
        f'<svg {_SVG_ATTRS}>'
        '<path d="M10 14h30a4 4 0 0 1 4 4v14a4 4 0 0 1-4 4H26l-9 8v-8h-7a4 4 0 0 1-4-4V18a4 4 0 0 1 4-4z"/>'
        '<path d="M48 26h6a4 4 0 0 1 4 4v12a4 4 0 0 1-4 4h-3v6l-7-6h-8"/>'
        '<path d="M16 22h20M16 29h12"/>'
        "</svg>"
    ),
    # Globe et méridiens : risque pays
    "risk": (
        f'<svg {_SVG_ATTRS}>'
        '<circle cx="32" cy="32" r="22"/>'
        '<path d="M10 32h44M32 10c-9 8-9 36 0 44M32 10c9 8 9 36 0 44"/>'
        '<path d="M15 20c6 3 12 3 17 0M32 44c6-3 12-3 17 0"/>'
        "</svg>"
    ),
    # Barres et courbe : valorisation
    "finance": (
        f'<svg {_SVG_ATTRS}>'
        '<path d="M8 54h48"/>'
        '<path d="M14 54V38M26 54V28M38 54V34M50 54V20"/>'
        '<path d="M10 28l14-12 12 8 18-14"/><path d="M46 10h8v8"/>'
        "</svg>"
    ),
}

_FOLDERS = ("ai", "risk", "finance")


def _hero_html() -> str:
    return f"""
    <div class="gc-home-q">
      <section class="gc-home-hero">
        <div class="gc-eyebrow">{ui.esc(t("home.eyebrow"))}</div>
        <h1>
          <span>{ui.esc(t("home.title.1"))}</span>
          <span>{ui.esc(t("home.title.2"))}</span>
          <em>{ui.esc(t("home.title.3"))}</em>
        </h1>
        <p class="gc-home-sub">{ui.esc(t("home.subtitle"))}</p>
        <div class="gc-home-note a" aria-hidden="true">
          <span class="gc-home-pin"></span>
          <p>{ui.esc(t("home.note.1"))}</p>
        </div>
        <div class="gc-home-note b" aria-hidden="true">
          <span class="gc-home-pin"></span>
          <p>{ui.esc(t("home.note.2"))}</p>
        </div>
      </section>
    </div>
    """


def _folders_html() -> str:
    cards = "".join(
        f"""
        <article class="gc-folder {key}">
          <div class="gc-folder-sheet" aria-hidden="true"></div>
          <div class="gc-folder-tab" aria-hidden="true"></div>
          <div class="gc-folder-body">
            <div class="gc-folder-visual">{_ICONS[key]}</div>
            <h3>{ui.esc(t(f"home.folder.{key}.title"))}</h3>
            <p>{ui.esc(t(f"home.folder.{key}.text"))}</p>
          </div>
        </article>
        """
        for key in _FOLDERS
    )
    return f'<div class="gc-home-q"><div class="gc-home-folders">{cards}</div></div>'


def _open_map() -> None:
    st.session_state["nav"] = "map"


def render() -> None:
    st.markdown(_hero_html(), unsafe_allow_html=True)
    with st.container(key="home_cta"):
        st.button(t("home.cta"), key="home_open_map", type="primary", on_click=_open_map, width="content")
    st.markdown(_folders_html(), unsafe_allow_html=True)
