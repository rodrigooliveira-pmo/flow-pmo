import dash
try:
    from dash import dcc, html, dash_table
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    import dash_table

import plotly.graph_objects as go
import pandas as pd
from dashboards.metrics.corporativo_metrics import (
    calc_lead_time_features,
    calc_execucao_onepage,
    calc_change_failure_rate
)

def layout_corporativo(df, df_portfolio, start_ts, end_ts, projeto, periodicity='M', group_by_product=False, feature_types=None):
    if isinstance(group_by_product, str):
        group_by_product = group_by_product == 'True'
        
    if feature_types is None:
        feature_types = ['Feature']
        
    if not isinstance(feature_types, list):
        feature_types = [feature_types]
        
    start_ts = pd.to_datetime(start_ts)
    end_ts = pd.to_datetime(end_ts)

    # Controles locais da aba
    controls = html.Div([
        html.Div([
            html.Label('Periodicidade', style={'fontWeight': '600', 'fontSize': '12px'}),
            dcc.Dropdown(
                id='corp-periodicity',
                options=[
                    {'label': 'Semanal', 'value': 'W'},
                    {'label': 'Mensal', 'value': 'M'},
                    {'label': 'Trimestral (Quarter)', 'value': 'Q'}
                ],
                value=periodicity,
                clearable=False,
                style={'width': '100%'}
            )
        ], style={'flex': '1', 'minWidth': '150px'}),
        
        html.Div([
            html.Label('Quebra por Produto', style={'fontWeight': '600', 'fontSize': '12px'}),
            dcc.RadioItems(
                id='corp-groupby-product',
                options=[
                    {'label': ' Tudo Agrupado', 'value': 'False'},
                    {'label': ' Por Produto', 'value': 'True'}
                ],
                value=str(group_by_product),
                labelStyle={'display': 'inline-block', 'marginRight': '10px'}
            )
        ], style={'flex': '1', 'minWidth': '200px'}),
        
        html.Div([
            html.Label('Tipos de Item', style={'fontWeight': '600', 'fontSize': '12px'}),
            dcc.Dropdown(
                id='corp-feature-types',
                options=[
                    {'label': 'Épicos', 'value': 'Epic'},
                    {'label': 'Features', 'value': 'Feature'},
                    {'label': 'Histórias', 'value': 'Story'}
                ],
                value=feature_types,
                multi=True,
                style={'width': '100%'}
            )
        ], style={'flex': '2', 'minWidth': '250px'}),
    ], style={
        'display': 'flex', 'gap': '20px', 'backgroundColor': 'white', 
        'padding': '16px', 'borderRadius': '10px', 'marginBottom': '20px',
        'border': '1px solid #e2e8f0', 'flexWrap': 'wrap', 'alignItems': 'flex-end'
    })

    # Calculations
    lt_global, lt_prod = calc_lead_time_features(df, df_portfolio, start_ts, end_ts, periodicity, group_by_product, feature_types)
    op_global, op_prod = calc_execucao_onepage(df, df_portfolio, start_ts, end_ts, periodicity, group_by_product, feature_types)
    cfr_global, cfr_prod = calc_change_failure_rate(df, start_ts, end_ts, periodicity, group_by_product)

    def _create_bar_chart(df_data, x_col, y_col, color_col, title, y_title, barmode='group'):
        fig = go.Figure()
        if df_data.empty:
            return fig
            
        if color_col and color_col in df_data.columns and df_data[color_col].nunique() > 1:
            for color_val in df_data[color_col].unique():
                df_sub = df_data[df_data[color_col] == color_val]
                fig.add_trace(go.Bar(
                    x=df_sub[x_col].astype(str),
                    y=df_sub[y_col],
                    name=str(color_val),
                    text=df_sub[y_col].round(1) if y_col != 'Percentual' else df_sub[y_col].round(1).astype(str) + '%',
                    textposition='outside'
                ))
            fig.update_layout(barmode=barmode)
        else:
            fig.add_trace(go.Bar(
                x=df_data[x_col].astype(str),
                y=df_data[y_col],
                marker_color='#2F80ED',
                text=df_data[y_col].round(1) if y_col != 'Percentual' else df_data[y_col].round(1).astype(str) + '%',
                textposition='outside'
            ))
            
        fig.update_layout(
            title=title,
            template='plotly_white',
            margin=dict(t=50, b=50, l=50, r=20),
            xaxis=dict(tickangle=-45),
            yaxis=dict(title=y_title, rangemode='nonnegative'),
            height=350,
            legend=dict(orientation='h', y=-0.2)
        )
        return fig

    # --- Matrix Table Construction ---
    periods = set()
    if not lt_global.empty: periods.update(lt_global['DataDone'].unique())
    if not op_global.empty: periods.update(op_global['DataRef'].unique())
    if not cfr_global.empty: periods.update(cfr_global['DataDone'].unique())
    
    periods = sorted(list(periods))
    
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}

    def format_period(p, freq):
        ts = pd.to_datetime(p)
        if freq == 'W':
            return f"{ts.strftime('%d/%m/%y')}"
        elif freq == 'Q':
            return f"Q{ts.quarter}/{ts.strftime('%y')}"
        else:
            return f"{meses_pt[ts.month]}/{ts.strftime('%y')}"

    table_cols = [{'name': "KPI's", 'id': 'KPI'}]
    for p in periods:
        table_cols.append({'name': format_period(p, periodicity), 'id': str(p)})

    def get_val(df, date_col, val_col, p, is_pct=False):
        if df.empty: return '-'
        row = df[df[date_col] == p]
        if row.empty: return '-'
        val = row.iloc[0][val_col]
        if pd.isna(val): return '-'
        if is_pct:
            return f"{val:.2f}%".replace('.', ',')
        return f"{val:.2f}".replace('.', ',')

    table_data = [
        {
            'KPI': '% Conclusão Projetos OnePage',
            **{str(p): get_val(op_global, 'DataRef', 'Percentual', p, is_pct=True) for p in periods}
        },
        {
            'KPI': 'Lead Time Entregas New Features',
            **{str(p): get_val(lt_global, 'DataDone', 'Media', p, is_pct=False) for p in periods}
        },
        {
            'KPI': 'Change Failure Rate (reForward)',
            **{str(p): get_val(cfr_global, 'DataDone', 'CFR', p, is_pct=True) for p in periods}
        }
    ]

    matrix_table = dash_table.DataTable(
        columns=table_cols,
        data=table_data,
        style_cell={'textAlign': 'center', 'padding': '12px', 'fontFamily': 'inherit', 'fontSize': '14px'},
        style_cell_conditional=[
            {'if': {'column_id': 'KPI'}, 'textAlign': 'left', 'fontWeight': 'bold', 'color': '#1e3a5f', 'width': '30%'}
        ],
        style_header={'backgroundColor': '#f8fafc', 'color': '#1e3a5f', 'fontWeight': 'bold', 'borderBottom': '2px solid #cbd5e1'},
        style_data={'borderBottom': '1px solid #e2e8f0'},
    )

    table_section = html.Div([
        html.H4('Resumo Executivo (Matriz)', style={'color': '#1e3a5f', 'marginBottom': '16px'}),
        matrix_table
    ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px', 'border': '1px solid #e2e8f0', 'overflowX': 'auto'})

    # --- Charts Construction ---
    lt_data = lt_prod if group_by_product and not lt_prod.empty else lt_global
    lt_fig = _create_bar_chart(lt_data, 'DataDone', 'Media', 'Produto', 'Lead Time (Média) por Período', 'Dias (Média)')
    
    op_data = op_prod if group_by_product and not op_prod.empty else op_global
    op_fig = _create_bar_chart(op_data, 'DataRef', 'Percentual', 'Produto', 'Conclusão Projetos OnePage (%)', '% Concluído')
    op_fig_abs = _create_bar_chart(op_data, 'DataRef', 'Entregues', 'Produto', 'Entregas Absolutas OnePage', 'Qtd Features')
    
    cfr_data = cfr_prod if group_by_product and not cfr_prod.empty else cfr_global
    cfr_fig = _create_bar_chart(cfr_data, 'DataDone', 'CFR', 'Produto', 'Change Failure Rate (%)', 'CFR (%)')
    cfr_fig_abs = _create_bar_chart(cfr_data, 'DataDone', 'Falhas', 'Produto', 'Vazão de Bugs (Absoluto)', 'Qtd Falhas')

    charts_section = html.Div([
        html.H4('Detalhamento e Evolução', style={'color': '#1e3a5f', 'marginBottom': '16px'}),
        html.Div([
            html.Div(dcc.Graph(figure=lt_fig, config={'displayModeBar': False}) if not lt_data.empty else html.P('Sem dados.', style={'color': '#aaa'}), style={'flex': '1', 'minWidth': '300px', 'marginBottom': '20px'}),
            html.Div(dcc.Graph(figure=op_fig, config={'displayModeBar': False}) if not op_data.empty else html.P('Sem dados.', style={'color': '#aaa'}), style={'flex': '1', 'minWidth': '300px', 'marginBottom': '20px'}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px'}),
        html.Div([
            html.Div(dcc.Graph(figure=cfr_fig, config={'displayModeBar': False}) if not cfr_data.empty else html.P('Sem dados.', style={'color': '#aaa'}), style={'flex': '1', 'minWidth': '300px', 'marginBottom': '20px'}),
            html.Div(dcc.Graph(figure=cfr_fig_abs, config={'displayModeBar': False}) if not cfr_data.empty else html.P('Sem dados.', style={'color': '#aaa'}), style={'flex': '1', 'minWidth': '300px', 'marginBottom': '20px'}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px'}),
    ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px', 'border': '1px solid #e2e8f0'})

    return html.Div([
        html.Div([
            html.H3('Indicadores Corporativos', style={'fontSize': '20px', 'fontWeight': '800', 'color': '#0f172a', 'marginBottom': '4px'}),
            html.P(f"Projeto: {projeto or 'Todos'} | Período: {start_ts.strftime('%d/%m/%Y')} a {end_ts.strftime('%d/%m/%Y')}", style={'fontSize': '12px', 'color': '#64748b', 'margin': '0'}),
        ], style={'padding': '20px 20px 12px', 'borderBottom': '2px solid #dbeafe', 'marginBottom': '20px'}),
        
        controls,
        table_section,
        charts_section
    ], style={'padding': '20px', 'backgroundColor': '#f4f6f8', 'minHeight': '100vh'})
