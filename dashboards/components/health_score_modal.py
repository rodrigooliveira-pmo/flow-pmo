import plotly.graph_objects as go

try:
    from dash import dcc, html
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html

# kept for backward compat with callback in dashboard_full.py (no longer used)
_OVERLAY_HIDDEN = {'display': 'none'}
_OVERLAY_VISIBLE = {'display': 'none'}

_PANEL_STYLE = {
    'backgroundColor': '#ffffff',
    'borderRadius': '12px',
    'padding': '20px 24px',
    'border': '1px solid #e2e8f0',
    'marginBottom': '24px',
}

_SCORE_THRESHOLDS = [(70, '#16a34a'), (40, '#ea580c'), (0, '#dc2626')]


def _score_color(score: int) -> str:
    for threshold, color in _SCORE_THRESHOLDS:
        if score >= threshold:
            return color
    return '#dc2626'


def _pts_color(pts: int) -> str:
    return {'100': '#16a34a', '50': '#ea580c', '0': '#dc2626'}.get(str(pts), '#334155')


def _score_badge(score: int, size: str = 'md') -> html.Span:
    font_sizes = {'sm': '12px', 'md': '14px', 'lg': '22px'}
    paddings = {'sm': '1px 7px', 'md': '2px 10px', 'lg': '4px 14px'}
    return html.Span(
        str(score),
        style={
            'backgroundColor': _score_color(score),
            'color': '#fff',
            'borderRadius': '999px',
            'padding': paddings[size],
            'fontWeight': '700',
            'fontSize': font_sizes[size],
            'display': 'inline-block',
            'lineHeight': '1.4',
        },
    )


def render_score_bar(score: int) -> dcc.Graph:
    fig = go.Figure()
    for x, base, color in [(40, 0, '#dc2626'), (30, 40, '#ea580c'), (30, 70, '#16a34a')]:
        fig.add_trace(go.Bar(
            x=[x], y=['score'], orientation='h', base=base,
            marker_color=color, showlegend=False, hoverinfo='skip', width=0.4,
        ))

    fig.add_annotation(
        x=score, y=0.7,
        text=f'<b>{score}</b>',
        showarrow=False,
        font={'size': 14, 'color': '#ffffff'},
        bgcolor=_score_color(score),
        bordercolor=_score_color(score),
        borderpad=6, borderwidth=0,
        yanchor='bottom', xanchor='center',
    )
    fig.update_layout(
        barmode='stack', height=80,
        margin={'t': 28, 'b': 4, 'l': 4, 'r': 4},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis={'range': [0, 100], 'tickvals': [0, 40, 70, 100], 'fixedrange': True},
        yaxis={'visible': False, 'fixedrange': True},
    )
    return dcc.Graph(figure=fig, config={'displayModeBar': False}, style={'margin': '0'})


def _dot(color: str) -> html.Span:
    return html.Span('●', style={'color': color, 'fontSize': '10px', 'marginRight': '3px'})


def _dimension_header_cell(dim, td_base: dict) -> html.Td:
    badges = html.Span([
        html.Span([_dot(dim.colors[i]), dim.thresholds[i]],
                  style={'marginRight': '6px', 'fontSize': '11px', 'color': '#64748b'})
        for i in range(3)
    ])
    return html.Td(
        html.Div([
            html.Div(f"{dim.icon} {dim.name}", style={'fontWeight': '600', 'marginBottom': '3px'}),
            badges,
        ]),
        style=td_base,
    )


def _render_single_table(dimensions: list, score: int) -> html.Table:
    th = {
        'textAlign': 'left', 'fontSize': '11px', 'fontWeight': '600',
        'color': '#64748b', 'letterSpacing': '0.07em', 'textTransform': 'uppercase',
        'padding': '8px 12px', 'borderBottom': '2px solid #e2e8f0',
    }
    td = {
        'padding': '10px 12px', 'borderBottom': '1px solid #f1f5f9',
        'fontSize': '14px', 'color': '#0f172a', 'verticalAlign': 'top',
    }

    rows = []
    for dim in dimensions:
        rows.append(html.Tr([
            _dimension_header_cell(dim, td),
            html.Td(dim.value_display, style={**td, 'color': _pts_color(dim.points), 'fontWeight': '700', 'textAlign': 'right'}),
            html.Td(str(dim.points), style={**td, 'color': _pts_color(dim.points), 'fontWeight': '700', 'textAlign': 'right'}),
        ]))

    rows.append(html.Tr([
        html.Td(
            html.Div('HEALTH SCORE', style={'fontWeight': '700', 'fontSize': '12px', 'letterSpacing': '0.06em', 'textTransform': 'uppercase', 'color': '#64748b'}),
            colSpan=2,
            style={**td, 'borderTop': '2px solid #e2e8f0', 'borderBottom': 'none'},
        ),
        html.Td(str(score), style={**td, 'color': _pts_color(score), 'fontWeight': '700', 'textAlign': 'right', 'borderTop': '2px solid #e2e8f0', 'borderBottom': 'none'}),
    ]))

    return html.Table(
        [
            html.Thead(html.Tr([
                html.Th('DIMENSÃO', style=th),
                html.Th('ATUAL', style={**th, 'textAlign': 'right'}),
                html.Th('PONTOS', style={**th, 'textAlign': 'right'}),
            ])),
            html.Tbody(rows),
        ],
        style={'width': '100%', 'borderCollapse': 'collapse'},
    )


def _render_monthly_table(overall, monthly: list) -> html.Table:
    th_base = {
        'textAlign': 'center', 'fontSize': '11px', 'fontWeight': '600',
        'color': '#64748b', 'letterSpacing': '0.07em', 'textTransform': 'uppercase',
        'padding': '8px 10px', 'borderBottom': '2px solid #e2e8f0',
        'whiteSpace': 'nowrap',
    }
    td_dim = {
        'padding': '10px 12px', 'borderBottom': '1px solid #f1f5f9',
        'fontSize': '13px', 'color': '#0f172a', 'verticalAlign': 'middle',
    }
    td_val = {
        'padding': '10px 8px', 'borderBottom': '1px solid #f1f5f9',
        'fontSize': '13px', 'textAlign': 'center', 'verticalAlign': 'middle',
    }

    def month_cell(dim_idx, result):
        dim = result.dimensions[dim_idx]
        return html.Td(
            html.Div([
                html.Div(dim.value_display, style={'fontWeight': '700', 'color': _pts_color(dim.points), 'fontSize': '13px'}),
                html.Div(f"{dim.points}pts", style={'fontSize': '10px', 'color': _pts_color(dim.points), 'marginTop': '2px'}),
            ]),
            style=td_val,
        )

    def overall_cell(dim_idx):
        dim = overall.dimensions[dim_idx]
        return html.Td(
            html.Div([
                html.Div(dim.value_display, style={'fontWeight': '700', 'color': _pts_color(dim.points), 'fontSize': '13px'}),
                html.Div(f"{dim.points}pts", style={'fontSize': '10px', 'color': _pts_color(dim.points), 'marginTop': '2px'}),
            ]),
            style={**td_val, 'backgroundColor': '#f8fafc', 'borderLeft': '2px solid #e2e8f0'},
        )

    headers = [html.Th('DIMENSÃO', style={**th_base, 'textAlign': 'left'})]
    for m in monthly:
        headers.append(html.Th(m.period_label, style=th_base))
    headers.append(html.Th('GERAL', style={**th_base, 'backgroundColor': '#f8fafc', 'borderLeft': '2px solid #e2e8f0'}))

    dim_count = len(overall.dimensions)
    rows = []
    for i in range(dim_count):
        dim_ref = overall.dimensions[i]
        badges = html.Span([
            html.Span([_dot(dim_ref.colors[j]), dim_ref.thresholds[j]],
                      style={'marginRight': '5px', 'fontSize': '10px', 'color': '#94a3b8'})
            for j in range(3)
        ])
        name_td = html.Td(
            html.Div([
                html.Div(f"{dim_ref.icon} {dim_ref.name}", style={'fontWeight': '600', 'fontSize': '13px', 'marginBottom': '2px'}),
                badges,
            ]),
            style=td_dim,
        )
        month_tds = [month_cell(i, m) for m in monthly]
        rows.append(html.Tr([name_td] + month_tds + [overall_cell(i)]))

    # Score row
    score_td = [html.Td(
        html.Div('HEALTH SCORE', style={'fontWeight': '700', 'fontSize': '11px', 'letterSpacing': '0.06em', 'textTransform': 'uppercase', 'color': '#64748b'}),
        style={**td_dim, 'borderTop': '2px solid #e2e8f0', 'borderBottom': 'none'},
    )]
    for m in monthly:
        score_td.append(html.Td(_score_badge(m.score, 'sm'), style={**td_val, 'borderTop': '2px solid #e2e8f0', 'borderBottom': 'none'}))
    score_td.append(html.Td(
        _score_badge(overall.score, 'sm'),
        style={**td_val, 'borderTop': '2px solid #e2e8f0', 'borderBottom': 'none', 'backgroundColor': '#f8fafc', 'borderLeft': '2px solid #e2e8f0'},
    ))
    rows.append(html.Tr(score_td))

    return html.Table(
        [html.Thead(html.Tr(headers)), html.Tbody(rows)],
        style={'width': '100%', 'borderCollapse': 'collapse'},
    )


def render_health_score_panel(overall, monthly: list = None) -> html.Div:
    """Render the Health Score inline panel.

    Args:
        overall: HealthScoreResult for the full period.
        monthly: list of HealthScoreResult per calendar month, or None for single-period view.
    """
    is_multi = monthly is not None and len(monthly) > 1

    header = html.Div([
        html.Div([
            html.Span('Health Score do Fluxo', style={
                'fontWeight': '700', 'fontSize': '16px', 'color': '#0f172a',
            }),
            html.Span(overall.period_label, style={
                'fontSize': '12px', 'color': '#64748b', 'marginLeft': '10px',
            }),
        ]),
        _score_badge(overall.score, 'lg'),
    ], style={
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'marginBottom': '12px',
    })

    description = html.Div(
        f"Saúde do fluxo no período selecionado ({overall.period_label}). "
        "Cada dimensão pontua ● 0, ● 50 ou ● 100. O Health Score é a média das dimensões com dados disponíveis. "
        "Sustentabilidade requer ao menos dois períodos para ser calculada.",
        style={
            'fontSize': '12px', 'color': '#475569',
            'backgroundColor': '#f8fafc', 'border': '1px solid #e2e8f0',
            'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '14px',
            'lineHeight': '1.5',
        },
    )

    no_data = html.Div(
        '⚠️ Dados insuficientes para algumas dimensões no período.',
        style={'fontSize': '12px', 'color': '#ea580c', 'marginBottom': '10px'},
    ) if not overall.has_data or any(not d.has_data for d in overall.dimensions) else html.Div()

    if is_multi:
        score_bar = render_score_bar(overall.score)
        table = _render_monthly_table(overall, monthly)
        table_wrapper = html.Div(table, style={'overflowX': 'auto'})
        content = [header, score_bar, description, no_data, table_wrapper]
    else:
        score_bar = render_score_bar(overall.score)
        table = _render_single_table(overall.dimensions, overall.score)
        content = [header, score_bar, description, no_data, table]

    return html.Div(content, style=_PANEL_STYLE)


# Legacy alias kept so existing import in dashboard_full.py doesn't break
def render_health_score_modal(result) -> html.Div:
    return render_health_score_panel(result)
