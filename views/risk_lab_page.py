"""Sovereign Risk Lab — vue d'analyse souveraine approfondie (Priorité 8).

Conventions :
- réutilise le moteur existant (scoring.model pour les paliers), la
  couche fraîcheur (freshness.py) et les statuts de l'audit qualité
  (via geocapital.risk_lab) — aucun calcul dupliqué ;
- une donnée indisponible est affichée comme indisponible (pourquoi
  cela compte, source requise) — jamais remplacée par zéro ;
- les calculs du lab n'influencent ni le score ni le verdict ;
- libellés via geocapital.i18n.t() (FR par défaut, EN disponible).
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from geocapital import data, freshness, i18n, risk_lab, ui
from geocapital.data import countries, country_by_id
from geocapital.i18n import t
from geocapital.scoring import model

# Couleurs des paliers de taux réel (cohérentes avec les feux du modèle).
_BAND_COLORS = {"good": "rgba(74,222,128,0.28)", "mid": "rgba(251,191,36,0.25)", "poor": "rgba(251,113,133,0.25)"}
_METRIC_CHOICES = ("debt_gdp", "real_rate", "reserves")


def _metric_label(key: str) -> str:
    if key in data.INDICATOR_LABELS:
        return i18n.indicator_label(key)
    return t(f"rl.metric.{key}")


def _fmt(value: object, decimals: int = 1) -> str:
    if value is None:
        return "n.d."
    return data.format_number(value, decimals)


def _country_selector() -> dict | None:
    ids = [c["id"] for c in countries()]
    default = st.session_state.get("country_id", "usa")
    if default not in ids:
        default = ids[0]
    selected = st.selectbox(
        t("rl.select"),
        ids,
        index=ids.index(default),
        format_func=lambda cid: f"{country_by_id(cid)['flag']} {i18n.country_name(cid)}",
        key="risk_lab_country",
    )
    st.session_state["country_id"] = selected
    return country_by_id(selected)


def _status_chip(metric: dict) -> tuple[str, str]:
    """Chip de statut DONNÉE (jamais la fraîcheur seule).

    - sources divergentes → rouge ;
    - estimation déclarée par la source → orange « Estimation » (jamais
      présentée comme confirmée) ;
    - sinon → statut neutre « observation sourcée » (ou « calculé » pour
      la métrique dérivée).
    """
    warnings = metric.get("warnings", [])
    if "conflicting" in warnings:
        return "red", t("rl.chip.conflicting")
    if "estimated" in warnings:
        return "orange", t("rl.chip.estimated")
    if metric.get("kind") == "derived":
        return "green", t("rl.badge.derived")
    return "green", t("rl.badge.observed")


def _display_fields(country_loc: dict, metric: dict) -> tuple[str, str]:
    """(note, source) affichés : overlay de langue quand il existe (fiche
    localisée), sinon les champs bruts. Les statuts, eux, restent calculés
    sur la fiche source (build_metrics) — présentation uniquement."""
    block = country_loc.get("indicators", {}).get(metric["key"]) or {}
    note = block.get("note") or metric.get("note") or ""
    source = block.get("source") or metric.get("source") or t("dash.source_missing")
    return note, source


def _metric_card(country_loc: dict, metric: dict) -> None:
    """Carte d'une métrique disponible : valeur, unité, période discrète,
    commentaire analytique d'origine — sans message de maintenance."""
    label = _metric_label(metric["key"])
    status, chip = _status_chip(metric)
    note, source = _display_fields(country_loc, metric)
    decimals = 1 if isinstance(metric["value"], float) and not float(metric["value"]).is_integer() else 0
    ui.indicator_card(
        label,
        _fmt(metric["value"], decimals),
        metric["unit"] or "",
        status,
        note,
        source,
        (str(metric["obs_period"]) if metric["obs_period"] else "—"),
        status_label=chip,
    )
    st.markdown("<div style='height:9px'></div>", unsafe_allow_html=True)


def _missing_section(metrics: list[dict]) -> None:
    """Les indicateurs non couverts, regroupés en UNE section expliquée.

    Tableau compact (indicateur · pourquoi · source requise) : les absences
    restent explicites sans noier les données utiles.
    """
    unavailable = [m for m in metrics if not m["available"]]
    if not unavailable:
        return
    ui.section_title(t("rl.missing.title"), t("rl.missing.sub"))
    st.markdown(t("rl.missing.count", count=len(unavailable)))
    rows = []
    for metric in unavailable:
        key = metric["key"]
        rows.append(
            f"<tr><td class='gc-table-label'>{ui.esc(_metric_label(key))}"
            f"<br><span style='color:#7f8fa5;font-weight:400'>{ui.esc(metric['unit'] or '')}</span></td>"
            f"<td>{ui.esc(t(f'rl.why.{key}'))}</td>"
            f"<td>{ui.esc(t(f'rl.need.{key}'))}</td></tr>"
        )
    st.markdown(
        f'<div style="overflow-x:auto"><table class="gc-table"><thead><tr>'
        f'<th>{t("comp.table.indicator")}</th><th>{t("rl.missing.th.why")}</th><th>{t("rl.missing.th.source")}</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _data_details_expander(country_loc: dict, metrics: list[dict]) -> None:
    """« Détails des données » : provenance et statuts de validation,
    indicateur par indicateur — chaque ligne décrit l'observation réelle
    de la fiche (période, source, statut calculé par l'audit)."""
    available = [m for m in metrics if m["available"]]
    with st.expander(t("rl.details.title")):
        st.caption(t("rl.details.sub"))
        rows = []
        for m in available:
            period = str(m["obs_period"]) if m["obs_period"] else "—"
            _note, source = _display_fields(country_loc, m)
            audit = m.get("audit_status")
            if m.get("kind") == "derived":
                phrase = t("rl.badge.derived")
            elif audit == "estimated":
                phrase = t("rl.q.estimated")
            elif audit == "conflicting":
                phrase = t("rl.q.conflicting")
            elif audit == "stale":
                phrase = t("rl.q.stale", limit=freshness.stale_threshold())
            elif audit == "verified":
                phrase = t("rl.badge.observed")
            else:
                phrase = t("rl.q.unverified")
            rows.append(
                f"<tr><td class='gc-table-label'>{ui.esc(_metric_label(m['key']))}</td>"
                f"<td>{ui.esc(period)}</td><td>{ui.esc(source)}</td><td>{ui.esc(phrase)}</td></tr>"
            )
        st.markdown(
            f'<div style="overflow-x:auto"><table class="gc-table"><thead><tr>'
            f'<th>{t("comp.table.indicator")}</th><th>{t("rl.details.period")}</th>'
            f'<th>{t("rl.details.source")}</th><th>{t("rl.details.status")}</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>',
            unsafe_allow_html=True,
        )
        st.caption(t("rl.details.as_of", as_of=freshness.as_of()))


def _real_rate_chart(detail: dict) -> go.Figure:
    """Position du taux réel dans les paliers existants du moteur."""
    fig = go.Figure()
    for low, high, score in detail["bands"]:
        color = _BAND_COLORS["good"] if score >= 72 else _BAND_COLORS["mid"] if score >= 40 else _BAND_COLORS["poor"]
        fig.add_shape(type="rect", x0=low, x1=high, y0=0, y1=1, fillcolor=color, line=dict(width=0))
        fig.add_annotation(
            x=(low + high) / 2,
            y=0.12,
            text=f"{t('rl.real.band_label')} {score:.0f}",
            showarrow=False,
            font=dict(size=9, color="#64748b"),
        )
    fig.add_vline(
        x=detail["real_rate"],
        line=dict(color="#e6b86b", width=3),
        annotation_text=f"{detail['real_rate']:.1f} %",
        annotation_position="top",
        annotation_font=dict(color="#e6b86b", size=13),
    )
    fig.update_layout(
        height=170,
        margin=dict(l=10, r=10, t=28, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#94a3b8"),
        xaxis=dict(title=t("rl.real.xaxis"), gridcolor="rgba(148,163,184,.09)", zerolinecolor="rgba(148,163,184,.2)"),
        yaxis=dict(visible=False, range=[0, 1]),
    )
    return fig


def _real_rate_panel(country: dict) -> None:
    detail = risk_lab.real_rate_detail(country)
    ui.section_title(t("rl.real.title"), t("rl.real.sub"))
    if not detail["available"]:
        ui.callout(t("rl.real.unavailable"), "red")
        return
    cols = st.columns(4)
    with cols[0]:
        ui.kpi(f"{detail['policy_rate']:.1f} %", t("rl.real.kpi.policy"), note=str(detail["policy_period"] or "—"))
    with cols[1]:
        ui.kpi(f"{detail['inflation']:.1f} %", t("rl.real.kpi.inflation"), note=str(detail["inflation_period"] or "—"))
    with cols[2]:
        ui.kpi(f"{detail['real_rate']:.1f} %", t("rl.real.kpi.real"))
    with cols[3]:
        band_text = f"{detail['band'][2]:.0f}/100" if detail["band"] else t("rl.real.outside_label")
        ui.kpi(band_text, t("rl.real.kpi.bandscore"))

    if detail["vintage_mismatch"]:
        ui.callout(
            t("rl.warn.vintage_mismatch", policy_period=str(detail["policy_period"]), inflation_period=str(detail["inflation_period"])),
            "red",
        )
    else:
        year = detail.get("policy_year")
        st.caption(t("rl.real.aligned", year=str(year) if year else "—"))
    st.plotly_chart(_real_rate_chart(detail), width="stretch", config={"displayModeBar": False})


def _debt_panel(country: dict) -> None:
    d = risk_lab.debt_sustainability(country)
    ui.section_title(t("rl.dsa.title"), t("rl.dsa.sub"))
    if d["debt_gdp"] is None:
        ui.callout(t("rl.dsa.limitation", count=len(d["missing_inputs"])), "red")
        return
    position = t(
        f"rl.dsa.position.{d['position']}",
        low=data.format_number(d["band"][0], 0),
        high=data.format_number(d["band"][1], 0),
    )
    line = t(
        "rl.summary.debt",
        value=data.format_number(d["debt_gdp"], 0),
        period=str(d["obs_period"] or "—"),
        position=position,
    )
    st.markdown(f"**{line}**")
    st.caption(
        t(
            "rl.dsa.band_note",
            low=data.format_number(d["band"][0], 0),
            high=data.format_number(d["band"][1], 0),
        )
    )
    if d["growth"] is not None:
        st.caption(t("rl.dsa.growth_line", growth=data.format_number(d["growth"], 1), period=str(d["obs_period"] or "—")))
    if not d["dsa_complete"]:
        # Une seule limite explicite ; le détail des entrées manquantes
        # (pourquoi + source requise) vit dans la section « Indicateurs
        # non disponibles » affichée plus haut — pas de duplication.
        ui.callout(t("rl.dsa.limitation", count=len(d["missing_inputs"])), "red")


def _comparison_panel() -> None:
    ui.section_title(t("rl.comp.section"), t("rl.comp.section_sub"))
    all_ids = [c["id"] for c in countries()]
    default_ids = [cid for cid in ["usa", "lebanon"] if cid in all_ids]
    selected_ids = st.multiselect(
        t("rl.comp.select"),
        all_ids,
        default=default_ids,
        max_selections=4,
        format_func=lambda cid: f"{country_by_id(cid)['flag']} {i18n.country_name(cid)}",
        key="risk_lab_compare",
        help=t("rl.comp.select_help"),
    )
    selected = [i18n.localize_country(country_by_id(cid)) for cid in selected_ids if country_by_id(cid)]
    if len(selected) < 2:
        ui.callout(t("rl.comp.min_two"), "blue")
        return

    matrix = risk_lab.comparison_matrix(selected)
    header = "".join(f"<th>{c['flag']} {ui.esc(c['name'])}</th>" for c in matrix["columns"])
    rows_html = []
    for row in matrix["rows"]:
        label = _metric_label(row["key"])
        cells = []
        for column in matrix["columns"]:
            cell = row["cells"][column["id"]]
            if not cell["available"]:
                cells.append("<td>n.d.</td>")
                continue
            value = cell["value"]
            decimals = 1 if isinstance(value, float) and not float(value).is_integer() else 0
            # marqueurs discrets, réservés aux statuts qui changent la
            # lecture (estimation, divergence, millésimes) — pas la fraîcheur
            marks = ""
            if "estimated" in cell["warnings"]:
                marks += "<sup>e</sup>"
            if "conflicting" in cell["warnings"]:
                marks += "<sup>d</sup>"
            if "vintage_mismatch" in cell["warnings"]:
                marks += "<sup>m</sup>"
            cells.append(f"<td>{ui.esc(_fmt(value, decimals))} {ui.esc(cell['unit'] or '')}{marks}</td>")
        rows_html.append(f"<tr><td class='gc-table-label'>{ui.esc(label)}</td>{''.join(cells)}</tr>")
    st.markdown(
        f'<div style="overflow-x:auto"><table class="gc-table"><thead><tr><th>{t("comp.table.indicator")}</th>{header}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )
    st.caption(t("rl.comp.legend"))

    metric_choice = st.radio(
        t("rl.comp.chart_metric"),
        _METRIC_CHOICES,
        format_func=_metric_label,
        horizontal=True,
        key="risk_lab_chart_metric",
    )
    _comparison_chart(selected, matrix, metric_choice)


def _comparison_chart(selected: list[dict], matrix: dict, metric_key: str) -> None:
    xs, ys, colors = [], [], []
    for country in selected:
        cell = next(row for row in matrix["rows"] if row["key"] == metric_key)["cells"][country["id"]]
        if not cell["available"]:
            continue
        xs.append(f"{country['flag']} {country['name']}")
        ys.append(float(cell["value"]))
        colors.append("#fb7185" if "conflicting" in cell["warnings"] else "#fbbf24" if cell["warnings"] else "#e6b86b")
    if not xs:
        st.caption(t("rl.comp.no_data"))
        return
    fig = go.Figure(
        go.Bar(
            x=xs,
            y=ys,
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:.1f}" for v in ys],
            textposition="outside",
            textfont=dict(color="#cbd5e1", size=11),
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=25, t=15, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#94a3b8"),
        yaxis=dict(title=_metric_label(metric_key), gridcolor="rgba(148,163,184,.09)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _method_expander() -> None:
    bands = model()["components"]["stabilite"]["real_rate_bands"]
    low, high = model()["components"]["solvabilite"]["ranges"]["debt_range"]
    outside = model()["components"]["stabilite"]["real_rate_outside_score"]
    with st.expander(t("rl.method.title")):
        st.markdown(
            f"""
            - {t("rl.method.real_rate")}
            - {t("rl.method.bands", bands=str([[b[0], b[1], b[2]] for b in bands]), outside=f"{outside:g}")}
            - {t("rl.method.debt", low=data.format_number(low, 0), high=data.format_number(high, 0))}
            - {t("rl.method.reserves")}
            - {t("rl.method.caveat", limit=freshness.stale_threshold(), as_of=freshness.as_of())}
            - {t("rl.method.assumption")}
            """,
        )


def render() -> None:
    ui.page_head(t("rl.eyebrow"), t("rl.title"), t("rl.subtitle"))
    country = _country_selector()
    if country is None:
        return
    country_loc = i18n.localize_country(country)

    metrics = risk_lab.build_metrics(country)

    # Indicateurs DISPONIBLES d'abord : cartes en avant, section par section.
    for section in ("fiscal", "external", "macro"):
        ui.section_title(t(f"rl.section.{section}"), t(f"rl.section.{section}_sub"))
        # real_rate a son panneau dédié (paliers du modèle) : pas de carte
        # redondante dans la grille macro.
        available = [
            m
            for m in metrics
            if m["section"] == section and m["available"] and m["key"] != "real_rate"
        ]
        if not available:
            st.caption(t("rl.missing.section_empty"))
            continue
        for start in range(0, len(available), 3):
            chunk = available[start : start + 3]
            cols = st.columns(len(chunk))
            for col, metric in zip(cols, chunk):
                with col:
                    _metric_card(country_loc, metric)

    # Indisponibles : une seule section groupée et expliquée.
    _missing_section(metrics)

    _real_rate_panel(country_loc)
    _debt_panel(country_loc)

    ui.section_title(t("rl.summary.title"), t("rl.summary.sub"))
    st.markdown("\n".join(f"- {line}" for line in risk_lab.summary_lines(country_loc)))

    _comparison_panel()
    _data_details_expander(country_loc, metrics)
    _method_expander()
    ui.footer()
