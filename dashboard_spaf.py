import dash
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    from dash import Input, Output, dcc, html, dash_table
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output
    import dash_table

from spaf_engine import SPAF_DIMENSIONS, compute_spaf_dashboard_payload, load_spaf_context


SPAF_CONTEXT = load_spaf_context()


def _fmt_score(value):
    if pd.isna(value):
        return "—"
    return f"{float(value):.0f}"


def _score_color(value):
    if pd.isna(value):
        return "#94a3b8"
    value = float(value)
    if value >= 80:
        return "#1d4ed8"
    if value >= 65:
        return "#0f766e"
    if value >= 45:
        return "#b45309"
    return "#b91c1c"


def _dimension_cards(payload):
    cards = []
    for dim in SPAF_DIMENSIONS:
        value = payload["overall_dimensions"].get(dim, np.nan)
        cards.append(
            html.Div(
                [
                    html.Div(dim, style={"fontSize": "13px", "color": "#475569", "marginBottom": "6px"}),
                    html.Div(_fmt_score(value), style={"fontSize": "34px", "fontWeight": "700", "color": _score_color(value)}),
                    html.Div("/100", style={"fontSize": "12px", "color": "#64748b"}),
                ],
                style={
                    "background": "white",
                    "border": "1px solid #dbe4ee",
                    "borderRadius": "16px",
                    "padding": "16px",
                    "boxShadow": "0 10px 30px rgba(15,23,42,0.06)",
                    "minWidth": "180px",
                    "flex": "1 1 200px",
                },
            )
        )
    return cards


def _build_radar(payload):
    scores = [payload["overall_dimensions"].get(dim, np.nan) for dim in SPAF_DIMENSIONS]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=scores + [scores[0]],
            theta=SPAF_DIMENSIONS + [SPAF_DIMENSIONS[0]],
            fill="toself",
            name="SPAF",
            line=dict(color="#0f766e", width=3),
            fillcolor="rgba(15,118,110,0.22)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=[75] * len(SPAF_DIMENSIONS) + [75],
            theta=SPAF_DIMENSIONS + [SPAF_DIMENSIONS[0]],
            name="Referência 75",
            line=dict(color="#b45309", width=2, dash="dash"),
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="SPAF Radar",
        height=500,
        margin=dict(t=60, b=30, l=30, r=30),
        polar=dict(
            radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], gridcolor="#dbe4ee"),
            angularaxis=dict(gridcolor="#e2e8f0"),
        ),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
    )
    return fig


def _build_project_heatmap(project_df):
    if project_df.empty:
        return go.Figure()
    melted = project_df.melt(id_vars=["Projeto"], value_vars=SPAF_DIMENSIONS, var_name="Dimensão", value_name="Score")
    fig = px.imshow(
        melted.pivot(index="Projeto", columns="Dimensão", values="Score"),
        aspect="auto",
        color_continuous_scale=["#b91c1c", "#f59e0b", "#10b981", "#1d4ed8"],
        zmin=0,
        zmax=100,
        labels={"color": "Score"},
    )
    fig.update_layout(template="plotly_white", height=max(320, 70 + len(project_df) * 42), margin=dict(t=50, b=30, l=30, r=30))
    return fig


def _build_project_bar(project_df):
    if project_df.empty:
        return go.Figure()
    fig = px.bar(
        project_df.sort_values("SPAF Overall", ascending=True),
        x="SPAF Overall",
        y="Projeto",
        orientation="h",
        color="SPAF Overall",
        color_continuous_scale=["#b91c1c", "#f59e0b", "#10b981", "#1d4ed8"],
        range_color=[0, 100],
        text="SPAF Overall",
    )
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    fig.update_layout(template="plotly_white", height=max(320, 100 + len(project_df) * 42), margin=dict(t=50, b=30, l=30, r=30))
    return fig


def _evidence_items(payload):
    labels = [
        "Itens Concluídos",
        "Pessoas Ativas",
        "Lead Time Mediano (dias)",
        "Pipeline Success (%)",
        "% Rework PM",
        "Flow Efficiency Média (%)",
        "% After Hours Commit",
        "% Weekend Commit",
    ]
    items = []
    for label in labels:
        value = payload["overall_evidence"].get(label, np.nan)
        value_text = "—" if pd.isna(value) else f"{value}"
        items.append(
            html.Div(
                [
                    html.Div(label, style={"fontSize": "12px", "color": "#64748b"}),
                    html.Div(value_text, style={"fontSize": "22px", "fontWeight": "700", "color": "#0f172a"}),
                ],
                style={
                    "background": "#f8fafc",
                    "border": "1px solid #e2e8f0",
                    "borderRadius": "14px",
                    "padding": "14px",
                    "minWidth": "180px",
                    "flex": "1 1 180px",
                },
            )
        )
    return items


def _empty_figure(message):
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        annotations=[
            dict(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(size=15, color="#64748b"))
        ],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


app = dash.Dash(
    __name__,
    external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"],
    suppress_callback_exceptions=True,
    serve_locally=True,
)
app.title = "SPAF Dashboard"


initial_payload = compute_spaf_dashboard_payload(SPAF_CONTEXT)

app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.Div("SPAF Module", style={"fontSize": "13px", "letterSpacing": "0.12em", "textTransform": "uppercase", "color": "#0f766e", "fontWeight": "700"}),
                        html.H1("Socio-Technical Sustainability Dashboard", style={"margin": "8px 0 10px 0", "fontSize": "38px", "lineHeight": "1.05", "color": "#0f172a"}),
                        html.P(
                            "Módulo separado do FlowPMO para leitura SPAF: 8 dimensões, radar executivo, corte por projeto e diagnóstico por pessoa. "
                            "As dimensões Intensity, Human Sustainability e Predictive ainda usam proxies operacionais nesta primeira versão.",
                            style={"maxWidth": "960px", "color": "#334155", "fontSize": "16px", "margin": "0"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div("SPAF Overall", style={"fontSize": "13px", "color": "#64748b", "marginBottom": "6px"}),
                        html.Div(_fmt_score(initial_payload["overall_score"]), id="spaf-overall-score", style={"fontSize": "58px", "fontWeight": "800", "color": _score_color(initial_payload["overall_score"])}),
                        html.Div("/100", style={"fontSize": "14px", "color": "#64748b"}),
                    ],
                    style={
                        "background": "linear-gradient(135deg, #eff6ff 0%, #ecfeff 100%)",
                        "border": "1px solid #cbd5e1",
                        "borderRadius": "22px",
                        "padding": "24px 26px",
                        "minWidth": "240px",
                        "boxShadow": "0 20px 45px rgba(15,23,42,0.08)",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "gap": "18px",
                "alignItems": "flex-end",
                "flexWrap": "wrap",
                "marginBottom": "18px",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Período", style={"fontWeight": "700", "fontSize": "13px", "color": "#334155"}),
                        dcc.DatePickerRange(
                            id="spaf-date-range",
                            start_date=SPAF_CONTEXT["min_date"].date(),
                            end_date=SPAF_CONTEXT["max_date"].date(),
                            min_date_allowed=SPAF_CONTEXT["min_date"].date(),
                            max_date_allowed=SPAF_CONTEXT["max_date"].date(),
                            display_format="YYYY-MM-DD",
                            style={"background": "white"},
                        ),
                    ],
                    style={"display": "flex", "flexDirection": "column", "gap": "8px", "minWidth": "280px"},
                ),
                html.Div(
                    [
                        html.Label("Projetos", style={"fontWeight": "700", "fontSize": "13px", "color": "#334155"}),
                        dcc.Dropdown(
                            id="spaf-projects",
                            options=[{"label": project, "value": project} for project in SPAF_CONTEXT["projects"]],
                            value=[],
                            multi=True,
                            placeholder="Todos os projetos",
                        ),
                    ],
                    style={"display": "flex", "flexDirection": "column", "gap": "8px", "minWidth": "320px", "flex": "1"},
                ),
            ],
            style={
                "display": "flex",
                "gap": "14px",
                "flexWrap": "wrap",
                "padding": "18px",
                "background": "white",
                "border": "1px solid #dbe4ee",
                "borderRadius": "18px",
                "boxShadow": "0 8px 24px rgba(15,23,42,0.05)",
                "marginBottom": "18px",
            },
        ),
        html.Div(id="spaf-dimension-cards", style={"display": "flex", "flexWrap": "wrap", "gap": "14px", "marginBottom": "18px"}, children=_dimension_cards(initial_payload)),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="spaf-radar", figure=_build_radar(initial_payload), config={"displayModeBar": False})],
                    style={"background": "white", "border": "1px solid #dbe4ee", "borderRadius": "18px", "padding": "8px", "flex": "1 1 420px"},
                ),
                html.Div(
                    [
                        html.Div("Evidências do Recorte", style={"fontSize": "17px", "fontWeight": "700", "color": "#0f172a", "margin": "4px 0 14px 0"}),
                        html.Div(id="spaf-evidence-cards", style={"display": "flex", "flexWrap": "wrap", "gap": "12px"}, children=_evidence_items(initial_payload)),
                    ],
                    style={"background": "white", "border": "1px solid #dbe4ee", "borderRadius": "18px", "padding": "18px", "flex": "1 1 420px"},
                ),
            ],
            style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "18px"},
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="spaf-project-bar", figure=_build_project_bar(initial_payload["project_df"]) if not initial_payload["project_df"].empty else _empty_figure("Sem projetos no recorte"), config={"displayModeBar": False})],
                    style={"background": "white", "border": "1px solid #dbe4ee", "borderRadius": "18px", "padding": "8px", "flex": "1 1 360px"},
                ),
                html.Div(
                    [dcc.Graph(id="spaf-project-heatmap", figure=_build_project_heatmap(initial_payload["project_df"]) if not initial_payload["project_df"].empty else _empty_figure("Sem heatmap no recorte"), config={"displayModeBar": False})],
                    style={"background": "white", "border": "1px solid #dbe4ee", "borderRadius": "18px", "padding": "8px", "flex": "1 1 500px"},
                ),
            ],
            style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "18px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Projeto x Dimensão", style={"fontSize": "18px", "fontWeight": "700", "color": "#0f172a", "marginBottom": "10px"}),
                        dash_table.DataTable(
                            id="spaf-project-table",
                            page_size=12,
                            sort_action="native",
                            style_table={"overflowX": "auto"},
                            style_cell={"fontSize": "12px", "padding": "8px", "textAlign": "left", "fontFamily": "Arial"},
                            style_header={"fontWeight": "700", "backgroundColor": "#f8fafc"},
                        ),
                    ],
                    style={"background": "white", "border": "1px solid #dbe4ee", "borderRadius": "18px", "padding": "18px", "marginBottom": "18px"},
                ),
                html.Div(
                    [
                        html.Div("Pessoas com Maior Risco no Recorte", style={"fontSize": "18px", "fontWeight": "700", "color": "#0f172a", "marginBottom": "10px"}),
                        dash_table.DataTable(
                            id="spaf-person-table",
                            page_size=15,
                            sort_action="native",
                            style_table={"overflowX": "auto"},
                            style_cell={"fontSize": "12px", "padding": "8px", "textAlign": "left", "fontFamily": "Arial"},
                            style_header={"fontWeight": "700", "backgroundColor": "#f8fafc"},
                            style_data_conditional=[
                                {"if": {"filter_query": "{SPAF Risk} >= 70", "column_id": "SPAF Risk"}, "backgroundColor": "#fee2e2", "color": "#991b1b", "fontWeight": "700"},
                                {"if": {"filter_query": "{SPAF Risk} >= 50 && {SPAF Risk} < 70", "column_id": "SPAF Risk"}, "backgroundColor": "#fef3c7", "color": "#92400e", "fontWeight": "700"},
                            ],
                        ),
                    ],
                    style={"background": "white", "border": "1px solid #dbe4ee", "borderRadius": "18px", "padding": "18px", "marginBottom": "18px"},
                ),
                html.Div(
                    [
                        html.Div("Metodologia e Maturidade", style={"fontSize": "18px", "fontWeight": "700", "color": "#0f172a", "marginBottom": "10px"}),
                        dash_table.DataTable(
                            id="spaf-method-table",
                            page_size=10,
                            sort_action="native",
                            style_table={"overflowX": "auto"},
                            style_cell={"fontSize": "12px", "padding": "8px", "textAlign": "left", "fontFamily": "Arial"},
                            style_header={"fontWeight": "700", "backgroundColor": "#f8fafc"},
                        ),
                        html.Div(
                            "Nesta versão, Predictive, Intensity e Human Sustainability são operados como baseline heurístico sobre telemetria existente. "
                            "A expansão para modelos calibrados, ICs estatísticos e validação externa fica isolada para a próxima fase do módulo SPAF.",
                            style={"marginTop": "12px", "fontSize": "13px", "color": "#475569"},
                        ),
                    ],
                    style={"background": "white", "border": "1px solid #dbe4ee", "borderRadius": "18px", "padding": "18px"},
                ),
            ]
        ),
    ],
    style={
        "minHeight": "100vh",
        "padding": "24px",
        "background": "linear-gradient(180deg, #f8fafc 0%, #eef2ff 45%, #f8fafc 100%)",
        "fontFamily": "Arial, sans-serif",
    },
)


@app.callback(
    Output("spaf-overall-score", "children"),
    Output("spaf-overall-score", "style"),
    Output("spaf-dimension-cards", "children"),
    Output("spaf-radar", "figure"),
    Output("spaf-evidence-cards", "children"),
    Output("spaf-project-bar", "figure"),
    Output("spaf-project-heatmap", "figure"),
    Output("spaf-project-table", "data"),
    Output("spaf-project-table", "columns"),
    Output("spaf-person-table", "data"),
    Output("spaf-person-table", "columns"),
    Output("spaf-method-table", "data"),
    Output("spaf-method-table", "columns"),
    Input("spaf-date-range", "start_date"),
    Input("spaf-date-range", "end_date"),
    Input("spaf-projects", "value"),
)
def refresh_spaf_dashboard(start_date, end_date, selected_projects):
    payload = compute_spaf_dashboard_payload(
        SPAF_CONTEXT,
        start_date=start_date,
        end_date=end_date,
        selected_projects=selected_projects,
    )

    project_df = payload["project_df"]
    person_df = payload["person_df"]
    method_df = payload["methodology_df"]

    overall_style = {
        "fontSize": "58px",
        "fontWeight": "800",
        "color": _score_color(payload["overall_score"]),
    }

    project_fig = _build_project_bar(project_df) if not project_df.empty else _empty_figure("Sem projetos no recorte")
    heatmap_fig = _build_project_heatmap(project_df) if not project_df.empty else _empty_figure("Sem heatmap no recorte")

    project_data = project_df.to_dict("records") if not project_df.empty else []
    project_cols = [{"name": col, "id": col} for col in project_df.columns] if not project_df.empty else []
    person_data = person_df.head(30).to_dict("records") if not person_df.empty else []
    person_cols = [{"name": col, "id": col} for col in person_df.columns] if not person_df.empty else []
    method_data = method_df.to_dict("records") if not method_df.empty else []
    method_cols = [{"name": col, "id": col} for col in method_df.columns] if not method_df.empty else []

    return (
        _fmt_score(payload["overall_score"]),
        overall_style,
        _dimension_cards(payload),
        _build_radar(payload),
        _evidence_items(payload),
        project_fig,
        heatmap_fig,
        project_data,
        project_cols,
        person_data,
        person_cols,
        method_data,
        method_cols,
    )


server = app.server


if __name__ == "__main__":
    app.run(debug=True, port=8052)
