import plotly.graph_objects as go

try:
    from dash import dcc, html
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html

from dashboards.metrics.health_score import HealthScoreResult

_OVERLAY_HIDDEN = {
    'display': 'none',
}

_OVERLAY_VISIBLE = {
    'display': 'flex',
    'position': 'fixed',
    'top': '0',
    'left': '0',
    'width': '100%',
    'height': '100%',
    'backgroundColor': 'rgba(0,0,0,0.5)',
    'zIndex': '9999',
    'justifyContent': 'center',
    'alignItems': 'center',
}

_MODAL_BOX = {
    'backgroundColor': '#ffffff',
    'borderRadius': '12px',
    'padding': '28px 32px',
    'width': '520px',
    'maxWidth': '95vw',
    'maxHeight': '90vh',
    'overflowY': 'auto',
    'boxShadow': '0 20px 60px rgba(0,0,0,0.3)',
    'position': 'relative',
}

_SCORE_COLOR = {
    'red': '#dc2626',
    'orange': '#ea580c',
    'green': '#16a34a',
}


def _score_color(score: int) -> str:
    if score >= 70:
        return _SCORE_COLOR['green']
    if score >= 40:
        return _SCORE_COLOR['orange']
    return _SCORE_COLOR['red']


def render_score_bar(score: int) -> dcc.Graph:
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[40], y=['score'],
        orientation='h',
        marker_color='#dc2626',
        showlegend=False,
        hoverinfo='skip',
        width=0.4,
    ))
    fig.add_trace(go.Bar(
        x=[30], y=['score'],
        orientation='h',
        base=40,
        marker_color='#ea580c',
        showlegend=False,
        hoverinfo='skip',
        width=0.4,
    ))
    fig.add_trace(go.Bar(
        x=[30], y=['score'],
        orientation='h',
        base=70,
        marker_color='#16a34a',
        showlegend=False,
        hoverinfo='skip',
        width=0.4,
    ))

    # Marker triangle indicating score position
    fig.add_annotation(
        x=score,
        y=0.7,
        text=f'<b>{score}</b>',
        showarrow=False,
        font={'size': 14, 'color': '#ffffff'},
        bgcolor=_score_color(score),
        bordercolor=_score_color(score),
        borderpad=6,
        borderwidth=0,
        yanchor='bottom',
        xanchor='center',
    )

    fig.update_layout(
        barmode='stack',
        height=90,
        margin={'t': 30, 'b': 10, 'l': 10, 'r': 10},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis={
            'range': [0, 100],
            'tickvals': [0, 40, 70, 100],
            'ticktext': ['0', '40', '70', '100'],
            'fixedrange': True,
        },
        yaxis={'visible': False, 'fixedrange': True},
    )

    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': False},
        style={'margin': '0'},
    )


def render_dimensions_table(dimensions: list, score: int = None) -> html.Table:
    _th_style = {
        'textAlign': 'left',
        'fontSize': '11px',
        'fontWeight': '600',
        'color': '#64748b',
        'letterSpacing': '0.08em',
        'textTransform': 'uppercase',
        'padding': '8px 12px',
        'borderBottom': '2px solid #e2e8f0',
    }
    _td_base = {
        'padding': '12px 12px',
        'borderBottom': '1px solid #f1f5f9',
        'fontSize': '14px',
        'color': '#0f172a',
        'verticalAlign': 'top',
    }

    def _pts_color(pts):
        return {'100': '#16a34a', '50': '#ea580c', '0': '#dc2626'}.get(str(pts), '#334155')

    def _dot(color):
        return html.Span('●', style={'color': color, 'fontSize': '10px', 'marginRight': '3px'})

    rows = []
    for dim in dimensions:
        threshold_badges = html.Span([
            html.Span([_dot(dim.colors[0]), dim.thresholds[0]], style={'marginRight': '8px', 'fontSize': '11px', 'color': '#475569'}),
            html.Span([_dot(dim.colors[1]), dim.thresholds[1]], style={'marginRight': '8px', 'fontSize': '11px', 'color': '#475569'}),
            html.Span([_dot(dim.colors[2]), dim.thresholds[2]], style={'fontSize': '11px', 'color': '#475569'}),
        ])
        name_cell = html.Td(
            html.Div([
                html.Div(f"{dim.icon} {dim.name}", style={'fontWeight': '600', 'marginBottom': '4px'}),
                threshold_badges,
            ]),
            style=_td_base,
        )
        value_cell = html.Td(
            dim.value_display,
            style={**_td_base, 'color': _pts_color(dim.points), 'fontWeight': '700', 'textAlign': 'right'},
        )
        pts_cell = html.Td(
            str(dim.points),
            style={**_td_base, 'color': _pts_color(dim.points), 'fontWeight': '700', 'textAlign': 'right'},
        )
        rows.append(html.Tr([name_cell, value_cell, pts_cell]))

    # Score total — usa valor pré-computado para garantir consistência com HealthScoreResult.score
    score_pts = score if score is not None else (int(round(sum(d.points for d in dimensions) / len(dimensions))) if dimensions else 0)
    rows.append(html.Tr([
        html.Td(
            html.Div('HEALTH SCORE', style={'fontWeight': '700', 'fontSize': '12px', 'letterSpacing': '0.06em', 'textTransform': 'uppercase', 'color': '#64748b'}),
            colSpan=2,
            style={**_td_base, 'borderTop': '2px solid #e2e8f0', 'borderBottom': 'none'},
        ),
        html.Td(
            str(score_pts),
            style={**_td_base, 'color': _pts_color(score_pts), 'fontWeight': '700', 'textAlign': 'right', 'borderTop': '2px solid #e2e8f0', 'borderBottom': 'none'},
        ),
    ]))

    return html.Table(
        [
            html.Thead(html.Tr([
                html.Th('DIMENSÃO', style=_th_style),
                html.Th('ATUAL', style={**_th_style, 'textAlign': 'right'}),
                html.Th('PONTOS', style={**_th_style, 'textAlign': 'right'}),
            ])),
            html.Tbody(rows),
        ],
        style={'width': '100%', 'borderCollapse': 'collapse'},
    )


def render_health_score_modal(result: HealthScoreResult) -> html.Div:
    description = html.Div(
        f"Saúde do fluxo nas últimas 4 semanas ({result.period_label}). "
        "Cada dimensão pontua ● 0, ● 50 ou ● 100. O Health Score é a média das 4 dimensões.",
        style={
            'fontSize': '13px',
            'color': '#475569',
            'backgroundColor': '#f8fafc',
            'border': '1px solid #e2e8f0',
            'borderRadius': '8px',
            'padding': '12px 14px',
            'margin': '16px 0',
            'lineHeight': '1.6',
        },
    )

    no_data_warning = html.Div(
        '⚠️ Dados insuficientes para algumas dimensões no período selecionado.',
        style={'fontSize': '12px', 'color': '#ea580c', 'marginBottom': '12px'},
    ) if not result.has_data or any(not d.has_data for d in result.dimensions) else html.Div()

    modal_box = html.Div(
        [
            html.Div([
                html.H3(
                    'Health Score',
                    style={'margin': '0', 'fontSize': '20px', 'fontWeight': '700', 'color': '#0f172a'},
                ),
                html.Button(
                    '×',
                    id='btn-close-health-score',
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'fontSize': '24px',
                        'cursor': 'pointer',
                        'color': '#64748b',
                        'padding': '0 4px',
                        'lineHeight': '1',
                    },
                ),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),

            render_score_bar(result.score),
            description,
            no_data_warning,
            render_dimensions_table(result.dimensions, result.score),
        ],
        style=_MODAL_BOX,
    )

    return html.Div(
        modal_box,
        id='health-score-overlay',
        style=_OVERLAY_HIDDEN,
    )
