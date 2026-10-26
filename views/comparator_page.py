"""Module comparateur — lire deux ou trois pays côte à côte."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from geocapital import freshness, i18n, ui
from geocapital.i18n import t
from geocapital.data import (
    INDICATOR_LABELS,
    comparison_frame,
    countries,
    country_by_id,
    indicator_summary,
)
from geocapital.scoring import (
    COMPONENT_LABELS,
    PROFILES,
    VERDICT_STYLES,
    component_scores,
    indicator_status,
    overall_score,
    required_return,
)

COLORS = ["#e6b86b", "#7dd3fc", "#a3e635"]


def _go_country(country_id: str) -> None:
    st.session_state["country_id"] = country_id
    st.session_state["nav"] = "country"


def _set_comparison(pair: tuple[str, str]) -> None:
    st.session_state["compare_ids"] = [pair[0], pair[1]]


def _radar(selected: list[dict], profile: str) -> go.Figure:
    fig = go.Figure()
    categories = [t(f"component.{key}") for key in COMPONENT_LABELS]
    for index, country in enumerate(selected):
        scores = component_scores(country)
        values = [scores[key] for key in COMPONENT_LABELS]
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor=f"rgba({_hex_to_rgb(COLORS[index])},0.10)",
                line=dict(color=COLORS[index], width=2),
                name=f"{country['flag']} {country['name']}",
                hovertemplate="%{theta}<br>%{r:.0f}/100<extra></extra>",
            )
        )
    fig.update_layout(
        height=420,
        margin=dict(l=45, r=45, t=35, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#94a3b8"),
        polar=dict(
            bgcolor="rgba(255,255,255,0.018)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showline=False,
                gridcolor="rgba(148,163,184,.14)",
                tickfont=dict(size=8, color="#64748b"),
                angle=90,
                tickangle=90,
            ),
            angularaxis=dict(
                gridcolor="rgba(148,163,184,.14)",
                linecolor="rgba(148,163,184,.18)",
                tickfont=dict(size=10, color="#aab7c9"),
            ),
        ),
        legend=dict(orientation="h", y=-0.08, x=0, font=dict(size=10)),
        showlegend=True,
    )
    return fig


def _hex_to_rgb(color: str) -> str:
    color = color.lstrip("#")
    return f"{int(color[0:2], 16)},{int(color[2:4], 16)},{int(color[4:6], 16)}"


def _ke_chart(selected: list[dict], profile: str) -> go.Figure:
    rows = []
    for country in selected:
        result = overall_score(country, profile)
        ke = required_return(country)
        rows.append((f"{country['flag']} {country['name']}", ke["ke"], result["score"]))
    rows.sort(key=lambda item: item[1])
    colors = ["#4ade80" if score >= 76 else "#a3e635" if score >= 62 else "#fbbf24" if score >= 45 else "#fb7185" for _, _, score in rows]
    fig = go.Figure(
        go.Bar(
            x=[row[1] for row in rows],
            y=[row[0] for row in rows],
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{row[1]:.1f} %" for row in rows],
            textposition="outside",
            textfont=dict(color="#cbd5e1", size=11),
            hovertemplate=f"<b>%{{y}}</b><br>{t('map.hover.ke')} %{{x:.1f}} %<extra></extra>",
        )
    )
    fig.update_layout(
        height=310,
        margin=dict(l=10, r=35, t=15, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#94a3b8"),
        xaxis=dict(title="Ke (%)", gridcolor="rgba(148,163,184,.09)", range=[0, max(row[1] for row in rows) * 1.25]),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    return fig


def _table(selected: list[dict]) -> None:
    header = "".join(f"<th>{country['flag']} {ui.esc(country['name'])}</th>" for country in selected)
    rows_html = []
    for key in [
        "gdp_growth", "inflation", "debt_gdp", "policy_rate", "unemployment", "reserves",
        "rating", "cds", "crp", "equity_index", "currency",
    ]:
        cells = []
        for country in selected:
            status = indicator_status(country, key)
            cells.append(
                f'<td><span class="gc-dot {status}"></span>{ui.esc(indicator_summary(country, key))}</td>'
            )
        rows_html.append(f"<tr><td class='gc-table-label'>{ui.esc(i18n.indicator_label(key))}</td>{''.join(cells)}</tr>")
    st.markdown(
        f'<div style="overflow-x:auto"><table class="gc-table"><thead><tr><th>{t("comp.table.indicator")}</th>{header}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    profile = st.session_state.get("profile", "Équilibré")
    ui.page_head(
        t("comp.eyebrow"),
        t("comp.title"),
        t("comp.subtitle"),
    )

    preset_cols = st.columns(5)
    presets = [
        (t("comp.preset.usa_china"), ("usa", "china")),
        (t("comp.preset.saudi_uae"), ("saudi", "uae")),
        (t("comp.preset.lebanon_syria"), ("lebanon", "syria")),
        (t("comp.preset.france_japan"), ("france", "japan")),
        (t("comp.preset.morocco_sa"), ("morocco", "south_africa")),
    ]
    for col, (label, pair) in zip(preset_cols, presets):
        with col:
            st.button(label, key=f"preset_{pair[0]}_{pair[1]}", width="stretch", on_click=_set_comparison, args=(pair,))

    control_a, control_b = st.columns([2.2, 1])
    with control_a:
        selected_ids = st.multiselect(
            t("comp.select"),
            [c["id"] for c in countries()],
            format_func=lambda cid: f"{country_by_id(cid)['flag']} {i18n.country_name(cid)}",
            max_selections=3,
            key="compare_ids",
            help=t("comp.select_help"),
        )
    with control_b:
        profile = st.radio(t("comp.profile_radio"), list(PROFILES.keys()), horizontal=True, key="profile", format_func=i18n.profile_label)

    # Copie traduite à l'affichage (EN) ; les calculs (scoring, Ke,
    # comparaison) donnent des valeurs identiques, seuls les libellés changent.
    selected = [country_by_id(cid) for cid in selected_ids if country_by_id(cid)]
    # Copie traduite à l'affichage (EN) ; les calculs (scoring, Ke,
    # comparaison) donnent des valeurs identiques, seuls les libellés changent.
    selected = [i18n.localize_country(c) for c in selected if c]
    if len(selected) < 2:
        ui.callout(t("comp.min_two"), "blue")
        return

    cards = st.columns(len(selected))
    for index, country in enumerate(selected):
        result = overall_score(country, profile)
        ke = required_return(country)
        tone = VERDICT_STYLES[result["verdict"]]["tone"]
        with cards[index]:
            st.markdown(
                f"""
                <div class="gc-card" style="min-height:280px">
                  <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:1.8rem">{country['flag']}</span>
                    <div><div style="color:#f1f5fb;font-weight:750;font-size:.94rem">{ui.esc(country['name'])}</div>
                    <div style="color:#7f8fa5;font-size:.68rem">{ui.esc(t(f"group.{i18n.group_key(country['group'])}"))}</div></div>
                  </div>
                  <div style="display:flex;align-items:center;gap:14px;margin-top:16px">
                    {ui.ring(result['score'], t('comp.ring_label'))}
                    <div>
                      {ui.verdict_badge(t(f"verdict.{i18n.verdict_key(result['verdict'])}"), tone)}
                      <div style="color:#e6b86b;font-size:1.45rem;font-weight:800;margin-top:10px;letter-spacing:-.04em">{ke['ke']:.1f} %</div>
                      <div class="gc-small">{t("comp.card_ke_risk", value=f"{result['risk']:.0f}")}</div>
                    </div>
                  </div>
                  <div class="gc-small" style="margin-top:12px">{ui.esc(t(f"verdict.copy.{i18n.verdict_key(result['verdict'])}"))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    chart_left, chart_right = st.columns([1.2, 1], gap="large")
    with chart_left:
        ui.section_title(t("comp.section.radar"), t("comp.section.radar_sub"))
        st.plotly_chart(_radar(selected, profile), width="stretch", config={"displayModeBar": False})
    with chart_right:
        ui.section_title(t("comp.section.ke"), t("comp.section.ke_sub"))
        st.plotly_chart(_ke_chart(selected, profile), width="stretch", config={"displayModeBar": False})
        st.markdown(
            f'<div class="gc-small">{t("comp.ke_note")}</div>',
            unsafe_allow_html=True,
        )

    ui.section_title(t("comp.section.table"), t("comp.section.table_sub"))
    # Millésime global : les cellules résument des observations datées
    # individuellement (voir les fiches pays pour le détail par indicateur).
    st.caption(t("fresh.as_of", as_of=freshness.as_of()))
    _table(selected)

    ui.section_title(t("comp.section.reading"), t("comp.section.reading_sub"))
    best = max(selected, key=lambda c: overall_score(c, profile)["score"])
    safest = min(selected, key=lambda c: overall_score(c, profile)["risk"])
    cheapest = min(selected, key=lambda c: required_return(c)["ke"])
    most_expensive = max(selected, key=lambda c: required_return(c)["ke"])
    st.markdown(
        f"""
        <div class="gc-card gc-card-gold">
          <p style="font-size:.87rem;line-height:1.75">
            {t("comp.reading", profile=ui.esc(i18n.profile_label(profile)), best=ui.esc(best['name']), best_score=f"{overall_score(best, profile)['score']:.0f}", safest=ui.esc(safest['name']), safest_risk=f"{overall_score(safest, profile)['risk']:.0f}", ke_min=f"{required_return(cheapest)['ke']:.1f} %", cheapest=ui.esc(cheapest['name']), ke_max=f"{required_return(most_expensive)['ke']:.1f} %", most_expensive=ui.esc(most_expensive['name']))}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Une colonne par bouton (CSV + chaque pays) ; l'écarteur limite l'étirement.
    download_cols = st.columns([1, 1, 1, 3])
    with download_cols[0]:
        frame = comparison_frame(selected)
        # Étiquettes affichées traduites (lignes), en-tête FR du frame
        # traduite par colonne ; les valeurs chiffrées restent inchangées.
        indicator_col = t("comp.csv.indicator")
        frame = frame.rename(columns={"Indicateur": indicator_col})
        frame[indicator_col] = frame[indicator_col].map(i18n.display_label)
        csv = frame.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            t("comp.export_csv"),
            data=csv,
            file_name="geocapital_comparaison.csv",
            mime="text/csv",
            width="stretch",
        )
    for index, country in enumerate(selected):
        with download_cols[index + 1]:
            st.button(
                t("comp.open_sheet", flag=country['flag']),
                key=f"compare_open_{country['id']}",
                width="stretch",
                on_click=_go_country,
                args=(country["id"],),
            )

    ui.callout(
        t("comp.callout.ke"),
        "blue",
    )
    ui.footer()
