"""Renderer do módulo 4Ps — componentes Dash para a aba de Governança TECH.

Converte o FourPsPayload (produzido pelo builder) em componentes Dash/HTML.
Não contém lógica de negócio — apenas apresentação.

Layout da aba:
  ┌─────────────────────────────────────────────────────────────────┐
  │  4Ps — Governança TECH     Mês: [Abr 2026 ▼]  [↻ Atualizar]   │
  ├──────────────────────────┬──────────────────────────────────────┤
  │  PROGRESSO               │  PRÓXIMOS PASSOS                    │
  │  ▸ Infra Tech            │  ▸ Infra Tech                       │
  │  ▸ W1nner                │  ▸ W1nner                           │
  │    ⚡ BAU (3 itens)       │    ⚡ BAU (1 item)                   │
  ├──────────────────────────┴──────────────────────────────────────┤
  │  PONTOS DE ATENÇÃO (sugestões automáticas Jira — >5d parados)  │
  ├─────────────────────────────────────────────────────────────────┤
  │  PONTOS DE DECISÃO — preencher manualmente no PowerPoint        │
  └─────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

try:
    from dash import html, dcc
    import dash_bootstrap_components as dbc
    _HAS_DBC = True
except ImportError:
    try:
        from dash import html, dcc
        _HAS_DBC = False
    except ImportError:
        html = dcc = None  # type: ignore
        _HAS_DBC = False

from dashboards.four_ps.builder import FourPsPayload, AreaData, ItemDict

# ---------------------------------------------------------------------------
# Paleta de cores (alinhada com PORTFOLIO_ROADMAP_STATUS_COLORS do dashboard)
# ---------------------------------------------------------------------------

_COLOR = {
    "running":   "#8ec7cf",
    "planning":  "#d5c6dc",
    "done":      "#97c95c",
    "paused":    "#e4d8ad",
    "bau_bg":    "#fff3cd",
    "bau_border": "#e6a817",
    "blocked_bg": "#fdecea",
    "blocked_border": "#c0392b",
    "section_header": "#2c3e50",
    "area_header": "#34495e",
    "epic_border": "#5b8db8",
    "feature_border": "#7b6fa0",
    "story_border": "#6b8e6b",
}

_SECTION_ORDER = [
    "W1nner", "S1NC", "BeFinance", "Dados",
    "Infra Tech", "Infra DevOps", "Arquitetura",
    "Cross Team", "Cibersegurança", "Esc. Agilidade",
    "Governança", "Data & Analytics",
]


def _sort_areas(areas: Dict[str, Any]) -> List[str]:
    known = [a for a in _SECTION_ORDER if a in areas]
    others = sorted(a for a in areas if a not in _SECTION_ORDER)
    return known + others


# ---------------------------------------------------------------------------
# Componentes atômicos
# ---------------------------------------------------------------------------

def _badge(text: str, bg: str, color: str = "#111") -> html.Span:
    return html.Span(
        text,
        style={
            "backgroundColor": bg,
            "color": color,
            "padding": "2px 8px",
            "borderRadius": "8px",
            "fontSize": "11px",
            "fontWeight": "bold",
            "marginLeft": "6px",
            "whiteSpace": "nowrap",
        },
    )


def _progress_bar(pct: Optional[int]) -> html.Div:
    if pct is None:
        return html.Span("N/D", style={"color": "#aaa", "fontSize": "11px", "marginLeft": "6px"})
    fill_color = "#97c95c" if pct >= 70 else "#8ec7cf" if pct >= 30 else "#d5c6dc"
    return html.Div(
        [
            html.Div(
                style={
                    "width": f"{pct}%",
                    "height": "6px",
                    "backgroundColor": fill_color,
                    "borderRadius": "3px",
                    "transition": "width 0.3s",
                }
            ),
            html.Span(f"{pct}%", style={"fontSize": "10px", "color": "#555", "marginLeft": "4px"}),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "4px",
            "backgroundColor": "#e9ecef",
            "borderRadius": "3px",
            "padding": "1px 4px",
            "minWidth": "80px",
        },
    )


def _item_link(key: str, title: str, link: str) -> html.Span:
    if link:
        return html.Span([
            html.A(
                key,
                href=link,
                target="_blank",
                style={"color": "#1a73e8", "fontSize": "11px", "marginRight": "4px", "textDecoration": "none"},
            ),
            html.Span(title, style={"fontSize": "13px"}),
        ])
    return html.Span([
        html.Span(key, style={"color": "#888", "fontSize": "11px", "marginRight": "4px"}),
        html.Span(title, style={"fontSize": "13px"}),
    ])


# ---------------------------------------------------------------------------
# Faixa de KPI cards
# ---------------------------------------------------------------------------

def render_four_ps_kpi_row(kpis: Dict[str, Any]) -> html.Div:
    """Renderiza a faixa de 8 KPI cards no topo da aba 4Ps."""

    def _card(
        title: str,
        value: Any,
        sub: str = "",
        bg: str = "#f8fafc",
        border: str = "#e2e8f0",
        val_color: str = "#0f172a",
    ) -> html.Div:
        return html.Div(
            [
                html.Div(
                    title,
                    style={
                        "fontSize": "10px",
                        "color": "#64748b",
                        "fontWeight": "600",
                        "textTransform": "uppercase",
                        "letterSpacing": "0.05em",
                        "marginBottom": "4px",
                    },
                ),
                html.Div(
                    str(value),
                    style={
                        "fontSize": "22px",
                        "fontWeight": "700",
                        "color": val_color,
                        "lineHeight": "1.1",
                    },
                ),
                html.Div(
                    sub,
                    style={"fontSize": "10px", "color": "#94a3b8", "marginTop": "2px"},
                ) if sub else html.Span(),
            ],
            style={
                "flex": "1",
                "minWidth": "110px",
                "backgroundColor": bg,
                "border": f"1px solid {border}",
                "borderRadius": "8px",
                "padding": "10px 12px",
            },
        )

    wip        = kpis.get("wip_total", 0)
    pipeline   = kpis.get("pipeline_total", 0)
    blocked    = kpis.get("blocked_total", 0)
    deliveries = kpis.get("deliveries_period", 0)
    bau_pct    = kpis.get("bau_pct", 0)
    bau_count  = kpis.get("bau_count", 0)
    no_date    = kpis.get("epics_no_date", 0)
    avg_pct    = kpis.get("epics_avg_pct")
    on_time    = kpis.get("on_time_pct")
    on_denom   = kpis.get("on_time_denominator", 0)

    # Bloqueados
    if blocked > 0:
        bl_bg, bl_bord, bl_col = "#fef2f2", "#fca5a5", "#dc2626"
    else:
        bl_bg, bl_bord, bl_col = "#f8fafc", "#e2e8f0", "#0f172a"

    # Épicos sem data
    if no_date > 0:
        nd_bg, nd_bord, nd_col = "#fff7ed", "#fdba74", "#ea580c"
    else:
        nd_bg, nd_bord, nd_col = "#f8fafc", "#e2e8f0", "#0f172a"

    # BAU %
    if bau_pct >= 50:
        bau_bg, bau_bord, bau_col = "#fff7ed", "#fdba74", "#ea580c"
    else:
        bau_bg, bau_bord, bau_col = "#f8fafc", "#e2e8f0", "#0f172a"

    # Progresso médio
    if avg_pct is None:
        avg_val, avg_col = "—", "#94a3b8"
    elif avg_pct >= 70:
        avg_val, avg_col = f"{avg_pct}%", "#16a34a"
    elif avg_pct >= 40:
        avg_val, avg_col = f"{avg_pct}%", "#d97706"
    else:
        avg_val, avg_col = f"{avg_pct}%", "#dc2626"

    # No prazo
    if on_time is None or on_denom == 0:
        ot_val, ot_col  = "—", "#94a3b8"
        ot_bg, ot_bord  = "#f8fafc", "#e2e8f0"
        ot_sub          = "sem itens c/ data"
    elif on_time >= 80:
        ot_val, ot_col  = f"{on_time}%", "#16a34a"
        ot_bg, ot_bord  = "#f0fdf4", "#86efac"
        ot_sub          = f"de {on_denom} c/ prazo"
    elif on_time >= 60:
        ot_val, ot_col  = f"{on_time}%", "#d97706"
        ot_bg, ot_bord  = "#fffbeb", "#fcd34d"
        ot_sub          = f"de {on_denom} c/ prazo"
    else:
        ot_val, ot_col  = f"{on_time}%", "#dc2626"
        ot_bg, ot_bord  = "#fef2f2", "#fca5a5"
        ot_sub          = f"de {on_denom} c/ prazo"

    return html.Div(
        [
            _card("Em Progresso",  wip,       "WIP total"),
            _card("Pipeline",      pipeline,  "próximos passos"),
            _card("Bloqueados",    blocked,   ">5 dias parados",    bl_bg,  bl_bord,  bl_col),
            _card("Entregas",      deliveries,"no período"),
            _card("BAU",           f"{bau_pct}%", f"{bau_count} itens", bau_bg, bau_bord, bau_col),
            _card("Épicos s/ Data",no_date,   "Running s/ prazo",   nd_bg,  nd_bord,  nd_col),
            _card("Prog. Médio",   avg_val,   "épicos running",     val_color=avg_col),
            _card("No Prazo",      ot_val,    ot_sub,               ot_bg,  ot_bord,  ot_col),
        ],
        style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginBottom": "16px"},
    )


# ---------------------------------------------------------------------------
# Cards por tipo de item
# ---------------------------------------------------------------------------

def _render_epic_card(epic: ItemDict) -> html.Div:
    pct = epic.get("progress_pct")
    done = epic.get("done_this_month", False)
    status_label = "Concluído" if done else epic.get("roadmap_status", "Planning")
    status_color = {
        "Running": _COLOR["running"],
        "Planning": _COLOR["planning"],
        "Concluído": _COLOR["done"],
        "Done": _COLOR["done"],
        "Paused": _COLOR["paused"],
    }.get(status_label, _COLOR["planning"])

    due = epic.get("due_date", "")
    due_label = f"Entrega: {due[:10]}" if due else ""
    bg_color = "#f4fff0" if done else "#f8fbff"
    border_color = _COLOR["done"] if done else _COLOR["epic_border"]

    return html.Div(
        [
            html.Div(
                [
                    _item_link(epic.get("key", ""), epic.get("title", ""), epic.get("link", "")),
                    _badge(status_label, status_color),
                ],
                style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "4px"},
            ),
            html.Div(
                [
                    _progress_bar(pct),
                    html.Span(due_label, style={"fontSize": "11px", "color": "#666", "marginLeft": "8px"}),
                ],
                style={"display": "flex", "alignItems": "center", "marginTop": "4px"},
            ),
        ],
        style={
            "borderLeft": f"4px solid {border_color}",
            "padding": "6px 10px",
            "marginBottom": "4px",
            "backgroundColor": bg_color,
            "borderRadius": "0 4px 4px 0",
        },
    )


def _render_feature_card(feature: ItemDict) -> html.Div:
    done = feature.get("done_this_month", False)
    badge_text = "Feature ✓" if done else "Feature"
    badge_bg = "#d4edda" if done else "#ede7f6"
    badge_fg = "#155724" if done else "#4a148c"
    bg_color = "#f4fff0" if done else "#faf8ff"
    border_color = _COLOR["done"] if done else _COLOR["feature_border"]
    due = feature.get("due_date", "")
    due_el = html.Span(
        f"  {due[:10]}",
        style={"fontSize": "10px", "color": "#888", "marginLeft": "6px", "whiteSpace": "nowrap"},
    ) if due else html.Span()
    return html.Div(
        [
            html.Div(
                [
                    html.Span("  ", style={"width": "12px", "display": "inline-block"}),
                    _badge(badge_text, badge_bg, badge_fg),
                    html.Span(" "),
                    _item_link(feature.get("key", ""), feature.get("title", ""), feature.get("link", "")),
                    due_el,
                ],
                style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "4px"},
            ),
        ],
        style={
            "borderLeft": f"4px solid {border_color}",
            "padding": "4px 10px 4px 20px",
            "marginBottom": "3px",
            "backgroundColor": bg_color,
            "borderRadius": "0 4px 4px 0",
        },
    )


def _render_story_card(story: ItemDict) -> html.Div:
    itype = str(story.get("issue_type") or "Story")
    done = story.get("done_this_month", False)
    type_colors = {
        "Bug": ("#fdecea", "#c0392b"),
        "Support": ("#fff8e1", "#e65100"),
        "Tech": ("#e8f5e9", "#1b5e20"),
    }
    bg, border = type_colors.get(itype, ("#f5f5f5", _COLOR["story_border"]))
    if done:
        bg, border = "#d4edda", "#155724"
        itype = f"{itype} ✓"
    due = story.get("due_date", "")
    due_el = html.Span(
        f"  {due[:10]}",
        style={"fontSize": "10px", "color": "#888", "marginLeft": "6px", "whiteSpace": "nowrap"},
    ) if due else html.Span()
    return html.Div(
        [
            html.Div(
                [
                    html.Span("    ", style={"width": "20px", "display": "inline-block"}),
                    _badge(itype, bg, border),
                    html.Span(" "),
                    _item_link(story.get("key", ""), story.get("title", ""), story.get("link", "")),
                    due_el,
                ],
                style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "4px"},
            ),
        ],
        style={
            "borderLeft": f"3px solid {_COLOR['done'] if done else _COLOR['story_border']}",
            "padding": "3px 10px 3px 28px",
            "marginBottom": "2px",
            "backgroundColor": "#f4fff0" if done else "#fafafa",
            "borderRadius": "0 4px 4px 0",
        },
    )


def _render_bau_item(item: ItemDict) -> html.Div:
    suggested = item.get("suggested_epic")
    suggestion_el = html.Span(
        f"  sugerir vínculo: {suggested}",
        style={"fontSize": "11px", "color": _COLOR["bau_border"], "marginLeft": "6px"},
    ) if suggested else html.Span()
    itype = str(item.get("issue_type") or "Story")
    return html.Div(
        [
            html.Div(
                [
                    _badge(itype, _COLOR["bau_bg"], _COLOR["bau_border"]),
                    html.Span(" "),
                    _item_link(item.get("key", ""), item.get("title", ""), item.get("link", "")),
                    suggestion_el,
                ],
                style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "4px"},
            ),
        ],
        style={
            "borderLeft": f"3px solid {_COLOR['bau_border']}",
            "padding": "4px 10px",
            "marginBottom": "3px",
            "backgroundColor": _COLOR["bau_bg"],
            "borderRadius": "0 4px 4px 0",
        },
    )


# ---------------------------------------------------------------------------
# Seção por área
# ---------------------------------------------------------------------------

def _render_area_section(area_name: str, data: AreaData, section_id_prefix: str) -> html.Div:
    epics    = data.get("epics") or []
    features = data.get("features") or []
    stories  = data.get("stories") or []
    bau      = data.get("bau") or []

    total = len(epics) + len(features) + len(stories) + len(bau)
    if total == 0:
        return html.Div()

    items_el: List[Any] = []

    # Épicos com features/stories filhas agrupadas
    epic_keys_shown: set = set()
    for epic in epics:
        epic_keys_shown.add(epic.get("key", ""))
        items_el.append(_render_epic_card(epic))
        # Features filhas deste épico
        for feat in features:
            if feat.get("epic_key") == epic.get("key"):
                items_el.append(_render_feature_card(feat))
                # Stories filhas desta feature
                for story in stories:
                    if story.get("feature_key") == feat.get("key"):
                        items_el.append(_render_story_card(story))

    # Features sem épico nos epics mostrados
    orphan_features = [f for f in features if f.get("epic_key") not in epic_keys_shown]
    for feat in orphan_features:
        items_el.append(_render_feature_card(feat))
        for story in stories:
            if story.get("feature_key") == feat.get("key"):
                items_el.append(_render_story_card(story))

    # Stories completamente soltas
    feature_keys_shown = {f.get("key") for f in features}
    for story in stories:
        if story.get("feature_key") not in feature_keys_shown:
            items_el.append(_render_story_card(story))

    # BAU
    if bau:
        items_el.append(
            html.Div(
                [
                    html.Span(
                        f"⚡ BAU — sem épico vinculado ({len(bau)} {'item' if len(bau)==1 else 'itens'})",
                        style={
                            "fontSize": "12px",
                            "fontWeight": "bold",
                            "color": _COLOR["bau_border"],
                            "borderBottom": f"1px dashed {_COLOR['bau_border']}",
                            "display": "block",
                            "margin": "8px 0 4px 0",
                        },
                    ),
                    *[_render_bau_item(item) for item in bau],
                ]
            )
        )

    area_id = f"{section_id_prefix}-{area_name.lower().replace(' ', '-')}"

    return html.Details(
        [
            html.Summary(
                html.Span(
                    [
                        html.Strong(area_name),
                        html.Span(
                            f" ({total} {'item' if total == 1 else 'itens'})",
                            style={"fontSize": "12px", "color": "#777", "fontWeight": "normal"},
                        ),
                        html.Span(
                            f"  ⚡ {len(bau)} BAU" if bau else "",
                            style={"fontSize": "11px", "color": _COLOR["bau_border"], "marginLeft": "6px"},
                        ),
                    ]
                ),
                style={"cursor": "pointer", "padding": "6px 8px", "userSelect": "none"},
            ),
            html.Div(items_el, style={"padding": "4px 0 4px 12px"}),
        ],
        id=area_id,
        open=True,
        style={
            "borderBottom": "1px solid #e0e0e0",
            "marginBottom": "4px",
        },
    )


# ---------------------------------------------------------------------------
# Resumo Mensal
# ---------------------------------------------------------------------------

def _render_monthly_summary(summary: Dict[str, Any]) -> html.Div:
    """Resumo mensal: entregas realizadas (key + título) agrupadas por mês × área."""
    months = summary.get("months") or []
    areas = summary.get("areas") or []
    done_items = summary.get("done_items") or {}

    if not months or not areas:
        return html.Div()

    # Filtra meses que têm pelo menos 1 entrega
    active_months = [m for m in months if any(
        done_items.get(m, {}).get(a) for a in areas
    )]
    if not active_months:
        return html.Div()

    _TYPE_ORDER = {"Epic": 0, "Feature": 1}

    month_sections: List[Any] = []
    for m in reversed(active_months):  # mais recente primeiro
        month_display = m[5:] + "/" + m[:4]  # "MM/YYYY"
        area_els: List[Any] = []
        for area in areas:
            items = done_items.get(m, {}).get(area) or []
            if not items:
                continue
            # Ordena: Épicos → Features → Stories, depois por key
            items_sorted = sorted(items, key=lambda x: (_TYPE_ORDER.get(x["type"], 2), x["key"]))
            item_els = []
            for it in items_sorted:
                type_colors = {"Epic": ("#dbeafe", "#1d4ed8"), "Feature": ("#ede7f6", "#4a148c")}
                bg, fg = type_colors.get(it["type"], ("#e8f5e9", "#155724"))
                link_el = html.A(
                    it["key"],
                    href=it.get("link", "#"),
                    target="_blank",
                    style={"color": "#1a73e8", "fontSize": "11px", "textDecoration": "none", "marginRight": "4px"},
                ) if it.get("link") else html.Span(
                    it["key"],
                    style={"color": "#888", "fontSize": "11px", "marginRight": "4px"},
                )
                item_els.append(
                    html.Div(
                        [
                            _badge(it["type"], bg, fg),
                            link_el,
                            html.Span(it["title"], style={"fontSize": "12px"}),
                        ],
                        style={
                            "display": "flex", "alignItems": "center", "gap": "4px",
                            "padding": "2px 4px", "marginBottom": "2px",
                        },
                    )
                )
            area_els.append(
                html.Div(
                    [
                        html.Span(
                            f"{area} ({len(items)})",
                            style={"fontSize": "12px", "fontWeight": "bold", "color": "#34495e",
                                   "display": "block", "marginBottom": "4px"},
                        ),
                        *item_els,
                    ],
                    style={"marginBottom": "8px"},
                )
            )

        if area_els:
            total = sum(len(done_items.get(m, {}).get(a) or []) for a in areas)
            month_sections.append(
                html.Details(
                    [
                        html.Summary(
                            html.Span([
                                html.Strong(month_display),
                                html.Span(f" — {total} {'entrega' if total == 1 else 'entregas'}",
                                          style={"fontSize": "12px", "color": "#777", "fontWeight": "normal"}),
                            ]),
                            style={"cursor": "pointer", "padding": "4px 6px", "userSelect": "none",
                                   "fontSize": "13px"},
                        ),
                        html.Div(area_els, style={"padding": "6px 0 2px 12px"}),
                    ],
                    open=True,
                    style={"marginBottom": "6px", "borderBottom": "1px solid #e8e8e8"},
                )
            )

    if not month_sections:
        return html.Div()

    return html.Details(
        [
            html.Summary(
                html.Span([
                    html.Strong("Entregas Realizadas"),
                    html.Span(" — histórico mensal por área",
                              style={"fontSize": "12px", "color": "#777", "fontWeight": "normal"}),
                ]),
                style={"cursor": "pointer", "padding": "6px 8px", "userSelect": "none",
                       "fontSize": "14px", "color": _COLOR["section_header"]},
            ),
            html.Div(month_sections, style={"padding": "8px 0 4px 8px"}),
        ],
        open=True,
        style={
            "border": f"1px solid {_COLOR['done']}",
            "borderRadius": "6px",
            "padding": "8px 12px",
            "backgroundColor": "#f8fff4",
            "marginBottom": "12px",
        },
    )


# ---------------------------------------------------------------------------
# Seção Pontos de Atenção
# ---------------------------------------------------------------------------

def _render_blocked_item(item: ItemDict) -> html.Div:
    days = item.get("days_stale", 0)
    return html.Div(
        [
            html.Span("⚠ ", style={"color": _COLOR["blocked_border"]}),
            _item_link(item.get("key", ""), item.get("title", ""), item.get("link", "")),
            html.Span(
                f" — parado há {days} dias",
                style={"fontSize": "11px", "color": _COLOR["blocked_border"], "marginLeft": "6px"},
            ),
        ],
        style={
            "borderLeft": f"3px solid {_COLOR['blocked_border']}",
            "padding": "4px 10px",
            "marginBottom": "3px",
            "backgroundColor": _COLOR["blocked_bg"],
            "borderRadius": "0 4px 4px 0",
        },
    )


def _render_atencao_section(pontos_atencao: Dict[str, List[ItemDict]]) -> html.Div:
    if not pontos_atencao:
        return html.Div(
            html.P(
                "Nenhum item bloqueado/parado identificado automaticamente no período.",
                style={"color": "#888", "fontStyle": "italic", "margin": "8px 0"},
            )
        )

    area_els: List[Any] = []
    for area in _sort_areas(pontos_atencao):
        items = pontos_atencao[area]
        if not items:
            continue
        area_els.append(
            html.Div(
                [
                    html.Strong(area, style={"fontSize": "13px", "display": "block", "marginBottom": "4px"}),
                    *[_render_blocked_item(item) for item in items],
                ],
                style={"marginBottom": "10px"},
            )
        )

    return html.Div(
        [
            html.P(
                "Itens identificados automaticamente com bloqueio ou sem movimento há mais de 5 dias. "
                "Complemente manualmente no PowerPoint.",
                style={"color": "#666", "fontSize": "12px", "marginBottom": "10px"},
            ),
            *area_els,
        ]
    )


# ---------------------------------------------------------------------------
# Geração de texto para copiar (PPTX)
# ---------------------------------------------------------------------------

def _payload_to_text(payload: FourPsPayload, month_label: str) -> str:
    lines: List[str] = [f"4Ps — Governança TECH | {month_label}", ""]

    for section_key, section_title in [
        ("progresso", "PROGRESSO"),
        ("proximos_passos", "PRÓXIMOS PASSOS"),
    ]:
        lines.append(f"▸ {section_title}")
        section = payload.get(section_key) or {}
        for area in _sort_areas(section):
            data = section[area]
            lines.append(f"\n  {area}")
            for epic in data.get("epics") or []:
                pct = f" ({epic['progress_pct']}%)" if epic.get("progress_pct") is not None else ""
                lines.append(f"    • [Épico] {epic['key']} — {epic['title']}{pct}")
            for feat in data.get("features") or []:
                lines.append(f"      ◦ [Feature] {feat['key']} — {feat['title']}")
            for story in data.get("stories") or []:
                itype = story.get("issue_type", "Story")
                lines.append(f"        - [{itype}] {story['key']} — {story['title']}")
            for bau in data.get("bau") or []:
                sug = f" → sugerir: {bau['suggested_epic']}" if bau.get("suggested_epic") else ""
                lines.append(f"      ⚡ BAU {bau['key']} — {bau['title']}{sug}")
        lines.append("")

    lines.append("▸ PONTOS DE ATENÇÃO (sugestões automáticas)")
    for area in _sort_areas(payload.get("pontos_atencao") or {}):
        for item in (payload["pontos_atencao"][area] or []):
            lines.append(f"  ⚠ [{area}] {item['key']} — {item['title']} (parado há {item.get('days_stale', 0)}d)")

    lines.append("\n▸ PONTOS DE DECISÃO")
    lines.append("  (preencher manualmente)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Renderer principal
# ---------------------------------------------------------------------------

def render_four_ps_tab(
    payload: FourPsPayload,
    month: Optional[date] = None,
    is_loading: bool = False,
    error_message: str = "",
    df_portfolio: Any = None,
    period_months: int = 1,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    kanban_data: Optional[Any] = None,
) -> html.Div:
    """Renderiza a aba completa 4Ps — Governança TECH."""
    ref_month = month or date.today().replace(day=1)
    month_label = ref_month.strftime("%b %Y").capitalize()

    # Calcula o intervalo de Próximos Passos para exibir no cabeçalho
    _nm = ref_month.month + period_months
    _ny = ref_month.year + (_nm - 1) // 12
    _nm = (_nm - 1) % 12 + 1
    next_start = date(_ny, _nm, 1)
    _em = next_start.month + period_months
    _ey = next_start.year + (_em - 1) // 12
    _em = (_em - 1) % 12 + 1
    next_end = date(_ey, _em, 1) - timedelta(days=1)
    if period_months >= 3:
        # Mostra o quarter
        q = (next_start.month - 1) // 3 + 1
        next_period_label = f"Q{q}-{next_start.year}"
        period_label = "trimestre"
    else:
        next_period_label = next_start.strftime("%b %Y").capitalize()
        period_label = "mês"

    # Resumo mensal restrito ao período selecionado
    monthly_summary_el: Any = html.Div()
    kpi_row_el: Any = html.Div()
    try:
        from dashboards.four_ps.builder import build_monthly_summary, compute_four_ps_kpis
        summary = build_monthly_summary(
            df_portfolio,
            date_start=date_start,
            date_end=date_end,
            payload=payload,
            kanban_data=kanban_data,
        )
        monthly_summary_el = _render_monthly_summary(summary)
        kpis = compute_four_ps_kpis(payload, summary, df_portfolio, kanban_data)
        kpi_row_el = render_four_ps_kpi_row(kpis)
    except Exception:
        pass

    if error_message:
        return html.Div(
            html.P(f"Erro ao carregar dados: {error_message}",
                   style={"color": "#c0392b", "padding": "20px"}),
        )

    if is_loading or (not payload.get("progresso") and not payload.get("proximos_passos")):
        return html.Div(
            html.P(
                "Carregando dados 4Ps..." if is_loading else
                "Nenhum item encontrado para o período selecionado.",
                style={"padding": "20px", "color": "#888", "fontStyle": "italic"},
            )
        )

    progresso_areas    = _sort_areas(payload.get("progresso") or {})
    proximos_areas     = _sort_areas(payload.get("proximos_passos") or {})
    pontos_atencao     = payload.get("pontos_atencao") or {}

    copy_text = _payload_to_text(payload, month_label)

    # Seção Progresso
    progresso_el = html.Div([
        html.H4("Progresso", style={"color": _COLOR["section_header"], "marginBottom": "8px", "fontSize": "15px"}),
        *[
            _render_area_section(area, payload["progresso"][area], "prog")
            for area in progresso_areas
            if payload["progresso"].get(area)
        ],
    ])

    # Seção Próximos Passos
    proximos_el = html.Div([
        html.H4("Próximos Passos", style={"color": _COLOR["section_header"], "marginBottom": "8px", "fontSize": "15px"}),
        *[
            _render_area_section(area, payload["proximos_passos"][area], "prox")
            for area in proximos_areas
            if payload["proximos_passos"].get(area)
        ],
    ])

    # Seção Pontos de Atenção
    atencao_el = html.Div([
        html.H4(
            "Pontos de Atenção",
            style={"color": _COLOR["blocked_border"], "marginBottom": "8px", "fontSize": "15px"},
        ),
        _render_atencao_section(pontos_atencao),
    ])

    # Seção Pontos de Decisão
    decisao_el = html.Div([
        html.H4("Pontos de Decisão", style={"color": _COLOR["section_header"], "marginBottom": "4px", "fontSize": "15px"}),
        html.P(
            "Preencher manualmente no PowerPoint após revisão do time de governança.",
            style={"color": "#888", "fontStyle": "italic", "fontSize": "12px"},
        ),
    ])

    return html.Div(
        [
            # Cabeçalho
            html.Div(
                [
                    html.H3(
                        "4Ps — Governança TECH",
                        style={"margin": "0", "fontSize": "18px", "color": _COLOR["section_header"]},
                    ),
                    html.Span(
                        [
                            html.Span(month_label),
                            html.Span(
                                f"  →  Próx: {next_period_label}",
                                style={"color": "#5b8db8", "fontWeight": "bold"},
                            ),
                            html.Span(
                                f" ({period_label})",
                                style={"color": "#aaa", "fontSize": "11px"},
                            ),
                        ],
                        style={
                            "fontSize": "13px", "color": "#666", "marginLeft": "12px",
                            "backgroundColor": "#f0f0f0", "padding": "2px 12px",
                            "borderRadius": "10px",
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "12px"},
            ),

            # Botão Copiar
            html.Div(
                [
                    html.Button(
                        "Copiar como texto",
                        id="btn-four-ps-copy",
                        n_clicks=0,
                        style={
                            "fontSize": "12px", "padding": "4px 12px",
                            "cursor": "pointer", "borderRadius": "4px",
                            "border": "1px solid #bbb", "backgroundColor": "#fafafa",
                        },
                    ),
                    html.Span(id="four-ps-copy-feedback", style={"fontSize": "11px", "color": "#666", "marginLeft": "8px"}),
                    dcc.Store(id="four-ps-copy-text-store", data=copy_text),
                ],
                style={"marginBottom": "12px"},
            ),

            # Faixa de KPIs
            kpi_row_el,

            # Grid 2 colunas: Progresso | Próximos Passos
            html.Div(
                [
                    html.Div(
                        progresso_el,
                        style={
                            "flex": "1", "minWidth": "0",
                            "border": "1px solid #e0e0e0",
                            "borderRadius": "6px", "padding": "12px",
                            "backgroundColor": "#fdfdfd",
                        },
                    ),
                    html.Div(
                        proximos_el,
                        style={
                            "flex": "1", "minWidth": "0",
                            "border": "1px solid #e0e0e0",
                            "borderRadius": "6px", "padding": "12px",
                            "backgroundColor": "#fdfdfd",
                        },
                    ),
                ],
                style={"display": "flex", "gap": "16px", "marginBottom": "16px"},
            ),

            # Resumo Mensal
            monthly_summary_el,

            # Pontos de Atenção
            html.Div(
                atencao_el,
                style={
                    "border": f"1px solid {_COLOR['blocked_border']}",
                    "borderRadius": "6px", "padding": "12px",
                    "backgroundColor": _COLOR["blocked_bg"],
                    "marginBottom": "12px",
                },
            ),

            # Pontos de Decisão
            html.Div(
                decisao_el,
                style={
                    "border": "1px solid #bbb",
                    "borderRadius": "6px", "padding": "12px",
                    "backgroundColor": "#fafafa",
                },
            ),
        ],
        style={"padding": "16px 20px"},
    )
