"""Style monochrome partagé des graphiques Plotly (présentation uniquement).

Aucune donnée ni aucun calcul ici : seulement la palette, la typographie et
les gabarits de mise en page. Les couleurs sémantiques (risque, alerte) ne
s'utilisent que là où le sens financier l'exige.
"""

from __future__ import annotations

from typing import Any

OBSIDIAN = "#121212"
GRAPHITE = "#3A3A3A"
SLATE = "#6E6E73"
SILVER = "#A1A1A6"
LIGHT = "#D1D1D6"
WHITE = "#FFFFFF"

# Séries : nuances de gris + symboles/tirets pour les distinguer.
SERIES = [OBSIDIAN, SLATE, SILVER, GRAPHITE]
SYMBOLS = ["circle", "diamond", "square", "triangle-up"]
DASHES = ["solid", "dash", "dot", "dashdot"]

# Sémantique (rare, atténuée)
RED = "#B4443C"
AMBER = "#B7791F"
GREEN = "#2E7D4F"

FONT = "Inter, system-ui, sans-serif"
GRID = "rgba(17,17,17,0.06)"
GRID_STRONG = "rgba(17,17,17,0.14)"
CLEAR = "rgba(0,0,0,0)"


def hex_to_rgb(color: str) -> str:
    color = color.lstrip("#")
    return f"{int(color[0:2], 16)},{int(color[2:4], 16)},{int(color[4:6], 16)}"


def axis(**extra: Any) -> dict[str, Any]:
    base = dict(
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID_STRONG,
        tickfont=dict(size=10, color=SLATE),
        title_font=dict(size=11, color=SLATE),
    )
    base.update(extra)
    return base


def layout(height: int, margin: dict[str, int] | None = None, **extra: Any) -> dict[str, Any]:
    """Gabarit de base : fond transparent (le verre vient de la carte CSS)."""
    base: dict[str, Any] = dict(
        height=height,
        margin=margin or dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=CLEAR,
        plot_bgcolor=CLEAR,
        font=dict(family=FONT, color=SLATE, size=11),
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.97)",
            bordercolor=LIGHT,
            font=dict(family=FONT, color=OBSIDIAN, size=12),
        ),
        legend=dict(
            orientation="h",
            y=-0.16,
            x=0,
            font=dict(size=10, color=SLATE),
            bgcolor=CLEAR,
        ),
    )
    base.update(extra)
    return base
