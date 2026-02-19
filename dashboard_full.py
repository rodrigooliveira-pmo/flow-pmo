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
import platform
if platform.system() == 'Windows':
    DATA_FOLDER = r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
else:
    DATA_FOLDER = os.path.join(os.path.expanduser('~'), 'Library', 'CloudStorage', 'OneDrive-W1', 'Documentos', 'Dados')
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
# Friendly column names
rename_map = {'NomeProjeto': 'Projeto', 'Tipo': 'Tipo', 'Responsavel': 'Responsavel', 'Prioridade': 'Prioridade'}
fato.rename(columns={k: v for k, v in rename_map.items() if k in fato.columns}, inplace=True)

# Semana padrão do sistema: semana ISO (segunda a domingo).
WEEK_DATE_RANGE_FREQ = 'W-MON'
WEEK_PERIOD = 'W-SUN'

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

def weekly_bucket_start(date_series):
    return date_series.dt.to_period(WEEK_PERIOD).dt.start_time

def add_statistical_lines(fig, x_values, y_values, name_prefix='', secondary_y=None):
    """Adiciona linhas de percentil 15, 85, 95, média e média móvel (5 períodos) a um gráfico de tendência."""
    y_series = pd.Series(y_values.values if hasattr(y_values, 'values') else y_values).dropna()
    if y_series.empty:
        return fig
    p15 = y_series.quantile(0.15)
    p85 = y_series.quantile(0.85)
    p95 = y_series.quantile(0.95)
    mean_val = y_series.mean()
    ma5 = y_series.rolling(5, min_periods=1).mean()
    kwargs = {}
    if secondary_y is not None:
        kwargs['secondary_y'] = secondary_y
    x_list = list(x_values)
    fig.add_trace(go.Scatter(x=x_list, y=[p15]*len(x_list), mode='lines', name=f'{name_prefix}P15',
                             line=dict(dash='dot', width=1, color='gray')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=[p85]*len(x_list), mode='lines', name=f'{name_prefix}P85',
                             line=dict(dash='dash', width=1.5, color='orange')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=[p95]*len(x_list), mode='lines', name=f'{name_prefix}P95',
                             line=dict(dash='dash', width=1.5, color='red')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=[mean_val]*len(x_list), mode='lines', name=f'{name_prefix}Média',
                             line=dict(dash='solid', width=1.5, color='blue')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=list(ma5), mode='lines', name=f'{name_prefix}MM(5)',
                             line=dict(dash='solid', width=2, color='purple')), **kwargs)
    return fig

def calculate_mm1_metrics(arrival_rate, service_rate):
    """Calcula indicadores de fila M/M/1 para taxa de chegada e vazão."""
    if service_rate <= 0 or arrival_rate < 0:
        return None
    if arrival_rate >= service_rate:
        return {
            'lambda': arrival_rate,
            'mu': service_rate,
            'rho': arrival_rate / service_rate if service_rate else np.nan,
            'Lq': np.inf,
            'Wq': np.inf,
            'W': np.inf,
        }

    rho = arrival_rate / service_rate
    lq = (rho ** 2) / (1 - rho)
    wq = lq / arrival_rate if arrival_rate > 0 else 0
    w = wq + (1 / service_rate)
    return {'lambda': arrival_rate, 'mu': service_rate, 'rho': rho, 'Lq': lq, 'Wq': wq, 'W': w}


def compute_flow_bottlenecks(df):
    """Monta ranking de gargalos por etapa do fluxo com base no tempo médio em dias."""
    stage_columns = [
        ('Backlog', 'TempoBacklog_Dias'),
        ('Execução', 'TempoExecucao_Dias'),
        ('Bloqueio', 'TempoBloqueioDias'),
        ('Espera Intermediária', 'TempoEsperaIntermediariaDias'),
    ]

    rows = []
    for stage_name, col in stage_columns:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors='coerce').dropna()
        if series.empty:
            continue
        rows.append({
            'Etapa': stage_name,
            'Tempo Médio (dias)': float(series.mean()),
            'Tempo Mediano (dias)': float(series.median()),
            'P90 (dias)': float(series.quantile(0.90)),
            'Qtde Itens': int(series.shape[0]),
        })

    bottlenecks_df = pd.DataFrame(rows)
    if not bottlenecks_df.empty:
        bottlenecks_df = bottlenecks_df.sort_values(
            by='Tempo Médio (dias)',
            ascending=False,
            ignore_index=True,
        )
    return bottlenecks_df

def compute_weekly_service_metrics(df_projeto, weeks):
    """Calcula métricas de performance do serviço por semana (layout transposto)."""
    metric_names = [
        'Taxa de chegada / semana',
        'Throughput / semana',
        'Média WIP / semana',
        'WIP Age (dias)',
        'Média Lead Time',
        'Média Eficiência de Fluxo',
        '% Demanda de Valor',
        '% Demanda de Falha',
        'Qtd. Itens Descartados',
        'P85% DO LEAD TIME',
        'DDP',
        'Frequência de Deploy',
        'Lead time para mudanças',
        'Taxa de demanda de falha',
        'MTTR',
    ]
    rows = {m: {} for m in metric_names}

    for i in range(len(weeks) - 1):
        week_start = weeks[i]
        week_end = weeks[i + 1]
        week_label = str(week_start.date())

        arrived = df_projeto[
            (df_projeto['DataInProgress'] >= week_start) & (df_projeto['DataInProgress'] < week_end)
        ]
        finished = df_projeto[
            (df_projeto['DataDone'] >= week_start) & (df_projeto['DataDone'] < week_end)
        ]
        wip = df_projeto[
            (df_projeto['DataInProgress'] < week_end) &
            ((df_projeto['DataDone'] >= week_end) | pd.isna(df_projeto['DataDone']))
        ]

        tp_total = len(finished)
        tp_dev = len(finished[finished['Tipo'] == 'Desenvolvimento']) if tp_total > 0 else 0
        tp_def = len(finished[finished['Tipo'] == 'Defeitos']) if tp_total > 0 else 0

        wip_age = (week_end - wip['DataInProgress']).dt.days.mean() if len(wip) > 0 else 0
        avg_lt = finished['LeadTime_Dias'].dropna().mean() if tp_total > 0 and 'LeadTime_Dias' in finished.columns else 0
        if pd.isna(avg_lt):
            avg_lt = 0
        avg_eff = 0
        if tp_total > 0:
            for eff_col in ['EficienciaAjustada', 'Eficiencia']:
                if eff_col in finished.columns and not finished[eff_col].dropna().empty:
                    avg_eff = finished[eff_col].dropna().mean()
                    break
        if pd.isna(avg_eff):
            avg_eff = 0
        p85_lt = finished['LeadTime_Dias'].dropna().quantile(0.85) if tp_total > 0 and 'LeadTime_Dias' in finished.columns and not finished['LeadTime_Dias'].dropna().empty else 0

        rows['Taxa de chegada / semana'][week_label] = str(len(arrived))
        rows['Throughput / semana'][week_label] = str(tp_total)
        rows['Média WIP / semana'][week_label] = str(len(wip))
        rows['WIP Age (dias)'][week_label] = f"{wip_age:.0f}" if wip_age else '0'
        rows['Média Lead Time'][week_label] = f"{avg_lt:.0f}" if avg_lt else '0'
        rows['Média Eficiência de Fluxo'][week_label] = f"{avg_eff:.3f}" if avg_eff else '0.000'
        rows['% Demanda de Valor'][week_label] = f"{tp_dev / tp_total * 100:.1f}%" if tp_total > 0 else '—'
        rows['% Demanda de Falha'][week_label] = f"{tp_def / tp_total * 100:.1f}%" if tp_total > 0 else '—'
        rows['Qtd. Itens Descartados'][week_label] = '—'
        rows['P85% DO LEAD TIME'][week_label] = f"{p85_lt:.0f}" if p85_lt else '0'
        rows['DDP'][week_label] = '—'
        rows['Frequência de Deploy'][week_label] = '—'
        rows['Lead time para mudanças'][week_label] = '—'
        rows['Taxa de demanda de falha'][week_label] = '—'
        rows['MTTR'][week_label] = '—'

    return metric_names, rows

min_date = fato['DataDone'].min() if 'DataDone' in fato.columns else pd.to_datetime('2023-01-01')
max_date = fato['DataDone'].max() if 'DataDone' in fato.columns else pd.to_datetime('today')

app.layout = html.Div([
    html.H1('Dashboard de Métricas - Full', style={'textAlign': 'center'}),
    html.Div([
        html.Div([html.Label('Período:'), dcc.DatePickerRange(id='date-range', start_date=min_date, end_date=max_date,
                                                            display_format='YYYY-MM-DD',
                                                            month_format='MMMM YYYY',
                                                            show_outside_days=True)], style={'display':'inline-block', 'marginRight':'20px'}),
        html.Div([html.Label('Projeto:'), dcc.Dropdown(id='filter-projeto', options=[{'label':p,'value':p} for p in unique_sorted(fato['Projeto'])], value=unique_sorted(fato['Projeto'])[0] if len(unique_sorted(fato['Projeto']))>0 else None, clearable=False)], style={'width':'20%', 'display':'inline-block'}),
        html.Div([html.Label('Tipo:'), dcc.Dropdown(id='filter-tipo', options=[{'label':t,'value':t} for t in unique_sorted(fato['Tipo'])], value=None, clearable=True)], style={'width':'15%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([html.Label('Responsável:'), dcc.Dropdown(id='filter-responsavel', options=[{'label':r,'value':r} for r in unique_sorted(fato['Responsavel'])], value=None, clearable=True)], style={'width':'20%', 'display':'inline-block', 'marginLeft':'20px'}),
    ], style={'display':'flex', 'justifyContent':'center', 'gap':'10px', 'marginBottom':'20px'}),

    dcc.Tabs(id='tabs', value='tab-performance', children=[
        dcc.Tab(label='Performance do Serviço', value='tab-performance'),
        dcc.Tab(label='Painel Fluxo 3x3', value='tab-painel-3x3'),
        dcc.Tab(label='Dashboard', value='tab-dashboard'),
        dcc.Tab(label='Fluxo', value='tab-fluxo'),
        dcc.Tab(label='Estabilidade', value='tab-estabilidade'),
        dcc.Tab(label='Saúde Fluxo', value='tab-saude'),
        dcc.Tab(label='Qualidade', value='tab-qualidade'),
        dcc.Tab(label='Análise Dimensional', value='tab-dim'),
        dcc.Tab(label='Análise Tipos', value='tab-tipos'),
        dcc.Tab(label='Tendências', value='tab-tendencias'),
        dcc.Tab(label='Throughput por Tipo', value='tab-throughput-tipo'),
        dcc.Tab(label='Análise Eficiência', value='tab-eficiencia'),
        dcc.Tab(label='WIP por Pessoa', value='tab-wip'),
        dcc.Tab(label='Estatística Descritiva', value='tab-estatistica'),
        dcc.Tab(label='Capacidade de Fila', value='tab-fila-capacidade'),
    ]),

    html.Div(id='tab-content')
])

def filter_df(df, start_date, end_date, projeto, tipo, responsavel):
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
    return d

@app.callback(Output('tab-content', 'children'), Input('tabs', 'value'), Input('date-range', 'start_date'), Input('date-range', 'end_date'), Input('filter-projeto', 'value'), Input('filter-tipo', 'value'), Input('filter-responsavel', 'value'))
def render_tab(tab, start_date, end_date, projeto, tipo, responsavel):
    df = filter_df(fato, start_date, end_date, projeto, tipo, responsavel)

    # Padrão de cores para os tipos de demanda
    color_map = {
        'Desenvolvimento': 'green', # Demanda de Valor
        'Defeitos': 'red',         # Demanda de Falha
        'Outro': 'lightgray'       # Outros tipos
    }

    if tab == 'tab-performance':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        df_proj = fato.copy()
        if projeto:
            df_proj = df_proj[df_proj['Projeto'] == projeto]
        if responsavel:
            df_proj = df_proj[df_proj['Responsavel'] == responsavel]
        weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal.')

        metric_names, rows = compute_weekly_service_metrics(df_proj, weeks)
        week_labels = [str(weeks[i].date()) for i in range(len(weeks) - 1)]

        table_data = []
        for m in metric_names:
            row = {'Métrica': m}
            for wl in week_labels:
                row[wl] = rows[m].get(wl, '—')
            table_data.append(row)

        columns = [{'name': 'Métrica', 'id': 'Métrica'}] + [{'name': wl, 'id': wl} for wl in week_labels]

        style_data_conditional = [
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
            {'if': {'filter_query': '{Métrica} = "% Demanda de Valor"'}, 'color': 'green', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Métrica} = "% Demanda de Falha"'}, 'color': 'red', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Métrica} contains "—"'}, 'color': '#aaa'},
        ]
        for m in ['Qtd. Itens Descartados', 'DDP', 'Frequência de Deploy', 'Lead time para mudanças', 'Taxa de demanda de falha', 'MTTR']:
            style_data_conditional.append({
                'if': {'filter_query': f'{{Métrica}} = "{m}"'},
                'backgroundColor': 'rgb(245, 245, 245)', 'color': '#bbb', 'fontStyle': 'italic'
            })

        titulo = f"Performance da Entrega do Serviço: {projeto}" if projeto else "Performance da Entrega do Serviço"

        return html.Div([
            html.H3(titulo, style={'textAlign': 'center', 'marginBottom': '20px'}),
            dash_table.DataTable(
                id='performance-table',
                columns=columns,
                data=table_data,
                style_cell={'textAlign': 'center', 'padding': '8px', 'minWidth': '120px'},
                style_cell_conditional=[{'if': {'column_id': 'Métrica'}, 'textAlign': 'left', 'fontWeight': 'bold', 'minWidth': '250px'}],
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=style_data_conditional + [
                    {'if': {'state': 'active'}, 'backgroundColor': 'rgba(0, 116, 217, 0.1)', 'border': '1px solid rgb(0, 116, 217)'}
                ],
                style_table={'overflowX': 'auto'},
            ),
            html.Div(id='performance-metric-chart')
        ])

    if tab == 'tab-painel-3x3':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        # Base exibida no painel (respeita todos os filtros ativos).
        df_signal_base = fato.copy()
        if projeto:
            df_signal_base = df_signal_base[df_signal_base['Projeto'] == projeto]
        if tipo:
            df_signal_base = df_signal_base[df_signal_base['Tipo'] == tipo]
        if responsavel:
            df_signal_base = df_signal_base[df_signal_base['Responsavel'] == responsavel]

        # Base de referência para thresholds (projeto/tipo), independente de período e responsável.
        df_threshold_base = fato.copy()
        if projeto:
            df_threshold_base = df_threshold_base[df_threshold_base['Projeto'] == projeto]
        if tipo:
            df_threshold_base = df_threshold_base[df_threshold_base['Tipo'] == tipo]

        weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal.')

        def build_weekly_metrics(df_source, start_ref, end_ref):
            rows = []
            weeks_ref = pd.date_range(start=start_ref, end=end_ref + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
            if len(weeks_ref) < 2:
                return pd.DataFrame()
            for i in range(len(weeks_ref) - 1):
                week_start = weeks_ref[i]
                week_end = weeks_ref[i + 1]
                arrived = df_source[
                    (df_source['DataInProgress'] >= week_start) &
                    (df_source['DataInProgress'] < week_end)
                ]
                done = df_source[
                    (df_source['DataDone'] >= week_start) &
                    (df_source['DataDone'] < week_end)
                ]
                wip_items = df_source[
                    (df_source['DataInProgress'] < week_end) &
                    ((df_source['DataDone'] >= week_end) | pd.isna(df_source['DataDone']))
                ]

                lt_p85 = np.nan
                lt_p50 = np.nan
                if 'LeadTime_Dias' in done.columns and not done['LeadTime_Dias'].dropna().empty:
                    lt_p85 = done['LeadTime_Dias'].quantile(0.85)
                    lt_p50 = done['LeadTime_Dias'].quantile(0.50)

                flow_eff_w = np.nan
                for eff_col in ['EficienciaAjustada', 'Eficiencia']:
                    if eff_col in done.columns and not done[eff_col].dropna().empty:
                        flow_eff_w = done[eff_col].mean()
                        break

                tp = len(done)
                ar = len(arrived)
                wip = len(wip_items)
                rows.append({
                    'Semana': week_start.date(),
                    'Chegadas': ar,
                    'Throughput': tp,
                    'WIP': wip,
                    'WIP_Age': (week_end - wip_items['DataInProgress']).dt.days.mean() if wip > 0 else np.nan,
                    'LeadTime_P85': lt_p85,
                    'FlowEfficiency': flow_eff_w,
                    'Pressure': (ar / tp) if tp > 0 else np.nan,
                    'QueueEfficiency': (1 - (ar / tp)) if tp > 0 else np.nan,
                    'WIP_TP_Ratio': (wip / tp) if tp > 0 else np.nan,
                    'Predictability': (lt_p85 / lt_p50) if pd.notna(lt_p85) and pd.notna(lt_p50) and lt_p50 > 0 else np.nan,
                })
            return pd.DataFrame(rows)

        weekly_rows = []
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = len(df_signal_base[
                (df_signal_base['DataInProgress'] >= week_start) &
                (df_signal_base['DataInProgress'] < week_end)
            ])
            throughput = len(df_signal_base[
                (df_signal_base['DataDone'] >= week_start) &
                (df_signal_base['DataDone'] < week_end)
            ])
            wip = len(df_signal_base[
                (df_signal_base['DataInProgress'] < week_end) &
                ((df_signal_base['DataDone'] >= week_end) | pd.isna(df_signal_base['DataDone']))
            ])
            weekly_rows.append({
                'Semana': week_start.date(),
                'Chegadas': arrivals,
                'Throughput': throughput,
                'WIP': wip,
            })
        weekly_df = pd.DataFrame(weekly_rows)

        # Histórico de referência para thresholds dinâmicos por projeto/tipo.
        date_candidates = []
        for col in ['DataInProgress', 'DataDone']:
            if col in df_threshold_base.columns and not df_threshold_base[col].dropna().empty:
                date_candidates.append(df_threshold_base[col].dropna().min())
        if not date_candidates:
            date_candidates = [start_ts]
        hist_start = min(date_candidates)
        hist_end = end_ts
        weekly_hist_df = build_weekly_metrics(df_threshold_base, hist_start, hist_end)

        df_done_period = df_signal_base[
            (df_signal_base['DataDone'] >= start_ts) &
            (df_signal_base['DataDone'] <= end_ts)
        ]
        df_wip_end = df_signal_base[
            (df_signal_base['DataInProgress'] <= end_ts) &
            ((df_signal_base['DataDone'] > end_ts) | pd.isna(df_signal_base['DataDone']))
        ]

        throughput_avg = weekly_df['Throughput'].mean() if not weekly_df.empty else np.nan
        arrivals_avg = weekly_df['Chegadas'].mean() if not weekly_df.empty else np.nan
        wip_avg = weekly_df['WIP'].mean() if not weekly_df.empty else np.nan
        wip_current = float(weekly_df['WIP'].iloc[-1]) if not weekly_df.empty else np.nan
        wip_age = (end_ts - df_wip_end['DataInProgress']).dt.days.mean() if not df_wip_end.empty else np.nan

        lead_time_p85 = np.nan
        lead_time_p50 = np.nan
        lead_time_p98 = np.nan
        if 'LeadTime_Dias' in df_done_period.columns and not df_done_period['LeadTime_Dias'].dropna().empty:
            lead_time_p85 = df_done_period['LeadTime_Dias'].quantile(0.85)
            lead_time_p50 = df_done_period['LeadTime_Dias'].quantile(0.50)
            lead_time_p98 = df_done_period['LeadTime_Dias'].quantile(0.98)

        pressure_ratio = arrivals_avg / throughput_avg if pd.notna(arrivals_avg) and pd.notna(throughput_avg) and throughput_avg > 0 else np.nan
        queue_efficiency = 1 - pressure_ratio if pd.notna(pressure_ratio) else np.nan
        wip_tp_ratio = wip_avg / throughput_avg if pd.notna(wip_avg) and pd.notna(throughput_avg) and throughput_avg > 0 else np.nan
        predictability = lead_time_p85 / lead_time_p50 if pd.notna(lead_time_p85) and pd.notna(lead_time_p50) and lead_time_p50 > 0 else np.nan
        risk_forecasting_ratio = lead_time_p98 / lead_time_p50 if pd.notna(lead_time_p98) and pd.notna(lead_time_p50) and lead_time_p50 > 0 else np.nan

        def classify_direction(value, good_limit, warn_limit, lower_is_better=True):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if lower_is_better:
                if value <= good_limit:
                    return ('Saudável', '#2e7d32')
                if value <= warn_limit:
                    return ('Atenção', '#f9a825')
                return ('Crítico', '#c62828')
            if value >= good_limit:
                return ('Saudável', '#2e7d32')
            if value >= warn_limit:
                return ('Atenção', '#f9a825')
            return ('Crítico', '#c62828')

        def fmt_value(value, pattern):
            if pd.isna(value):
                return '—'
            return pattern.format(value)

        def dynamic_limits(series, lower_is_better, fallback_good, fallback_warn):
            s = pd.Series(series).dropna()
            if len(s) >= 8:
                if lower_is_better:
                    return (s.quantile(0.50), s.quantile(0.85), int(len(s)), 'histórico')
                return (s.quantile(0.50), s.quantile(0.25), int(len(s)), 'histórico')
            return (fallback_good, fallback_warn, int(len(s)), 'fallback')

        def merge_limits(dynamic_good, dynamic_warn, lower_is_better, hard_good=None, hard_warn=None):
            good = dynamic_good
            warn = dynamic_warn
            if hard_good is not None:
                good = min(good, hard_good) if lower_is_better else max(good, hard_good)
            if hard_warn is not None:
                warn = min(warn, hard_warn) if lower_is_better else max(warn, hard_warn)
            if lower_is_better and warn < good:
                warn = good
            if not lower_is_better and warn > good:
                warn = good
            return good, warn

        def classify_with_hard_cap(value, good_limit, warn_limit, hard_cap):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if value > hard_cap:
                return ('Crítico', '#c62828')
            effective_good = min(good_limit, hard_cap)
            effective_warn = min(warn_limit, hard_cap)
            if effective_warn < effective_good:
                effective_warn = effective_good
            return classify_direction(value, effective_good, effective_warn, lower_is_better=True)

        def classify_forecasting_risk(value):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if value < 6:
                return ('RISCO MODERADO', '#2e7d32')
            return ('RISCO ALTO', '#ef7d32')

        cards = []
        wip_good, wip_warn, _, _ = dynamic_limits(weekly_hist_df.get('WIP', pd.Series(dtype=float)), True, 20, 35)
        lt_good, lt_warn, _, _ = dynamic_limits(weekly_hist_df.get('LeadTime_P85', pd.Series(dtype=float)), True, 15, 25)
        tp_good, tp_warn, _, _ = dynamic_limits(weekly_hist_df.get('Throughput', pd.Series(dtype=float)), False, 8, 4)
        pressure_good, pressure_warn, _, _ = dynamic_limits(weekly_hist_df.get('Pressure', pd.Series(dtype=float)), True, 1.0, 1.15)
        wip_age_good, wip_age_warn, _, _ = dynamic_limits(weekly_hist_df.get('WIP_Age', pd.Series(dtype=float)), True, 10, 20)

        # Eficiência com cortes fixos solicitados.
        eff_good, eff_warn = 0.20, 0.10
        # WIP Age por P50/P85 com hard cap absoluto em 30 dias.
        wip_age_good, wip_age_warn = merge_limits(wip_age_good, wip_age_warn, lower_is_better=True, hard_warn=30)

        card_specs = [
            ('WIP médio (semana)', wip_avg, '{:.1f} itens', classify_direction(wip_avg, wip_good, wip_warn, lower_is_better=True)),
            ('Lead Time P85', lead_time_p85, '{:.1f} dias', classify_direction(lead_time_p85, lt_good, lt_warn, lower_is_better=True)),
            ('Vazão média semanal', throughput_avg, '{:.1f} itens/sem', classify_direction(throughput_avg, tp_good, tp_warn, lower_is_better=False)),
            ('Taxa de chegada média', arrivals_avg, '{:.1f} itens/sem', classify_direction(pressure_ratio, pressure_good, pressure_warn, lower_is_better=True)),
            ('Eficiência (1 - ρ)', queue_efficiency, '{:.2f}', classify_direction(queue_efficiency, eff_good, eff_warn, lower_is_better=False)),
            ('Pressão de fluxo (chegada/vazão)', pressure_ratio, '{:.2f}', classify_direction(pressure_ratio, pressure_good, pressure_warn, lower_is_better=True)),
            ('WIP Age médio', wip_age, '{:.1f} dias', classify_with_hard_cap(wip_age, wip_age_good, wip_age_warn, hard_cap=30)),
            ('WIP atual (fim do período)', wip_current, '{:.0f} itens', classify_direction(wip_current, wip_good, wip_warn, lower_is_better=True)),
            ('Risco Forecasting (P98/Mediana)', risk_forecasting_ratio, '{:.2f}', classify_forecasting_risk(risk_forecasting_ratio)),
        ]

        for title, raw_value, value_pattern, (status_label, status_color) in card_specs:
            cards.append(
                html.Div([
                    html.Div(status_label, style={'fontSize': '12px', 'fontWeight': 'bold', 'color': status_color, 'textTransform': 'uppercase'}),
                    html.H4(title, style={'marginTop': '8px', 'marginBottom': '8px', 'fontSize': '17px'}),
                    html.Div(fmt_value(raw_value, value_pattern), style={'fontSize': '30px', 'fontWeight': 'bold', 'lineHeight': '1.1'}),
                ], style={
                    'backgroundColor': 'white',
                    'border': '1px solid #e5e5e5',
                    'borderTop': f'6px solid {status_color}',
                    'borderRadius': '10px',
                    'padding': '14px',
                    'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
                    'minHeight': '150px',
                })
            )

        return html.Div([
            html.H3("Painel Principal de Gestão de Fluxo (3 x 3)", style={'textAlign': 'center'}),
            html.P(
                "Sinais executivos de fluxo para o filtro ativo de projeto e período. "
                "Semáforo: Saudável, Atenção e Crítico.",
                style={'textAlign': 'center', 'color': '#666', 'marginBottom': '20px'}
            ),
            html.Div([
                html.Div([html.Div(cards[i], className='four columns') for i in range(0, 3)], className='row'),
                html.Div([html.Div(cards[i], className='four columns') for i in range(3, 6)], className='row', style={'marginTop': '14px'}),
                html.Div([html.Div(cards[i], className='four columns') for i in range(6, 9)], className='row', style={'marginTop': '14px'}),
            ], style={'maxWidth': '1200px', 'margin': '0 auto'}),
        ])

    if tab == 'tab-dashboard':
        # Para o detalhamento, precisamos de uma base que ignore o filtro de 'tipo'
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_base_breakdown = fato.copy()
        if projeto: df_base_breakdown = df_base_breakdown[df_base_breakdown['Projeto'] == projeto]
        if responsavel: df_base_breakdown = df_base_breakdown[df_base_breakdown['Responsavel'] == responsavel]
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
        ].copy()
        df_throughput_chart_data['Semana'] = weekly_bucket_start(df_throughput_chart_data['DataDone'])
        fig_throughput = px.histogram(df_throughput_chart_data,
                                      x='Semana',
                                      color='Tipo',
                                      title='Breakdown do Throughput Semanal',
                                      labels={'x': 'Semana', 'y': 'Itens Concluídos'},
                                      barmode='stack',
                                      color_discrete_map=color_map)
        fig_throughput.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))
        fig_lead = px.box(df, y='LeadTime_Dias', title='Distribuição de Lead Time (dias)') if 'LeadTime_Dias' in df.columns else {}
        if fig_lead:
            fig_lead.update_layout(height=500)

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
                                   height=400, template='plotly_white')
            fig_breakdown.update_layout(barmode='stack', yaxis_title=None, yaxis_showticklabels=False, legend_title_text='Componente')

        fig_cycle_hist = px.histogram(df, x='TempoExecucao_Dias', nbins=30, title='Distribuição do Cycle Time (dias)') if 'TempoExecucao_Dias' in df.columns else {}
        if fig_cycle_hist:
            fig_cycle_hist.update_layout(height=500)

        # --- 3. Ranking de Gargalos por Etapa ---
        bottlenecks_df = compute_flow_bottlenecks(df)
        if bottlenecks_df.empty:
            fig_bottlenecks = {}
            bottlenecks_table = html.P('Sem dados suficientes para calcular gargalos por etapa.')
        else:
            fig_bottlenecks = px.bar(
                bottlenecks_df,
                x='Tempo Médio (dias)',
                y='Etapa',
                orientation='h',
                title='Ranking de Gargalos do Fluxo (Maior para Menor)',
                text='Tempo Médio (dias)',
                labels={'Tempo Médio (dias)': 'Tempo Médio (dias)', 'Etapa': 'Etapa'},
                template='plotly_white',
                color='Tempo Médio (dias)',
                color_continuous_scale='Reds',
            )
            fig_bottlenecks.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_bottlenecks.update_layout(
                yaxis=dict(autorange='reversed'),
                coloraxis_showscale=False,
                height=480,
                margin=dict(l=140, r=40, t=70, b=50),
            )

            display_df = bottlenecks_df.copy()
            for c in ['Tempo Médio (dias)', 'Tempo Mediano (dias)', 'P90 (dias)']:
                display_df[c] = display_df[c].round(2)
            bottlenecks_table = dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in display_df.columns],
                data=display_df.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            )

        return html.Div([
            html.H3("Análise Avançada de Fluxo", style={'textAlign': 'center'}),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            html.H4("Indicador de Gargalo do Fluxo", style={'textAlign': 'center', 'marginTop': '10px'}),
            html.Div(bottlenecks_table, style={'width': '70%', 'margin': 'auto', 'marginBottom': '20px'}),
            dcc.Graph(figure=fig_bottlenecks),
            dcc.Graph(figure=fig_breakdown),
            dcc.Graph(figure=fig_cycle_hist),
        ])

    if tab == 'tab-estabilidade':
        if df.empty or 'LeadTime_Dias' not in df.columns or df['LeadTime_Dias'].dropna().empty:
            return html.Div('Sem dados de Lead Time para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas de Estabilidade ---
        metrics = {}
        # Throughput
        tp_weekly = df.dropna(subset=['DataDone']).copy()
        tp_weekly['Semana'] = weekly_bucket_start(tp_weekly['DataDone'])
        tp_weekly = tp_weekly.groupby('Semana').size().reset_index(name='Throughput')
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
        fig_throughput_trend = px.line(tp_weekly, x='Semana', y='Throughput', title='Throughput Semanal', markers=True)
        add_statistical_lines(fig_throughput_trend, tp_weekly['Semana'], tp_weekly['Throughput'])
        fig_throughput_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))
        fig_lead_time_dist = px.box(df, y='LeadTime_Dias', title='Distribuição de Lead Time e Percentis', points="all")
        fig_lead_time_dist.update_layout(height=500)

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
        arrivals_weekly = arrivals_df.dropna(subset=['DataInProgress']).copy()
        arrivals_weekly['Semana'] = weekly_bucket_start(arrivals_weekly['DataInProgress'])
        arrivals_weekly = arrivals_weekly.groupby('Semana').size().reset_index(name='Count')
        arrivals_weekly['Métrica'] = 'Chegadas'
        throughput_weekly = throughput_df.dropna(subset=['DataDone']).copy()
        throughput_weekly['Semana'] = weekly_bucket_start(throughput_weekly['DataDone'])
        throughput_weekly = throughput_weekly.groupby('Semana').size().reset_index(name='Count')
        throughput_weekly['Métrica'] = 'Throughput'

        flow_df = pd.concat([arrivals_weekly, throughput_weekly]).sort_values('Semana')
        fig_flow = px.bar(flow_df, x='Semana', y='Count', color='Métrica', barmode='group', title='Chegadas vs. Throughput Semanal', color_discrete_map={'Chegadas': 'blue', 'Throughput': 'green'})
        fig_flow.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        # Tendência do WIP
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_health_base[(df_health_base['DataInProgress'] <= week_end) & ((df_health_base['DataDone'] > week_end) | pd.isna(df_health_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        
        wip_trend_df = pd.DataFrame(wip_trend_data)
        fig_wip_trend = px.line(wip_trend_df, x='Semana', y='WIP', title='Tendência do WIP Semanal', markers=True) if not wip_trend_df.empty else {}
        if not wip_trend_df.empty:
            add_statistical_lines(fig_wip_trend, wip_trend_df['Semana'], wip_trend_df['WIP'])
            fig_wip_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

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
        fig_pie.update_layout(height=500)

        razao_explicacao = html.Div([
            html.H4("Razão Valor/Custo", style={'marginTop': '30px', 'marginBottom': '10px'}),
            html.P([
                "A ", html.Strong("Razão Valor/Custo"), " indica quantos itens de ",
                html.Span("Desenvolvimento (demanda de valor)", style={'color': 'green', 'fontWeight': 'bold'}),
                " foram entregues para cada item de ",
                html.Span("Defeito (demanda de falha)", style={'color': 'red', 'fontWeight': 'bold'}),
                " no período selecionado."
            ], style={'fontSize': '14px', 'lineHeight': '1.6'}),
            html.Ul([
                html.Li([html.Strong("Exemplo: 3.00:1"), " — para cada defeito corrigido, 3 itens de valor foram entregues."]),
                html.Li([html.Strong("Valor alto (> 4:1)"), " — o time está focado em gerar valor, com baixa incidência de retrabalho."]),
                html.Li([html.Strong("Valor baixo (< 2:1)"), " — grande parte do esforço está sendo consumido por correções de defeitos, sinalizando problemas de qualidade."]),
                html.Li([html.Strong("Infinito"), " — nenhum defeito foi registrado no período."]),
            ], style={'fontSize': '13px', 'lineHeight': '1.8', 'color': '#444'}),
            html.P("Fórmula: Throughput de Desenvolvimento / Throughput de Defeitos",
                   style={'fontSize': '12px', 'color': '#888', 'fontStyle': 'italic', 'marginTop': '10px'}),
        ], style={'padding': '15px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'border': '1px solid #e0e0e0', 'marginTop': '20px'})

        return html.Div([
            html.H3("Análise de Qualidade", style={'textAlign': 'center'}),
            html.Div([
                html.Div(kpi_table, className='six columns', style={'padding': '20px'}),
                html.Div(dcc.Graph(figure=fig_pie), className='six columns'),
            ], className='row'),
            razao_explicacao,
        ])

    if tab == 'tab-dim':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        def create_dim_graphs(df_filtered, dim_col, dim_title, top_n=30):
            # Throughput
            by_dim_tp = df_filtered.groupby(dim_col).size().reset_index(name='Throughput').sort_values('Throughput', ascending=False).head(top_n)
            fig_tp = px.bar(by_dim_tp, x=dim_col, y='Throughput', title=f'Throughput por {dim_title}')
            fig_tp.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))

            # Defect Rate
            total_by_dim = df_filtered.groupby(dim_col).size()
            defects_by_dim = df_filtered[df_filtered['Tipo'] == 'Defeitos'].groupby(dim_col).size()
            defect_rate_df = (defects_by_dim / total_by_dim * 100).fillna(0).reset_index(name='Taxa de Defeitos (%)')
            defect_rate_df = defect_rate_df[defect_rate_df[dim_col].isin(by_dim_tp[dim_col])]

            fig_defect = px.bar(defect_rate_df, x=dim_col, y='Taxa de Defeitos (%)', title=f'Taxa de Defeitos por {dim_title}')
            fig_defect.update_traces(marker_color='red')
            fig_defect.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))
            
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
        fig_pie.update_layout(height=500)
        graphs.append(dcc.Graph(figure=fig_pie))

        # Lead Time por Tipo
        fig_lt = px.bar(by_tipo, x='Tipo', y='LeadTime_Mediano', title='Lead Time Mediano por Tipo', color='Tipo', color_discrete_map=color_map)
        fig_lt.update_layout(height=500)
        graphs.append(dcc.Graph(figure=fig_lt))

        # Throughput por Subtipo
        if 'WorkItemSubType' in df.columns and not df['WorkItemSubType'].dropna().empty:
            by_subtipo = df.groupby('WorkItemSubType').size().reset_index(name='Throughput').sort_values('Throughput', ascending=False)
            fig_subtipo = px.bar(by_subtipo, x='WorkItemSubType', y='Throughput', title='Throughput por Subtipo')
            fig_subtipo.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))
            graphs.append(dcc.Graph(figure=fig_subtipo))

        return html.Div(graphs)

    if tab == 'tab-tendencias':
        tp = df.dropna(subset=['DataDone']).copy()
        tp['Semana'] = weekly_bucket_start(tp['DataDone'])
        tp = tp.groupby('Semana').size().reset_index(name='Throughput')
        fig_tp = go.Figure()
        fig_tp.add_trace(go.Scatter(x=tp['Semana'], y=tp['Throughput'], mode='lines+markers', name='Throughput'))
        add_statistical_lines(fig_tp, tp['Semana'], tp['Throughput'])
        fig_tp.update_layout(title='Throughput Semanal (P15, P85, P95, Média, MM5)', height=600, xaxis_tickangle=-45, margin=dict(b=130))

        # Trend Direction
        ma5_tp = tp['Throughput'].rolling(5, min_periods=1).mean()
        trend_direction = '→'
        if len(ma5_tp) >= 5:
            last_ma = ma5_tp.iloc[-1]
            prev_ma = ma5_tp.iloc[-5]
            if prev_ma > 0:
                if last_ma > prev_ma * 1.1: trend_direction = '↑'
                elif last_ma < prev_ma * 0.9: trend_direction = '↓'

        # WIP e Lead Time média móvel
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)
        df_trend_base = fato.copy()
        if projeto: df_trend_base = df_trend_base[df_trend_base['Projeto'] == projeto]
        if responsavel: df_trend_base = df_trend_base[df_trend_base['Responsavel'] == responsavel]
        # Lead Time Trend
        lt_weekly = df.dropna(subset=['DataDone', 'LeadTime_Dias']).copy()
        lt_weekly['Semana'] = weekly_bucket_start(lt_weekly['DataDone'])
        lt_weekly = lt_weekly.groupby('Semana', as_index=False).agg(LeadTime_Dias=('LeadTime_Dias', 'mean'))

        # WIP Trend
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_trend_base[(df_trend_base['DataInProgress'] <= week_end) & ((df_trend_base['DataDone'] > week_end) | pd.isna(df_trend_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        wip_trend_df = pd.DataFrame(wip_trend_data)

        # Create figure with secondary y-axis
        fig_wip_lt = make_subplots(specs=[[{"secondary_y": True}]])
        if not wip_trend_df.empty:
            fig_wip_lt.add_trace(go.Scatter(x=wip_trend_df['Semana'], y=wip_trend_df['WIP'], name="WIP", mode='lines+markers'), secondary_y=False)
            add_statistical_lines(fig_wip_lt, wip_trend_df['Semana'], wip_trend_df['WIP'], name_prefix='WIP ', secondary_y=False)
        if not lt_weekly.empty:
            fig_wip_lt.add_trace(go.Scatter(x=lt_weekly['Semana'], y=lt_weekly['LeadTime_Dias'], name="Lead Time", mode='lines+markers'), secondary_y=True)
            add_statistical_lines(fig_wip_lt, lt_weekly['Semana'], lt_weekly['LeadTime_Dias'], name_prefix='LT ', secondary_y=True)

        fig_wip_lt.update_layout(title_text="Tendência Semanal de WIP e Lead Time", height=600, margin=dict(b=130))
        fig_wip_lt.update_xaxes(title_text="Semana", tickangle=-45)
        fig_wip_lt.update_yaxes(title_text="Contagem de WIP", secondary_y=False)
        fig_wip_lt.update_yaxes(title_text="Lead Time Médio (dias)", secondary_y=True)

        return html.Div([
            create_kpi_card('Direção da Tendência (Throughput)', trend_direction, class_name='twelve columns'),
            dcc.Graph(figure=fig_tp),
            dcc.Graph(figure=fig_wip_lt)
        ])

    if tab == 'tab-throughput-tipo':
        tp = df.dropna(subset=['DataDone']).copy()
        tp['Semana'] = weekly_bucket_start(tp['DataDone'])
        tp = tp.groupby(['Semana', 'Tipo']).size().reset_index(name='Throughput')
        fig = px.line(tp, x='Semana', y='Throughput', color='Tipo', title='Throughput por Tipo (semanal)', color_discrete_map=color_map)
        # Adiciona linhas estatísticas para o throughput total por semana
        tp_total = tp.groupby('Semana')['Throughput'].sum().reset_index()
        add_statistical_lines(fig, tp_total['Semana'], tp_total['Throughput'], name_prefix='Total ')
        fig.update_layout(height=600, xaxis_tickangle=-45, margin=dict(b=130))
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
                               height=400, template='plotly_white')
        fig_breakdown.update_layout(barmode='stack', yaxis_title=None, yaxis_showticklabels=False, legend_title_text='Componente')

        fig_scatter_eff = px.scatter(df_eff, x='Eficiencia', y='EficienciaAjustada',
                                     color='Tipo', hover_data=['ItemID'], title='Eficiência Simples vs. Ajustada',
                                     labels={'Eficiencia': 'Eficiência Simples', 'EficienciaAjustada': 'Eficiência Ajustada'}, color_discrete_map=color_map)
        fig_scatter_eff.update_layout(height=550)
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

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
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

        wip_df = pd.concat(wip_weekly_data, ignore_index=True)
        if wip_df.empty:
            return html.Div('Sem dados de WIP para o período e filtros selecionados.')

        summary_data = []
        for person in wip_df['Responsavel'].unique():
            person_wip = wip_df[wip_df['Responsavel'] == person]
            wip_medio = person_wip['WIP'].mean()
            wip_max = person_wip['WIP'].max()
            last_week_data = person_wip[person_wip['Semana'] == person_wip['Semana'].max()]
            items_ativos_fim = last_week_data['WIP'].iloc[0] if not last_week_data.empty else 0
            
            summary_data.append({'Responsável': person, 'WIP Médio Semanal': wip_medio, 'WIP Máximo na Semana': wip_max, 'Items Ativos no Fim': items_ativos_fim})

        summary_df = pd.DataFrame(
            summary_data,
            columns=['Responsável', 'WIP Médio Semanal', 'WIP Máximo na Semana', 'Items Ativos no Fim']
        )
        if summary_df.empty:
            return html.Div('Sem dados consolidados de WIP por responsável para o período e filtros selecionados.')
        summary_df = summary_df.sort_values('WIP Médio Semanal', ascending=False)

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
        fig_wip_avg.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        if responsavel:
            df_trend = wip_df
        else:
            top_responsaveis = summary_df.head(5)['Responsável'].tolist()
            df_trend = wip_df[wip_df['Responsavel'].isin(top_responsaveis)]
            
        fig_wip_trend = px.line(df_trend, x='Semana', y='WIP', color='Responsavel', title='Tendência do WIP Semanal (Top 5 Responsáveis)', markers=True)
        # Adiciona linhas estatísticas para o WIP total por semana
        wip_total_weekly = df_trend.groupby('Semana')['WIP'].sum().reset_index()
        if not wip_total_weekly.empty:
            add_statistical_lines(fig_wip_trend, wip_total_weekly['Semana'], wip_total_weekly['WIP'], name_prefix='Total ')
        fig_wip_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        return html.Div([
            html.H3("Análise de WIP por Pessoa", style={'textAlign': 'center'}),
            html.H4("Resumo do Período", style={'textAlign': 'center', 'marginTop': '30px'}),
            kpi_table,
            dcc.Graph(figure=fig_wip_avg),
            dcc.Graph(figure=fig_wip_trend),
        ])

    if tab == 'tab-estatistica':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        # Base sem filtro de DataDone para calcular WIP
        df_base = fato.copy()
        if projeto:
            df_base = df_base[df_base['Projeto'] == projeto]
        if tipo:
            df_base = df_base[df_base['Tipo'] == tipo]
        if responsavel:
            df_base = df_base[df_base['Responsavel'] == responsavel]
        # Itens concluídos no período (para Lead Time)
        df_done = df_base[
            (df_base['DataDone'] >= start_date_ts) &
            (df_base['DataDone'] <= end_date_ts)
        ]

        # --- 1. Estatísticas de Lead Time ---
        lead_time_stats = {}
        if not df_done.empty and 'LeadTime_Dias' in df_done.columns and not df_done['LeadTime_Dias'].dropna().empty:
            lt = df_done['LeadTime_Dias'].dropna()
            lead_time_stats = {
                'Contagem': int(len(lt)),
                'Média': f"{lt.mean():.2f}",
                'Mediana (P50)': f"{lt.median():.2f}",
                'Desvio Padrão': f"{lt.std():.2f}",
                'Mínimo': f"{lt.min():.2f}",
                'Máximo': f"{lt.max():.2f}",
                'P25': f"{lt.quantile(0.25):.2f}",
                'P75': f"{lt.quantile(0.75):.2f}",
                'P85': f"{lt.quantile(0.85):.2f}",
                'P95': f"{lt.quantile(0.95):.2f}",
                'Coef. Variação (%)': f"{(lt.std() / lt.mean() * 100):.2f}" if lt.mean() > 0 else '—',
                'Amplitude': f"{lt.max() - lt.min():.2f}",
                'IQR (P75-P25)': f"{lt.quantile(0.75) - lt.quantile(0.25):.2f}",
                'Assimetria (Skewness)': f"{lt.skew():.2f}",
                'Curtose': f"{lt.kurtosis():.2f}",
            }

        lt_table_data = [{'Estatística': k, 'Valor': v} for k, v in lead_time_stats.items()]
        lt_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=lt_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if lt_table_data else html.P('Sem dados de Lead Time para o período selecionado.')

        # Gráficos de Lead Time
        fig_lt_hist = {}
        fig_lt_box = {}
        if not df_done.empty and 'LeadTime_Dias' in df_done.columns and not df_done['LeadTime_Dias'].dropna().empty:
            fig_lt_hist = px.histogram(df_done, x='LeadTime_Dias', nbins=30,
                                       title='Distribuição do Lead Time (dias)',
                                       labels={'LeadTime_Dias': 'Lead Time (dias)', 'count': 'Frequência'},
                                       height=500)
            lt_mean_val = df_done['LeadTime_Dias'].mean()
            lt_median_val = df_done['LeadTime_Dias'].median()
            lt_p85_val = df_done['LeadTime_Dias'].quantile(0.85)
            fig_lt_hist.add_vline(x=lt_mean_val, line_dash="dash", line_color="red", annotation_text=f"Média: {lt_mean_val:.1f}")
            fig_lt_hist.add_vline(x=lt_median_val, line_dash="dash", line_color="blue", annotation_text=f"Mediana: {lt_median_val:.1f}")
            fig_lt_hist.add_vline(x=lt_p85_val, line_dash="dash", line_color="orange", annotation_text=f"P85: {lt_p85_val:.1f}")

            fig_lt_box = px.box(df_done, y='LeadTime_Dias', title='Box Plot do Lead Time (dias)',
                                labels={'LeadTime_Dias': 'Lead Time (dias)'}, points='all', height=500)

        # --- 2. Estatísticas de Throughput (semanal) ---
        tp_weekly = df_done.dropna(subset=['DataDone']).copy()
        tp_weekly['Semana'] = weekly_bucket_start(tp_weekly['DataDone'])
        tp_weekly = tp_weekly.groupby('Semana').size().reset_index(name='Throughput')

        tp_stats = {}
        if not tp_weekly.empty:
            tp = tp_weekly['Throughput']
            tp_stats = {
                'Semanas Analisadas': int(len(tp)),
                'Total de Itens': int(tp.sum()),
                'Média / Semana': f"{tp.mean():.2f}",
                'Mediana / Semana': f"{tp.median():.2f}",
                'Desvio Padrão': f"{tp.std():.2f}",
                'Mínimo / Semana': int(tp.min()),
                'Máximo / Semana': int(tp.max()),
                'P25': f"{tp.quantile(0.25):.2f}",
                'P75': f"{tp.quantile(0.75):.2f}",
                'P85': f"{tp.quantile(0.85):.2f}",
                'P95': f"{tp.quantile(0.95):.2f}",
                'Coef. Variação (%)': f"{(tp.std() / tp.mean() * 100):.2f}" if tp.mean() > 0 else '—',
            }

        tp_table_data = [{'Estatística': k, 'Valor': str(v)} for k, v in tp_stats.items()]
        tp_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=tp_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if tp_table_data else html.P('Sem dados de Throughput para o período selecionado.')

        # Gráficos de Throughput
        fig_tp_hist = {}
        fig_tp_line = {}
        if not tp_weekly.empty:
            fig_tp_hist = px.histogram(tp_weekly, x='Throughput', nbins=15,
                                       title='Distribuição do Throughput Semanal',
                                       labels={'Throughput': 'Throughput (itens/semana)', 'count': 'Frequência'},
                                       height=500)
            tp_mean_val = tp_weekly['Throughput'].mean()
            fig_tp_hist.add_vline(x=tp_mean_val, line_dash="dash", line_color="red", annotation_text=f"Média: {tp_mean_val:.1f}")

            tp_weekly_sorted = tp_weekly.sort_values('Semana')
            fig_tp_line = px.bar(tp_weekly_sorted, x='Semana', y='Throughput',
                                 title='Throughput Semanal ao Longo do Tempo',
                                 labels={'Semana': 'Semana', 'Throughput': 'Itens Concluídos'},
                                 height=500)
            fig_tp_line.update_layout(xaxis_tickangle=-45, margin=dict(b=130))

        # --- 3. Estatísticas de WIP (semanal) ---
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_weekly_values = []
        for week_end in weeks:
            wip_count = len(df_base[
                (df_base['DataInProgress'] <= week_end) &
                ((df_base['DataDone'] > week_end) | pd.isna(df_base['DataDone']))
            ])
            wip_weekly_values.append({'Semana': week_end, 'WIP': wip_count})
        wip_weekly_df = pd.DataFrame(wip_weekly_values)

        wip_stats = {}
        if not wip_weekly_df.empty and len(wip_weekly_df) > 0:
            w = wip_weekly_df['WIP']
            wip_stats = {
                'Semanas Analisadas': int(len(w)),
                'Média': f"{w.mean():.2f}",
                'Mediana': f"{w.median():.2f}",
                'Desvio Padrão': f"{w.std():.2f}",
                'Mínimo': int(w.min()),
                'Máximo': int(w.max()),
                'P25': f"{w.quantile(0.25):.2f}",
                'P75': f"{w.quantile(0.75):.2f}",
                'P85': f"{w.quantile(0.85):.2f}",
                'P95': f"{w.quantile(0.95):.2f}",
                'Coef. Variação (%)': f"{(w.std() / w.mean() * 100):.2f}" if w.mean() > 0 else '—',
                'WIP Atual (última semana)': int(w.iloc[-1]) if len(w) > 0 else '—',
            }

        wip_table_data = [{'Estatística': k, 'Valor': str(v)} for k, v in wip_stats.items()]
        wip_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=wip_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if wip_table_data else html.P('Sem dados de WIP para o período selecionado.')

        # Gráficos de WIP
        fig_wip_line = {}
        fig_wip_hist = {}
        if not wip_weekly_df.empty:
            fig_wip_line = px.line(wip_weekly_df, x='Semana', y='WIP',
                                   title='WIP Semanal ao Longo do Tempo', markers=True, height=500)
            fig_wip_line.update_layout(xaxis_tickangle=-45, margin=dict(b=130))
            fig_wip_hist = px.histogram(wip_weekly_df, x='WIP', nbins=15,
                                        title='Distribuição do WIP Semanal',
                                        labels={'WIP': 'WIP (itens)', 'count': 'Frequência'},
                                        height=500)

        # --- Layout da aba ---
        filtro_info = f"Projeto: {projeto or 'Todos'} | Tipo: {tipo or 'Todos'}"

        return html.Div([
            html.H3("Estatística Descritiva", style={'textAlign': 'center'}),
            html.P(filtro_info, style={'textAlign': 'center', 'color': '#666', 'marginBottom': '30px'}),

            # Lead Time
            html.H4("Lead Time (dias)", style={'textAlign': 'center', 'marginTop': '30px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(lt_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_lt_hist),
                    dcc.Graph(figure=fig_lt_box),
                ], className='seven columns'),
            ], className='row'),

            # Throughput
            html.H4("Throughput (semanal)", style={'textAlign': 'center', 'marginTop': '40px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(tp_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_tp_hist),
                    dcc.Graph(figure=fig_tp_line),
                ], className='seven columns'),
            ], className='row'),

            # WIP
            html.H4("WIP - Work in Progress (semanal)", style={'textAlign': 'center', 'marginTop': '40px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(wip_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_wip_line),
                    dcc.Graph(figure=fig_wip_hist),
                ], className='seven columns'),
            ], className='row'),
        ])

    if tab == 'tab-fila-capacidade':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        # Base para cálculo de capacidade: usa dados importados e filtros ativos.
        df_capacity_base = fato.copy()
        if projeto:
            df_capacity_base = df_capacity_base[df_capacity_base['Projeto'] == projeto]
        if tipo:
            df_capacity_base = df_capacity_base[df_capacity_base['Tipo'] == tipo]
        if responsavel:
            df_capacity_base = df_capacity_base[df_capacity_base['Responsavel'] == responsavel]

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts + pd.Timedelta(days=7), freq='W-MON')
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal de capacidade de fila.')

        weekly_rows = []
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = len(df_capacity_base[
                (df_capacity_base['DataInProgress'] >= week_start) &
                (df_capacity_base['DataInProgress'] < week_end)
            ])
            throughput = len(df_capacity_base[
                (df_capacity_base['DataDone'] >= week_start) &
                (df_capacity_base['DataDone'] < week_end)
            ])
            weekly_rows.append({
                'Semana': str(week_start.date()),
                'Chegadas': arrivals,
                'Throughput': throughput,
            })

        weekly_df = pd.DataFrame(weekly_rows)
        n_weeks = len(weekly_df)
        lambda_base = weekly_df['Chegadas'].mean() if n_weeks > 0 else 0.0
        mu = weekly_df['Throughput'].mean() if n_weeks > 0 else 0.0
        lambda_stress = lambda_base * 1.18

        if mu <= 0:
            return html.Div('Não há throughput suficiente no período para calcular capacidade de fila (μ = 0).')

        base = calculate_mm1_metrics(lambda_base, mu)
        stress = calculate_mm1_metrics(lambda_stress, mu)
        if base is None or stress is None:
            return html.Div('Não foi possível calcular métricas de fila com os dados selecionados.')

        lq_growth_pct = ((stress['Lq'] - base['Lq']) / base['Lq']) * 100 if np.isfinite(base['Lq']) and base['Lq'] > 0 else np.nan
        w_growth_pct = ((stress['W'] - base['W']) / base['W']) * 100 if np.isfinite(base['W']) and base['W'] > 0 else np.nan
        arrival_growth_pct = ((lambda_stress - lambda_base) / lambda_base) * 100 if lambda_base > 0 else np.nan

        def fmt_metric_value(value, unit=''):
            if value is None or (isinstance(value, float) and not np.isfinite(value)):
                return 'Sistema instável (ρ >= 1)'
            return f"{value:.2f}{unit}"

        period_label = f"{start_date_ts.date()} a {end_date_ts.date()}"
        efficiency = 1 - base['rho'] if base is not None and np.isfinite(base['rho']) else np.nan
        kpi_data = [
            {'Métrica': 'Período analisado', 'Valor': period_label},
            {'Métrica': 'Semanas analisadas', 'Valor': f"{n_weeks}"},
            {'Métrica': 'Taxa de chegada média (λ)', 'Valor': f"{base['lambda']:.2f} tarefas/semana"},
            {'Métrica': 'Taxa de vazão média (μ)', 'Valor': f"{base['mu']:.2f} tarefas/semana"},
            {'Métrica': 'Utilização (ρ)', 'Valor': fmt_metric_value(base['rho'])},
            {'Métrica': 'Eficiência (1 - ρ)', 'Valor': fmt_metric_value(efficiency)},
            {'Métrica': 'Lq - fila média', 'Valor': fmt_metric_value(base['Lq'], ' tarefas')},
            {'Métrica': 'Wq - espera média na fila', 'Valor': fmt_metric_value(base['Wq'], ' semanas')},
            {'Métrica': 'W - tempo total no sistema', 'Valor': fmt_metric_value(base['W'], ' semanas')},
            {'Métrica': 'Cenário de estresse (+18% em λ)', 'Valor': f"{arrival_growth_pct:.1f}%"},
            {'Métrica': 'Lq no estresse', 'Valor': fmt_metric_value(stress['Lq'], ' tarefas')},
            {'Métrica': 'W no estresse', 'Valor': fmt_metric_value(stress['W'], ' semanas')},
            {'Métrica': 'Aumento de fila (Lq)', 'Valor': f"{lq_growth_pct:.0f}%" if np.isfinite(lq_growth_pct) else 'N/A'},
            {'Métrica': 'Aumento de tempo total (W)', 'Valor': f"{w_growth_pct:.0f}%" if np.isfinite(w_growth_pct) else 'N/A'},
        ]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        scenario_df = pd.DataFrame([
            {
                'Cenário': 'Base',
                'λ': base['lambda'],
                'μ': base['mu'],
                'ρ': round(base['rho'], 2),
                'Lq (tarefas)': round(base['Lq'], 2) if np.isfinite(base['Lq']) else 'Instável',
                'Wq (semanas)': round(base['Wq'], 2) if np.isfinite(base['Wq']) else 'Instável',
                'W (semanas)': round(base['W'], 2) if np.isfinite(base['W']) else 'Instável',
            },
            {
                'Cenário': 'Aumento de demanda (+18%)',
                'λ': stress['lambda'],
                'μ': stress['mu'],
                'ρ': round(stress['rho'], 2),
                'Lq (tarefas)': round(stress['Lq'], 2) if np.isfinite(stress['Lq']) else 'Instável',
                'Wq (semanas)': round(stress['Wq'], 2) if np.isfinite(stress['Wq']) else 'Instável',
                'W (semanas)': round(stress['W'], 2) if np.isfinite(stress['W']) else 'Instável',
            },
        ])
        scenario_table = dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in scenario_df.columns],
            data=scenario_df.to_dict('records'),
            style_cell={'textAlign': 'center', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        )

        rho_series = np.linspace(0.50, 0.98, 49)
        lambda_series = rho_series * mu
        lq_series = (rho_series ** 2) / (1 - rho_series)
        w_series = (lq_series / lambda_series) + (1 / mu)

        fig_queue = make_subplots(specs=[[{"secondary_y": True}]])
        fig_queue.add_trace(
            go.Scatter(x=rho_series, y=w_series, mode='lines', name='W - Tempo total (semanas)', line=dict(color='royalblue', width=3)),
            secondary_y=False
        )
        fig_queue.add_trace(
            go.Scatter(x=rho_series, y=lq_series, mode='lines', name='Lq - Fila média (tarefas)', line=dict(color='firebrick', width=3)),
            secondary_y=True
        )
        fig_queue.add_vline(x=0.8, line_dash='dash', line_color='orange')
        fig_queue.add_vline(x=0.9, line_dash='dash', line_color='red')
        fig_queue.add_annotation(x=0.72, y=max(w_series) * 0.15, text='Baixa utilização (ρ < 0.8)', showarrow=False)
        fig_queue.add_annotation(x=0.84, y=max(w_series) * 0.35, text='Intermediária (ρ = 0.8)', showarrow=False)
        fig_queue.add_annotation(x=0.93, y=max(w_series) * 0.70, text='Alta utilização (ρ > 0.9)', showarrow=False)
        fig_queue.update_layout(
            title='Sensibilidade do Sistema à Utilização (Modelo M/M/1)',
            height=580,
            template='plotly_white',
            xaxis_title='Taxa de Utilização (ρ)',
            margin=dict(t=60, b=50),
        )
        fig_queue.update_yaxes(title_text='W - Tempo total no sistema (semanas)', secondary_y=False)
        fig_queue.update_yaxes(title_text='Lq - Comprimento médio da fila (tarefas)', secondary_y=True)

        insight_block = html.Div([
            html.H4("Mensagem de Gestão", style={'marginBottom': '10px'}),
            html.P('"Ah, é só mais uma demanda..." parece pequeno, mas o impacto é exponencial quando ρ se aproxima de 1.'),
            html.P('Associe custo financeiro às demandas na fila para evidenciar o custo de atraso no sistema.'),
        ], style={'padding': '14px', 'backgroundColor': '#f9f9f9', 'border': '1px solid #e0e0e0', 'borderRadius': '8px'})

        return html.Div([
            html.H3("Capacidade de Fila e Impacto de Utilização", style={'textAlign': 'center'}),
            html.P("Modelo M/M/1 com taxas calculadas a partir dos dados importados e filtros ativos.",
                   style={'textAlign': 'center', 'color': '#666'}),
            html.Div(kpi_table, style={'width': '62%', 'margin': '20px auto'}),
            html.H4("Comparação de Cenários", style={'textAlign': 'center', 'marginTop': '24px'}),
            scenario_table,
            dcc.Graph(figure=fig_queue),
            insight_block,
        ])

    return html.Div('Aba não encontrada')


@app.callback(
    Output('performance-metric-chart', 'children'),
    Input('performance-table', 'active_cell'),
    Input('performance-table', 'data'),
    prevent_initial_call=True
)
def render_metric_chart(active_cell, table_data):
    if not active_cell or not table_data:
        return html.Div()

    row_idx = active_cell['row']
    row = table_data[row_idx]
    metric_name = row['Métrica']

    # Extrair semanas (colunas exceto 'Métrica') e valores numéricos
    week_labels = [col for col in row.keys() if col != 'Métrica']
    values = []
    for wl in week_labels:
        val_str = str(row[wl]).replace('%', '').replace(',', '.').strip()
        try:
            values.append(float(val_str))
        except (ValueError, TypeError):
            values.append(None)

    # Filtrar semanas com valores válidos
    valid = [(w, v) for w, v in zip(week_labels, values) if v is not None]
    if not valid:
        return html.Div(
            f'A métrica "{metric_name}" não possui dados numéricos para exibir.',
            style={'textAlign': 'center', 'padding': '20px', 'color': '#999'}
        )

    weeks_valid, vals_valid = zip(*valid)
    weeks_valid = list(weeks_valid)
    vals_valid = list(vals_valid)

    # Criar gráfico de linha
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks_valid, y=vals_valid,
        mode='lines+markers', name=metric_name,
        line=dict(width=2.5, color='#0074D9'),
        marker=dict(size=8)
    ))

    # Adicionar linhas de percentis
    s = pd.Series(vals_valid)
    if len(s) >= 2:
        add_statistical_lines(fig, weeks_valid, s)

    fig.update_layout(
        title=f'{metric_name} — Tendência Semanal',
        xaxis_title='Semana',
        yaxis_title=metric_name,
        template='plotly_white',
        height=550,
        margin=dict(t=60, b=130),
        xaxis_tickangle=-45,
    )

    return html.Div([
        dcc.Graph(figure=fig)
    ], style={'marginTop': '20px'})


def create_table(df, table_id='table-main', title='Tabela'):
    if df is None or getattr(df, 'empty', True):
        return html.Div('Sem dados para exibir')
    return html.Div([html.H3(title), dash_table.DataTable(id=table_id, columns=[{'name':c,'id':c} for c in df.columns], data=df.head(200).to_dict('records'), page_size=20, style_table={'overflowX':'auto'})])

def create_generic_datatable(df, table_id, title):
    return create_table(df, table_id=table_id, title=title)

if __name__ == '__main__':
    app.run(debug=True)
