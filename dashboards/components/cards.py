import dash
try:
    from dash import dcc, html, Input, Output, State, dash_table
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State
    import dash_table


def create_kpi_card(title, value, class_name='six columns', card_style=None, title_style=None, value_style=None):
    base_card_style = {'padding': '10px', 'borderRadius': '6px'}
    if isinstance(card_style, dict):
        base_card_style.update(card_style)
    base_title_style = {'textAlign': 'center'}
    if isinstance(title_style, dict):
        base_title_style.update(title_style)
    base_value_style = {'textAlign': 'center'}
    if isinstance(value_style, dict):
        base_value_style.update(value_style)
    return html.Div([
        html.H4(title, style=base_title_style),
        html.H2(value, style=base_value_style)
    ], className=class_name, style=base_card_style)


def _portfolio_metric_card(title, value):
    return create_kpi_card(
        title,
        value,
        class_name='',
        card_style={
            'padding': '14px 16px',
            'borderRadius': '10px',
            'backgroundColor': '#f8fafc',
            'border': '1px solid #e2e8f0',
            'minHeight': '136px',
            'display': 'flex',
            'flexDirection': 'column',
            'justifyContent': 'space-between',
        },
        title_style={
            'textAlign': 'left',
            'fontSize': '15px',
            'lineHeight': '1.25',
            'margin': '0',
            'fontWeight': '600',
            'color': '#334155',
        },
        value_style={
            'textAlign': 'left',
            'fontSize': '26px',
            'lineHeight': '1.15',
            'margin': '8px 0 0 0',
            'fontWeight': '700',
            'color': '#0f172a',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
        },
    )