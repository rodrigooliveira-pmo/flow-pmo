"""Performance metrics and CFD callbacks — RF-034/RF-035."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from dash.exceptions import PreventUpdate

from dashboards.components.error_boundary import callback_error_div, error_boundary
from dashboards.metrics.time_metrics import add_statistical_lines


def register_callbacks(app):
    from dashboard_full import (  # lazy: avoids circular import at module load time
        optional_input,
        create_cfd_summary_panel,
    )

    @app.callback(
        Output('performance-metric-chart', 'children'),
        Input('performance-table', 'active_cell'),
        Input('performance-table', 'data'),
        prevent_initial_call=True
    )
    @error_boundary(fallback=callback_error_div())
    def render_metric_chart(active_cell, table_data):
        if not active_cell or not table_data:
            return html.Div()

        row_idx = active_cell['row']
        row = table_data[row_idx]
        metric_name = row['Métrica']
        week_labels = [col for col in row.keys() if col != 'Métrica']

        if metric_name in ['% Demanda de Valor', '% Demanda de Falha']:
            row_valor = next((r for r in table_data if r.get('Métrica') == '% Demanda de Valor'), None)
            row_falha = next((r for r in table_data if r.get('Métrica') == '% Demanda de Falha'), None)

            if row_valor and row_falha:
                weeks_cmp, vals_valor, vals_falha = [], [], []
                for wl in week_labels:
                    raw_valor = str(row_valor.get(wl, '')).replace('%', '').replace(',', '.').strip()
                    raw_falha = str(row_falha.get(wl, '')).replace('%', '').replace(',', '.').strip()
                    try:
                        weeks_cmp.append(wl)
                        vals_valor.append(float(raw_valor))
                        vals_falha.append(float(raw_falha))
                    except (ValueError, TypeError):
                        continue

                if weeks_cmp:
                    fig_cmp = go.Figure()
                    fig_cmp.add_trace(go.Bar(x=weeks_cmp, y=vals_valor, name='Demanda de Valor', marker_color='green', opacity=0.85))
                    fig_cmp.add_trace(go.Bar(x=weeks_cmp, y=vals_falha, name='Demanda de Falha', marker_color='red', opacity=0.85))
                    fig_cmp.update_layout(
                        title='Demanda de Falha x Demanda de Valor',
                        xaxis_title='Semana',
                        yaxis_title='Percentual (%)',
                        template='plotly_white',
                        height=550,
                        margin=dict(t=60, b=130),
                        xaxis_tickangle=-45,
                        barmode='overlay',
                        legend_title_text='Valores'
                    )
                    return html.Div([dcc.Graph(figure=fig_cmp)], style={'marginTop': '20px'})

        def _parse_metric_numeric_value(raw_value, metric):
            txt = str(raw_value or '').strip().lower().replace(',', '.')
            if not txt or txt in {'—', '-', 'nan', 'none'}:
                return None
            if metric == 'Cadência sugerida (λ Weibull, dias)' and '|' in txt:
                txt = txt.split('|', 1)[0].strip()
            if metric == 'Lead time para mudanças':
                if txt.endswith('h'):
                    try:
                        return float(txt[:-1].strip()) / 24.0
                    except (ValueError, TypeError):
                        return None
                if txt.endswith('d'):
                    try:
                        return float(txt[:-1].strip())
                    except (ValueError, TypeError):
                        return None
            txt = txt.replace('%', '').strip()
            try:
                return float(txt)
            except (ValueError, TypeError):
                return None

        values = [_parse_metric_numeric_value(row.get(wl), metric_name) for wl in week_labels]
        valid = [(w, v) for w, v in zip(week_labels, values) if v is not None]
        if not valid:
            return html.Div(
                f'A métrica "{metric_name}" não possui dados numéricos para exibir.',
                style={'textAlign': 'center', 'padding': '20px', 'color': '#999'}
            )

        weeks_valid, vals_valid = zip(*valid)
        weeks_valid = list(weeks_valid)
        vals_valid = list(vals_valid)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weeks_valid, y=vals_valid,
            mode='lines+markers', name=metric_name,
            line=dict(width=2.5, color='#0074D9'),
            marker=dict(size=8)
        ))

        s = pd.Series(vals_valid)
        if len(s) >= 2:
            add_statistical_lines(fig, weeks_valid, s)

        yaxis_title = metric_name
        if metric_name == 'Lead time para mudanças':
            yaxis_title = 'Lead time para mudanças (dias)'
        elif metric_name == 'Cadência sugerida (λ Weibull, dias)':
            yaxis_title = 'Cadência sugerida (λ Weibull, dias)'

        fig.update_layout(
            title=f'{metric_name} — Tendência Semanal',
            xaxis_title='Semana',
            yaxis_title=yaxis_title,
            template='plotly_white',
            height=550,
            margin=dict(t=60, b=130),
            xaxis_tickangle=-45,
        )
        return html.Div([dcc.Graph(figure=fig)], style={'marginTop': '20px'})

    @app.callback(
        Output('cfd-summary-panel', 'children'),
        optional_input('cfd-graph', 'clickData'),
        optional_input('cfd-graph', 'hoverData'),
        Input('cfd-summary-store', 'data'),
    )
    @error_boundary(fallback=callback_error_div())
    def update_cfd_summary_panel(click_data, hover_data, summary_payload):
        if not summary_payload:
            raise PreventUpdate

        selected_date = None
        source = click_data or hover_data
        try:
            points = (source or {}).get('points') or []
            if points:
                selected_date = points[0].get('x')
        except Exception:
            selected_date = None

        return create_cfd_summary_panel(summary_payload, selected_date=selected_date)
