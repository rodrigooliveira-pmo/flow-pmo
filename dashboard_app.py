import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import glob
import os
import hashlib
import urllib.request

# --- 1. CONFIGURAÇÃO E CARREGAMENTO DE DADOS ---

def find_latest_file(folder, prefix):
    """Encontra o arquivo mais recente em uma pasta com um determinado prefixo."""
    files = glob.glob(os.path.join(folder, f'{prefix}*.xlsx'))
    if not files:
        return None
    return max(files, key=os.path.getctime)

if os.name == 'nt':
    LEGACY_DATA_FOLDER = r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
else:
    LEGACY_DATA_FOLDER = os.path.join(os.path.expanduser('~'), 'Library', 'CloudStorage', 'OneDrive-W1', 'Documentos', 'Dados')


def _existing_dirs(paths):
    out = []
    seen = set()
    for raw in paths:
        if not raw:
            continue
        p = os.path.abspath(raw.strip())
        if p in seen:
            continue
        seen.add(p)
        if os.path.isdir(p):
            out.append(p)
    return out


def _candidate_data_folders():
    env_dirs = os.getenv('FLOW_PMO_DATA_DIRS', '').strip()
    split_env_dirs = [p for p in env_dirs.split(os.pathsep) if p.strip()]
    explicit_dir = os.getenv('FLOW_PMO_DATA_DIR', '').strip()
    legacy_override = os.getenv('DATA_FOLDER', '').strip()
    base_dir = os.path.dirname(__file__)
    return _existing_dirs([
        explicit_dir,
        legacy_override,
        *split_env_dirs,
        os.path.join(base_dir, 'data'),
        base_dir,
        LEGACY_DATA_FOLDER,
    ])


def _download_dashboard_output_from_url(url):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'dashboard_output_{file_key}.xlsx')
    if not os.path.exists(out_file):
        urllib.request.urlretrieve(url, out_file)
    return out_file


def _resolve_dashboard_file(data_folders):
    explicit_file = os.getenv('FLOW_PMO_DASHBOARD_OUTPUT_FILE', '').strip()
    if explicit_file:
        candidate = explicit_file if os.path.isabs(explicit_file) else os.path.join(os.path.dirname(__file__), explicit_file)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise FileNotFoundError(f'FLOW_PMO_DASHBOARD_OUTPUT_FILE aponta para arquivo inexistente: {candidate}')

    file_url = os.getenv('FLOW_PMO_DASHBOARD_OUTPUT_URL', '').strip()
    if file_url:
        return _download_dashboard_output_from_url(file_url)

    for folder in data_folders:
        match = find_latest_file(folder, 'dashboard_output_')
        if match:
            return match

    raise FileNotFoundError(
        "Nenhum arquivo 'dashboard_output_*.xlsx' foi encontrado. Configure FLOW_PMO_DASHBOARD_OUTPUT_FILE "
        "ou FLOW_PMO_DASHBOARD_OUTPUT_URL, ou adicione o arquivo em uma destas pastas: "
        + ', '.join(data_folders or ['(nenhuma pasta encontrada)'])
    )


DATA_FOLDERS = _candidate_data_folders()
DASHBOARD_FILE_PATH = _resolve_dashboard_file(DATA_FOLDERS)

print(f'Carregando dados do arquivo: {DASHBOARD_FILE_PATH}')

# Carrega todas as abas do arquivo Excel para um dicionário de DataFrames
try:
    xls = pd.ExcelFile(DASHBOARD_FILE_PATH)
    sheet_names = xls.sheet_names
    dfs = {}
    for sheet in sheet_names:
        dfs[sheet] = pd.read_excel(xls, sheet_name=sheet)
    print(f"Abas carregadas com sucesso: {list(dfs.keys())}")
except FileNotFoundError:
    raise

# --- 2. FUNÇÕES AUXILIARES PARA GERAR LAYOUTS DAS ABAS ---

def create_generic_datatable(df, table_id, title):
    """Cria um Dash DataTable padrão para uma aba."""
    if df is None or df.empty:
        return html.Div(f"Dados para '{title}' não encontrados ou a aba está vazia.")
    
    # Converte colunas de data para um formato legível
    for col in df.select_dtypes(include=['datetime64[ns]']).columns:
        df[col] = df[col].dt.strftime('%Y-%m-%d')

    return html.Div([
        html.H3(title, style={'marginTop': '20px'}),
        dash_table.DataTable(
            id=table_id,
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            page_size=15,
            filter_action="native",
            sort_action="native",
            style_table={'overflowX': 'auto'},
            style_cell={
                'height': 'auto',
                'minWidth': '90px', 'width': '120px', 'maxWidth': '180px',
                'whiteSpace': 'normal',
                'textAlign': 'left'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            }
        )
    ])

def create_layout_dimensional():
    """Cria o layout para a aba de Análise Dimensional com gráfico."""
    df = dfs.get('Análise Dimensional')
    if df is None or df.empty:
        return html.Div("Dados para 'Análise Dimensional' não encontrados.")

    dimensoes = df['Dimensão'].unique()

    return html.Div([
        html.H3('Análise por Dimensão', style={'marginTop': '20px'}),
        html.Label('Selecione a Dimensão para Análise:'),
        dcc.Dropdown(
            id='dropdown-dimensional',
            options=[{'label': d, 'value': d} for d in dimensoes],
            value=dimensoes[0]
        ),
        html.Div([
            dcc.Graph(id='graph-dimensional-throughput', className='six columns', style={'height': '500px'}),
            dcc.Graph(id='graph-dimensional-defeitos', className='six columns', style={'height': '500px'}),
        ], className='row')
    ])

def create_layout_throughput_tipo():
    """Cria o layout para a aba Throughput por Tipo."""
    df = dfs.get('Throughput por Tipo')
    if df is None or df.empty:
        return html.Div("Dados para 'Throughput por Tipo' não encontrados.")

    tipos_item = df['Tipo Item'].unique()

    return html.Div([
        html.H3('Throughput Semanal por Tipo de Item', style={'marginTop': '20px'}),
        html.Label('Selecione o Tipo de Item:'),
        dcc.Dropdown(
            id='dropdown-throughput-tipo',
            options=[{'label': t, 'value': t} for t in tipos_item],
            value=tipos_item[0] if len(tipos_item) > 0 else None
        ),
        dcc.Graph(id='graph-throughput-tipo-trend', style={'height': '600px'}),
    ])

def create_layout_wip_pessoa(df_filtered):
    """Cria o layout para a aba WIP por Pessoa."""
    if df_filtered is None or df_filtered.empty:
        return html.Div("Dados para 'WIP por Pessoa' não encontrados para este projeto.")

    return html.Div([
        html.H3('Work In Progress (WIP) por Pessoa', style={'marginTop': '20px'}),
        dcc.Graph(id='graph-wip-pessoa-ranking', style={'height': '600px'}),
        create_generic_datatable(df_filtered, 'table-wip-pessoa', 'Dados Detalhados de WIP por Pessoa')
    ])

def create_layout_analise_tipos(df_filtered):
    """Cria o layout para a aba Análise Tipos."""
    if df_filtered is None or df_filtered.empty:
        return html.Div("Dados para 'Análise Tipos' não encontrados para este projeto.")

    return html.Div([
        html.H3('Análise por Tipo de Item', style={'marginTop': '20px'}),
        html.Div([
            dcc.Graph(id='graph-tipos-distribuicao', className='six columns', style={'height': '500px'}),
            dcc.Graph(id='graph-tipos-leadtime', className='six columns', style={'height': '500px'}),
        ], className='row'),
        create_generic_datatable(df_filtered, 'table-analise-tipos', 'Dados Detalhados por Tipo')
    ])

def create_layout_analise_fluxo(selected_project):
    """Consolida análises dimensional, tipos e eficiência em uma única aba."""
    df_tipos = dfs.get('Análise Tipos')
    if df_tipos is not None and not df_tipos.empty and 'Projeto' in df_tipos.columns:
        df_tipos = df_tipos[df_tipos['Projeto'] == selected_project].copy()

    df_eff = dfs.get('Análise Eficiência')
    if df_eff is not None and not df_eff.empty and 'Projeto' in df_eff.columns:
        df_eff = df_eff[df_eff['Projeto'] == selected_project].copy()

    return html.Div([
        html.H3('Análise Fluxo', style={'marginTop': '20px'}),
        html.P(
            'Visualizações consolidadas de análise dimensional, tipos e eficiência de fluxo.',
            style={'color': '#666', 'marginTop': '-8px'}
        ),
        html.Hr(),
        create_layout_dimensional(),
        html.Hr(),
        create_layout_analise_tipos(df_tipos),
        html.Hr(),
        create_generic_datatable(df_eff, 'table-analise-eficiencia-fluxo', 'Análise Eficiência de Fluxo')
    ])

def create_layout_tendencias():
    """Cria o layout para a aba de Tendências."""
    return html.Div([
        html.H3('Análise de Tendências', style={'marginTop': '20px'}),
        dcc.Graph(id='graph-tendencias-throughput', style={'height': '600px'}),
        dcc.Graph(id='graph-tendencias-wip-leadtime', style={'height': '600px'})
    ])

def create_layout_lead_time():
    """Cria o layout para a aba dedicada de Lead Time."""
    return html.Div([
        html.H3('Lead Time', style={'marginTop': '20px'}),
        html.P(
            'Distribuição e tendência temporal de Lead Time com percentis, média e média móvel.',
            style={'color': '#666', 'marginTop': '-8px'}
        ),
        dcc.Graph(id='graph-leadtime-distribution', style={'height': '620px'}),
        dcc.Graph(id='graph-leadtime-trend', style={'height': '620px'})
    ])

# --- 3. INICIALIZAÇÃO DA APLICAÇÃO ---
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'], suppress_callback_exceptions=True)
app.title = "Dashboard de Métricas de Fluxo"

# --- 4. LAYOUT PRINCIPAL DA APLICAÇÃO ---
app.layout = html.Div(children=[
    html.H1(children='Dashboard de Métricas de Fluxo', style={'textAlign': 'center', 'marginBottom': '20px'}),

    # Filtro Global de Projeto
    html.Div([
        html.Label('Selecione o Projeto:'),
        dcc.Dropdown(
            id='filtro-projeto',
            options=[{'label': proj, 'value': proj} for proj in sorted(dfs.get('Dashboard', pd.DataFrame(columns=['Projeto'])).get('Projeto', pd.Series(dtype=str)).unique())],
            value=sorted(dfs.get('Dashboard', pd.DataFrame(columns=['Projeto'])).get('Projeto', pd.Series(dtype=str)).unique())[0] if not dfs.get('Dashboard', pd.DataFrame()).empty else None,
            clearable=False
        ),
    ], style={'width': '50%', 'margin': 'auto', 'marginBottom': '20px'}),

    # Estrutura de Abas
    dcc.Tabs(id="tabs-main", value='tab-1-dashboard', children=[
        dcc.Tab(label='Dashboard', value='tab-1-dashboard'),
        dcc.Tab(label='Adv - Fluxo', value='tab-2-fluxo'),
        dcc.Tab(label='Adv - Estabilidade', value='tab-3-estabilidade'),
        dcc.Tab(label='Adv - Saúde Fluxo', value='tab-4-saude'),
        dcc.Tab(label='Adv - Qualidade', value='tab-5-qualidade'),
        dcc.Tab(label='Análise Fluxo', value='tab-6-analise-fluxo'),
        dcc.Tab(label='Tendências', value='tab-8-tendencias'),
        dcc.Tab(label='Tendências Completas', value='tab-9-tendencias-comp'),
        dcc.Tab(label='Throughput por Tipo', value='tab-10-throughput-tipo'),
        dcc.Tab(label='WIP por Pessoa', value='tab-12-wip-pessoa'),
        dcc.Tab(label='Lead Time', value='tab-13-lead-time'),
    ]),
    
    # Container para o conteúdo da aba selecionada
    html.Div(id='tabs-content', style={'padding': '20px'})
])

# --- 5. CALLBACKS PARA INTERATIVIDADE ---

# Callback principal para renderizar o conteúdo da aba selecionada
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs-main', 'value'),
    Input('filtro-projeto', 'value')
)
def render_tab_content(tab, selected_project):
    """Renderiza o conteúdo da aba com base na seleção e no filtro de projeto."""
    if not selected_project:
        return html.Div("Por favor, selecione um projeto.")

    # Mapeia o valor da aba para o nome da planilha e o tipo de layout
    tab_map = {
        'tab-1-dashboard': ('Dashboard', 'table'),
        'tab-2-fluxo': ('Adv - Fluxo', 'table'),
        'tab-3-estabilidade': ('Adv - Estabilidade', 'table'),
        'tab-4-saude': ('Adv - Saúde Fluxo', 'table'),
        'tab-5-qualidade': ('Adv - Qualidade', 'table'),
        'tab-6-analise-fluxo': (None, 'analise_fluxo'), # Consolida gráficos/tabela
        'tab-8-tendencias': ('Tendências', 'tendencias'),
        'tab-9-tendencias-comp': ('Tendências Completas', 'table'),
        'tab-10-throughput-tipo': ('Throughput por Tipo', 'throughput_tipo'), # Gráfico
        'tab-12-wip-pessoa': ('WIP por Pessoa', 'wip_pessoa'), # Gráfico
        'tab-13-lead-time': ('Análise Eficiência', 'lead_time'), # Gráficos de Lead Time
    }

    sheet_name, layout_type = tab_map.get(tab, (None, None))

    if layout_type == 'analise_fluxo':
        return create_layout_analise_fluxo(selected_project)

    if not sheet_name or sheet_name not in dfs:
        return html.Div(f"Aba '{sheet_name}' não encontrada no arquivo de dados.")

    # Filtra o DataFrame pelo projeto selecionado
    df_filtered = dfs[sheet_name]
    if 'Projeto' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Projeto'] == selected_project]

    # Renderiza o layout apropriado
    if layout_type == 'table':
        return create_generic_datatable(df_filtered, f'table-{sheet_name}', sheet_name)
    elif layout_type == 'dimensional':
        return create_layout_dimensional()
    elif layout_type == 'tendencias':
        return create_layout_tendencias()
    elif layout_type == 'throughput_tipo':
        return create_layout_throughput_tipo()
    elif layout_type == 'wip_pessoa':
        return create_layout_wip_pessoa(df_filtered)
    elif layout_type == 'tipos':
        return create_layout_analise_tipos(df_filtered)
    elif layout_type == 'lead_time':
        return create_layout_lead_time()

    return html.Div("Tipo de layout não implementado.")

def _empty_figure(message):
    fig = go.Figure()
    fig.update_layout(
        template='plotly_white',
        xaxis={'visible': False},
        yaxis={'visible': False},
        annotations=[{
            'text': message,
            'xref': 'paper',
            'yref': 'paper',
            'x': 0.5,
            'y': 0.5,
            'showarrow': False,
            'font': {'size': 15}
        }]
    )
    return fig

def _lead_time_reference_stats(selected_project, lead_values=None):
    """Percentis/média de Lead Time por projeto (prioriza a aba Adv - Estabilidade)."""
    stats = {}

    df_est = dfs.get('Adv - Estabilidade')
    if df_est is not None and not df_est.empty and 'Projeto' in df_est.columns:
        est_row = df_est[df_est['Projeto'] == selected_project]
        if not est_row.empty:
            est_row = est_row.iloc[0]
            stats['p50'] = pd.to_numeric(est_row.get('Lead Time P50 (dias)'), errors='coerce')
            stats['p75'] = pd.to_numeric(est_row.get('Lead Time P75 (dias)'), errors='coerce')
            stats['p95'] = pd.to_numeric(est_row.get('Lead Time P95 (dias)'), errors='coerce')
            stats['mean'] = pd.to_numeric(est_row.get('Lead Time Médio (dias)'), errors='coerce')

    if lead_values is not None and len(lead_values) > 0:
        arr = np.asarray(lead_values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size > 0:
            fallback = {
                'p50': float(np.percentile(arr, 50)),
                'p75': float(np.percentile(arr, 75)),
                'p85': float(np.percentile(arr, 85)),
                'p95': float(np.percentile(arr, 95)),
                'mean': float(np.mean(arr))
            }
            for k, v in fallback.items():
                if k not in stats or pd.isna(stats.get(k)):
                    stats[k] = v
            if 'p85' not in stats or pd.isna(stats.get('p85')):
                stats['p85'] = fallback['p85']

    return {k: float(v) for k, v in stats.items() if v is not None and not pd.isna(v)}

# Callback para a aba 'Análise Dimensional'
@app.callback(
    [Output('graph-dimensional-throughput', 'figure'),
     Output('graph-dimensional-defeitos', 'figure')],
    [Input('dropdown-dimensional', 'value'),
     Input('filtro-projeto', 'value')]
)
def update_dimensional_graphs(selected_dimension, selected_project):
    df_dim = dfs.get('Análise Dimensional')
    if df_dim is None or df_dim.empty:
        return {}, {}

    # Filtra pela dimensão e projeto
    df_filtered = df_dim[df_dim['Dimensão'] == selected_dimension]
    
    # O campo 'Categoria' pode conter o projeto, então filtramos por ele
    # Ex: "W1NNER - João" ou apenas "W1NNER"
    if selected_dimension != 'Por Projeto':
        df_filtered = df_filtered[df_filtered['Categoria'].str.startswith(selected_project)]

    # Gráfico de Throughput
    fig_throughput = px.bar(df_filtered, x='Categoria', y='Throughput',
                            title=f'Throughput por {selected_dimension} em {selected_project}',
                            labels={'Categoria': selected_dimension, 'Throughput': 'Itens Concluídos'})
    fig_throughput.update_layout(height=480, xaxis_tickangle=-45, margin=dict(b=120))

    # Gráfico de Taxa de Defeitos
    fig_defeitos = px.bar(df_filtered, x='Categoria', y='Taxa_Defeitos',
                          title=f'Taxa de Defeitos (%) por {selected_dimension} em {selected_project}',
                          labels={'Categoria': selected_dimension, 'Taxa_Defeitos': 'Taxa de Defeitos (%)'})
    fig_defeitos.update_layout(height=480, xaxis_tickangle=-45, margin=dict(b=120))

    return fig_throughput, fig_defeitos

# Callback para a aba 'Tendências'
@app.callback(
    [Output('graph-tendencias-throughput', 'figure'),
     Output('graph-tendencias-wip-leadtime', 'figure')],
    [Input('tabs-main', 'value'), # Para garantir que só rode quando a aba estiver ativa
     Input('filtro-projeto', 'value')]
)
def update_tendencias_graphs(active_tab, selected_project):
    if active_tab != 'tab-8-tendencias':
        return {}, {}

    df_trends = dfs.get('Tendências')
    if df_trends is None or df_trends.empty:
        return {}, {}

    df_filtered = df_trends[df_trends['Projeto'] == selected_project]

    # Gráfico de Throughput
    fig_throughput = px.line(df_filtered, x='Semana', y=['Throughput Semanal', 'Throughput Médio (4s)'],
                             title=f'Tendência de Throughput para {selected_project}',
                             labels={'value': 'Quantidade', 'Semana': 'Semana'},
                             markers=True)
    fig_throughput.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=120))

    # Gráfico de WIP e Lead Time
    fig_wip_lt = px.line(df_filtered, x='Semana', y=['WIP Médio (4s)', 'Lead Time Médio (4s)'],
                         title=f'Tendência de WIP e Lead Time para {selected_project}',
                         labels={'value': 'Valor', 'Semana': 'Semana'},
                         markers=True)
    fig_wip_lt.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=120))

    return fig_throughput, fig_wip_lt

# Callback para a aba 'Throughput por Tipo'
@app.callback(
    Output('graph-throughput-tipo-trend', 'figure'),
    [Input('dropdown-throughput-tipo', 'value'),
     Input('filtro-projeto', 'value')]
)
def update_throughput_tipo_graphs(selected_type, selected_project):
    df_full = dfs.get('Throughput por Tipo')
    if df_full is None or df_full.empty or not selected_type:
        return {}

    df_filtered = df_full[(df_full['Projeto'] == selected_project) & (df_full['Tipo Item'] == selected_type)]

    fig_trend = px.line(df_filtered, x='Semana', y=['Throughput', 'P85 Lead Time (dias)', 'Eficiência'],
                        title=f'Tendências para o tipo "{selected_type}" em {selected_project}',
                        labels={'value': 'Valor', 'variable': 'Métrica'},
                        markers=True)
    fig_trend.update_layout(hovermode="x unified", height=550, xaxis_tickangle=-45, margin=dict(b=120))

    return fig_trend

# Callback para a aba 'WIP por Pessoa'
@app.callback(
    Output('graph-wip-pessoa-ranking', 'figure'),
    Input('filtro-projeto', 'value')
)
def update_wip_pessoa_graph(selected_project):
    df_wip = dfs.get('WIP por Pessoa')
    if df_wip is None or df_wip.empty:
        return {}
    
    df_filtered = df_wip[df_wip['Projeto'] == selected_project]
    
    # Agrupar por responsável para obter o WIP médio do período completo exibido
    df_agg = df_filtered.groupby('Responsável')['WIP_Médio'].mean().reset_index().sort_values('WIP_Médio', ascending=False).head(20)

    fig = px.bar(df_agg, x='Responsável', y='WIP_Médio', title=f'Ranking de WIP Médio por Pessoa (Top 20) em {selected_project}')
    fig.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=120))
    return fig

# Callback para a aba 'Análise Tipos'
@app.callback(
    [Output('graph-tipos-distribuicao', 'figure'),
     Output('graph-tipos-leadtime', 'figure')],
    Input('filtro-projeto', 'value')
)
def update_analise_tipos_graphs(selected_project):
    df_tipos = dfs.get('Análise Tipos')
    if df_tipos is None or df_tipos.empty:
        return {}, {}

    df_filtered = df_tipos[df_tipos['Projeto'] == selected_project]
    
    # Para o gráfico de pizza, pegar apenas as categorias principais (não subtipos que começam com espaços)
    df_main_types = df_filtered[~df_filtered['Tipo'].str.strip().str.startswith(('  '))]

    fig_pie = px.pie(df_main_types, names='Tipo', values='Throughput', title=f'Distribuição de Throughput por Tipo em {selected_project}')
    fig_pie.update_layout(height=480)
    fig_bar = px.bar(df_filtered, x='Tipo', y='Lead Time Médio (dias)', color='Tipo', title=f'Lead Time Médio por Tipo/Subtipo em {selected_project}')
    fig_bar.update_layout(height=480, xaxis_tickangle=-45, margin=dict(b=120))
    return fig_pie, fig_bar

# Callback para a aba 'Lead Time'
@app.callback(
    [Output('graph-leadtime-distribution', 'figure'),
     Output('graph-leadtime-trend', 'figure')],
    [Input('tabs-main', 'value'),
     Input('filtro-projeto', 'value')]
)
def update_lead_time_graphs(active_tab, selected_project):
    if active_tab != 'tab-13-lead-time' or not selected_project:
        return {}, {}

    ref_lines = {
        'p50': ('P50', '#27AE60', 'dash'),
        'p75': ('P75', '#2D9CDB', 'dash'),
        'p85': ('P85', '#9B51E0', 'dash'),
        'p95': ('P95', '#EB5757', 'dash'),
        'mean': ('Média', '#333333', 'dot'),
    }

    df_eff = dfs.get('Análise Eficiência')
    if df_eff is None or df_eff.empty or 'Projeto' not in df_eff.columns or 'Lead Time (dias)' not in df_eff.columns:
        return _empty_figure("Dados de Análise Eficiência não encontrados."), _empty_figure("Dados de tendência indisponíveis.")

    df_eff_proj = df_eff[df_eff['Projeto'] == selected_project].copy()
    df_eff_proj['Lead Time (dias)'] = pd.to_numeric(df_eff_proj['Lead Time (dias)'], errors='coerce')
    lead_values = df_eff_proj['Lead Time (dias)'].dropna()
    lead_values = lead_values[lead_values >= 0]

    if lead_values.empty:
        fig_dist = _empty_figure(f"Sem valores válidos de Lead Time para {selected_project}.")
    else:
        freq = lead_values.round().astype(int).value_counts().sort_index().reset_index()
        freq.columns = ['LeadTimeDia', 'Frequencia']
        freq['CumulativoPct'] = (freq['Frequencia'].cumsum() / freq['Frequencia'].sum()) * 100
        stats = _lead_time_reference_stats(selected_project, lead_values.values)

        fig_dist = make_subplots(specs=[[{'secondary_y': True}]])
        fig_dist.add_trace(
            go.Bar(
                x=freq['LeadTimeDia'],
                y=freq['Frequencia'],
                name='Frequência',
                marker_color='#2F80ED'
            ),
            secondary_y=False
        )
        fig_dist.add_trace(
            go.Scatter(
                x=freq['LeadTimeDia'],
                y=freq['CumulativoPct'],
                mode='lines',
                name='Cumulativo %',
                line=dict(color='#F2994A', width=3)
            ),
            secondary_y=True
        )

        for key, (label, color, dash_style) in ref_lines.items():
            value = stats.get(key)
            if value is None:
                continue
            fig_dist.add_vline(
                x=value,
                line_color=color,
                line_dash=dash_style,
                line_width=1.5,
                annotation_text=f'{label}: {value:.1f}',
                annotation_position='top'
            )

        fig_dist.update_layout(
            title=f'Distribuição de Lead Time + Curva Acumulada ({selected_project})',
            template='plotly_white',
            hovermode='x unified',
            legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center'),
            margin=dict(t=70, b=110, l=60, r=60)
        )
        fig_dist.update_xaxes(title_text='Lead Time (dias)')
        fig_dist.update_yaxes(title_text='Frequência (# itens)', secondary_y=False)
        fig_dist.update_yaxes(title_text='Cumulativo (%)', range=[0, 100], secondary_y=True)

    df_trend = dfs.get('Tendências Completas')
    if df_trend is None or df_trend.empty or 'Projeto' not in df_trend.columns:
        fig_trend = _empty_figure("Dados de Tendências Completas não encontrados.")
    else:
        df_trend_proj = df_trend[df_trend['Projeto'] == selected_project].copy()
        if df_trend_proj.empty or 'Semana' not in df_trend_proj.columns:
            fig_trend = _empty_figure(f"Sem tendência de Lead Time para {selected_project}.")
        else:
            df_trend_proj['Semana'] = pd.to_datetime(df_trend_proj['Semana'], errors='coerce')
            df_trend_proj['Lead Time'] = pd.to_numeric(df_trend_proj.get('Lead Time'), errors='coerce')
            df_trend_proj['Lead Time Médio (4s)'] = pd.to_numeric(df_trend_proj.get('Lead Time Médio (4s)'), errors='coerce')
            df_trend_proj = df_trend_proj.dropna(subset=['Semana']).sort_values('Semana')

            if df_trend_proj[['Lead Time', 'Lead Time Médio (4s)']].dropna(how='all').empty:
                fig_trend = _empty_figure(f"Sem série temporal de Lead Time para {selected_project}.")
            else:
                stats = _lead_time_reference_stats(
                    selected_project,
                    lead_values.values if not lead_values.empty else None
                )
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=df_trend_proj['Semana'],
                    y=df_trend_proj['Lead Time'],
                    mode='lines+markers',
                    name='Lead Time (semanal)',
                    line=dict(color='#2F80ED', width=2),
                    marker=dict(size=7)
                ))
                fig_trend.add_trace(go.Scatter(
                    x=df_trend_proj['Semana'],
                    y=df_trend_proj['Lead Time Médio (4s)'],
                    mode='lines',
                    name='Média móvel (4s)',
                    line=dict(color='#F2994A', width=3, dash='dash')
                ))

                for key, (label, color, dash_style) in ref_lines.items():
                    value = stats.get(key)
                    if value is None:
                        continue
                    fig_trend.add_hline(
                        y=value,
                        line_color=color,
                        line_dash=dash_style,
                        line_width=1.2,
                        annotation_text=f'{label}: {value:.1f}',
                        annotation_position='top right'
                    )

                fig_trend.update_layout(
                    title=f'Tendência de Lead Time (média semanal + média móvel) - {selected_project}',
                    template='plotly_white',
                    hovermode='x unified',
                    legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center'),
                    margin=dict(t=70, b=110, l=60, r=40)
                )
                fig_trend.update_xaxes(title_text='Semana', tickformat='%d/%m/%Y', tickangle=-45)
                fig_trend.update_yaxes(title_text='Lead Time (dias)')

    return fig_dist, fig_trend

# --- 6. EXECUÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    app.run(debug=True)
