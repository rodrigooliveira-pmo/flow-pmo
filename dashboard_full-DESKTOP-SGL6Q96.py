import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import pandas as pd
import os
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Config ---
DATA_FOLDER = r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
model_files = [os.path.join(DATA_FOLDER, f) for f in os.listdir(DATA_FOLDER) if f.startswith('PowerBI_Model_') and f.endswith('.xlsx')]
if not model_files:
    raise FileNotFoundError('PowerBI model file not found in DATA_FOLDER')
MODEL_FILE = max(model_files, key=os.path.getctime)

# Load model
xls = pd.ExcelFile(MODEL_FILE)
dim_projeto = pd.read_excel(xls, sheet_name='Dim_Projeto')
dim_tipo = pd.read_excel(xls, sheet_name='Dim_Tipo')

def safe_read_sheet(excel_file, sheet_name, default_cols):
    if sheet_name in excel_file.sheet_names:
        return pd.read_excel(excel_file, sheet_name=sheet_name)
    return pd.DataFrame(columns=default_cols)

dim_responsavel = safe_read_sheet(xls, 'Dim_Responsavel', ['ResponsavelID', 'Responsavel'])
dim_prioridade = safe_read_sheet(xls, 'Dim_Prioridade', ['PrioridadeID', 'Prioridade'])
dim_componente = safe_read_sheet(xls, 'Dim_Componente', ['ComponenteID', 'Componente'])

fato = pd.read_excel(xls, sheet_name='Fato_Items')

# Normalize date columns
for dcol in ['DataBacklog', 'DataInProgress', 'DataDone']:
    if dcol in fato.columns:
        fato[dcol] = pd.to_datetime(fato[dcol], errors='coerce')

# Merge readable names
fato = fato.merge(dim_projeto, how='left', left_on='ProjetoID', right_on='ProjetoID')
fato = fato.merge(dim_tipo, how='left', left_on='TipoID', right_on='TipoID')
if not dim_responsavel.empty:
    fato = fato.merge(dim_responsavel, how='left', left_on='ResponsavelID', right_on='ResponsavelID')
if not dim_prioridade.empty:
    fato = fato.merge(dim_prioridade, how='left', left_on='PrioridadeID', right_on='PrioridadeID')
if not dim_componente.empty:
    fato = fato.merge(dim_componente, how='left', left_on='ComponenteID', right_on='ComponenteID')

# Friendly column names
rename_map = {'NomeProjeto': 'Projeto', 'Tipo': 'Tipo', 'Responsavel': 'Responsavel', 'Prioridade': 'Prioridade', 'Componente': 'Componente'}
fato.rename(columns={k: v for k, v in rename_map.items() if k in fato.columns}, inplace=True)

# App
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'], suppress_callback_exceptions=True)
app.title = 'Dashboard de Métricas (Full)'

def create_kpi_card(title, value, class_name='six columns'):
    return html.Div([
        html.H4(title, style={'textAlign': 'center'}),
        html.H2(value, style={'textAlign': 'center'})
    ], className=class_name)

def unique_sorted(col):
    return sorted([x for x in col.dropna().unique()])

min_date = fato['DataDone'].min() if 'DataDone' in fato.columns else pd.to_datetime('2023-01-01')
max_date = fato['DataDone'].max() if 'DataDone' in fato.columns else pd.to_datetime('today')

app.layout = html.Div([
    html.H1('Dashboard de Métricas - Full', style={'textAlign': 'center'}),
    html.Div([
        html.Div([html.Label('Período:'), dcc.DatePickerRange(id='date-range', start_date=min_date, end_date=max_date,
                                                            display_format='YYYY-MM-DD')], style={'display':'inline-block', 'marginRight':'20px'}),
        html.Div([html.Label('Projeto:'), dcc.Dropdown(id='filter-projeto', options=[{'label':p,'value':p} for p in unique_sorted(fato['Projeto'])], value=unique_sorted(fato['Projeto'])[0] if len(unique_sorted(fato['Projeto']))>0 else None, clearable=False)], style={'width':'20%', 'display':'inline-block'}),
        html.Div([html.Label('Tipo:'), dcc.Dropdown(id='filter-tipo', options=[{'label':t,'value':t} for t in unique_sorted(fato['Tipo'])], value=None, clearable=True)], style={'width':'15%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([html.Label('Responsável:'), dcc.Dropdown(id='filter-responsavel', options=[{'label':r,'value':r} for r in unique_sorted(fato['Responsavel'])], value=None, clearable=True)], style={'width':'20%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([html.Label('Componente:'), dcc.Dropdown(id='filter-componente', options=[{'label':c,'value':c} for c in unique_sorted(fato.get('Componente', pd.Series(dtype='str')))], value=None, clearable=True)], style={'width':'20%', 'display':'inline-block', 'marginLeft':'20px'})
    ], style={'display':'flex', 'justifyContent':'center', 'gap':'10px', 'marginBottom':'20px'}),

    dcc.Tabs(id='tabs', value='tab-dashboard', children=[
        dcc.Tab(label='Dashboard', value='tab-dashboard'),
        dcc.Tab(label='Adv - Fluxo', value='tab-fluxo'),
        dcc.Tab(label='Adv - Estabilidade', value='tab-estabilidade'),
        dcc.Tab(label='Adv - Saúde Fluxo', value='tab-saude'),
        dcc.Tab(label='Adv - Qualidade', value='tab-qualidade'),
        dcc.Tab(label='Análise Dimensional', value='tab-dim'),
        dcc.Tab(label='Análise Tipos', value='tab-tipos'),
        dcc.Tab(label='Tendências', value='tab-tendencias'),
        dcc.Tab(label='Throughput por Tipo', value='tab-throughput-tipo'),
        dcc.Tab(label='Análise Eficiência', value='tab-eficiencia'),
        dcc.Tab(label='WIP por Pessoa', value='tab-wip')
    ]),

    html.Div(id='tab-content')
])

def filter_df(df, start_date, end_date, projeto, tipo, responsavel, componente):
    d = df.copy()
    if start_date:
        d = d[d['DataDone'] >= pd.to_datetime(start_date)]
    if end_date:
        d = d[d['DataDone'] <= pd.to_datetime(end_date)]
    if projeto:
        d = d[d['Projeto'] == projeto]
    if tipo:
        d = d[d['Tipo'] == tipo]
    if responsavel:
        d = d[d['Responsavel'] == responsavel]
    if componente and 'Componente' in d.columns:
        d = d[d['Componente'] == componente]
    return d

@app.callback(Output('tab-content', 'children'), Input('tabs', 'value'), Input('date-range', 'start_date'), Input('date-range', 'end_date'), Input('filter-projeto', 'value'), Input('filter-tipo', 'value'), Input('filter-responsavel', 'value'), Input('filter-componente', 'value'))
def render_tab(tab, start_date, end_date, projeto, tipo, responsavel, componente):
    df = filter_df(fato, start_date, end_date, projeto, tipo, responsavel, componente)

    # Padrão de cores para os tipos de demanda
    color_map = {
        'Desenvolvimento': 'green', # Demanda de Valor
        'Defeitos': 'red',         # Demanda de Falha
        'Outro': 'lightgray'       # Outros tipos
    }

    if tab == 'tab-dashboard':
        # Para o detalhamento, precisamos de uma base que ignore o filtro de 'tipo'
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_base_breakdown = fato.copy()
        if projeto: df_base_breakdown = df_base_breakdown[df_base_breakdown['Projeto'] == projeto]
        if responsavel: df_base_breakdown = df_base_breakdown[df_base_breakdown['Responsavel'] == responsavel]
        if componente and 'Componente' in df_base_breakdown.columns: df_base_breakdown = df_base_breakdown[df_base_breakdown['Componente'] == componente]

        metrics_data = []
        categories = ['Desenvolvimento', 'Defeitos', 'Outro']

        for cat in categories:
            # Itens concluídos na categoria e período
            df_completed_cat = df_base_breakdown[
                (df_base_breakdown['Tipo'] == cat) &
                (df_base_breakdown['DataDone'] >= start_date_ts) &
                (df_base_breakdown['DataDone'] <= end_date_ts)
            ]
            # Itens que chegaram na categoria e período
            df_arrived_cat = df_base_breakdown[
                (df_base_breakdown['Tipo'] == cat) &
                (df_base_breakdown['DataInProgress'] >= start_date_ts) &
                (df_base_breakdown['DataInProgress'] <= end_date_ts)
            ]
            # Itens em WIP no final do período para a categoria
            df_wip_cat = df_base_breakdown[
                (df_base_breakdown['Tipo'] == cat) &
                (df_base_breakdown['DataInProgress'] <= end_date_ts) &
                ((df_base_breakdown['DataDone'] > end_date_ts) | pd.isna(df_base_breakdown['DataDone']))
            ]

            throughput = len(df_completed_cat)
            arrivals = len(df_arrived_cat)
            wip = len(df_wip_cat)
            wip_age = (end_date_ts - df_wip_cat['DataInProgress']).dt.days.mean() if wip > 0 else 0
            
            lead_time = df_completed_cat['LeadTime_Dias'].mean() if throughput > 0 else 0
            p85_lt = df_completed_cat['LeadTime_Dias'].quantile(0.85) if throughput > 0 else 0
            eff_simple = df_completed_cat['Eficiencia'].mean() if throughput > 0 else 0
            eff_ajustada = df_completed_cat['EficienciaAjustada'].mean() if throughput > 0 else 0

            metrics_data.append({
                'Tipo de Demanda': cat,
                'Taxa Chegada': arrivals,
                'Throughput': throughput,
                'WIP': wip,
                'WIP Age': f"{wip_age:.1f}",
                'Lead Time': f"{lead_time:.1f}",
                'P85 Lead Time': f"{p85_lt:.1f}",
                'Eficiência Simples': f"{eff_simple:.2f}",
                'Eficiência Ajustada': f"{eff_ajustada:.2f}",
            })

        total_throughput_for_pct = sum(item['Throughput'] for item in metrics_data)
        throughput_defeitos = next((item['Throughput'] for item in metrics_data if item['Tipo de Demanda'] == 'Defeitos'), 0)
        throughput_desenvolvimento = next((item['Throughput'] for item in metrics_data if item['Tipo de Demanda'] == 'Desenvolvimento'), 0)

        pct_demanda_falha = (throughput_defeitos / total_throughput_for_pct * 100) if total_throughput_for_pct > 0 else 0
        pct_demanda_valor = (throughput_desenvolvimento / total_throughput_for_pct * 100) if total_throughput_for_pct > 0 else 0

        # O gráfico de throughput deve sempre mostrar o breakdown, ignorando o filtro de 'tipo'
        df_throughput_chart_data = df_base_breakdown[
            (df_base_breakdown['DataDone'] >= start_date_ts) &
            (df_base_breakdown['DataDone'] <= end_date_ts)
        ]
        fig_throughput = px.histogram(df_throughput_chart_data,
                                      x=df_throughput_chart_data['DataDone'].dt.to_period('W').astype(str),
                                      color='Tipo',
                                      title='Breakdown do Throughput Semanal',
                                      labels={'x': 'Semana', 'y': 'Itens Concluídos'},
                                      barmode='stack',
                                      color_discrete_map=color_map)
        fig_lead = px.box(df, y='LeadTime_Dias', title='Distribuição de Lead Time (dias)') if 'LeadTime_Dias' in df.columns else {}

        return html.Div([
            html.Div([
                create_kpi_card('% Demanda de Valor', f"{pct_demanda_valor:.1f}%"),
                create_kpi_card('% Demanda de Falha', f"{pct_demanda_falha:.1f}%"),
            ], className='row', style={'marginBottom': '20px'}),
            html.H3("Detalhamento por Tipo de Demanda", style={'textAlign': 'center'}),
            dash_table.DataTable(columns=[{"name": i, "id": i} for i in metrics_data[0].keys()], data=metrics_data, style_cell={'textAlign': 'center'}, style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}),
            dcc.Graph(figure=fig_throughput),
            dcc.Graph(figure=fig_lead),
        ])

    if tab == 'tab-fluxo':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas ---
        metrics = {}
        if 'TempoExecucao_Dias' in df.columns and not df['TempoExecucao_Dias'].dropna().empty:
            metrics['Cycle Time Médio (dias)'] = df['TempoExecucao_Dias'].mean()
            metrics['Cycle Time Mediano (dias)'] = df['TempoExecucao_Dias'].median()
        if 'TempoBacklog_Dias' in df.columns and not df['TempoBacklog_Dias'].dropna().empty:
            # Assumindo que "Tempo até Primeiro Movimento" é equivalente ao tempo em backlog.
            metrics['Tempo em Backlog Médio (dias)'] = df['TempoBacklog_Dias'].mean()
            metrics['Tempo até Primeiro Movimento (dias)'] = df['TempoBacklog_Dias'].mean()
        if 'EficienciaAjustada' in df.columns and not df['EficienciaAjustada'].dropna().empty:
            metrics['Eficiência Ajustada Média'] = df['EficienciaAjustada'].mean()
        if 'TempoBloqueioDias' in df.columns and not df['TempoBloqueioDias'].dropna().empty:
            metrics['Tempo de Bloqueio Médio (dias)'] = df['TempoBloqueioDias'].mean()
        if 'TempoEsperaIntermediariaDias' in df.columns and not df['TempoEsperaIntermediariaDias'].dropna().empty:
            metrics['Tempo de Espera Intermediária Médio (dias)'] = df['TempoEsperaIntermediariaDias'].mean()
        if 'Bloqueado' in df.columns:
            total_items = len(df)
            blocked_items = df['Bloqueado'].sum()
            metrics['Taxa de Bloqueio (%)'] = (blocked_items / total_items * 100) if total_items > 0 else 0

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}"} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        # --- 2. Criar Gráficos ---
        lead_time_components = {}
        if 'TempoBacklog_Dias' in df.columns and not df['TempoBacklog_Dias'].dropna().empty: lead_time_components['Backlog'] = df['TempoBacklog_Dias'].mean()
        if 'TempoExecucao_Dias' in df.columns and not df['TempoExecucao_Dias'].dropna().empty: lead_time_components['Execução (Cycle Time)'] = df['TempoExecucao_Dias'].mean()
        if 'TempoBloqueioDias' in df.columns and not df['TempoBloqueioDias'].dropna().empty: lead_time_components['Bloqueio'] = df['TempoBloqueioDias'].mean()
        if 'TempoEsperaIntermediariaDias' in df.columns and not df['TempoEsperaIntermediariaDias'].dropna().empty: lead_time_components['Espera Intermediária'] = df['TempoEsperaIntermediariaDias'].mean()

        fig_breakdown = {}
        if lead_time_components and 'LeadTime_Dias' in df.columns and not df['LeadTime_Dias'].dropna().empty:
            total_accounted = sum(lead_time_components.values())
            avg_lead_time = df['LeadTime_Dias'].mean()
            if avg_lead_time > total_accounted:
                lead_time_components['Outros'] = avg_lead_time - total_accounted
            
            df_breakdown = pd.DataFrame(lead_time_components.items(), columns=['Componente', 'Dias'])
            df_breakdown['dummy'] = 'Lead Time Médio'
            
            fig_breakdown = px.bar(df_breakdown, x='Dias', y='dummy', orientation='h', color='Componente',
                                   title='Breakdown do Lead Time Médio', labels={'Dias': 'Dias Médios', 'dummy': ''},
                                   height=300, template='plotly_white')
            fig_breakdown.update_layout(barmode='stack', yaxis_title=None, yaxis_showticklabels=False, legend_title_text='Componente')

        fig_cycle_hist = px.histogram(df, x='TempoExecucao_Dias', nbins=30, title='Distribuição do Cycle Time (dias)') if 'TempoExecucao_Dias' in df.columns else {}

        return html.Div([
            html.H3("Análise Avançada de Fluxo", style={'textAlign': 'center'}),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            dcc.Graph(figure=fig_breakdown),
            dcc.Graph(figure=fig_cycle_hist),
        ])

    if tab == 'tab-estabilidade':
        if df.empty or 'LeadTime_Dias' not in df.columns or df['LeadTime_Dias'].dropna().empty:
            return html.Div('Sem dados de Lead Time para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas de Estabilidade ---
        metrics = {}
        # Throughput
        tp_weekly = df.dropna(subset=['DataDone']).groupby(df['DataDone'].dt.to_period('W').astype(str)).size().reset_index(name='Throughput')
        if not tp_weekly.empty and tp_weekly['Throughput'].mean() > 0:
            metrics['Desvio Padrão do Throughput'] = tp_weekly['Throughput'].std()
            metrics['Coeficiente de Variação (%)'] = (tp_weekly['Throughput'].std() / tp_weekly['Throughput'].mean()) * 100

        # Lead Time
        lead_times = df['LeadTime_Dias'].dropna()
        metrics['Lead Time P50 (dias)'] = lead_times.quantile(0.50)
        metrics['Lead Time P75 (dias)'] = lead_times.quantile(0.75)
        metrics['Lead Time P95 (dias)'] = lead_times.quantile(0.95)

        # Intervalo de Confiança 95% para o Lead Time
        lt_mean = lead_times.mean()
        lt_std = lead_times.std()
        n = len(lead_times)
        if n > 1:
            ci_margin = 1.96 * (lt_std / np.sqrt(n))
            metrics['Intervalo de Confiança 95%'] = f"{lt_mean - ci_margin:.1f} - {lt_mean + ci_margin:.1f} dias"

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}" if isinstance(v, (int, float)) else v} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        # --- 2. Criar Gráficos ---
        fig_throughput_trend = px.line(tp_weekly, x='DataDone', y='Throughput', title='Throughput Semanal', markers=True)
        fig_lead_time_dist = px.box(df, y='LeadTime_Dias', title='Distribuição de Lead Time e Percentis', points="all")

        return html.Div([
            html.H3("Análise de Estabilidade", style={'textAlign': 'center'}),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            dcc.Graph(figure=fig_throughput_trend),
            dcc.Graph(figure=fig_lead_time_dist),
        ])

    if tab == 'tab-saude':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_health_base = fato.copy()
        if projeto: df_health_base = df_health_base[df_health_base['Projeto'] == projeto]
        if responsavel: df_health_base = df_health_base[df_health_base['Responsavel'] == responsavel]
        if componente and 'Componente' in df_health_base.columns: df_health_base = df_health_base[df_health_base['Componente'] == componente]

        # --- 1. Calcular Métricas de Saúde ---
        arrivals_df = df_health_base[(df_health_base['DataInProgress'] >= start_date_ts) & (df_health_base['DataInProgress'] <= end_date_ts)]
        throughput_df = df_health_base[(df_health_base['DataDone'] >= start_date_ts) & (df_health_base['DataDone'] <= end_date_ts)]
        wip_start_count = len(df_health_base[(df_health_base['DataInProgress'] < start_date_ts) & ((df_health_base['DataDone'] >= start_date_ts) | pd.isna(df_health_base['DataDone']))])
        wip_end_count = len(df_health_base[(df_health_base['DataInProgress'] <= end_date_ts) & ((df_health_base['DataDone'] > end_date_ts) | pd.isna(df_health_base['DataDone']))])

        arrivals_count = len(arrivals_df)
        throughput_count = len(throughput_df)

        metrics = {}
        work_to_be_done = wip_start_count + arrivals_count
        metrics['Taxa Conclusão (%)'] = (throughput_count / work_to_be_done * 100) if work_to_be_done > 0 else 0
        metrics['Ratio Chegada/Throughput'] = arrivals_count / throughput_count if throughput_count > 0 else 0
        metrics['Crescimento WIP (%)'] = ((wip_end_count - wip_start_count) / wip_start_count * 100) if wip_start_count > 0 else (wip_end_count * 100 if wip_end_count > 0 else 0)
        
        p85_lt = throughput_df['LeadTime_Dias'].quantile(0.85) if not throughput_df.empty else 0
        metrics['Itens Vencidos (>P85)'] = len(throughput_df[throughput_df['LeadTime_Dias'] > p85_lt]) if p85_lt > 0 else 0

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}"} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']], data=kpi_data, style_cell={'textAlign': 'left', 'padding': '5px'}, style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'})

        # --- 2. Criar Gráficos ---
        # Chegadas vs Throughput
        arrivals_weekly = arrivals_df.groupby(arrivals_df['DataInProgress'].dt.to_period('W').astype(str)).size().reset_index(name='Count')
        arrivals_weekly['Métrica'] = 'Chegadas'
        throughput_weekly = throughput_df.groupby(throughput_df['DataDone'].dt.to_period('W').astype(str)).size().reset_index(name='Count')
        throughput_weekly['Métrica'] = 'Throughput'
        
        # Renomear colunas para concatenar
        arrivals_weekly.rename(columns={'DataInProgress': 'Semana'}, inplace=True)
        throughput_weekly.rename(columns={'DataDone': 'Semana'}, inplace=True)
        
        flow_df = pd.concat([arrivals_weekly, throughput_weekly]).sort_values('Semana')
        fig_flow = px.bar(flow_df, x='Semana', y='Count', color='Métrica', barmode='group', title='Chegadas vs. Throughput Semanal', color_discrete_map={'Chegadas': 'blue', 'Throughput': 'green'})

        # Tendência do WIP
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq='W-MON')
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_health_base[(df_health_base['DataInProgress'] <= week_end) & ((df_health_base['DataDone'] > week_end) | pd.isna(df_health_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        
        wip_trend_df = pd.DataFrame(wip_trend_data)
        fig_wip_trend = px.line(wip_trend_df, x='Semana', y='WIP', title='Tendência do WIP Semanal', markers=True) if not wip_trend_df.empty else {}

        return html.Div([
            html.H3("Análise de Saúde do Fluxo", style={'textAlign': 'center'}),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            dcc.Graph(figure=fig_flow),
            dcc.Graph(figure=fig_wip_trend),
        ])

    if tab == 'tab-qualidade':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas de Qualidade ---
        defects_count = len(df[df['Tipo'] == 'Defeitos'])
        development_count = len(df[df['Tipo'] == 'Desenvolvimento'])
        total_completed = len(df)

        metrics = {}
        metrics['Debt Ratio (% Defeitos)'] = (defects_count / total_completed * 100) if total_completed > 0 else 0
        
        razao = development_count / defects_count if defects_count > 0 else float('inf')
        metrics['Razão Valor/Custo'] = f"{razao:.2f}:1" if razao != float('inf') else "Infinito (sem defeitos)"

        if 'Eficiencia' in df.columns and not df['Eficiencia'].dropna().empty:
            metrics['Eficiência Média (Simples)'] = df['Eficiencia'].mean()
        if 'EficienciaAjustada' in df.columns and not df['EficienciaAjustada'].dropna().empty:
            metrics['Eficiência Média (Ajustada)'] = df['EficienciaAjustada'].mean()

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}" if isinstance(v, (int, float)) else v} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        )

        # --- 2. Criar Gráfico ---
        by_tipo = df.groupby('Tipo').size().reset_index(name='Count')
        fig_pie = px.pie(by_tipo, names='Tipo', values='Count', 
                         title='Distribuição do Throughput por Tipo',
                         color='Tipo', color_discrete_map=color_map)

        return html.Div([
            html.H3("Análise de Qualidade", style={'textAlign': 'center'}),
            html.Div([
                html.Div(kpi_table, className='six columns', style={'padding': '20px'}),
                html.Div(dcc.Graph(figure=fig_pie), className='six columns'),
            ], className='row')
        ])

    if tab == 'tab-dim':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        def create_dim_graphs(df_filtered, dim_col, dim_title, top_n=30):
            # Throughput
            by_dim_tp = df_filtered.groupby(dim_col).size().reset_index(name='Throughput').sort_values('Throughput', ascending=False).head(top_n)
            fig_tp = px.bar(by_dim_tp, x=dim_col, y='Throughput', title=f'Throughput por {dim_title}')

            # Defect Rate
            total_by_dim = df_filtered.groupby(dim_col).size()
            defects_by_dim = df_filtered[df_filtered['Tipo'] == 'Defeitos'].groupby(dim_col).size()
            defect_rate_df = (defects_by_dim / total_by_dim * 100).fillna(0).reset_index(name='Taxa de Defeitos (%)')
            defect_rate_df = defect_rate_df[defect_rate_df[dim_col].isin(by_dim_tp[dim_col])]

            fig_defect = px.bar(defect_rate_df, x=dim_col, y='Taxa de Defeitos (%)', title=f'Taxa de Defeitos por {dim_title}')
            fig_defect.update_traces(marker_color='red')
            
            return html.Div([
                html.H4(f"Análise por {dim_title}", style={'textAlign': 'center', 'marginTop': '40px'}),
                html.Div([
                    html.Div(dcc.Graph(figure=fig_tp), className='six columns'),
                    html.Div(dcc.Graph(figure=fig_defect), className='six columns'),
                ], className='row')
            ])

        graphs = [html.H3("Análise Dimensional", style={'textAlign': 'center'})]
        
        if 'Projeto' in df.columns:
            graphs.append(create_dim_graphs(df, 'Projeto', 'Projeto', top_n=100))
        if 'Responsavel' in df.columns:
            graphs.append(create_dim_graphs(df, 'Responsavel', 'Responsável', top_n=30))
        if 'Componente' in df.columns and not df['Componente'].dropna().empty:
            graphs.append(create_dim_graphs(df, 'Componente', 'Componente', top_n=30))
        if 'Prioridade' in df.columns and not df['Prioridade'].dropna().empty:
            graphs.append(create_dim_graphs(df, 'Prioridade', 'Prioridade', top_n=100))

        return html.Div(graphs)

    if tab == 'tab-tipos':
        by_tipo = df.groupby('Tipo').agg({'ItemID':'count', 'LeadTime_Dias':'median'}).rename(columns={'ItemID':'Throughput','LeadTime_Dias':'LeadTime_Mediano'}).reset_index()
        
        graphs = []
        # % por Tipo de Problema (Bug, Feature, Tarefa, Suporte) -> Usando a coluna 'Tipo'
        fig_pie = px.pie(by_tipo, names='Tipo', values='Throughput', title='Distribuição do Throughput por Tipo', color='Tipo', color_discrete_map=color_map)
        graphs.append(dcc.Graph(figure=fig_pie))

        # Lead Time por Tipo
        fig_lt = px.bar(by_tipo, x='Tipo', y='LeadTime_Mediano', title='Lead Time Mediano por Tipo', color='Tipo', color_discrete_map=color_map)
        graphs.append(dcc.Graph(figure=fig_lt))

        # Throughput por Subtipo
        if 'WorkItemSubType' in df.columns and not df['WorkItemSubType'].dropna().empty:
            by_subtipo = df.groupby('WorkItemSubType').size().reset_index(name='Throughput').sort_values('Throughput', ascending=False)
            fig_subtipo = px.bar(by_subtipo, x='WorkItemSubType', y='Throughput', title='Throughput por Subtipo')
            graphs.append(dcc.Graph(figure=fig_subtipo))

        return html.Div(graphs)

    if tab == 'tab-tendencias':
        tp = df.dropna(subset=['DataDone']).groupby(df['DataDone'].dt.to_period('W').astype(str)).size().reset_index(name='Throughput')
        tp['Semana'] = tp['DataDone']
        tp['MA4'] = tp['Throughput'].rolling(4, min_periods=1).mean()
        fig_tp = px.line(tp, x='Semana', y=['Throughput', 'MA4'], title='Throughput Semanal e Média Móvel (4 semanas)')

        # Trend Direction
        trend_direction = '→'
        if len(tp['MA4']) >= 5:
            last_ma = tp['MA4'].iloc[-1]
            prev_ma = tp['MA4'].iloc[-5]
            if prev_ma > 0:
                if last_ma > prev_ma * 1.1: trend_direction = '↑'
                elif last_ma < prev_ma * 0.9: trend_direction = '↓'

        # WIP e Lead Time média móvel
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)
        df_trend_base = fato.copy()
        if projeto: df_trend_base = df_trend_base[df_trend_base['Projeto'] == projeto]
        if responsavel: df_trend_base = df_trend_base[df_trend_base['Responsavel'] == responsavel]
        if componente and 'Componente' in df_trend_base.columns: df_trend_base = df_trend_base[df_trend_base['Componente'] == componente]

        # Lead Time Trend
        lt_weekly = df.dropna(subset=['DataDone', 'LeadTime_Dias']).groupby(pd.Grouper(key='DataDone', freq='W-MON')).agg(LeadTime_Dias=('LeadTime_Dias', 'mean')).reset_index()
        if not lt_weekly.empty:
            lt_weekly['LeadTime_MA4'] = lt_weekly['LeadTime_Dias'].rolling(4, min_periods=1).mean()

        # WIP Trend
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq='W-MON')
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_trend_base[(df_trend_base['DataInProgress'] <= week_end) & ((df_trend_base['DataDone'] > week_end) | pd.isna(df_trend_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        wip_trend_df = pd.DataFrame(wip_trend_data)

        # Create figure with secondary y-axis
        fig_wip_lt = make_subplots(specs=[[{"secondary_y": True}]])
        if not wip_trend_df.empty:
            fig_wip_lt.add_trace(go.Scatter(x=wip_trend_df['Semana'], y=wip_trend_df['WIP'], name="WIP", mode='lines+markers'), secondary_y=False)
        if not lt_weekly.empty:
            fig_wip_lt.add_trace(go.Scatter(x=lt_weekly['DataDone'], y=lt_weekly['LeadTime_MA4'], name="Lead Time (Média Móvel 4s)", mode='lines+markers'), secondary_y=True)

        fig_wip_lt.update_layout(title_text="Tendência Semanal de WIP e Lead Time")
        fig_wip_lt.update_xaxes(title_text="Semana")
        fig_wip_lt.update_yaxes(title_text="Contagem de WIP", secondary_y=False)
        fig_wip_lt.update_yaxes(title_text="Lead Time Médio (dias)", secondary_y=True)

        return html.Div([
            create_kpi_card('Direção da Tendência (Throughput)', trend_direction, class_name='twelve columns'),
            dcc.Graph(figure=fig_tp),
            dcc.Graph(figure=fig_wip_lt)
        ])

    if tab == 'tab-throughput-tipo':
        tp = df.dropna(subset=['DataDone']).groupby([df['DataDone'].dt.to_period('W').astype(str), 'Tipo']).size().reset_index(name='Throughput')
        fig = px.line(tp, x='DataDone', y='Throughput', color='Tipo', title='Throughput por Tipo (semanal)', color_discrete_map=color_map)
        return html.Div([dcc.Graph(figure=fig)])

    if tab == 'tab-eficiencia':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular colunas adicionais ---
        df_eff = df.copy()
        
        time_cols = ['TempoBacklog_Dias', 'TempoExecucao_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias']
        for col in time_cols:
            if col not in df_eff.columns: df_eff[col] = 0
            else: df_eff[col] = df_eff[col].fillna(0)

        if 'LeadTime_Dias' in df_eff.columns:
            df_eff['Outros Tempos (dias)'] = df_eff['LeadTime_Dias'] - df_eff[time_cols].sum(axis=1)
            df_eff['Outros Tempos (dias)'] = df_eff['Outros Tempos (dias)'].clip(lower=0)

        eff_cols = ['Eficiencia', 'EficienciaAjustada']
        for col in eff_cols:
            if col not in df_eff.columns: df_eff[col] = 0
            else: df_eff[col] = df_eff[col].fillna(0)

        df_eff['Diferença Eficiência'] = df_eff['EficienciaAjustada'] - df_eff['Eficiencia']

        # --- 2. Criar Gráficos ---
        breakdown_components = {
            'Backlog': df_eff['TempoBacklog_Dias'].mean(),
            'Execução': df_eff['TempoExecucao_Dias'].mean(),
            'Bloqueio': df_eff['TempoBloqueioDias'].mean(),
            'Espera Intermediária': df_eff['TempoEsperaIntermediariaDias'].mean(),
            'Outros': df_eff.get('Outros Tempos (dias)', pd.Series(0)).mean()
        }
        df_breakdown = pd.DataFrame(breakdown_components.items(), columns=['Componente', 'Dias'])
        df_breakdown['dummy'] = 'Lead Time Médio'
        fig_breakdown = px.bar(df_breakdown, x='Dias', y='dummy', orientation='h', color='Componente',
                               title='Breakdown do Lead Time Médio por Componente', labels={'Dias': 'Dias Médios', 'dummy': ''},
                               height=300, template='plotly_white')
        fig_breakdown.update_layout(barmode='stack', yaxis_title=None, yaxis_showticklabels=False, legend_title_text='Componente')

        fig_scatter_eff = px.scatter(df_eff, x='Eficiencia', y='EficienciaAjustada', 
                                     color='Tipo', hover_data=['ItemID'], title='Eficiência Simples vs. Ajustada',
                                     labels={'Eficiencia': 'Eficiência Simples', 'EficienciaAjustada': 'Eficiência Ajustada'}, color_discrete_map=color_map)
        fig_scatter_eff.add_shape(type='line', x0=0, y0=0, x1=1, y1=1, line=dict(color='grey', width=2, dash='dash'))

        # --- 3. Criar Tabela Detalhada ---
        table_cols = ['ItemID', 'Projeto', 'Tipo', 'LeadTime_Dias', 'TempoBacklog_Dias', 'TempoExecucao_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias', 'Outros Tempos (dias)', 'Eficiencia', 'EficienciaAjustada', 'Diferença Eficiência']
        available_cols = [c for c in table_cols if c in df_eff.columns]
        detail_table = dash_table.DataTable(id='table-eficiencia-detalhada', columns=[{"name": i, "id": i} for i in available_cols], data=df_eff[available_cols].to_dict('records'), page_size=15, filter_action="native", sort_action="native", style_table={'overflowX': 'auto'}, style_cell={'minWidth': '100px', 'width': '150px', 'maxWidth': '180px', 'textAlign': 'center'})

        return html.Div([
            html.H3("Análise de Eficiência de Fluxo", style={'textAlign': 'center'}),
            dcc.Graph(figure=fig_breakdown),
            dcc.Graph(figure=fig_scatter_eff),
            html.H4("Análise Detalhada por Item", style={'textAlign': 'center', 'marginTop': '40px'}),
            detail_table
        ])

    if tab == 'tab-wip':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_wip_base = fato.copy()
        if projeto: df_wip_base = df_wip_base[df_wip_base['Projeto'] == projeto]
        if responsavel: df_wip_base = df_wip_base[df_wip_base['Responsavel'] == responsavel]

        if 'Responsavel' not in df_wip_base.columns or df_wip_base['Responsavel'].dropna().empty:
            return html.Div('Dados de Responsável não disponíveis para calcular WIP.')

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq='W-SUN')
        if weeks.empty:
            return html.Div("Período selecionado é muito curto para análise semanal.")

        wip_weekly_data = []
        for week_end in weeks:
            wip_at_date_df = df_wip_base[(df_wip_base['DataInProgress'] <= week_end) & ((df_wip_base['DataDone'] > week_end) | pd.isna(df_wip_base['DataDone']))]
            wip_counts = wip_at_date_df.groupby('Responsavel').size().reset_index(name='WIP')
            wip_counts['Semana'] = week_end
            wip_weekly_data.append(wip_counts)

        if not wip_weekly_data:
            return html.Div('Sem dados de WIP para o período e filtros selecionados.')

        wip_df = pd.concat(wip_weekly_data)

        summary_data = []
        for person in wip_df['Responsavel'].unique():
            person_wip = wip_df[wip_df['Responsavel'] == person]
            wip_medio = person_wip['WIP'].mean()
            wip_max = person_wip['WIP'].max()
            last_week_data = person_wip[person_wip['Semana'] == person_wip['Semana'].max()]
            items_ativos_fim = last_week_data['WIP'].iloc[0] if not last_week_data.empty else 0
            
            summary_data.append({'Responsável': person, 'WIP Médio Semanal': wip_medio, 'WIP Máximo na Semana': wip_max, 'Items Ativos no Fim': items_ativos_fim})

        summary_df = pd.DataFrame(summary_data).sort_values('WIP Médio Semanal', ascending=False)

        kpi_table = dash_table.DataTable(
            columns=[
                {"name": "Responsável", "id": "Responsável"},
                {"name": "WIP Médio Semanal", "id": "WIP Médio Semanal", "type": "numeric", "format": dash_table.Format.Format(precision=1, scheme=dash_table.Format.Scheme.fixed)},
                {"name": "WIP Máximo na Semana", "id": "WIP Máximo na Semana", "type": "numeric"},
                {"name": "Items Ativos no Fim", "id": "Items Ativos no Fim", "type": "numeric"},
            ],
            data=summary_df.to_dict('records'),
            style_cell={'textAlign': 'left'}, style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}, sort_action="native"
        )

        fig_wip_avg = px.bar(summary_df.head(30), x='Responsável', y='WIP Médio Semanal', title='WIP Médio Semanal por Pessoa (Top 30)')

        if responsavel:
            df_trend = wip_df
        else:
            top_responsaveis = summary_df.head(5)['Responsável'].tolist()
            df_trend = wip_df[wip_df['Responsavel'].isin(top_responsaveis)]
            
        fig_wip_trend = px.line(df_trend, x='Semana', y='WIP', color='Responsável', title='Tendência do WIP Semanal (Top 5 Responsáveis)', markers=True)

        return html.Div([
            html.H3("Análise de WIP por Pessoa", style={'textAlign': 'center'}),
            html.H4("Resumo do Período", style={'textAlign': 'center', 'marginTop': '30px'}),
            kpi_table,
            dcc.Graph(figure=fig_wip_avg),
            dcc.Graph(figure=fig_wip_trend),
        ])

    return html.Div('Aba não encontrada')

def create_table(df, table_id='table-main', title='Tabela'):
    if df is None or getattr(df, 'empty', True):
        return html.Div('Sem dados para exibir')
    return html.Div([html.H3(title), dash_table.DataTable(id=table_id, columns=[{'name':c,'id':c} for c in df.columns], data=df.head(200).to_dict('records'), page_size=20, style_table={'overflowX':'auto'})])

def create_generic_datatable(df, table_id, title):
    return create_table(df, table_id=table_id, title=title)

if __name__ == '__main__':
    app.run(debug=True)
