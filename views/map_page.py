"""Module 1 — La carte vivante."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from geocapital import ai, i18n, ui
from geocapital.i18n import t
from geocapital.data import countries
from geocapital.scoring import (
    PROFILES,
    VERDICT_STYLES,
    overall_score,
    required_return,
)

# Clés internes du sélecteur (stockées telles quelles dans session_state)
# → codes i18n pour les libellés d'affichage (jamais traduits comme clés).
METRIC_CODES = {
    "Attractivité": "attractivite",
    "Risque maîtrisé": "risque",
    "Croissance": "croissance",
    "Stabilité devise": "devise",
}

# Options du sélecteur : clés internes stockées telles quelles dans
# session_state["map_metric"] (compat) — les libellés d'affichage viennent
# de i18n via METRIC_CODES ci-dessus.
METRICS = ["Attractivité", "Risque maîtrisé", "Croissance", "Stabilité devise"]

# Bornes géographiques approximatives (lon_min, lon_max, lat_min, lat_max)
# pour recentrer la carte sur le pays sélectionné (clé interne des pays).
# Encadrements volontairement larges : pédagogiques, pas cartographiques.
COUNTRY_BOUNDS: dict[str, tuple[float, float, float, float]] = {
    "usa": (-132, -64, 23, 51),
    "china": (72, 136, 16, 55),
    "france": (-6, 10, 41, 52),
    "japan": (127, 147, 29, 47),
    "germany": (5, 16.5, 46.5, 55.5),
    "brazil": (-75, -33, -35, 7),
    "india": (66, 91, 6, 37),
    "morocco": (-14, 6, 26, 37),
    "saudi": (34, 57, 15, 33),
    "south_africa": (15.5, 33.5, -35.5, -21.5),
    "uae": (50.5, 57, 21.5, 27),
    "syria": (35, 43, 31.5, 38),
    "lebanon": (34.5, 37.5, 32.5, 35.5),
}


def reset_map_selection() -> None:
    """Efface la sélection du pays : retour à la vue monde."""
    st.session_state.pop("world_map", None)
    st.session_state.pop("map_zoom", None)


def _select_country(country_id: str) -> None:
    """Callback des boutons pays : sélection + zoom fiable côté rendu."""
    st.session_state["map_zoom"] = country_id


def _selected_country_id(event: dict[str, Any], rows: list[dict[str, Any]]) -> str | None:
    """Pays sélectionné dans l'événement Plotly (dernier point cliqué).

    Le frontend Streamlit renomme les clés camelCase en snake_case :
    ``pointIndex`` devient ``point_index``. On accepte les deux écritures.
    """
    if not event:
        return None
    selection = event.get("selection") or {}
    points = selection.get("points") or []
    for point in reversed(points):
        if not isinstance(point, dict):
            continue
        iso = point.get("location") or point.get("iso3")
        for row in rows:
            if row["country"].get("iso3") == iso:
                return row["country"]["id"]
        # Repli : position du point dans la série choropleth.
        index = point.get("point_index") or point.get("point_number")
        if isinstance(index, int):
            try:
                return rows[index]["country"]["id"]
            except (IndexError, KeyError):
                continue
    return None


def zoom_target_id(rows: list[dict[str, Any]]) -> str | None:
    """Pays actuellement zoomé : sélection native sur la carte si elle
    existe, sinon sélection via les contrôles de la page (boutons pays).
    Méthode native (clic Plotly) volontairement conservée : elle ne
    s'applique pas à un choropleth dans Streamlit 1.66, mais redeviendrait
    fonctionnelle dans une version où Streamlit retransmet ``location``."""
    native_id = _selected_country_id(st.session_state.get("world_map"), rows)  # type: ignore[arg-type]
    if native_id:
        return native_id
    chip_id = st.session_state.get("map_zoom")
    if chip_id:
        for row in rows:
            if row["country"]["id"] == chip_id:
                return chip_id
    return None


def go_to_country(country_id: str) -> None:
    st.session_state["country_id"] = country_id
    st.session_state["nav"] = "country"


def _metric_value(country: dict[str, Any], metric: str, profile: str) -> float:
    result = overall_score(country, profile)
    if metric == "Risque maîtrisé":
        return 100 - result["risk"]
    if metric == "Croissance":
        return result["components"]["dynamisme"]
    if metric == "Stabilité devise":
        return float(country.get("qualitative", {}).get("currency_stability", 50))
    return result["score"]


def _rows(profile: str) -> list[dict[str, Any]]:
    rows = []
    for country in countries():
        result = overall_score(country, profile)
        ke = required_return(country)
        rows.append(
            {
                "country": i18n.localize_country(country),
                "score": result["score"],
                "risk": result["risk"],
                "verdict": result["verdict"],
                "tone": VERDICT_STYLES[result["verdict"]]["tone"],
                "ke": ke["ke"],
                "crp": ke["crp"],
            }
        )
    return rows


def _map_figure(
    rows: list[dict[str, Any]],
    metric: str,
    profile: str,
    selected_id: str | None = None,
) -> go.Figure:
    metric_label = t(f"map.metric.{METRIC_CODES[metric]}")
    values = [_metric_value(row["country"], metric, profile) for row in rows]
    custom = [
        [
            row["country"]["name"],
            f"{row['score']:.0f}",
            f"{row['ke']:.1f} %",
            f"{row['risk']:.0f}",
            t(f"verdict.{i18n.verdict_key(row['verdict'])}"),
        ]
        for row in rows
    ]
    line_colors = ["#e6b86b" if row["country"]["id"] == selected_id else "#0b1220" for row in rows]
    line_widths = [1.8 if row["country"]["id"] == selected_id else 0.9 for row in rows]
    fig = go.Figure(
        go.Choropleth(
            locations=[row["country"]["iso3"] for row in rows],
            z=values,
            customdata=custom,
            locationmode="ISO-3",
            colorscale=[
                [0.0, "#6b1f2a"],
                [0.28, "#9a3412"],
                [0.47, "#b45309"],
                [0.62, "#a3a30d"],
                [0.78, "#4d9b3a"],
                [1.0, "#22c55e"],
            ],
            zmin=0,
            zmax=100,
            marker_line_color=line_colors,
            marker_line_width=line_widths,
            colorbar=dict(
                title=dict(text=metric_label, font=dict(color="#9aa8bd", size=11)),
                thickness=9,
                len=0.62,
                x=1.01,
                tickfont=dict(color="#7f8fa5", size=9),
                outlinewidth=0,
                bgcolor="rgba(0,0,0,0)",
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                + f"{metric_label} : %{{z:.0f}}/100<br>"
                + f"{t('map.hover.score')} %{{customdata[1]}}/100<br>"
                + f"{t('map.hover.ke')} %{{customdata[2]}}<br>"
                + f"{t('map.hover.risk')} %{{customdata[3]}}/100<br>"
                + f"{t('map.hover.verdict')} %{{customdata[4]}}<extra></extra>"
            ),
        )
    )
    fig.update_geos(
        projection_type="natural earth",
        showframe=False,
        showcoastlines=False,
        showland=True,
        landcolor="#151d2d",
        showocean=True,
        oceancolor="#080e19",
        showcountries=True,
        countrycolor="#2b3548",
        bgcolor="rgba(0,0,0,0)",
        lataxis_range=[-58, 85],
        domain=dict(x=[0.0, 0.94], y=[0.0, 1.0]),
    )
    # Zoom sur le pays sélectionné : recentrage géographique réel (bornes
    # lon/lat + rotation de projection). Pays sans encadrement connu
    # (aucun aujourd'hui) → la vue monde est conservée, sans erreur.
    selected_row = next((r for r in rows if r["country"]["id"] == selected_id), None)
    if selected_row:
        bounds = COUNTRY_BOUNDS.get(selected_row["country"]["id"])
        if bounds:
            lon_min, lon_max, lat_min, lat_max = bounds
            center_lon = (lon_min + lon_max) / 2
            fig.update_geos(
                lonaxis_range=[lon_min, lon_max],
                lataxis_range=[lat_min, lat_max],
                projection_rotation_lon=center_lon,
                projection_rotation_lat=0,
            )
    fig.update_layout(
        height=540,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#cbd5e1"),
        hoverlabel=dict(
            bgcolor="#0e1626",
            bordercolor="#334155",
            font=dict(color="#e9eef7", family="Manrope, sans-serif"),
        ),
        dragmode=False,
    )
    return fig


def _risk_return_figure(rows: list[dict[str, Any]]) -> go.Figure:
    group_colors = {
        "Développé": "#7dd3fc",
        "Émergent": "#e6b86b",
        "Golfe": "#a3e635",
        "Frontière": "#fb7185",
    }
    fig = go.Figure()
    for group, color in group_colors.items():
        # Le filtre passe par le code de groupe (FR et EN mappent au même
        # code) : fonctionne avec des pays localisés ou non.
        subset = [r for r in rows if i18n.group_key(r["country"]["group"]) == i18n.group_key(group)]
        if not subset:
            continue
        group_label = t(f"group.{i18n.group_key(group)}")
        fig.add_trace(
            go.Scatter(
                x=[r["risk"] for r in subset],
                y=[r["ke"] for r in subset],
                mode="markers+text",
                name=group_label,
                text=[r["country"]["name"] for r in subset],
                textposition="top center",
                textfont=dict(size=9, color="#aebaca"),
                marker=dict(
                    size=[max(10, r["score"] * 0.38) for r in subset],
                    color=color,
                    opacity=0.82,
                    line=dict(width=1, color="#0b1220"),
                ),
                customdata=[
                    [r["country"]["flag"], r["score"], t(f"verdict.{i18n.verdict_key(r['verdict'])}")]
                    for r in subset
                ],
                hovertemplate=(
                    "%{customdata[0]} <b>%{text}</b><br>"
                    + f"{t('map.hover.risk')} %{{x:.0f}}/100<br>"
                    + f"{t('map.hover.ke')} %{{y:.1f}} %<br>"
                    + f"{t('map.hover.score_short')} %{{customdata[1]:.0f}}/100<br>"
                    + "%{customdata[2]}<extra></extra>"
                ),
            )
        )
    fig.add_vline(x=50, line_dash="dot", line_color="rgba(148,163,184,.25)")
    fig.add_hline(y=12, line_dash="dot", line_color="rgba(148,163,184,.25)")
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#94a3b8"),
        xaxis=dict(
            title=t("map.riskret.xaxis"),
            range=[0, 100],
            gridcolor="rgba(148,163,184,.09)",
            zeroline=False,
        ),
        yaxis=dict(
            title=t("map.riskret.yaxis"),
            gridcolor="rgba(148,163,184,.09)",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            y=-0.18,
            x=0,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(bgcolor="#0e1626", bordercolor="#334155"),
    )
    return fig


def render() -> None:
    profile = st.session_state.get("profile", "Équilibré")
    rows = _rows(profile)
    ranked = sorted(rows, key=lambda r: r["score"], reverse=True)
    positive = sum(1 for row in rows if row["verdict"] in {"Investir", "Investir avec prudence"})

    # Sélection courante : événement natif de la carte (on_select="rerun")
    # ou choix explicite via les contrôles de la page, lu AVANT de
    # construire la figure afin que le zoom s'applique dès ce run.
    selected_id = zoom_target_id(rows)

    ui.hero(
        t("map.hero.title"),
        t("map.hero.subtitle"),
        t("map.hero.text"),
        [t("map.hero.chip1"), t("map.hero.chip2"), t("map.hero.chip3")],
    )

    top_cols = st.columns(4)
    with top_cols[0]:
        ui.kpi("10", t("map.kpi.countries"), t("map.kpi.countries_desc"))
    with top_cols[1]:
        ui.kpi(f"{ranked[0]['score']:.0f}<small>/100</small>", t("map.kpi.best"), f"{ranked[0]['country']['flag']} {ranked[0]['country']['name']}")
    with top_cols[2]:
        median_ke = sorted(row["ke"] for row in rows)[len(rows) // 2]
        ui.kpi(f"{median_ke:.1f}<small> %</small>", t("map.kpi.median"), t("map.kpi.median_desc"))
    with top_cols[3]:
        ui.kpi(f"{positive}<small>/10</small>", t("map.kpi.positive"), t("map.kpi.positive_desc"))

    st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

    control_a, control_b, control_c = st.columns([1.5, 1.25, 1.25])
    with control_a:
        profile = st.radio(
            t("map.profile.radio"),
            list(PROFILES.keys()),
            horizontal=True,
            key="profile",
            format_func=i18n.profile_label,
            help=t("map.profile.help"),
        )
    with control_b:
        metric = st.selectbox(
            t("map.metric.radio_label"),
            METRICS,
            key="map_metric",
            format_func=lambda m: t(f"map.metric.{METRIC_CODES[m]}"),
        )
    profile_pct = f"{PROFILES[profile]['weights']['dynamisme'] * 100:.0f}"
    with control_c:
        st.markdown(
            f'<div class="gc-chip gold" style="margin-top:1.85rem">{t("map.chip_profile", profile=i18n.profile_label(profile), pct=profile_pct)}</div>',
            unsafe_allow_html=True,
        )

    map_col, side_col = st.columns([2.25, 1], gap="large")
    with map_col:
        st.markdown(
            f'<div class="gc-section-title"><h3>{t("map.section.world")}</h3><span>{ui.esc(t(f"map.metric_desc.{METRIC_CODES[metric]}"))}</span></div>',
            unsafe_allow_html=True,
        )
        st.caption(t("map.zoom.hint"))
        zoom_row_a, zoom_row_b = st.columns(5), st.columns(5)
        for index, row in enumerate(rows):
            with (zoom_row_a if index < 5 else zoom_row_b)[index % 5]:
                st.button(
                    f"{row['country']['flag']} {ui.esc(row['country']['name'])} · {row['score']:.0f}",
                    key=f"map_zoom_{row['country']['id']}",
                    width="stretch",
                    type="primary" if row["country"]["id"] == selected_id else "secondary",
                    on_click=_select_country,
                    args=(row["country"]["id"],),
                )
        fig = _map_figure(rows, metric, profile, selected_id=selected_id)
        st.plotly_chart(
            fig,
            width="stretch",
            key="world_map",
            on_select="rerun",
            selection_mode=("points",),
            config={"displayModeBar": False},
        )
        st.caption(t("map.caption.mvp"))

        if selected_id:
            selected_row = next(r for r in rows if r["country"]["id"] == selected_id)
            c = selected_row["country"]
            st.markdown(
                f"""
                <div class="gc-card gc-card-gold" style="margin-top:10px">
                  <div class="gc-eyebrow">{t("map.selected.eyebrow")}</div>
                  <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">
                    <h4 style="font-size:1.05rem">{c['flag']} {ui.esc(c['name'])}</h4>
                    <strong style="color:var(--gold);font-size:1.25rem">{selected_row['score']:.0f}</strong>
                  </div>
                  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">
                    <span class="gc-chip">{t("map.card.score", value=f"{selected_row['score']:.0f}")}</span>
                    <span class="gc-chip">{t("map.card.ke", value=f"{selected_row['ke']:.1f}")}</span>
                    <span class="gc-chip">{t("map.card.risk", value=f"{selected_row['risk']:.0f}")}</span>
                    <span class="gc-chip">{ui.esc(t(f"verdict.{i18n.verdict_key(selected_row['verdict'])}"))}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            card_cols = st.columns(2)
            with card_cols[0]:
                st.button(
                    t("pr.btn.open"),
                    key=f"map_selected_open_{selected_id}",
                    width="stretch",
                    on_click=go_to_country,
                    args=(selected_id,),
                )
            with card_cols[1]:
                st.button(
                    t("map.btn.reset"),
                    key="map_reset_selection",
                    width="stretch",
                    on_click=reset_map_selection,
                )

    with side_col:
        pkey = i18n.profile_key(profile)
        pweights = PROFILES[profile]["weights"]
        st.markdown(
            f"""
            <div class="gc-card gc-card-gold">
              <div class="gc-eyebrow">{t("map.card.eyebrow")}</div>
              <h4>{ui.esc(t(f"profile.{pkey}"))}</h4>
              <p>{ui.esc(t(f"profile_desc.{pkey}"))}</p>
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:12px">
                <span class="gc-chip">{t("map.chip.growth", pct=f"{pweights['dynamisme']*100:.0f}")}</span>
                <span class="gc-chip">{t("map.chip.stability", pct=f"{pweights['stabilite']*100:.0f}")}</span>
                <span class="gc-chip">{t("map.chip.solvency", pct=f"{pweights['solvabilite']*100:.0f}")}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ui.section_title(t("map.section.top"), t("map.section.top_sub"))
        for row in ranked[:3]:
            c = row["country"]
            st.markdown(
                f"""
                <div class="gc-card" style="padding:14px;margin-bottom:8px">
                  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
                    <div><span style="font-size:1.4rem">{c['flag']}</span>
                    <strong style="color:#f1f5fb;font-size:.88rem;margin-left:6px">{ui.esc(c['name'])}</strong></div>
                    <strong style="color:var(--gold);font-size:1.2rem">{row['score']:.0f}</strong>
                  </div>
                  <div class="gc-small" style="margin-top:5px">{ui.esc(t(f"verdict.{i18n.verdict_key(row['verdict'])}"))} · Ke {row['ke']:.1f} %</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="gc-small" style="margin-top:10px">{t("map.note.score")}</div>',
            unsafe_allow_html=True,
        )

    ui.section_title(t("map.section.explore"), t("map.section.explore_sub"))
    quick = st.columns(5)
    for index, row in enumerate(rows):
        with quick[index % 5]:
            st.button(
                f"{row['country']['flag']} {ui.esc(row['country']['name'])} · {row['score']:.0f}",
                key=f"map_open_{row['country']['id']}",
                width="stretch",
                on_click=go_to_country,
                args=(row["country"]["id"],),
            )

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    with st.expander(t("map.expander.risk_return"), expanded=False):
        st.markdown(
            f'<div class="gc-small" style="margin-bottom:8px">{t("map.riskret.hint")}</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_risk_return_figure(rows), width="stretch", config={"displayModeBar": False})

    ui.callout(
        t("map.callout.ke"),
        "blue",
    )

    if ai.is_available():
        st.caption(t("map.ai.caption"))
    ui.footer()
